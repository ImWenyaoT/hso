# HSO 系统架构参考

本文档是 HSO 系统架构的综合参考，涵盖仓库结构、运行时归属、领域模型、UI 架构与核心流程契约。

---

## 1. 仓库结构与运行时归属

### 1.1 最小仓库结构

| 目录 | 归属 |
|------|------|
| `src/main/` | Electron 主进程：生命周期、窗口、IPC 注册、worker 派生、本地路径解析 |
| `src/renderer/` | React 渲染进程：用户输入、页面状态、视图展示、交互反馈 |
| `src/application/` | 应用编排层：用例流程、Agent 调用、跨领域协调 |
| `src/worker/` | 本地 LaTeX Worker：构建执行、工具链调用、产物收集 |
| `src/shared/` | 共享契约：TypeScript schema、IPC channel、DTO、枚举、常量 |
| `docs/` | 面向实现的工程笔记（非 memory_bank 权威来源） |
| `tests/` | 自动化测试与回归用例 |
| `memory_bank/` | 产品、架构、规划、范围的权威来源文档 |
| `assets/` | 应用静态资产（图标、模板 fixture），不归属用户项目资产 |

TypeScript 是 `src/` 下所有运行时拥有代码路径的默认实现语言。Python 仅用于辅助脚本与分析工具。

### 1.2 运行时职责边界

**Electron 主进程**
- 桌面应用生命周期、窗口创建、原生对话框
- 应用数据目录解析、受控 IPC 入口注册
- 本地 worker 进程派生与监管
- 系统 PDF 查看器调起

主进程**不**承担：繁重 LaTeX 构建、领域编排、UI 渲染。

**渲染进程**
- 页面渲染与交互状态
- 研究输入、研究卡片审阅、项目转化、模板选择、章节编辑、构建触发、预览/导出

渲染进程**不**承担：构建执行、直接数据库操作、超出已批准 IPC 调用的文件系统特权。

**本地 Worker**
- 受控 LaTeX 构建执行（`latexmk + xelatex + BibTeX`）
- 构建工作区准备、日志与产物收集
- 结构化执行结果返回给应用层

Worker **不**承担：窗口管理、长生命周期 UI 状态、产品层页面决策。

**可选在线服务**（独立于本地运行时）
- AI 提供方（结构化摘要、修复建议）
- 可选远程错误聚合
- 研究输入检索相关网络访问

### 1.3 环境依赖类别（v1）

| 类别 | 实现 |
|------|------|
| `local_database` | SQLite（better-sqlite3 + Drizzle ORM） |
| `local_filesystem_storage` | 项目文件夹、`.hso/`、全局 asset store、构建产物 |
| `ai_provider` | Anthropic Claude API（Vercel AI SDK） |
| `local_worker_runtime` | Node 子进程，执行受控 LaTeX 工具链 |
| `optional_error_tracking` | Sentry（可选，非 v1 硬性要求） |

v1 不引入：协作后端、同步服务、认证平台、队列基础设施、远程构建服务。

### 1.4 本地存储布局

**项目本地存储**（随项目文件夹一同移动）
```
<项目目录>/
├── .hso/                # 项目本地元数据、修订状态、构建本地记录
└── <项目内容文件>        # 规范化论文内容、项目专属素材
```

**全局应用数据存储**（机器本地，不随项目复制）
- 全局 SQLite 数据库（`app.getPath('userData')/hso.db`）
- 全局 asset store（可复用资产，不按项目重复存储）
- 受控 LaTeX 工具链安装
- 应用级缓存
- 跨项目日志与诊断

### 1.5 质量基础设施（v1 必需）

1. **结构化日志** — 每个主要操作输出机器可读日志
2. **Trace ID** — 从 UI 触发到 worker 输出可端到端追踪
3. **聚焦自动化测试** — 针对契约、编排边界和关键回归
4. **手动回归检查清单** — 里程碑验收前运行
5. **缺陷转测试工作流** — 发现故障模式时记录可复现回归用例

---

