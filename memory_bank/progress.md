# HSO 进度记录

## 2026-03-28

### 已完成：第 1 步 —— 锁定基础产品契约

`memory_bank/implementation_plan.md` 的第 1 步已完成，并由用户手动验收。

#### 交付内容

1. 新增 `memory_bank/base_game_contract.md`，作为第 1 步契约的唯一权威来源。
2. 冻结六步基础产品用户流程：
   研究输入 -> 研究卡片 -> 论文项目 -> 模板 -> 结构 -> 构建与预览。
3. 冻结核心对象词汇表，涵盖：
   `research input`（研究输入）、`research card`（研究卡片）、`paper project`（论文项目）、`template`（模板）、`section`（章节）、`asset`（素材）、`build job`（构建任务）、`build result`（构建结果）和 `reference source`（参考来源）。
4. 冻结 v1 非目标，明确第 1 步不涵盖协作功能、任意 LaTeX 项目导入、主观学术判断、完整 IDE 行为、构建取消、自定义模板上传及应用商店级分发。
5. 更新 `tasks/todo.md`，追踪第 1 步工作及测试后文档跟进项。

#### 验收依据

第 1 步依据以下检查项通过验收：

1. 六项基础产品操作可追溯回 `memory_bank/PRD.md`，未引入隐性第七项操作。
2. `memory_bank/base_game_contract.md` 对 `research card` 与 `paper project` 的区别描述足够清晰，其他开发者可据此做出一致解释。
3. 非目标与 `memory_bank/PRD.md` 第 8 节保持对齐。
4. `tasks/todo.md` 一致反映第 1 步工作、审查摘要及等待测试状态。
5. 第 1 步验收完成前，未提前引入第 2 步的仓库结构、运行时边界或存储布局决策。

#### 当前边界

第 1 步已完成并通过验收。第 2 步仓库骨架与交付边界工作此后已完成并通过验收（见下文）。

---

### 已完成：第 2 步 —— 仓库骨架与交付边界

`memory_bank/implementation_plan.md` 的第 2 步已完成并通过验证。

#### 交付内容

1. 新增 `memory_bank/repository_skeleton.md`，作为第 2 步契约的唯一权威来源。
2. 冻结最小仓库结构，涵盖九个顶层区域：`src/main/`、`src/renderer/`、`src/application/`、`src/worker/`、`src/shared/`、`docs/`、`tests/`、`memory_bank/` 和 `assets/`。
3. 冻结 Electron 主进程、渲染进程和本地 worker 运行时的运行时归属，并为每个边界设定明确禁止项。
4. 冻结五个必需的环境依赖类别：`local_database`、`local_filesystem_storage`、`ai_provider`、`local_worker_runtime` 和 `optional_error_tracking`。
5. 冻结两层本地存储模型：随项目文件夹一同移动的项目本地 `.hso/` 元数据，以及机器本地的全局应用数据资源（支撑基础设施）。
6. 冻结五项必需质量基础设施：结构化日志、trace ID、聚焦的自动化测试、手动回归检查清单，以及缺陷转测试工作流。
7. 更新 `memory_bank/architecture.md`，注册新文档及其阅读位置。

#### 验收依据

第 2 步依据 `memory_bank/repository_skeleton.md` 第 7 节的全部七项检查通过验收：

1. 每个顶层仓库部分均有唯一明确的职责。✓
2. 未将繁重的 LaTeX 构建步骤分配给渲染进程。✓
3. 环境列表仅包含必需的运行时依赖类别。✓
4. 项目本地 `.hso/` 数据及项目输出可随项目文件夹一同移动。✓
5. 全局 SQLite、全局资产存储、工具链文件和缓存无需按项目重复存储。✓
6. 质量边界被视为必需基础设施，而非可选的后期加固项。✓
7. 本文档未定义第 3 步的实体、字段或关系。✓

已对 `tech_stack.md`、`implementation_plan.md`、`base_game_contract.md`、`architecture.md` 和 `progress.md` 进行跨文档一致性校验，未发现冲突。

#### 当前边界

项目在第 3 步之前有意暂停。下一步实现工作应从 `memory_bank/implementation_plan.md` 的第 3 步任务（领域模型）开始，而非依赖已冻结的第 2 步边界之外的未文档化假设。

---

### 已完成：第 3 步 —— 核心领域建模

