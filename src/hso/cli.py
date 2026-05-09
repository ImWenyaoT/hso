"""Typer CLI 入口：search / analyze / login / logout / whoami。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from hso.config import load_settings
from hso.literature import (
    ArxivProvider,
    JCRFilter,
    SearchAggregator,
    SemanticScholarProvider,
)
from hso.llm import LLMClient, clear_auth, load_auth, login, refresh_and_save
from hso.models import Paper, SearchQuery
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


def _papers_to_jsonable(papers: list[Paper]) -> list[dict]:
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
    settings,
    auth_mode: str,
    model_override: str | None = None,
) -> LLMClient:
    """根据 auth_mode 装配 LLMClient。

    - ``auto``：先看 ~/.config/hso/auth.json 是否存在；有就 OAuth，否则 api_key
    - ``oauth``：强制 OAuth（未登录抛错）
    - ``api_key``：强制 API key
    """
    if auth_mode == "auto":
        auth_mode = "oauth" if load_auth() is not None else "api_key"

    if auth_mode == "oauth":
        # OAuth 模式默认走 ChatGPT 后端可用模型；用户可用 --model 覆盖
        model = model_override or "gpt-5.2"
        console.print(
            f"[cyan]使用 OAuth (ChatGPT 订阅)[/cyan] · model={model}"
        )
        return LLMClient(
            auth_mode="oauth",
            model=model,
            timeout=settings.llm_timeout,
            cache_dir=settings.cache_dir / "llm",
        )

    if not settings.llm_api_key:
        console.print(
            "[red]auth_mode=api_key 但 HSO_LLM_API_KEY 未设置。请配置 .env，或先 `hso login`。[/red]"
        )
        raise typer.Exit(code=2)
    model = model_override or settings.llm_model
    console.print(f"[cyan]使用 API key[/cyan] · model={model}")
    return LLMClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=model,
        timeout=settings.llm_timeout,
        cache_dir=settings.cache_dir / "llm",
    )


@app.command()
def analyze(
    input_path: Annotated[Path, typer.Option("--input", "-i", help="search 命令输出的 JSON")],
    out: Annotated[Path, typer.Option("--out", "-o", help="SectionProfile JSON 输出路径")],
    auth_mode: Annotated[
        str,
        typer.Option(
            "--auth-mode",
            help="auto / oauth / api_key。auto 优先用 OAuth（如已登录），否则 fallback 到 API key",
        ),
    ] = "auto",
    model: Annotated[
        str | None,
        typer.Option(help="覆盖默认模型；OAuth 默认 gpt-5.2，api_key 默认 settings 中的值"),
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