## 2. 核心领域模型

### 2.1 最小实体集（9 个，v1 冻结）

`research_card` · `paper_project` · `paper_section` · `template` · `asset` · `reference_source` · `build_job` · `build_artifact` · `error_event`

`user` 不是 v1 核心领域对象（本地单用户助手，不需要身份模型）。

### 2.2 实体字段定义

**`research_card`** — 研究卡片，`paper_project` 的上游输入

| 字段 | 作用 |
|------|------|
| `id` | 唯一标识 |
| `input_type` | `keyword` / `doi` / `arxiv_id` / `title` / `url` |
| `input_value` | 保留原始输入，支持重试追溯 |
| `topic_label` | 面向用户的主题标签 |
| `key_papers` | 结构化关键论文列表（JSON） |
| `trend_summary` | 客观趋势摘要 |
| `distribution_summary` | 客观分布摘要 |
| `project_importable_sections` | 可直接转入项目的结构化章节（JSON） |
| `reference_candidates` | 候选引用来源（JSON） |
| `notes` | 不可导入项目的备注区 |
| `created_at` | 生成时间 |

**`paper_project`** — 论文项目，基础产品核心对象

| 字段 | 作用 |
|------|------|
| `id` | 唯一标识 |
| `source_research_card_id` | 来源研究卡片，保证可追溯性 |
| `title` | 项目标题（来自候选或占位） |
| `template_id` | 当前模板；模板未选时允许为空 |
| `current_version` | 项目版本号，构建必须绑定版本快照 |
| `created_at` / `updated_at` | 时间戳 |

**`paper_section`** — 有序规范化章节

| 字段 | 作用 |
|------|------|
| `id` / `paper_project_id` | 标识与归属 |
| `order_index` | 保证顺序稳定 |
| `section_key` | 规范化类型：`title` / `abstract` / `introduction` / `method` / `conclusion` 等 |
| `heading` | 展示标题（支持模板映射差异） |
| `content` | 章节正文，构建时必须消费 |
| `created_at` / `updated_at` | 时间戳 |

**`template`** — 受控模板包

| 字段 | 作用 |
|------|------|
| `id` / `slug` | 标识与稳定键（`generic-article` / `ieee` / `elsevier`） |
| `display_name` | 面向用户名称 |
| `template_version` | 模板包自身版本 |
| `supported_section_keys` | 可直接映射的章节类型列表（JSON） |
| `mapping_rules` | 规范化章节到渲染槽位的映射规则（JSON） |

**`asset`** — 构建相关素材（v1 仅图像）

| 字段 | 作用 |
|------|------|
| `id` / `owner_project_id` | 标识与来源项目 |
| `name` / `asset_kind` | 名称与类型（v1 固定 `image`） |
| `storage_path` | 受控存储路径 |
| `visibility_mode` | `project_only` / `selected_projects` / `all_projects` |
| `selected_project_ids` | `selected_projects` 模式下允许访问的项目集（JSON） |
| `created_at` | 登记时间 |

**`reference_source`** — 结构化引用来源（非通用 asset）

| 字段 | 作用 |
|------|------|
| `id` / `paper_project_id` | 标识与归属 |
| `source_type` | `doi` / `arxiv_id` / `title_match` / `url_resolved` |
| `source_value` | 来源主键值 |
| `title` / `authors` / `publication_year` | 最小引用元数据 |
| `created_at` | 引用进入项目时间 |

**`build_job`** — 构建任务（绑定项目版本快照）

| 字段 | 作用 |
|------|------|
| `id` / `paper_project_id` | 标识与归属 |
| `project_version` | 构建时消费的版本快照 |
| `status` | `queued` / `running` / `succeeded` / `failed`（v1 不含 `canceled`） |
| `requested_at` / `started_at` / `finished_at` | 时间戳 |
| `status_summary` | 面向用户的构建结果摘要 |

**`build_artifact`** — 构建产物

