"""Typer CLI 入口：search / analyze / login / logout / whoami。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

import typer
import uvicorn
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from hso.config import Settings, load_settings
from hso.literature import (
    ArxivProvider,
    JCRFilter,
    SearchAggregator,
    SemanticScholarProvider,
)
from hso.llm import LLMClient, clear_auth, load_auth, login, refresh_and_save
from hso.manuscript import DraftPipeline, ExperimentLoader, LatexCompiler
from hso.models import Paper, SearchQuery, SectionProfile
from hso.synthesis import SectionProfileBuilder

app = typer.Typer(help="Manuscript Agent CLI", no_args_is_help=True)
console = Console()


def _setup_logging(verbose: bool) -> None:
    """配置 rich logging。"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


def _build_aggregator(jcr_path: Path | None, s2_api_key: str) -> SearchAggregator:
    """根据是否提供 JCR JSON 装配 aggregator。"""
    providers = [ArxivProvider(), SemanticScholarProvider(api_key=s2_api_key)]
    jcr_filter: JCRFilter | None = None
    if jcr_path is not None and jcr_path.exists():
        jcr_filter = JCRFilter.from_json(jcr_path)
    return SearchAggregator(providers=providers, jcr_filter=jcr_filter)


def _papers_to_jsonable(papers: list[Paper]) -> list[dict[str, Any]]:
    """把 Paper 列表序列化为可写 JSON 的 dict（处理 date / pydantic）。"""
    return [json.loads(p.model_dump_json()) for p in papers]


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="研究方向，如 'diffusion model image editing'")],
    years: Annotated[int, typer.Option(help="近 N 年")] = 2,
    max_zone: Annotated[int, typer.Option("--max-zone", help="中科院分区上限（1-4，越小越严）")] = 2,
    top_k: Annotated[int, typer.Option(help="单 provider 候选上限")] = 30,
    require_q_zone: Annotated[
        bool, typer.Option("--require-q-zone/--allow-preprint", help="是否强制 JCR 命中")
    ] = True,
    jcr: Annotated[
        Path | None, typer.Option(help="ShowJCR 风格 JSON 路径；不传则 data/jcr/jcr.json")
    ] = None,
    out: Annotated[Path | None, typer.Option(help="输出 JSON 路径；不传则只打印表格")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose")] = False,
) -> None:
    """检索近 N 年中科院 max_zone 区及以上论文。"""
    _setup_logging(verbose)
    settings = load_settings()
    jcr_path = jcr or (settings.data_dir / "jcr" / "jcr.json")
    aggregator = _build_aggregator(jcr_path, settings.s2_api_key)

    sq = SearchQuery(
        query=query,
        years=years,
        max_zone=max_zone,
        top_k_per_provider=top_k,
        require_q_zone=require_q_zone,
    )
    papers = aggregator.search(sq)

    _print_papers(papers)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {"query": query, "max_zone": max_zone, "papers": _papers_to_jsonable(papers)},
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        console.print(f"\n[green]已写入[/green] {out}")


def _build_llm(
    settings: Settings,
    auth_mode: str,
    model_override: str | None = None,
) -> LLMClient:
    """根据 auth_mode/provider 装配 LLMClient。

    - ``auto``：使用 ``LLM_PROVIDER`` / ``HSO_LLM_PROVIDER`` 选择 provider
    - ``oauth``：强制 OAuth（未登录抛错）
    - ``gpt``：强制 OpenAI Responses API provider
    - ``deepseek`` / ``custom`` / ``xai`` / ``legacy``：强制 Chat Completions 兼容 provider
    - ``api_key``：兼容旧参数，等同 legacy
    """
    if auth_mode == "auto":
        backend = settings.active_llm_backend()
    elif auth_mode == "api_key":
        backend = settings.model_copy(update={"llm_provider": "legacy"}).active_llm_backend()
    elif auth_mode in ("deepseek", "custom", "oauth", "legacy", "gpt", "xai"):
        backend = settings.model_copy(update={"llm_provider": auth_mode}).active_llm_backend()
    else:
        console.print(
            "[red]未知 auth/provider。可用值：auto / gpt / deepseek / custom / xai / oauth / legacy / api_key。[/red]"
        )
        raise typer.Exit(code=2)

    model = model_override or backend.model
    if backend.auth_mode == "oauth":
        console.print(f"[cyan]使用 OAuth (ChatGPT 订阅)[/cyan] · model={model}")
        return LLMClient(
            auth_mode="oauth",
            model=model,
            timeout=settings.llm_timeout,
            cache_dir=settings.cache_dir / "llm",
        )

    if not backend.api_key:
        console.print(
            f"[red]provider={backend.provider} 但 API key 未设置。请配置 .env，或切换 provider。[/red]"
        )
        raise typer.Exit(code=2)
    console.print(f"[cyan]使用 {backend.provider} API key[/cyan] · model={model}")
    return LLMClient(
        api_key=backend.api_key,
        base_url=backend.base_url,
        model=model,
        timeout=settings.llm_timeout,
        cache_dir=settings.cache_dir / "llm",
        api_surface=backend.api_surface,
    )


