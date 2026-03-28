# HSO 进度记录

## 2026-03-28

### 已完成：第 1 步 —— 锁定基础游戏契约

`memory_bank/implementation_plan.md` 的第 1 步已完成，并由用户手动验收。

#### 交付内容

1. 新增 `memory_bank/base_game_contract.md`，作为第 1 步契约的唯一权威来源。
2. 冻结六步基础游戏用户流程：
   研究输入 -> 研究卡片 -> 论文项目 -> 模板 -> 结构 -> 构建与预览。
3. 冻结核心对象词汇表，涵盖：
   `research input`（研究输入）、`research card`（研究卡片）、`paper project`（论文项目）、`template`（模板）、`section`（章节）、`asset`（素材）、`build job`（构建任务）、`build result`（构建结果）和 `reference source`（参考来源）。
4. 冻结 v1 非目标，明确第 1 步不涵盖协作功能、任意 LaTeX 项目导入、主观学术判断、完整 IDE 行为、构建取消、自定义模板上传及应用商店级分发。
5. 更新 `tasks/todo.md`，追踪第 1 步工作及测试后文档跟进项。

#### 验收依据

第 1 步依据以下检查项通过验收：

1. 六项基础游戏操作可追溯回 `memory_bank/PRD.md`，未引入隐性第七项操作。
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