| 字段 | 作用 |
|------|------|
| `id` / `build_job_id` | 标识与来源构建 |
| `artifact_kind` | `pdf` / `build_log` / `aux_output` |
| `storage_path` | 产物受控路径（支持预览、打开、导出） |
| `created_at` | 产物生成时间 |

**`error_event`** — 可见失败事件（跨阶段）

| 字段 | 作用 |
|------|------|
| `id` | 唯一标识 |
| `paper_project_id` / `build_job_id` | 可选归属（允许脱离二者独立存在） |
| `stage` | `research_generation` / `project_conversion` / `template_mapping` / `build_execution` / `preview_open` |
| `error_code` | 机器可识别错误代码 |
| `human_summary` | 面向用户的可读摘要 |
| `location_hint` | 错误位置提示（可选） |
| `suggested_fix` | 修复建议（可选） |
| `created_at` | 记录时间 |

### 2.3 实体关系

```
research_card ──(1:N)──> paper_project
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         template(N:1)  paper_section    reference_source
                              │
              ┌───────────────┘
              │
           asset          build_job ──(1:N)──> build_artifact
                              │
                          error_event (也可关联 paper_project)
```

关键约束：
- 转化时仅导入 `project_importable_sections`、选定标题候选、选定 `reference_candidates`，不导入 `notes`
- 模板切换不改变规范化章节与引用，只改变映射与渲染规则
- 构建历史按时间保留，不只保留最后一次
- 用户感知的 `build_result` 由 `build_job + build_artifact` 共同承载

---

## 3. UI 架构

### 3.1 最小页面与区域

**3 个顶层页面**

| 页面 | 职责 |
|------|------|
| `research_input_page` | 研究起点入口，接收输入，进入研究卡片流程 |
| `research_card_results_page` | 展示研究卡片，提供重试/返回/转化入口 |
| `paper_project_detail_page` | 论文项目主工作页，汇总所有后续操作 |

**`paper_project_detail_page` 内 4 个受控区域**（不是独立顶层路由）

| 区域 | 职责 |
|------|------|
| `template_selection_panel` | 查看/切换模板，展示映射反馈 |
| `asset_panel` | 查看/添加/移除构建素材 |
| `build_status_panel` | 触发构建，查看状态、摘要、错误与修复建议 |
| `pdf_preview_export_panel` | 展示最近成功 PDF，提供打开/导出操作 |

v1 不拆出：独立模板中心、独立资产库、独立构建历史、独立 PDF 预览页。

### 3.2 用户旅程

```
research_input_page
  → (提交) → research_card_results_page
                → (转化) → paper_project_detail_page
                                ├── template_selection_panel
                                ├── asset_panel
                                ├── build_status_panel
                                └── pdf_preview_export_panel
```

### 3.3 各 UI 单元四态要求

| 单元 | 空态 | 加载态 | 成功态 | 错误态 |
|------|------|--------|--------|--------|
| `research_input_page` | 输入表单 | 禁用重复提交 | 跳转结果页 | 显示错误，保留输入，重试 |
| `research_card_results_page` | 提示返回重新发起 | 骨架加载反馈 | 展示卡片，允许转化 | 错误摘要与返回/重试 |
| `paper_project_detail_page` | 可操作初始工作区 | 局部或整页加载 | 所有区域可见可操作 | 错误 + trace 线索 + 返回入口 |
| `template_selection_panel` | "未选择模板" + 下一步 | 禁用重复切换 | 展示模板与映射结果 | 加载失败或映射不兼容提示 |
| `asset_panel` | 添加入口与格式说明 | 局部加载 | 展示素材列表及操作 | 失败原因 + 重试 |
| `build_status_panel` | "尚无构建" + 首次构建入口 | `queued`/`running` 可见状态 | `succeeded` 摘要，联动预览 | `failed` 摘要、位置提示、修复建议 |
| `pdf_preview_export_panel` | "暂无可预览文件" | 可见等待反馈 | PDF 展示 + 打开/导出 | 错误摘要 + 恢复路径 |

---

## 4. 研究输入流程

### 4.1 支持的输入类型（v1 冻结 5 种）

