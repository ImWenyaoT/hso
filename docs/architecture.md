# hso Architecture

## Intent

hso is a local-first research agent gateway. The current primary architecture is
TypeScript full-stack: a Next.js App Router application provides both the
operator workspace and the gateway API, while package workspaces hold reusable
runtime, storage, and schema code.

## Runtime Split

```text
Next.js operator workspace
  uses @ai-sdk/react useChat for /api/chat UI streaming
  reads sessions, events, and memory from Next route handlers

Next.js route handlers
  /api/health
  /api/sessions
  /api/sessions/[sessionId]/messages
  /api/sessions/[sessionId]/events
  /api/sessions/[sessionId]/memory
  /api/chat

packages/agent-runtime
  GatewayRuntime
  OpenAIAgentsRunner
  injected fake runners for tests

packages/storage
  GatewayStore
  data/gateway/gateway.sqlite3
  data/gateway/memory.sqlite3

packages/shared
  Zod schemas
  JSON-compatible API types
```

## Responsibilities

- `apps/web`: UI shell, route handlers, and AI SDK UIMessage streaming adapter.
- `packages/shared`: API schemas for `SessionRecord`, `GatewayEvent`,
  `MemoryRecord`, `CreateSessionRequest`, `SendMessageRequest`, and
  `SendMessageResponse`.
- `packages/storage`: SQLite persistence for `gateway_sessions`,
  `gateway_events`, and `memory_records`.
- `packages/agent-runtime`: OpenAI Agents SDK orchestration, memory append, event
  generation, and error event persistence.
- `packages/cli`: `hso start`, `hso status`, and `hso smoke`.

## Provider Policy

The TypeScript gateway is GPT-first for this phase:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `LLM_PROVIDER=gpt` as the default compatibility switch

xAI/custom/OAuth and manuscript tools remain future concerns until a new
TypeScript provider interface is added.

## Build-Time Boundary

Route handlers and runtime clients lazy-initialize storage and OpenAI Agents SDK
objects. `next build` must not require a model key or open SQLite files earlier
than request time.
