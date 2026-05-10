# hso — the haiku, the sonnet and the opus

> AI agent for drafting Elsevier-format LaTeX manuscripts from your experiments.

`hso` 取名来自 Anthropic Claude 三个模型层级（Haiku / Sonnet / Opus），暗合"短句 → 节诗 → 长篇"的写作进化路径。但实际跑在 **OpenAI Agents SDK + ChatGPT 订阅配额** 上 —— 是的，名字是 Anthropic，引擎是 OpenAI。

## 它是什么

一个学术写作 AI agent。给它你的研究方向和实验数据，它会：

1. **检索**：自动搜近 N 年中科院 Q1/Q2 期刊论文（arXiv + Semantic Scholar + ShowJCR 分区过滤）
2. **归纳**：让 LLM 总结这个领域大家**怎么写** —— intro 套路、experiment 章节常用图表、少被讨论的角度
3. **起草**：基于上面的"风格画像" + 你的实验数据，生成 `main.tex` / `refs.bib` / `tables/` / `figs/` 的 Elsevier LaTeX 项目目录
4. **审稿循环**（Phase 3）：另一个 agent 扮 Q1 审稿人发 issues，原 agent 改稿，loop 到收敛

## 现在能跑通的端到端

```bash
uv sync --extra dev

# 1. 登录 ChatGPT（OAuth，免 API 费）
uv run hso login

# 2. 检索方向
uv run hso search "diffusion model image editing" \
  --years 2 --top-k 10 --allow-preprint \
  --out output/demo/papers.json

# 3. LLM 归纳章节惯例
uv run hso analyze \
  --input output/demo/papers.json \
  --out output/demo/profile.json

# 4. 验证 Agents SDK runtime（OAuth backend + 工具调用）
uv run python scripts/agents_smoke.py

# 5. 起草完整 LaTeX 项目目录
cp tests/fixtures/experiment.json output/demo/experiment.json
uv run hso draft \
  --profile output/demo/profile.json \
  --experiment output/demo/experiment.json \
  --papers output/demo/papers.json \
  --out output/demo/draft
```

详见 [docs/quickstart.md](docs/quickstart.md)。

## 双 backend

| Backend | 怎么用 | 适用 |
|---|---|---|
| **OAuth** (复用 ChatGPT Plus) | `hso login` → token 存 `~/.config/hso/auth.json` | 个人项目；想白嫖 ChatGPT 订阅配额 |
| **API key** | `.env` 填 `HSO_LLM_API_KEY` | 工作项目；按 token 计费正规走自己 OpenAI 账户 |

```bash
hso analyze --auth-mode auto      # 默认：检测 OAuth token，没就 fallback 到 API key
hso analyze --auth-mode oauth     # 强制 OAuth
hso analyze --auth-mode api_key   # 强制 API key
```

> ⚠️ **ToS 警告**：OAuth 模式复用 OpenAI Codex CLI 的 `client_id` `app_EMoamEEZ73f0CkXaXp7hrann`，**反向工程做法**，OpenAI 没有官方授权第三方应用走 ChatGPT 订阅配额。OpenAI 一旦修改 auth check / Hydra allow-list 即失效。
>
> 用户账号本身风险低（OAuth scope 是用户主动授权的），但应用可能停止工作。**仅用于个人项目，不要部署给他人使用**。
>
> 合规替代：申请 OpenAI [Sign in with ChatGPT for API](https://platform.openai.com/) 走官方流程。

## 架构

```
┌─────────────── hso/agents/runtime.py ────────────────┐
│  build_runtime(auth_mode=...)                         │
│   → 注入 AsyncOpenAI client（OAuth → ChatGPT 后端）   │
│   → 关 SDK 默认 tracing 上传（防 OAuth token 泄漏）   │
│   → 装配 ModelSettings (store=False / 无 temperature) │
│   → 返回 OpenAIResponsesModel + 默认 settings         │
└──────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        ▼                                ▼
┌────────────────────┐        ┌─────────────────────┐
│  OutlineBuilder    │        │  Drafting Agent     │
│  (Phase 2.2)       │        │  (Phase 2.3)        │
│  Agents SDK +      │        │  Tools: cite_paper  │
│  output_type=      │        │   / insert_table    │
│  Outline           │        │   / insert_figure   │
└────────────────────┘        └─────────────────────┘
                                       │
                                ┌──────┴──────┐
                                ▼             ▼
                       ┌────────────────────────────┐
                       │  Tool Registry             │
                       │  literature/ + synthesis/  │
                       │  + manuscript/             │
                       │  ── 已有的"流水线 utility" │
                       │  全部包成 @function_tool   │
                       └────────────────────────────┘
```

主要技术决策：

- **Python 3.12+ 单一栈**，uv 管理依赖
- **OpenAI Agents SDK** (`openai-agents`) 做 agent loop / tool calling / structured output / sessions
- 不引入 LangGraph / CrewAI / AutoGen
- LLM 后端走 **OpenAI Responses API**；OAuth 模式下走 `chatgpt.com/backend-api/codex`，强制 stream + `store=False` + 无 `temperature` 等 [7 处 ChatGPT 后端怪癖](docs/spec.md#10-oauth-backend)
- **Pydantic v2 schema 一套贯穿** LLM structured output / API request/response / 持久化 / agent tool 参数
- **状态持久化**：`SQLiteSession`（Agents SDK 内置）记 agent 跨 run 上下文

## 模块

| 模块 | 职责 |
|---|---|
| `agents/runtime.py` | OpenAI Agents SDK 配置：注入 OAuth client + 调 ChatGPT 后端的 ModelSettings |
| `models/` | Pydantic schema：`Paper` / `Experiment` / `SectionProfile` / `Outline` / `DraftedSection` / `BibEntry` |
| `llm/` | LLM 抽象层（pre-Agents SDK，逐渐被 agents/ 替代）；OAuth 流程 / token 持久化 |
| `literature/` | `PaperProvider` 抽象 + arXiv / Semantic Scholar 实现 + JCR 分区过滤 + 聚合去重 |
| `synthesis/` | 章节结构归纳（`SectionProfile`） |
| `manuscript/` | Outline / Drafter / Bibliography / LaTeX 模板 / 表格 / 图 |
| `cli.py` | Typer 入口（`hso login` / `search` / `analyze` 等） |

## 阶段路线

1. **Phase 1** ✅ 检索 + 章节结构分析
2. **Phase 2** ✅ Elsevier 模板 + LaTeX 表格 + 时序图 + Outline + Drafter (基础设施层)
3. **Phase 2.5** ✅ OAuth ("Sign in with ChatGPT") 端到端打通
4. **Phase 2.3** ✅ Manuscript 装配 + `hso draft` CLI + 可选 LaTeX 编译
5. **Phase 3** 🚧 重构为真 agent：把 Outline/Drafter 包成 Agents SDK loop + tools；加 ReviewLoopAgent
5. **Phase 4** 装配 + LaTeX 编译 + Web UI（FastAPI + Next.js）

## 测试

```bash
uv run pytest                      # 129 测试，coverage ~80%
uv run ruff check src tests        # lint
uv run python scripts/agents_smoke.py   # Agents SDK + OAuth 端到端
```

## 历史文档

仓库早期规划（实验室 GPU 调度 / 大架构那套）见 [docs/archive/](docs/archive/)，已归档不再 follow。
