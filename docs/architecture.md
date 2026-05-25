# hso Architecture

## Intent

hso is a local-first agent gateway for research and manuscript workflows. It is
inspired by OpenClaw's gateway/session/agent shape, but keeps the core runtime in
Python and limits TypeScript to the operator UI.

## Runtime Split

```text
CLI
  hso start / hso status
    |
Python FastAPI Gateway
  SQLite-backed sessions/events, memory, tool execution
    |
Agent Runtime
  main agent, sub-agent orchestration, future OpenAI Agents SDK execution
    |
Workspace
  SQLite gateway state and memory, artifacts, manuscript outputs

Next.js UI
  operator workspace, event timeline, memory viewer
  calls Python gateway through /api/* only
```

## Python Responsibilities

- Gateway process and API surface.
- Session lifecycle and event stream ownership backed by local SQLite.
- Memory persistence and later compaction/retrieval backed by local SQLite.
- Agent and sub-agent orchestration.
- OpenAI Agents SDK and Responses API integration.
- Tool execution, permissions, and artifacts.
- Existing manuscript pipeline compatibility.

## TypeScript Responsibilities

- Next.js UI only.
- Session list, event timeline, memory panel, and message composer.
- Local API calls to the Python gateway.
- No direct OpenAI calls.
- No secret storage.
- No tool execution.

## Current P0 Components

- `hso.memory.MemoryStore`: SQLite-backed memory store.
- `hso.gateway.GatewaySQLiteStore`: async SQLite persistence for sessions and events.
- `hso.gateway.GatewayRuntime`: session/event/memory runtime backed by SQLite state.
- `hso.agents.LocalAgentOrchestrator`: deterministic main/sub-agent event producer for
  offline development.
- `hso.gateway.create_app`: FastAPI app factory exposing the local gateway API.
- `apps/web`: Next.js operator workspace shell.

## Next Migration Steps

1. Replace `LocalAgentOrchestrator` with an interface-backed OpenAI Agents SDK runner.
2. Bind OpenAI Agents SDK `SQLiteSession` ids to gateway session ids.
3. Add SSE or WebSocket event streaming.
4. Convert `search`, `analyze`, and `draft` into gateway tools.
5. Add approval boundaries for shell/file/browser tools.
