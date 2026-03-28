# Repository Guidelines

# IMPORTANT:
# Always read memory_bank/@architecture.md before writing any code. Include entire database schema.
# Always read memory_bank/@PRD.md before writing any code.
# After adding a major feature or completing a milestone, update memory_bank/@architecture.md.

## Project Structure & Module Organization
This repository is currently a planning workspace for HSO, a low-barrier academic paper workbench. Core product and architecture context lives in `PRD.md`, `idea.md`, and `tech_stack.md`. Task tracking belongs in `tasks/todo.md`. As implementation starts, keep app code under `src/`, tests under `tests/`, static assets under `assets/`, and long-form design or decision notes under `docs/`.

## Build, Test, and Development Commands
There is no scaffolded runtime yet, so contributors should treat the current repo as docs-first. Use:

- `ls` or `rg --files` to inspect repository contents quickly
- `sed -n '1,160p' PRD.md` to review product scope before editing
- `git status` and `git diff` once the repository is initialized

When the app is scaffolded, standardize on explicit commands such as `npm run dev`, `npm run build`, `npm run lint`, and `npm run test`, and document them in the project README.

## Coding Style & Naming Conventions
Keep edits minimal and directly tied to product scope. Use Markdown for planning docs and prefer short sections, numbered lists, and precise wording over long narrative paragraphs. For future code, use 2-space indentation in frontend files, descriptive file names like `paper-project-service.ts`, and add function-level comments for non-trivial functions. Prefer kebab-case for Markdown files and feature docs, for example `latex-build-flow.md`.

## Modularity Rules

**High cohesion, low coupling — per `idea.md` DDD values.**

- Each file owns a single named concern: `paper-project.service.ts` does service logic; `paper-project.repository.ts` does data access; `paper-project.types.ts` holds types. A file mixing routing, business logic, *and* DB calls is a design smell — split it.
- **File length is a signal, not a rule.** A 400-line file with a single tight concern is fine. A 150-line file that straddles two domains needs to be split. Ask "does this file have one job?" not "how many lines is it?"
- Domain boundaries are hard walls: the **Information Retrieval** domain (`src/retrieval/`) and the **LaTeX Build** domain (`src/latex/`) must not import from each other. Cross-domain orchestration belongs exclusively in the Agent layer — this is the direct expression of `idea.md`'s "two independent domains, coordinated by the top-level orchestrator Agent."
- Map every file to exactly one of the three architecture layers (Web App / Agent+Application / Execution). A file that spans layers must be refactored.
- When scaffolding a new feature, write the file breakdown first (`service`, `repository`, `types`, `handler`) and confirm before implementing. This prevents the "start with one file and keep adding" pattern that creates monoliths.
- Do not create a catch-all barrel `index.ts` that re-exports the entire domain.

## Testing Guidelines
No automated test framework is checked in yet. Until code exists, verify documentation changes by checking factual consistency across `PRD.md`, `idea.md`, and `tech_stack.md`. Once implementation begins, create tests in `tests/` with names like `paper-project.test.ts` or `test_latex_build.py`, and require contributors to run the relevant focused test command before submitting changes.

## Commit & Pull Request Guidelines
Local git history is not available in this workspace, so no repository-specific commit pattern can be inferred yet. Adopt Conventional Commits going forward, e.g. `docs: refine repository guidelines` or `feat(agent): add plan executor`. PRs should include a short summary, impacted files, verification performed, and screenshots only when UI behavior changes.

## Agent-Specific Notes
Follow the repo-level workflow in `CLAUDE.md`: plan first, track work in `tasks/todo.md`, verify before marking done, and avoid speculative over-engineering.
