# hso — TypeScript local-first research agent gateway

hso is a TypeScript full-stack research agent gateway. The main runtime is
Next.js App Router route handlers plus package-level TypeScript services for
schema validation, SQLite persistence, OpenAI Agents SDK orchestration, Vercel
AI SDK UI streaming, and a small CLI.

## Workspace

```text
apps/web                  Next.js operator workspace and route handlers
packages/shared           Zod schemas and JSON-compatible TypeScript types
packages/storage          better-sqlite3 sessions, events, and memory
packages/agent-runtime    OpenAI Agents SDK turn orchestration
packages/cli              Minimal hso start/status/smoke CLI
data/gateway              Local SQLite gateway state
```

## Gateway API

The Next app owns the gateway API directly:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | readiness check |
| `GET /api/sessions` | list sessions |
| `POST /api/sessions` | create a session |
| `POST /api/sessions/[sessionId]/messages` | run one agent turn and return JSON events |
| `GET /api/sessions/[sessionId]/events` | inspect persisted events |
| `GET /api/sessions/[sessionId]/memory` | inspect persisted memory |
| `POST /api/chat` | Vercel AI SDK UIMessage stream backed by the same runtime |

## Run

```bash
npm install
npm run dev
```

Open the printed Next.js URL. The UI talks to the local route handlers directly;
there is no Python FastAPI proxy in the primary path.

For real model calls, create `.env` from `.env.example`:

```bash
LLM_PROVIDER=gpt
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5.4-mini
```

## CLI

```bash
npm run hso -- start
npm run hso -- status
npm run hso -- smoke
```

`smoke` loads `.env`, runs one real OpenAI Agents SDK turn, and writes sessions,
events, and memory to `data/gateway/*.sqlite3`.

## Checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