@app.command()
def analyze(
    input_path: Annotated[Path, typer.Option("--input", "-i", help="search 命令输出的 JSON")],
    out: Annotated[Path, typer.Option("--out", "-o", help="SectionProfile JSON 输出路径")],
    auth_mode: Annotated[
        str,
        typer.Option(
            "--auth-mode",
            help="auto / gpt / deepseek / custom / xai / oauth / legacy / api_key。auto 使用 LLM_PROVIDER",
        ),
    ] = "auto",
    model: Annotated[
        str | None,
        typer.Option(help="覆盖默认模型；GPT 默认 gpt-5.4-mini，OAuth 默认 gpt-5.2"),
    ] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose")] = False,
) -> None:
    """基于 search 结果生成章节结构 profile。"""
    _setup_logging(verbose)
    settings = load_settings()
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    papers = [Paper.model_validate(p) for p in payload.get("papers", [])]
    if not papers:
        console.print("[yellow]输入文件没有论文，跳过。[/yellow]")
        raise typer.Exit(code=1)

    llm = _build_llm(settings, auth_mode=auth_mode, model_override=model)
    builder = SectionProfileBuilder(llm)
    profile = builder.build(payload.get("query", ""), papers, max_zone=payload.get("max_zone", 2))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"[green]SectionProfile 已生成[/green] → {out}")
    console.print(f"  涉及论文数：{profile.n_papers}")
    console.print(f"  归纳章节数：{len(profile.sections)}")


@app.command()
def draft(
    profile: Annotated[Path, typer.Option("--profile", help="SectionProfile JSON 路径")],
    experiment: Annotated[Path, typer.Option("--experiment", help="Experiment JSON 路径")],
    papers: Annotated[Path, typer.Option("--papers", help="search 命令输出的 JSON 路径")],
    out: Annotated[Path, typer.Option("--out", "-o", help="输出 LaTeX 项目目录")],
    auth_mode: Annotated[
        str,
        typer.Option(
            "--auth-mode",
            help="auto / gpt / deepseek / custom / xai / oauth / legacy / api_key。auto 使用 LLM_PROVIDER",
        ),
    ] = "auto",
    model: Annotated[
        str | None,
        typer.Option(help="覆盖默认模型；GPT 默认 gpt-5.4-mini，OAuth 默认 gpt-5.2"),
    ] = None,
    journal: Annotated[str, typer.Option(help="Elsevier 模板中的 journal 名称")] = "Journal Name",
    compile_pdf: Annotated[
        bool,
        typer.Option("--compile/--no-compile", help="生成后是否尝试调用 latexmk/tectonic 编译 PDF"),
    ] = False,
    verbose: Annotated[bool, typer.Option("-v", "--verbose")] = False,
) -> None:
    """从 profile / experiment / papers 端到端起草 manuscript LaTeX 项目。"""
    _setup_logging(verbose)
    settings = load_settings()
    section_profile = SectionProfile.model_validate_json(profile.read_text(encoding="utf-8"))
    experiment_data = ExperimentLoader.from_json(experiment)
    candidate_papers = _load_papers_from_search(papers)

    llm = _build_llm(settings, auth_mode=auth_mode, model_override=model)
    result = DraftPipeline(llm).run(
        section_profile=section_profile,
        experiment=experiment_data,
        papers=candidate_papers,
        output_dir=out,
        journal=journal,
    )

    console.print(f"[green]Manuscript project 已生成[/green] → {result.assembly.output_dir}")
    console.print(f"  main.tex: {result.assembly.main_tex_path}")
    console.print(f"  refs.bib: {result.assembly.refs_bib_path}")
    console.print(f"  sections: {len(result.drafted_sections)}")
    if result.assembly.unresolved_citations:
        console.print(
            "[yellow]未解析 citations:[/yellow] "
            + ", ".join(result.assembly.unresolved_citations)
        )
    if result.assembly.missing_artifacts:
        console.print(
            "[yellow]缺失 artifacts:[/yellow] " + ", ".join(result.assembly.missing_artifacts)
        )

    if compile_pdf:
        compile_result = LatexCompiler().compile(result.assembly.main_tex_path)
        if compile_result.success:
            console.print(f"[green]PDF 编译成功[/green] → {compile_result.pdf_path}")
        else:
            console.print(f"[red]PDF 编译失败[/red] {compile_result.error_summary}")
            raise typer.Exit(code=3)


