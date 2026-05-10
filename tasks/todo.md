# hso — Todo

详细 spec 在 [docs/spec.md](../docs/spec.md)。历史规划见 [docs/archive/](../docs/archive/)。

## Phase 1：检索 + 章节结构分析 ✅ 完成 2026-05-09

- [x] 拍平项目结构到仓库根（`src/`, `tests/`, `data/`, `output/`）
- [x] uv + Python 3.12+ 项目骨架
- [x] Pydantic schemas（Paper / Author / Venue / SearchQuery / JCRRecord / SectionProfile / SectionStructure）
- [x] **LLM 抽象层**：基于 OpenAI **Responses API**（`responses.parse` + `text_format=PydanticModel`） + 磁盘缓存 + tenacity 重试
- [x] arXiv provider（lukasschwab/arxiv.py）
- [x] Semantic Scholar provider（直连 REST，含 retry/reraise）
- [x] JCRFilter（ShowJCR 中文 JSON 与扁平 list 双格式）
- [x] SearchAggregator（union-find 三级去重）
- [x] SectionProfileBuilder（type-safe structured output；LLM schema 与业务 schema 解耦）
- [x] CLI：`hso search` / `hso analyze`
- [x] 41 测试，coverage 77.99%（>70% 门槛），ruff 干净
- [x] CI workflow（ubuntu+macos × Python 3.12）

## Phase 2：起草 manuscript

### Phase 2.1：数据基础与 LaTeX 渲染 ✅ 完成 2026-05-09

- [x] `Experiment / ExperimentResult / ExperimentTimeSeries` schema
- [x] `ExperimentLoader.from_json / from_results_csv / from_timeseries_csv`
- [x] Elsevier `elsarticle.cls` jinja2 模板 + `ElsevierTemplate.render`
- [x] `results_to_latex_table`（booktabs + 加粗最优 + higher/lower direction）
- [x] `render_timeseries_figure`（matplotlib → PDF）
- [x] 33 个新测试，全套 74 测试通过；coverage 83.48%
- [x] 端到端 smoke：从 fixtures/experiment.json 生成 1.4KB main.tex + 12KB PDF 图

### Phase 2.2：起草 agent ✅ 完成 2026-05-09

- [x] `Outline / SectionPlan / DraftedSection / BibEntry` schema（`models/manuscript.py`）
- [x] `OutlineBuilder`：基于 SectionProfile + Experiment + 候选 papers，OpenAI Responses API structured output
- [x] `SectionDrafter`：单章节起草，prompt 仅暴露 plan 允许的 papers / artifacts，强制 `\cite{paper:<id>}` 占位
- [x] BibTeX 生成（`bibliography.papers_to_bib_entries`）：cite key = surname+year+firstword，自动处理冲突（a/b/c 后缀），区分 `@article` / `@misc`
- [x] `resolve_citekeys`：正文占位 → 真实 cite key；未匹配 paper_id 报告
- [x] `check_citation_consistency`：正文 vs declared 双向集合差
- [x] **per-metric direction 表格 bug 修复**（顺手完成 §2.4）：`directions={"FID": "min", "CLIP-Score": "max"}` + `default_direction`
- [x] **LLMClient `auth_mode` 双后端**：`'api_key'` 走 Responses API；`'oauth'` 走 ChatGPT Codex backend（stream + refresh）
- [x] 102 测试，coverage 85.65%

### Phase 2.3：装配与编译 ✅ 完成 2026-05-10

- [x] `ManuscriptAssembler`：Outline → 多个 DraftedSection → 一份完整 .tex 项目目录（main.tex + refs.bib + figs/ + tables/）
- [x] 端到端 pipeline：`SectionProfile + Experiment + Papers → ManuscriptDocument`
- [x] LaTeX 编译（latexmk / tectonic）+ error 定位
- [x] CLI：`hso draft --profile profile.json --experiment exp.json --papers search.json --out output/draft/`

### 2026-05-10 Project Optimization Plan

目标：把当前项目从“Phase 2.2 utility 已完成”优化到“Phase 2.3 可通过 CLI 产出完整 manuscript 项目目录”，同时修掉质量门禁和文档明显漂移。

