# 5 分钟体验：从零跑通 hso

> 当前能跑通的端到端形态：**研究方向 → 检索 Q2+ 论文 → LLM 总结章节写作惯例 → 结合实验数据起草完整 Elsevier LaTeX 项目目录**。

## 0. 准备

一次性：

```bash
cd /Users/edward/Documents/hso
uv sync --extra dev
```

## 1. 登录 ChatGPT（用 OAuth，免 API 费）

```bash
uv run hso login
```

会弹浏览器到 OpenAI auth 页面，登录你的 ChatGPT 账号 → token 写入 `~/.config/hso/auth.json`。

> **替代方案**：在仓库根目录创建 `.env`，用 `LLM_PROVIDER` 选择后端。
> 默认 `gpt` 使用 `OPENAI_API_KEY` / `OPENAI_BASE_URL` 走 Responses API；
> 可切 `deepseek` / `custom` / `xai` 接 OpenAI-compatible Chat Completions
> endpoint，也可切 `oauth` 使用 `hso login` 写入的个人 ChatGPT token。

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

不传 `--auth-mode`：按 `.env` 的 `LLM_PROVIDER` 选择。手动指定：

```bash
uv run hso analyze ... --auth-mode gpt --model gpt-5.4-mini
uv run hso analyze ... --auth-mode deepseek --model deepseek-v4-flash
uv run hso analyze ... --auth-mode custom --model local-model
uv run hso analyze ... --auth-mode oauth --model gpt-5.2
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

## 5. 准备实验数据

实验数据 JSON 与 `Experiment` schema 对齐即可。可以先用内置 fixture 体验：

```bash
cp tests/fixtures/experiment.json output/demo/experiment.json
```

## 6. 起草完整 LaTeX 项目

```bash
uv run hso draft \
  --profile output/demo/profile.json \
  --experiment output/demo/experiment.json \
  --papers output/demo/papers.json \
  --out output/demo/draft
```

输出目录包含：

| 文件/目录 | 说明 |
|---|---|
| `main.tex` | Elsevier `elsarticle.cls` 主文件 |
| `refs.bib` | 从检索论文生成的 BibTeX |
| `tables/` | 从实验 results 生成的 LaTeX 表格 |
| `figs/` | 从时序数据生成的 PDF 图 |

如本机装了 `latexmk` 或 `tectonic`，可直接尝试编译：

```bash
uv run hso draft \
  --profile output/demo/profile.json \
  --experiment output/demo/experiment.json \
  --papers output/demo/papers.json \
  --out output/demo/draft \
  --compile
```

## 想看底层 utility 怎么用？

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
