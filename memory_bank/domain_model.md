# HSO 核心领域模型

## 目的

本文档是 HSO 基础产品第 3 步的唯一权威来源。

冻结内容：

1. 基础产品所需的最小实体集。
2. 每个实体在 v1 中必需的字段。
3. 支撑基础产品闭环的实体关系。

本文档**不**定义页面路由、页面状态、组件结构或交互布局。这些内容属于第 4 步。

## 1. 最小实体集

基础产品仅冻结以下九个实体：

1. `research_card`
2. `paper_project`
3. `paper_section`
4. `template`
5. `asset`
6. `reference_source`
7. `build_job`
8. `build_artifact`
9. `error_event`

`user` 不属于 v1 的核心领域对象。第一版是本地单用户助手，不需要把身份模型拉入领域主线。

## 2. 实体定义与必要字段

以下字段只保留 v1 工作所必需的最小集合。若某字段无法直接支撑基础产品六步流程中的一个具体动作，则不应在第 3 步冻结。

### `research_card`

用于承载检索加结构化摘要后的研究结果，是 `paper_project` 的上游输入，而不是主工作对象。

必需字段：

1. `id`
   唯一标识一张研究卡片。
2. `input_type`
   记录研究起点类型，限定在冻结范围内：`keyword`、`doi`、`arxiv_id`、`title`、`url`。
3. `input_value`
   保留用户原始输入，支持失败后重试与结果追溯。
4. `topic_label`
   提供这张卡片面向用户展示的主题标签。
5. `key_papers`
   结构化关键论文列表，是研究结果中的核心客观内容。
6. `trend_summary`
   面向用户的客观趋势摘要。
7. `distribution_summary`
   面向用户的客观分布摘要。
8. `project_importable_sections`
   可直接转入 `paper_project` 的结构化章节建议。
9. `reference_candidates`
   可供项目导入的候选引用来源。
10. `notes`
   非导入型备注区域，用于保留不应进入项目主结构的补充信息。
11. `created_at`
   标识卡片生成时间，支持历史追溯。

### `paper_project`

基础产品的主工作对象，承载模板选择、章节组织、资产管理、构建与预览。

必需字段：

1. `id`
   唯一标识一个论文项目。
2. `source_research_card_id`
   记录该项目来源于哪张研究卡片，支持从研究到项目的可追溯转换。
3. `title`
   项目当前标题，可来自导入候选标题或占位标题。
4. `template_id`
   当前选中的模板；在模板尚未选择前允许为空。
5. `current_version`
   项目当前结构版本号。每次构建必须绑定到明确版本快照，因此该字段是必需的。
6. `created_at`
   项目创建时间。
7. `updated_at`
   项目最近一次结构性修改时间。

### `paper_section`

`paper_project` 中的有序规范化章节单元，服务于“不是自由编辑器”的第一版结构模型。

必需字段：

1. `id`
   唯一标识一个章节。
2. `paper_project_id`
   标识所属论文项目。
3. `order_index`
   保证章节顺序可控且稳定。
4. `section_key`
   记录规范化章节类型，例如 `title`、`abstract`、`introduction`、`method`、`conclusion`。
5. `heading`
   当前章节展示标题，支持模板映射后的标签差异。
6. `content`
   章节正文内容，是构建时必须消费的核心文本。
7. `created_at`
   章节创建时间。
8. `updated_at`
   章节最近修改时间。

### `template`

受控模板目录中的模板包定义，用于将规范化论文内容映射到支持的输出格式。

必需字段：

1. `id`
   唯一标识一个模板。
2. `slug`
   稳定的模板键，例如 `generic-article`、`ieee`、`elsevier`。
3. `display_name`
   面向用户展示的模板名称。
4. `template_version`
   标识模板包自身版本，便于区分模板内容升级与项目内容版本。
5. `supported_section_keys`
   列出该模板可直接映射的规范化章节类型。
6. `mapping_rules`
   定义规范化章节、标题标签和渲染槽位如何映射到具体模板。

### `asset`

论文项目构建所需的受控素材对象。在 v1 中主要指图像等构建相关文件，而不是任意文件仓库。

必需字段：

1. `id`
   唯一标识一个素材。
2. `owner_project_id`
   标识首次引入该素材的项目，用于解释素材来源。
3. `name`
   面向用户展示的素材名称。
4. `asset_kind`
   标识素材类型；v1 仅冻结为构建相关图像类素材。
5. `storage_path`
   指向素材在项目本地或全局素材存储中的受控路径。
6. `visibility_mode`
   冻结为 `project_only`、`selected_projects`、`all_projects` 之一。
7. `selected_project_ids`
   当 `visibility_mode` 为 `selected_projects` 时，用于记录允许访问该素材的项目集合。
8. `created_at`
   素材登记时间。

### `reference_source`

与论文项目相关联的结构化引用来源对象。它不是通用上传文件，也不是普通 `asset`。

必需字段：

1. `id`
   唯一标识一个引用来源。
2. `paper_project_id`
   标识该引用当前属于哪个论文项目。
3. `source_type`
   记录来源主键类型，例如 `doi`、`arxiv_id`、`title_match`、`url_resolved`。
4. `source_value`
   记录来源主键值，例如 DOI、arXiv ID 或规范化 URL。
5. `title`
   引用标题。
6. `authors`
   作者列表快照。
7. `publication_year`
   最小可用的年份元数据。
8. `created_at`
   引用进入项目的时间。

### `build_job`

一次绑定到项目版本快照的构建执行记录，是构建状态流转的核心实体。

必需字段：

1. `id`
   唯一标识一次构建。
2. `paper_project_id`
   标识构建属于哪个项目。
3. `project_version`
   记录构建时消费的项目版本快照。
