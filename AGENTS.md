# 仓库规范指南

# 重要提示：
# 编写任何代码前，务必先阅读 memory_bank/@architecture.md，包括完整的数据库 schema。
# 编写任何代码前，务必先阅读 memory_bank/@PRD.md。
# 添加主要功能或完成里程碑后，更新 memory_bank/@architecture.md。

## 项目结构与模块组织
本仓库目前是 HSO 的规划工作区，HSO 是一个低门槛学术论文工作台。核心产品与架构背景位于 `PRD.md`、`idea.md` 和 `tech_stack.md`。任务追踪位于 `tasks/todo.md`。实现启动后，应用代码置于 `src/` 下，测试置于 `tests/` 下，静态资产置于 `assets/` 下，长篇设计或决策说明置于 `docs/` 下。

## 构建、测试与开发命令
当前尚无已搭建的运行时，贡献者应将当前仓库视为文档优先。可使用：

- `ls` 或 `rg --files` 快速检查仓库内容
- `sed -n '1,160p' PRD.md` 在编辑前审阅产品范围
- `git status` 和 `git diff` 在仓库初始化后使用

应用脚手架搭建完成后，统一使用明确的命令，如 `npm run dev`、`npm run build`、`npm run lint` 和 `npm run test`，并在项目 README 中加以说明。

## 代码风格与命名规范
保持编辑最小化，与产品范围直接相关。规划文档使用 Markdown，偏好短节、编号列表和精确措辞，而非冗长的叙述段落。未来代码使用前端文件 2 空格缩进，文件名具有描述性，如 `paper-project-service.ts`，并为非平凡函数添加函数级注释。Markdown 文件和功能文档偏好使用 kebab-case，例如 `latex-build-flow.md`。

## 模块化规则

**高内聚，低耦合 —— 遵循 `idea.md` 的 DDD 原则。**

- 每个文件归属单一具名职责：`paper-project.service.ts` 负责服务逻辑；`paper-project.repository.ts` 负责数据访问；`paper-project.types.ts` 存放类型定义。混合路由、业务逻辑与数据库调用的文件是设计异味——应将其拆分。
- **文件长度是信号，不是规则。** 一个拥有单一紧密职责的 400 行文件是可以的。一个横跨两个领域的 150 行文件需要拆分。问"这个文件只做一件事吗？"而非"它有多少行？"
- 领域边界是硬墙：**信息检索**领域（`src/retrieval/`）与 **LaTeX 构建**领域（`src/latex/`）不得相互导入。跨领域编排专属于 Agent 层——这是 `idea.md` 中"两个独立领域，由顶层编排 Agent 协调"的直接体现。
- 每个文件精确对应三层架构（Web App 层 / Agent+Application 层 / Execution 层）中的一层。横跨多层的文件必须重构。
- 搭建新功能脚手架时，先写出文件分解方案（`service`、`repository`、`types`、`handler`），确认后再实现。这能防止"从一个文件开始不断堆积"形成巨石文件的模式。
- 不要创建重新导出整个领域的兜底桶文件 `index.ts`。

## 测试规范
当前尚无已纳入的自动化测试框架。在代码存在之前，通过检查 `PRD.md`、`idea.md` 和 `tech_stack.md` 之间的事实一致性来验证文档变更。实现启动后，在 `tests/` 中创建测试，命名如 `paper-project.test.ts` 或 `test_latex_build.py`，并要求贡献者在提交变更前运行相关的聚焦测试命令。

## 提交与 Pull Request 规范
本工作区无本地 git 历史可参考，因此暂无仓库专属的提交模式可推断。从现在起采用约定式提交（Conventional Commits），例如 `docs: refine repository guidelines` 或 `feat(agent): add plan executor`。PR 应包含简短摘要、影响文件、已执行的验证，以及仅在 UI 行为变更时附上截图。

## Agent 专项说明
遵循 `CLAUDE.md` 中的仓库级工作流：先规划，在 `tasks/todo.md` 中追踪工作，验证后再标记完成，避免投机性过度设计。
