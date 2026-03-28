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
- Use subagents liberally to keep main contect window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problens, throw more compute at it via subagents
- One tack per subagent for focused execution

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
- Skip this for simple, chvious fixes - don't over-engineer
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

- **Simplicity First**: Make every change as simple as possible. Inpact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.

---

## Project: HSO — 低门槛论文工作台

HSO 是一个面向科研新手（研究生/初级研究者）的**论文工作台**，核心价值是让不熟悉 LaTeX 的用户能够结构化地管理论文项目、完成 LaTeX 编译与预览。信息检索域是前置辅助能力，LaTeX 构建域是第一版主价值域。

**当前阶段**：规划/规格阶段，尚无实现代码。关键文档：
- [PRD.md](PRD.md) — 产品需求与范围
- [idea.md](idea.md) — 系统架构理念（LUI、Agent 中枢、thin client、DDD）
- [tech_stack.md](tech_stack.md) — 技术选型与部署方案
- [tasks/todo.md](tasks/todo.md) — 当前任务进度

## 开发命令

> 项目尚未初始化。一旦 scaffold 完成，预期命令如下：

```bash
# Web App (Next.js)
npm install
npm run dev       # 启动开发服务器
npm run build     # 生产构建
npm run lint      # 代码检查
npm run test      # 运行测试

# LaTeX Worker（独立容器服务）
# 见 worker/ 目录的 README
```

## 系统架构

系统分为三层，遵循 **thin client + smart agent, dumb tool** 原则：

```
Web App 层 (Next.js)
  └─ LUI 入口 + 论文项目页 + 构建状态展示
       ↓
Agent / Application 层 (Node.js + Vercel AI SDK)
  └─ 中枢协调器：理解输入 → 生成计划 → 调用工具 → 汇总结果
       ↓
Execution 层（dumb tools）
  ├─ Postgres (Drizzle ORM) — 核心数据：论文项目、研究卡片、构建记录
  ├─ Cloudflare R2 (S3-compatible) — 文件：上传资料、模板、构建产物
  ├─ Upstash Redis — 异步任务队列（触发 LaTeX 构建、检索任务）
  └─ LaTeX Worker (独立容器, TeX Live) — 编译执行、日志采集、结果上报
```

**两个独立领域**：
- **信息检索域**：关键词/种子论文 → 研究卡片 → 候选资料（客观材料，不做学术判断）
- **LaTeX 构建域**：论文项目 + 模板 + 章节 + 素材 → PDF 编译 + 预览（第一版核心价值）

**核心对象**：`Paper Project`（目标模板、章节结构、图表素材、参考资料、构建状态）

## 关键设计决策

- **Agent 用 Plan + Execute，不用 ReAct loop**：先生成完整计划，用户确认一次，工具统一执行
- **LaTeX Worker 必须独立**：编译依赖重、耗时长，不能放进 Vercel Serverless
- **20% 可观测性投入**：所有关键步骤必须带 `requestId / traceId / decisionId`，用 Sentry + structured logging
- **第一版不做多 Agent 网络**：单中枢 Agent 足够，过早拆分只增加复杂度
- **向量检索是辅助，不是主存储**：核心数据放 Postgres，向量能力按需叠加

## 部署组合

| 组件 | 服务 |
|------|------|
| Web App | Vercel |
| LaTeX Worker | Render 或 Fly.io |
| 数据库 | 托管 Postgres |
| 文件存储 | Cloudflare R2 |
| 队列 | Upstash Redis |
| 监控 | Sentry |