4. `status`
   冻结为 `queued`、`running`、`succeeded`、`failed`。
5. `requested_at`
   构建请求创建时间。
6. `started_at`
   构建实际开始时间；队列中允许为空。
7. `finished_at`
   构建结束时间；未完成前允许为空。
8. `status_summary`
   面向用户展示的简短构建结果摘要。

### `build_artifact`

一次 `build_job` 产出的受控文件记录。它是 Step 1 中用户可感知 `build_result` 的持久化落点。

必需字段：

1. `id`
   唯一标识一个构建产物。
2. `build_job_id`
   标识该产物来自哪次构建。
3. `artifact_kind`
   标识产物类别，例如 `pdf`、`build_log`、`aux_output`。
4. `storage_path`
   产物受控路径，支持预览、打开与导出。
5. `created_at`
   产物生成时间。

### `error_event`

用于记录基础产品中的可见失败事件，尤其是研究生成失败、项目创建失败、模板映射问题和构建失败。

必需字段：

1. `id`
   唯一标识一个错误事件。
2. `paper_project_id`
   若错误发生在项目上下文中则记录所属项目；否则允许为空。
3. `build_job_id`
   若错误由某次构建触发则记录对应构建；否则允许为空。
4. `stage`
   标识错误所属阶段，例如 `research_generation`、`project_conversion`、`template_mapping`、`build_execution`、`preview_open`。
5. `error_code`
   机器可识别的错误代码，用于归类与测试沉淀。
6. `human_summary`
   面向用户的可读错误摘要。
7. `location_hint`
   错误位置提示，例如章节名、资源名或日志位置；无可用位置时允许为空。
8. `suggested_fix`
   第一版要求提供的修复建议；若当前阶段无法生成则允许为空。
9. `created_at`
   错误记录时间。

## 3. 实体关系

第 3 步冻结以下关系，不额外引入新的核心领域对象：

### `research_card` -> `paper_project`

1. 一张 `research_card` 可以被转化为零个或多个 `paper_project`。
2. 一个 `paper_project` 在 v1 中必须记录其来源 `research_card`。
3. 转化时仅导入 `project_importable_sections`、选定标题和选定 `reference_candidates`，不导入 `notes`。

### `paper_project` -> `template`

1. 一个 `paper_project` 在任一时刻最多绑定一个 `template`。
2. 一个 `template` 可以被多个 `paper_project` 复用。
3. 模板切换不改变项目的规范化章节和引用对象，只改变映射与渲染规则。

### `paper_project` -> `paper_section`

1. 一个 `paper_project` 拥有多个 `paper_section`。
2. 每个 `paper_section` 只属于一个 `paper_project`。
3. `order_index` 保证结构顺序可解释且可构建。

### `paper_project` -> `asset`

1. 一个 `paper_project` 可以关联多个 `asset`。
2. 一个 `asset` 可以依据 `visibility_mode` 被一个、多个或所有项目复用。
3. 第 3 步只冻结这种业务关系，不要求现在引入额外的共享素材领域对象。

### `paper_project` -> `reference_source`

1. 一个 `paper_project` 可以拥有多个 `reference_source`。
2. 每个 `reference_source` 在 v1 中只归属于一个 `paper_project`。
3. `reference_source` 的来源通常来自 `research_card.reference_candidates` 的用户确认导入。

### `paper_project` -> `build_job`

1. 一个 `paper_project` 可以触发多次 `build_job`。
2. 每个 `build_job` 必须绑定一个明确的 `paper_project` 版本快照。
3. 构建历史必须按时间保留，而不是只保留最后一次结果。

### `build_job` -> `build_artifact`

1. 一个 `build_job` 可以产出多个 `build_artifact`。
2. 每个 `build_artifact` 只属于一次 `build_job`。
3. 用户在 Step 1 中感知到的 `build_result`，在第 3 步由 `build_job + build_artifact` 共同承载。

### `build_job` / `paper_project` -> `error_event`

1. 一个 `paper_project` 可以关联多个 `error_event`。
2. 一次 `build_job` 可以关联多个 `error_event`。
3. `error_event` 允许脱离 `build_job` 存在，以覆盖研究生成失败和项目创建失败等非构建阶段问题。

## 4. 基础产品流程映射

仅凭上述实体与关系，应能解释完整的基础产品闭环：

1. 用户提交研究起点，系统生成 `research_card`。
2. 用户从 `research_card` 选中可导入内容，创建 `paper_project`。
3. 系统为 `paper_project` 初始化有序的 `paper_section` 与 `reference_source`。
4. 用户为 `paper_project` 选择一个 `template`。
5. 用户补充或复用 `asset`，继续编辑 `paper_section`。
6. 用户触发 `build_job`；成功时得到 `build_artifact`，失败时记录 `error_event` 并提供摘要与修复建议。

若某个用户动作需要额外发明新的核心领域对象才能被解释，则说明当前模型不合格，应先修正文档，再进入第 4 步。

## 5. 第 3 步范围外内容

以下内容不得在本文件中冻结：

1. 页面路由、页面层职责或页面状态。
2. Electron IPC 载荷细节。
3. SQLite 表结构、Drizzle schema、索引或迁移脚本。
4. AI 提示词、检索 provider 或模板文件目录的具体实现。
5. 与多用户、协作、权限系统相关的身份对象。

## 6. 验证说明

第 3 步应依据以下检查项进行验证：

1. 每个实体都必须直接支撑基础产品中的至少一个用户动作。
2. 每个字段都必须能回答“如果没有它，哪一个 v1 功能会坏掉”。
3. 仅凭本文件的关系说明，开发者应能走通从研究输入到构建预览的完整闭环。
4. 本文档不得提前引入第 4 步的页面规划。
