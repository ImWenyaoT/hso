# HSO Architecture Notes

## Purpose

This file explains what the current key documentation files do so future developers can find the right source of truth without re-deriving intent from scattered notes.

The repository is still in a docs-first stage. These notes describe document ownership and architectural responsibility, not implementation code modules yet.

## Current Source-Of-Truth Files

### `memory_bank/PRD.md`

Owns the product definition for HSO.

It answers:

1. What HSO is.
2. Who the product is for.
3. What the first-release product loop is trying to achieve.
4. What the first-release scope and non-goals are at the product level.

Use this file when the question is about product intent, user value, domain emphasis, or v1 product boundaries.

### `memory_bank/tech_stack.md`

Owns the default technical direction and selection criteria.

It answers:

1. Which technologies are the current default recommendations.
2. Why the stack is desktop-first.
3. Why `TypeScript` is the main implementation language.
4. Which supporting technologies are core, conditional, or deferred.

Use this file when the question is about stack selection, runtime preferences, toolchain direction, or engineering baseline assumptions.

### `memory_bank/implementation_plan.md`

Owns the execution order for building the HSO base game.

It answers:

1. Which tasks exist.
2. What each task is supposed to deliver.
3. How each task should be validated.
4. Which product and engineering decisions are already frozen before implementation begins.

Use this file when the question is about sequencing, task boundaries, delivery checkpoints, or what must happen before later steps can start.

### `memory_bank/repository_skeleton.md`

Owns the frozen Step 2 repository skeleton and runtime delivery boundaries for the base game.

It answers:

1. Which top-level repository areas exist before implementation starts.
2. Which responsibilities belong to Electron main, renderer, and local worker.
3. Which environment dependency categories are required for v1.
4. How project-local storage differs from global app-data storage.
5. Which quality infrastructure is mandatory from the beginning.

Use this file when the question is about repository layout, runtime ownership, local-vs-global storage boundaries, or Step 2 delivery guardrails.

### `memory_bank/base_game_contract.md`

Owns the frozen Step 1 contract for the base game.

It answers:

1. What the exact six-step base game loop is.
2. What the core object vocabulary means.
3. Which non-goals are explicitly outside v1.
4. Which boundaries later steps must treat as already fixed.

Use this file when the question is about the exact meaning of `research card`, `paper project`, `build result`, `reference source`, or the precise Step 1 base-game boundary.

This file should be treated as the immediate source of truth for Step 1 terminology and scope guardrails.

### `memory_bank/progress.md`

Owns milestone tracking for completed documentation or implementation work.

It answers:

1. What has been completed.
2. What artifacts were produced.
3. Which validations were used to accept the work.
4. Where the next boundary or handoff starts.

Use this file when the question is about project history, completed milestones, or whether a task has already been accepted.

## Supporting Files

### `idea.md`

Owns the higher-level architectural philosophy behind HSO, including `LUI`, `thin client`, `DDD`, `smart agent, dumb tool`, design tokens, and the long-term multi-agent direction.

This file is upstream guidance. It should shape the memory bank, but it is not the day-to-day execution contract by itself.

### `tasks/todo.md`

Owns the working session checklist and review trail for the current repository tasks.

It is the operational tracking file for active work, while `memory_bank/progress.md` is the accepted milestone record.

## Practical Reading Order

Future developers should usually read in this order before making non-trivial changes:

1. `memory_bank/architecture.md`
2. `memory_bank/PRD.md`
3. `memory_bank/tech_stack.md`
4. `memory_bank/implementation_plan.md`
5. `memory_bank/base_game_contract.md` when Step 1 terminology or scope boundaries matter
6. `memory_bank/repository_skeleton.md` when Step 2 repository and runtime boundaries matter
7. `memory_bank/progress.md` to understand what has already been accepted
