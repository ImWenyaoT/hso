# hso — 项目 Spec

> 版本：v0.2（2026-05-10）
> 当前阶段：Phase 2.3 已实现

## 1. 目标

构建一个 AI agent，帮助用户根据自己的实验内容产出一篇符合 **Elsevier `elsarticle.cls`** 模板的 LaTeX manuscript。

## 2. 形态

- **CLI 优先**：`hso` 命令行（typer + rich）
- **Web 后续做**：FastAPI + 简单前端，包装相同的核心 pipeline
- **不做 desktop app**

## 3. 技术栈（决策已固定）

| 维度 | 选型 |
|---|---|
| 语言 | Python 3.12+ |
| 依赖管理 | uv |
| LLM | **OpenAI Responses API**（`responses.parse(text_format=PydanticModel)`）。仅 OpenAI / Azure OpenAI 原生支持。两种 backend：API key（默认）/ OAuth 复用 Codex 协议（见 §10） |
| 编排 | 显式 pipeline + 状态机；**不引入 LangGraph / CrewAI / AutoGen** |
| schema | Pydantic v2 |
| HTTP | httpx（trust_env 默认开，测试场景显式关） |
| 重试 | tenacity（reraise=True 避免 RetryError 包裹） |
| CLI | typer + rich |
| 测试 | pytest + respx + monkeypatch |
| Lint | ruff（中文注释，已 ignore RUF001/002/003） |

## 4. 模块边界

```
src/hso/
├── models/        # Paper / Author / Venue / JCRRecord / SectionProfile / SectionStructure
├── llm/           # OpenAI Responses API 封装：parse() / respond() + 磁盘缓存 + 重试
├── literature/    # PaperProvider 抽象 + arXiv / Semantic Scholar + JCR 过滤 + 聚合去重
├── synthesis/     # LLM 驱动的章节结构归纳（structured output）
├── manuscript/    # Outline / Drafter / Assembler / LaTeX 编译 / 模板与图表
├── agents/        # OpenAI Agents SDK runtime 配置
├── config.py      # pydantic-settings：HSO_* 环境变量
└── cli.py         # typer 入口
```

### 4.1 LLM 抽象（`llm/client.py`）

只暴露两个方法：
- `parse(text_format: type[BaseModel], instructions: str, user_input: str) -> BaseModel`：
  type-safe structured output。直接拿 `response.output_parsed`，无需手工 JSON 校验
- `respond(instructions: str, user_input: str) -> str`：纯文本响应

特性：
- 缓存按 `(instructions, user_input, model, schema_name)` SHA-256 命中，避免重复调用花钱
- 重试限定在 `RateLimitError / APIConnectionError / httpx.HTTPError`，并 `reraise=True`
- `trust_env=False` 选项专用于测试

### 4.2 检索（`literature/`）

- `PaperProvider` 抽象：`search(SearchQuery) -> list[Paper]`
- 实现：`ArxivProvider`（基于 lukasschwab/arxiv.py）、`SemanticScholarProvider`（直连 REST + retry）
- `JCRFilter`：兼容 ShowJCR 中文 JSON 与扁平 list 两种结构；ISSN 优先、名字后备
- `SearchAggregator`：union-find 三级去重（DOI / arXiv id / 标题指纹），高引版本胜出 + 字段补全

### 4.3 章节归纳（`synthesis/section_profile.py`）

- 输入：研究方向 + N 篇 Paper 的 abstract
- 通过 `LLMClient.parse(text_format=_SectionProfileLLM, ...)` 走 Responses API
- LLM schema 与持久化 schema 解耦：`_SectionStructureLLM`（strict 兼容） → `SectionStructure`（业务模型，带 default）

## 5. CLI

```bash
hso search "<query>" --years 2 --max-zone 2 --top-k 30 [--out output/r.json]
hso analyze --input output/r.json --out output/profile.json
hso draft --profile output/profile.json --experiment data/processed/exp.json --papers output/r.json --out output/draft/
```

需要的环境变量见 `.env.example`：
- `HSO_LLM_API_KEY`（必填，调 LLM 时）
- `HSO_LLM_BASE_URL` / `HSO_LLM_MODEL`
- `HSO_S2_API_KEY`（可选，无 key 也能调 Semantic Scholar）

需要的数据：
- `data/jcr/jcr.json`（用户自备 ShowJCR 风格 JSON）

## 6. 边界（明确不做）

- ❌ Agent 自动跑实验（这是 AI-Scientist / AgentLaboratory 的事）
- ❌ 多出版商模板切换（先锁 Elsevier）
- ❌ Google Scholar 爬虫（IP 封禁风险）
- ❌ 直接复制句式（伦理；只模仿章节结构与段落组织）
- ❌ 自动下载非开放 PDF
- ❌ 中文 manuscript（先英文）

