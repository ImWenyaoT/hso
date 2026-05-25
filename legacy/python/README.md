# hso legacy Python pipeline

This directory contains the previous Python implementation:

- manuscript `search`
- manuscript `analyze`
- manuscript `draft`
- the old FastAPI gateway reference
- the previous pytest/ruff/mypy suite

The TypeScript gateway is now the primary runtime at the repository root. This
legacy project is kept for regression checks and future tool migration.

## Run

```bash
cd legacy/python
uv sync --extra dev
uv run hso --help
uv run pytest
```

From the repository root, the optional regression command is:

```bash
npm run legacy:pytest
```
