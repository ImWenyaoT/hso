# hso — local-first research agent gateway

hso is being migrated from a manuscript-only CLI pipeline into an OpenClaw-inspired,
local-first agent gateway for research workflows.

The target shape is:

- **Python core**: gateway, memory, agent runtime, sub-agent orchestration, tools,
  persistence, CLI, and LLM SDK integration.
- **TypeScript frontend only**: a Next.js operator workspace that talks to the Python
  gateway over local HTTP APIs.
- **CLI as control plane**: `hso start` launches the local gateway; existing
  manuscript commands remain available while they are promoted into gateway tools.

## Current P0 Runtime

```text
Next.js UI
  -> /api/* rewrite
Python FastAPI gateway
  -> GatewayRuntime
  -> GatewaySQLiteStore SQLite sessions/events
  -> MemoryStore SQLite memory
  -> LocalAgentOrchestrator
```

Implemented gateway endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | gateway readiness |
| `GET /api/sessions` | list local sessions |
| `POST /api/sessions` | create a session |
| `POST /api/sessions/{id}/messages` | run one local agent turn |
| `GET /api/sessions/{id}/events` | inspect agent/gateway events |
| `GET /api/sessions/{id}/memory` | inspect session memory |

## Run

Install Python dependencies:

```bash
uv sync --extra dev
```

For API-key backends, create `/Users/edward/Documents/hso/.env` from `.env.example`.
`LLM_PROVIDER=gpt` is the default and uses `OPENAI_API_KEY` /
`OPENAI_BASE_URL` through the OpenAI Responses API. Switch to
`LLM_PROVIDER=deepseek`, `custom`, or `xai` for OpenAI-compatible Chat
Completions endpoints, or `LLM_PROVIDER=oauth` after `uv run hso login` to use
the personal ChatGPT OAuth path.

Start the Python gateway:

```bash
uv run hso start --host 127.0.0.1 --port 8765
```

Check the gateway URL:

```bash
uv run hso status --host 127.0.0.1 --port 8765
```

The Next.js UI lives in `apps/web` and proxies `/api/*` to
`http://127.0.0.1:8765` by default. Install and run it separately:

```bash
cd apps/web
npm install
npm run dev
```

## Existing Manuscript Pipeline

The earlier manuscript pipeline is still present:

```bash
uv run hso search "diffusion model image editing" --allow-preprint --out output/demo/papers.json
uv run hso analyze --input output/demo/papers.json --out output/demo/profile.json
uv run hso draft --profile output/demo/profile.json --experiment data/processed/exp.json --papers output/demo/papers.json --out output/demo/draft
```

During the migration, these commands remain stable. The next step is to expose them
as gateway tools and agent/sub-agent workflows.

## Architecture Direction

hso intentionally does not use LangChain or LangGraph as the main spine. The
project uses explicit gateway/session/memory/tool boundaries and keeps the OpenAI
Agents SDK / Responses API integration behind the Python runtime layer.

The frontend must not call OpenAI directly. Secrets, memory writes, tool execution,
and agent orchestration stay inside the Python gateway.
