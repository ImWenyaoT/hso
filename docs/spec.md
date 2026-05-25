# hso TypeScript Gateway Spec

> 版本：v0.3
> 当前阶段：TypeScript gateway Phase 1

## 1. 目标

把 hso 的主运行路径迁移为 TypeScript full-stack gateway：

- Next.js App Router 提供 UI 和 API。
- OpenAI Agents SDK TS 负责 agent turn orchestration。
- Vercel AI SDK 只负责 UIMessage stream 和 React `useChat` 协议。
- SQLite 负责 session/event/memory persistence。
- Python manuscript pipeline 保留在 `legacy/python`。

## 2. 技术栈

| 维度 | 选型 |
|---|---|
| App | Next.js App Router |
| Workspaces | npm workspaces |
| Schema | Zod |
| Storage | better-sqlite3 |
| Agent | `@openai/agents` |
| UI Stream | `ai` + `@ai-sdk/react` |
| Tests | Vitest |
| Legacy | Python 3.12 + uv under `legacy/python` |

## 3. API Shape

JSON shape 保持兼容旧 FastAPI gateway：

- `SessionRecord`: `id`, `title`, `created_at`
- `GatewayEvent`: `id`, `session_id`, `type`, `message`, `agent_name`,
  `payload`, `created_at`
- `MemoryRecord`: `id`, `session_id`, `role`, `content`, `metadata`,
  `created_at`
- `CreateSessionRequest`: `title`
- `SendMessageRequest`: `content`
- `SendMessageResponse`: `session`, `events`

## 4. Module Boundaries

```text
packages/shared
  Zod schemas and exported TypeScript types

packages/storage
  gateway.sqlite3: gateway_sessions, gateway_events
  memory.sqlite3: memory_records

packages/agent-runtime
  GatewayRuntime
  OpenAIAgentsRunner
  fake runner injection for tests

apps/web
  route handlers
  operator workspace
  /api/chat UIMessage stream

packages/cli
  start/status/smoke
```

## 5. Phase 1 Non-Goals

- 不迁 manuscript pipeline。
- 不迁 arXiv/Semantic Scholar/JCR/LaTeX compiler。
- 不实现 OAuth backend。
- 不实现 xAI/custom provider。
- 不重做 UI 视觉系统。

## 6. Validation

Required:

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run hso -- smoke
```

Optional:

```bash
npm run legacy:pytest
```