## 7. 阶段路线

| 阶段 | 目标 | 状态 |
|---|---|---|
| **Phase 1** | 检索 + 章节结构分析 | ✅ 完成 2026-05-09 |
| **Phase 2** | Elsevier 模板填充器；用户实验数据 (CSV/JSON) → LaTeX 表格/图（matplotlib）；产出 LaTeX 项目目录 | ✅ 完成 2.1/2.2/2.3 |
| **Phase 3** | 模拟审稿 loop：参考 AgentReview，硬上限 N 轮 + 收敛判定 | 待开始 |
| **Phase 4** | Web UI（FastAPI + 简单前端） | 待开始 |

## 8. 风险与控制

| 风险 | 控制 |
|---|---|
| 引用幻觉 | 所有 citation 必须绑定 DOI/arXiv/S2 id；Phase 2 强制 evidence grounding |
| 数据造假 | 实验图表只能从用户文件或可执行脚本生成 |
| 审稿 loop 不收敛 | Phase 3 设硬上限 + reviewer 分数阈值 |
| ShowJCR 2026 起停更 | 数据版本锁定 + 优雅降级（无分区不剔除而标 unranked） |
| 学术伦理 | 最终产物含 AI assistance disclosure 模板，由用户开关 |

## 9. 验证标准

- 每个 provider 有离线 fixture 测试，CI 不依赖外网 ✅
- 每个 schema 有 Pydantic 校验 ✅
- LLM client 通过 monkeypatch 测试 parse / cache / retry ✅
- 当前测试 coverage ≥ 70% 门槛 ✅
- Phase 2 引入：LaTeX 产物在 toy fixture 上能编译出 PDF

## 10. OAuth backend（"Sign in with ChatGPT"）

**目标**：让用户用自己的 ChatGPT Plus/Pro/Team 订阅配额跑 LLM 调用，免 API 费。

**方法**：复刻 OpenAI Codex CLI 的 OAuth 流程（PKCE + 本地 callback）。技术细节来自 [openai/codex](https://github.com/openai/codex) 仓库 `codex-rs/login/`。

### 10.1 关键参数（与 Codex CLI 对齐）

| 项 | 值 |
|---|---|
| `client_id` | `app_EMoamEEZ73f0CkXaXp7hrann` |
| authorize endpoint | `https://auth.openai.com/oauth/authorize` |
| token endpoint | `https://auth.openai.com/oauth/token` |
| redirect_uri | `http://localhost:1455/auth/callback`（端口在 OpenAI Hydra allow-list 写死，1457 fallback） |
| scope | `openid profile email offline_access api.connectors.read api.connectors.invoke` |
| API base_url | `https://chatgpt.com/backend-api/codex`（不是 api.openai.com！） |
| 必加 header | `ChatGPT-Account-ID: <id>` (从 id_token JWT 取) + `originator: hso` |

### 10.2 流程

1. `hso login`：生成 PKCE pair + state，开浏览器到 authorize URL
2. 本地 server (端口 1455) 收 callback
3. `POST /oauth/token` form-encoded → 拿 `{access_token, refresh_token, id_token}`
4. 解 id_token JWT 取 `chatgpt_account_id`
5. 写 `~/.config/hso/auth.json`（权限 0600）
6. `LLMClient(auth_mode='oauth')` 启动时读 auth.json，过期/陈旧自动 refresh（refresh 用 JSON body）
7. 调 `responses.parse` 时 SDK 自动加 `Authorization: Bearer <access>` + 我们的 `default_headers`

### 10.3 ToS / 风险

- ❌ OpenAI 没有授权第三方应用复用 Codex client_id
- ⚠️ 仓库 README 没明文禁止，但 redirect_uri allow-list 表明设计上是给 Codex CLI 自身用
- ✅ OpenClaw (370k stars) 也是这套做法，commit `d1b2d81 (2026-04-29)` 把 originator 从 `codex_cli` 改回 `openclaw`，相当于"自首"反向工程身份
- 🚨 OpenAI 修改 auth check / Hydra allow-list 即失效；本应用停止工作，但**用户账号本身**风险低（OAuth 流程合规，scope 是用户主动授权的）

### 10.4 适用范围

- ✅ 个人项目 / 简历 demo
- ❌ 商业部署 / 多用户 SaaS（合规与稳定性都不行）

合规替代：申请 OpenAI [Sign in with ChatGPT for API](https://platform.openai.com/) 拿独立 client_id（按 token 走用户账单计费）。