@app.command()
def start(
    host: Annotated[str, typer.Option(help="Gateway 监听地址")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Gateway 监听端口")] = 8765,
    reload: Annotated[bool, typer.Option("--reload/--no-reload", help="是否开启开发热重载")] = False,
) -> None:
    """启动 hso Python gateway，供 Web UI / CLI 控制面连接。"""
    console.print(f"[cyan]hso gateway[/cyan] listening on http://{host}:{port}")
    uvicorn.run(
        "hso.gateway.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def status(
    host: Annotated[str, typer.Option(help="Gateway 地址")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Gateway 端口")] = 8765,
) -> None:
    """打印本地 gateway 的健康检查地址。"""
    console.print(f"hso gateway health: http://{host}:{port}/api/health")


@app.command(name="login")
def login_cmd(
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open-browser/--no-open-browser", help="是否自动打开浏览器（headless 时关掉）"
        ),
    ] = True,
    timeout: Annotated[int, typer.Option(help="等浏览器回调的超时秒数")] = 300,
) -> None:
    """通过 OAuth 登录 ChatGPT 账户，token 存入 ~/.config/hso/auth.json。

    [yellow]注意：本流程复用 OpenAI Codex CLI 的 client_id；这是反向工程做法，
    OpenAI 一旦修改 auth check 即失效。请仅用于个人项目。[/yellow]
    """
    _setup_logging(False)
    console.print(
        "[yellow]⚠️  即将复用 OpenAI Codex CLI 的 OAuth client_id。OpenAI 没有官方授权第三方"
        "应用走 ChatGPT 订阅配额，本流程在 OpenAI 调整 auth check 后可能失效。[/yellow]"
    )
    try:
        auth = login(open_browser=open_browser, timeout_seconds=timeout)
    except TimeoutError as e:
        console.print(f"[red]登录超时：{e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]登录失败：{e}[/red]")
        raise typer.Exit(code=2) from e

    console.print(
        f"[green]登录成功[/green] account_id={auth.account_id} expires_at={auth.expires_at.isoformat()}"
    )


@app.command(name="logout")
def logout_cmd() -> None:
    """删除本地 OAuth token。"""
    if clear_auth():
        console.print("[green]已登出，token 已删除。[/green]")
    else:
        console.print("[yellow]当前未登录。[/yellow]")


@app.command(name="whoami")
def whoami_cmd() -> None:
    """显示当前 OAuth 登录状态；过期时尝试 refresh。"""
    auth = load_auth()
    if auth is None:
        console.print("[yellow]未登录。[/yellow]运行 `hso login` 登录。")
        raise typer.Exit(code=1)
    console.print(f"account_id: [cyan]{auth.account_id}[/cyan]")
    console.print(f"expires_at: {auth.expires_at.isoformat()}")
    console.print(f"last_refresh: {auth.last_refresh.isoformat()}")
    if auth.is_access_expired():
        console.print("[yellow]access_token 已过期，尝试 refresh...[/yellow]")
        try:
            refreshed = refresh_and_save(auth)
            console.print(
                f"[green]已 refresh[/green] new expires_at={refreshed.expires_at.isoformat()}"
            )
        except Exception as e:
            console.print(f"[red]refresh 失败：{e}；请重新登录。[/red]")


def _load_papers_from_search(path: Path) -> list[Paper]:
    """读取 search 命令输出，兼容顶层 list 或包含 papers 字段的对象。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_papers = payload.get("papers", []) if isinstance(payload, dict) else payload
    return [Paper.model_validate(p) for p in raw_papers]


def _print_papers(papers: list[Paper]) -> None:
    """用 rich 打印检索结果。"""
    if not papers:
        console.print("[yellow]没有命中。[/yellow]")
        return
    table = Table(title=f"Search results — {len(papers)} papers")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Zone", width=6)
    table.add_column("Year", width=4)
    table.add_column("Venue", width=24, overflow="fold")
    table.add_column("Title", overflow="fold")
    table.add_column("Source", width=12)
    for i, p in enumerate(papers, 1):
        table.add_row(
            str(i),
            f"Q{p.jcr_zone}" if p.jcr_zone else "—",
            str(p.published_at.year) if p.published_at else "—",
            (p.venue.name if p.venue else "—")[:40],
            p.title[:120],
            p.source,
        )
    console.print(table)


if __name__ == "__main__":
    app()
