# 5 分钟体验：跑通 TypeScript hso gateway

## 0. 准备

```bash
cd /Users/edward/Documents/hso
npm install
```

## 1. 配置模型

从 `.env.example` 复制 `.env`，至少配置：

```bash
LLM_PROVIDER=gpt
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5.4-mini
```

## 2. 启动 Web + Gateway

```bash
npm run dev
```

Next.js 会提供 UI 和 gateway API。主路径不再需要单独启动 Python
FastAPI。

## 3. 跑 CLI smoke

```bash
npm run hso -- smoke
```

预期输出类似：

```json
{
  "session_id": "ses_...",
  "event_count": 3,
  "final": "hso-ok"
}
```

这会写入：

- `data/gateway/gateway.sqlite3`
- `data/gateway/memory.sqlite3`

## 4. 验证

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## 5. 旧 manuscript pipeline

旧 Python pipeline 已移动到 `legacy/python`。需要跑旧流程时：

```bash
cd legacy/python
uv sync --extra dev
uv run hso search "diffusion model image editing" --allow-preprint --out output/demo/papers.json
uv run hso analyze --input output/demo/papers.json --out output/demo/profile.json
uv run hso draft --profile output/demo/profile.json --experiment tests/fixtures/experiment.json --papers output/demo/papers.json --out output/demo/draft
```