| 类型 | 说明 |
|------|------|
| `keyword` | 主题关键词/短语，走主题级检索 |
| `doi` | 规范 DOI，直接定位单篇论文 |
| `arxiv_id` | 规范化 arXiv 标识符，直接定位单篇论文 |
| `title` | 论文标题，走候选检索与用户确认 |
| `url` | 论文相关 URL，仅作辅助解析（不是主检索路径） |

v1 明确拒绝：自由格式引用文本、多论文混杂列表、PDF 直传作为主入口、未分隔长段落猜测输入。

### 4.2 检索优先级（冻结）

```
DOI 查询 → arXiv ID 查询 → 标题搜索 → URL 解析辅助 → 用户确认候选
```

关键规则：
- URL 只做辅助解析，提取出的 DOI/arXiv ID 重新进入确定性顺序
- 标题搜索不假设唯一精确匹配，多候选时必须展示给用户确认
- 用户确认候选前，不得将模糊结果固化为 `reference_source`
- `keyword` 走主题级检索，不要求先确认种子论文

### 4.3 研究卡片导入边界

| 内容 | 可导入项目 |
|------|-----------|
| `project_importable_sections` | 是（用户选择后） |
| `reference_candidates` | 是（用户确认后） |
| 标题候选辅助信息 | 是（用户选中后作为 `title`） |
| `trend_summary` / `distribution_summary` | 否 |
| `notes` | 否 |
| `key_papers`（未确认部分） | 否 |
| 检索轨迹、Agent 推理 | 否 |

### 4.4 研究生成失败行为

必须提供：可见错误、保留原始输入、重试入口、返回修改入口、不伪造成功卡片、保留 trace ID 与错误代码。

---

## 5. 项目转化流程

### 5.1 转化边界

**允许导入（3 类）：**
1. 用户选中的 `project_importable_sections` → 初始 `paper_section`
2. 用户选中的标题候选 → `paper_project.title`
3. 用户选中的 `reference_candidates` → 初始 `reference_source`

**禁止导入：** `notes`、`trend_summary`、`distribution_summary`、未确认的 `key_papers`、检索轨迹、URL 解析中间结果、Agent 推理过程。

### 5.2 新建项目初始状态

| 字段/关联 | 初始值 |
|-----------|--------|
| `source_research_card_id` | 必填 |
| `title` | 选定候选 > `topic_label` 占位 > 默认占位 |
| `template_id` | 空（第 7 步选择） |
| `current_version` | 1 |
| `paper_section` | 有序章节（来自选中的 importable_sections） |
| `reference_source` | 仅用户本次选择的引用 |
| `asset` / `build_job` | 空 |

### 5.3 项目创建失败处理

**原子性**：完整创建或完全不暴露，不允许半成品状态。

**用户体验**：可见错误、保留源卡片与已确认选择、重试入口、返回修改入口、不伪造成功项目。

**日志**：结构化日志 + trace ID + 阶段标记 `project_conversion` + `error_event`。

---

## 6. 文档职责索引

| 文件 | 拥有什么 |
|------|----------|
| `PRD.md` | 产品目标、用户、范围、非目标、系统原则 |
| `tech_stack.md` | 技术选型、主辅语言边界、工程基线假设 |
| `implementation_plan.md` | 实施顺序、步骤拆解、验证要求、决策冻结列表 |
| `architecture.md`（本文件） | 仓库结构、运行时归属、领域模型、UI 架构、核心流程契约 |
| `progress.md` | 基础产品六步契约（流程、词汇、非目标）+ 已完成里程碑记录 |

辅助文件：
- `idea.md` — 高层架构理念（LUI、thin client、DDD、多 Agent 长期方向）
- `tasks/todo.md` — 活跃工作会话检查清单
- `tasks/lessons.md` — 纠正模式与防错规则

## 7. 推荐阅读顺序

1. `architecture.md`（本文件）
2. `PRD.md`
3. `tech_stack.md`
4. `implementation_plan.md`
5. `progress.md`
