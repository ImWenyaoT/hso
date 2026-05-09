# 5 分钟体验：从零跑通 hso

> 当前能跑通的端到端形态：**研究方向 → 检索 Q2+ 论文 → LLM 总结这些论文的章节写作惯例 → 输出 SectionProfile JSON**。
>
> 起草成完整 .tex（Phase 2.3）还没串成 CLI，但基础设施都在了。下面 demo 走 Phase 1 + Phase 2.1/2.2 的 LLM 部分。

## 0. 准备

一次性：

```bash
cd ~/Desktop/kendrick_lamar
uv sync --extra dev
```

## 1. 登录 ChatGPT（用 OAuth，免 API 费）

```bash
uv run hso login
```

会弹浏览器到 OpenAI auth 页面，登录你的 ChatGPT 账号 → token 写入 `~/.config/hso/auth.json`。

> **替代方案**：填 `HSO_LLM_API_KEY` 进 `.env` 用 API key（按 token 计费走自己 OpenAI 账户）。

```bash
uv run hso whoami       # 看登录状态
uv run hso logout       # 删 token
```

## 2. 检索某个方向的近 2 年论文

```bash
uv run hso search "diffusion model image editing" \
  --years 2 \
  --top-k 10 \
  --allow-preprint \
  --out output/demo/papers.json
```

输出会同时打印一张 rich 表格 + 写入 `papers.json`。

> 想强制只要中科院 Q1/Q2：去掉 `--allow-preprint`，并把 [hitfyd/ShowJCR](https://github.com/hitfyd/ShowJCR) 的 JSON 放到 `data/jcr/jcr.json`。

## 3. LLM 分析这些论文的写作惯例

```bash
uv run hso analyze \
  --input output/demo/papers.json \
  --out output/demo/profile.json
```

不传 `--auth-mode`：自动检测 OAuth token，有就用 ChatGPT 订阅；没有 fallback 到 API key。手动指定：

```bash
uv run hso analyze ... --auth-mode oauth --model gpt-5.2
uv run hso analyze ... --auth-mode api_key --model gpt-4o-mini
```

输出 `profile.json`：每个章节（intro / related_work / method / experiment / conclusion）一份"这个领域大家都怎么写"的结构化总结，包括：
- `common_subtopics`：常展开的子话题
- `typical_opening`：开篇套路
- `underexplored`：少被讨论但你的工作可以贡献的角度
- `recommended_artifacts`：推荐图表
- `evidence_paper_ids`：支撑此归纳的论文 id

## 4. 看产物

```bash
cat output/demo/profile.json | uv run python -m json.tool | head -50
```

或在 IDE 里打开 [output/demo/profile.json](../output/demo/profile.json)。

## 现在还没做完的（Phase 2.3）

下面这些代码都写好了，但还没接进 CLI：

| 模块 | 现状 |
|---|---|
| ExperimentLoader | 能从 JSON/CSV 加载实验数据 |
| ElsevierTemplate | 能渲染 elsarticle.cls 主文件 |
| `results_to_latex_table` | 能生成 booktabs 表格 |
| `render_timeseries_figure` | 能输出 matplotlib PDF |
| OutlineBuilder | 能基于 SectionProfile + Experiment 生成大纲（OAuth/api_key 都通） |
| SectionDrafter | 能逐章起草正文（带 \cite 占位） |
| `papers_to_bib_entries` | 能生成 .bib + cite key 解析 |

**还差**：把这些串成 `hso draft --profile profile.json --experiment exp.json --papers papers.json --out output/draft/` 一条 CLI 命令，输出可编译的 LaTeX 项目目录。

## 想看 Phase 2.1 已有能力的 demo？

```bash
uv run python <<'EOF'
from pathlib import Path
from hso.manuscript import (
    ExperimentLoader, ElsevierTemplate, ManuscriptSection,
    results_to_latex_table, render_timeseries_figure,
)
from hso.manuscript.template import (
    Affiliation, ManuscriptDocument, TemplateAuthor,
)

# 用 fixture 的实验数据
exp = ExperimentLoader.from_json(Path("tests/fixtures/experiment.json"))

# 生成主结果表（FID/LPIPS 越小越好，CLIP-Score 越大越好）
table_tex = results_to_latex_table(
    exp.results,
    caption="Main results on CelebA-HQ.",
    label="main",
    metrics=["FID", "LPIPS", "CLIP-Score"],
    directions={"FID": "min", "LPIPS": "min", "CLIP-Score": "max"},
)

# 生成训练曲线 PDF
out_dir = Path("output/demo")
fig_path = render_timeseries_figure(
    exp.timeseries, out_dir / "figs" / "train_loss.pdf",
    series_name="train_loss", title="Training Loss",
)

# 装配成完整 .tex
doc = ManuscriptDocument(
    title=exp.title,
    authors=[TemplateAuthor(name="Author One", affiliation_id="a")],
    affiliations=[Affiliation(id="a", organization="Test Lab", country="China")],
    abstract=exp.abstract or "TBD",
    keywords=exp.keywords,
    sections=[
        ManuscriptSection(id="intro", title="Introduction", body="TBD."),
        ManuscriptSection(id="exp", title="Experiments", body=table_tex),
    ],
)
ElsevierTemplate().render_to_file(doc, out_dir / "main.tex")
print("生成完毕：", out_dir / "main.tex", "+", fig_path)
EOF
```

跑完 `output/demo/main.tex` 是一份合法 Elsevier 模板。装了 `latexmk` 的话：

```bash
cd output/demo && latexmk -pdf main.tex
```
