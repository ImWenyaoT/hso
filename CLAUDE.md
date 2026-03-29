# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

### TL;DR
- 请保持对话语言为中文
- 我的系统为 Mac/Windows/Linux
- 请在生成代码时添加函数级注释

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review Lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Code Over Docs**: When a spec is clear enough, write code — not more documentation.

---

## Project: HSO — 低门槛论文工作台

HSO 是一个面向科研新手（研究生/初级研究者）的**桌面论文工作台**，核心价值是让不熟悉 LaTeX 的用户能够结构化地管理论文项目、完成 LaTeX 编译与预览。信息检索域是前置辅助能力，LaTeX 构建域是第一版主价值域。

**当前阶段**：编码实施阶段。脚手架与核心骨架已完成，下一步是 LaTeX Worker。

关键文档：
- [memory_bank/architecture.md](memory_bank/architecture.md) — 系统架构、领域模型、UI 规划、研究流程、转化流程
- [memory_bank/progress.md](memory_bank/progress.md) — 基础产品契约与里程碑记录
- [memory_bank/implementation_plan.md](memory_bank/implementation_plan.md) — 编码任务与进度

## 开发命令

```bash
npm install          # 安装依赖
npm run dev          # Electron + React HMR 开发模式
npm run build        # 生产构建
npm run lint         # ESLint 检查
npm run test         # Vitest 单元测试
npm run db:studio    # Drizzle Studio 可视化数据库
```

## 系统架构

Electron 桌面应用，本地单用户，无云依赖：

```
渲染进程 (src/renderer/)
  └─ React 18 + Tailwind CSS — 3 个页面 + 4 个项目区域
       ↓ window.api.invoke(channel, payload)
主进程 (src/main/)
  └─ IPC handlers + DB 初始化 + Worker 管理
       ↓
应用编排层 (src/application/)
  ├─ research-agent.ts  — Vercel AI SDK generateObject → research_card
  └─ project-converter.ts — research_card → paper_project（DB 事务）
       ↓
本地存储 (better-sqlite3 + Drizzle ORM)
  └─ ~/.../hso.db — 9 个实体表
       ↓
LaTeX Worker (src/worker/)
  └─ 独立 Node 进程 — latexmk + xelatex + BibTeX
```

**共享契约** (`src/shared/`):
- `schema.ts` — Drizzle 表定义（9 个实体）
- `types.ts` — TypeScript 接口
- `enums.ts` — BuildStatus, AssetVisibility, ResearchInputType, ErrorStage
- `ipc-channels.ts` — IPC channel 常量

## 关键设计决策

- **IPC 桥接**：渲染进程通过 `window.api.invoke(channel, payload)` 调用主进程，preload 脚本暴露接口
- **本地数据库**：`better-sqlite3` + Drizzle ORM，DB 文件在 `app.getPath('userData')/hso.db`
- **研究 Agent**：`generateObject` + Zod schema，模型为 `claude-haiku-4-5-20251001`
- **原子性项目创建**：project-converter 使用 Drizzle 事务，失败时全部回滚
- **LaTeX Worker 隔离**：独立子进程，只处理构建执行，不接触 UI 状态或项目逻辑
- **模板 Fixture**：3 个预定义模板（generic-article, ieee, elsevier）首次启动时幂等写入
- **无路由库**：渲染层用 `{ page, params }` 状态对象管理路由，Electron 无 URL 栏
