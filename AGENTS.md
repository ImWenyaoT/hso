# 仓库规范指南

# 重要提示：
# 编写任何代码前，务必先阅读 memory_bank/architecture.md，包括完整的数据库 schema。
# 编写任何代码前，务必先阅读 memory_bank/progress.md 了解产品契约。
# 添加主要功能或完成里程碑后，更新 memory_bank/progress.md。

## 项目结构与模块组织

HSO 是一个面向科研新手的桌面论文工作台，基于 Electron + React + TypeScript 构建，本地 SQLite 存储，无云依赖。

**当前状态**：编码实施阶段，脚手架与核心骨架已完成。

```
src/
├── main/          # Electron 主进程（IPC handlers, DB 初始化, Worker 管理）
├── renderer/      # React UI（3 个页面: 研究输入、研究卡片、论文项目）
├── application/   # 编排层（research-agent.ts, project-converter.ts）
├── worker/        # LaTeX Worker 子进程（latexmk + xelatex + BibTeX）
└── shared/        # 共享契约（schema.ts, types.ts, enums.ts, ipc-channels.ts）
tests/             # Vitest 测试
assets/            # 静态资产（模板文件等）
memory_bank/       # 架构文档与产品契约
tasks/             # 任务追踪与经验教训
```

## 构建、测试与开发命令

```bash
npm run dev          # Electron + React HMR 开发模式（主进程 + 渲染进程同时热更新）
npm run build        # 生产构建（打包 Electron 应用）
npm run lint         # ESLint 检查（TypeScript + React 规则）
npm run test         # Vitest 单元测试
npm run db:studio    # Drizzle Studio 可视化数据库（仅开发时使用）
```

## 代码风格与命名规范

- 文件名使用 kebab-case：`paper-project-service.ts`、`latex-worker.ts`
- 非平凡函数必须添加函数级注释（JSDoc 风格）
- 前端文件使用 2 空格缩进
- TypeScript 为所有运行时代码的主语言；Python 仅用于离线脚本和分析工具

## 模块化规则

**高内聚，低耦合 —— 遵循 DDD 原则。**

- 每个文件归属单一具名职责
- **进程边界是硬墙**：渲染进程只能通过 `window.api.invoke(channel, payload)` 与主进程通信，不得直接访问 `better-sqlite3` 或文件系统
- LaTeX Worker 只处理构建执行，不得接触 UI 状态、项目逻辑或数据库写入
- `src/shared/` 只存放类型、枚举、schema 定义和 IPC channel 常量，不含业务逻辑
- 应用编排层 (`src/application/`) 只做协调：调用 AI SDK、执行 DB 事务，不含 UI 状态管理

## 测试规范

- 测试文件置于 `tests/` 目录，命名如 `research-agent.test.ts`
- 每个 IPC handler 应有对应的集成测试
- 构建流程变更必须在 macOS 和 Windows 上均通过验证
- 发现 bug 时，先写可复现测试，再修复

## 提交与 Pull Request 规范

采用约定式提交（Conventional Commits）：
- `feat(research): add keyword input type`
- `fix(build): handle latexmk timeout`
- `docs(memory-bank): update architecture for LaTeX worker`

PR 应包含：影响范围、验证方式、仅在 UI 行为变更时附截图。

## Agent 专项说明

- 遵循 `CLAUDE.md` 中的工作流：先规划，在 `tasks/todo.md` 追踪，验证后再标记完成
- **规格已足够清楚时，直接写代码，不再写规划文档**
- 核心技术规格见 `memory_bank/architecture.md`；产品契约见 `memory_bank/progress.md`