`memory_bank/implementation_plan.md` 的第 3 步已完成并通过验证。

#### 交付内容

1. 新增 `memory_bank/domain_model.md`，作为第 3 步契约的唯一权威来源。
2. 冻结基础产品的九个最小核心实体：`research_card`、`paper_project`、`paper_section`、`template`、`asset`、`reference_source`、`build_job`、`build_artifact` 和 `error_event`。
3. 为每个实体冻结 v1 必需字段，只保留能直接支撑基础产品闭环的标识符、状态字段、时间戳、版本字段和最小元数据。
4. 冻结核心实体关系，覆盖研究卡片到论文项目、论文项目到模板、章节、素材、参考来源、构建任务，以及构建任务到构建产物的关系。
5. 明确 Step 1 中用户可感知的 `build_result` 在 Step 3 中由 `build_job + build_artifact` 共同承载，避免术语漂移。
6. 在不额外引入新的核心领域对象前提下，解释素材可见性模型 `project_only / selected_projects / all_projects` 与项目关系。
7. 更新 `tasks/todo.md`，追踪第 3 步工作、审查摘要及测试后文档收口状态。

#### 验收依据

第 3 步依据以下检查项通过验收：

1. 每个实体都能直接映射到基础产品六步流程中的至少一个用户动作。
2. 每个冻结字段都能回答“如果没有它，哪一个 v1 功能会坏掉”。
3. 仅凭 `memory_bank/domain_model.md` 的关系说明，开发者可以从研究输入走通到构建预览，无需发明额外核心对象。
4. 本轮文档未提前进入 `memory_bank/implementation_plan.md` 第 4 步的页面、路由或状态规划。
5. `domain_model.md` 与 `base_game_contract.md`、`repository_skeleton.md`、`implementation_plan.md`、`tech_stack.md` 间未发现术语或边界冲突。

#### 当前边界

第 3 步已完成并通过验收。第 4 步用户界面页面规划工作此后已完成并通过验收（见下文）。

---

### 已完成：第 4 步 —— 用户界面页面规划

`memory_bank/implementation_plan.md` 的第 4 步已完成并通过验证。

#### 交付内容

1. 新增 `memory_bank/ui_page_plan.md`，作为第 4 步契约的唯一权威来源。
2. 冻结基础产品最小 UI 结构：3 个顶层页面（`research_input_page`、`research_card_results_page`、`paper_project_detail_page`）和 4 个项目页内区域（`template_selection_panel`、`asset_panel`、`build_status_panel`、`pdf_preview_export_panel`）。
3. 为每个页面与区域写明单一主职责与明确禁止项，将编排、数据库操作、LaTeX 构建和模板映射推理继续留在应用层或 worker 边界内。
4. 为全部 7 个 UI 单元（3 页面 + 4 区域）补齐空态、加载态、成功态和错误态，共 28 条状态描述。
5. 明确列出 7 类超出第 4 步范围的内容，避免提前冻结第 5 步的研究输入流程、检索策略或研究卡片 schema。
6. 更新 `tasks/todo.md`，追踪第 4 步工作及测试后文档收口状态。
7. 为后续开发者明确 UI 实现入口：先按 `ui_page_plan.md` 落 3 个顶层页面与 4 个项目页区域，再进入 Step 5 细化研究输入流程，而不是反向扩张新的顶层路由。

#### 验收依据

第 4 步依据 `memory_bank/ui_page_plan.md` 第 6 节的全部五项检查通过验收：

1. 从研究输入到 PDF 预览，完整用户旅程可仅凭文档中的 3 个顶层页面和 4 个项目页区域走通。✓
2. 每个页面或区域都只有一个清晰主职责，并明确说明"不应做什么"。✓
3. 不存在为了"以后可能会用"而提前拆出的额外顶层路由。✓
4. 每个页面或区域都覆盖空态、加载态、成功态和错误态，且这些状态不依赖协作、在线同步或其他范围外能力。✓
5. 本文档未提前冻结第 5 步的研究输入流程、检索策略或研究卡片 schema。✓

#### 当前边界

第 4 步已完成并通过验收。下一步实现工作应从 `memory_bank/implementation_plan.md` 的第 5 步任务（研究输入流程细节）开始，而不是回退修改已冻结的 UI 页面规划边界。