- [x] 设计并实现纯装配层：`ManuscriptAssembler` 只负责文件、引用、图表、模板装配，不调用 LLM
- [x] 设计并实现 pipeline 层：`DraftPipeline` 串起 `OutlineBuilder`、`SectionDrafter`、`ManuscriptAssembler`
- [x] 设计并实现编译层：`LatexCompiler` 封装 `latexmk` / `tectonic`，返回结构化结果和错误摘要
- [x] 接入 CLI：新增 `hso draft --profile --experiment --papers --out [--compile]`
- [x] 补测试：assembler / pipeline / compiler / CLI 的离线测试，不依赖真实 LLM 或外网
- [x] 修质量门禁：CI 中 mypy 变为阻塞；ruff 覆盖 `scripts/`
- [x] 修文档漂移：`.env.example` 改为 `HSO_*`；README / quickstart / spec 同步当前阶段
- [ ] 验证：`ruff`、`mypy`、`pytest` 全通过，并在本节记录结果

Review:
- 已通过：`.venv/bin/python -m compileall -q src tests scripts`
- 已通过：`ManuscriptAssembler` 离线 smoke，可写出 `main.tex`、`tables/main_results.tex`、`figs/train_loss.pdf`
- 未完成：`uv run --extra dev ruff/mypy/pytest` 因 PyPI wheel 下载长时间卡住，已按用户指示先 push

### Phase 2.5：OAuth ("Sign in with ChatGPT") ✅ 完成 2026-05-09（端到端验证通过）

实现路径：复刻 OpenAI Codex CLI 的 OAuth 流程（PKCE + 本地 callback + token refresh），技术细节见 `docs/spec.md §10`。

- [x] `llm/auth_storage.py`：StoredAuth schema、save/load/clear、XDG 路径、过期判定
- [x] `llm/oauth.py`：PKCE 生成、authorize URL 构造、本地 callback server (端口 1455)、token exchange (form-encoded)、refresh (JSON body)、JWT decode 取 `chatgpt_account_id`、顶层 `login()` / `refresh_and_save()`
- [x] `llm/client.py`：`auth_mode='oauth'` 切到 `chatgpt.com/backend-api/codex`、加 `ChatGPT-Account-ID` header、自动 refresh、stream 模式（ChatGPT 后端强制）、手工 deltas 收集 + JSON 解析（SDK `output_parsed` 不可用）
- [x] `cli.py`：`hso login` / `logout` / `whoami` 命令
- [x] 测试：tests/test_llm/test_auth_storage.py + test_oauth.py（共 23 个测试；PKCE / URL / JWT / token exchange mock / refresh mock / 本地 callback server）
- [x] httpx[socks] 加 SOCKS 代理支持（用户机器有本地 SOCKS）
- [x] **端到端实测通过**：`hso login` → token 持久化 → `LLMClient(auth_mode='oauth', model='gpt-5.2').respond(...)` 真返回；`parse(text_format=...)` 真返回 type-safe pydantic 实例
- [x] README + spec §10 + ToS 警告

实测发现的 ChatGPT 后端 7 处差异已记进 [memory/feedback_chatgpt_backend_quirks.md](../../../.claude/projects/-Users-snoopy-Desktop-kendrick-lamar/memory/feedback_chatgpt_backend_quirks.md)。

## Phase 3：模拟审稿 loop（待开始）

- [ ] Reviewer rubric schema（novelty / clarity / method / experiment / citation）
- [ ] Reviewer agent（基于 SectionProfile + Q1/Q2 标准）
- [ ] Revision planner（issue list → 修改计划）
- [ ] Reviser agent（按 plan 改 LaTeX）
- [ ] 收敛判定 + 硬上限（max_iterations）
- [ ] Diff / changelog 持久化

## Phase 4：Web UI（待开始）

- [ ] FastAPI 包装核心 pipeline
- [ ] 简单前端（Vue / React）项目列表 + outline 可视化 + review 进度
- [ ] WebSocket 推送 review loop 进度

## 风险跟踪

- ShowJCR 2026 起停更 → 数据版本锁定 + 无分区降级
- Responses API 限定 OpenAI/Azure 端点 → 文档明示，base_url 切其他端点会失败
- 审稿 loop 不收敛 → Phase 3 设硬上限
