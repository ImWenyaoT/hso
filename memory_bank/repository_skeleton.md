# HSO Repository Skeleton And Delivery Boundaries

## Purpose

This document is the Step 2 source of truth for the HSO base game.

It freezes:

1. The minimum repository structure.
2. Runtime ownership across Electron main, renderer, and local worker.
3. The required environment dependency categories.
4. The boundary between project-local storage and global app-data storage.
5. The minimum quality infrastructure that must exist from the beginning.

This document does **not** define the core domain entities, field schema, or entity relationships. Those belong to Step 3.

## 1. Minimum Repository Structure

The initial repository layout for the base game should be:

1. `src/main/`
   Owns the Electron main process: app lifecycle, window management, native dialogs, app-data path resolution, IPC registration, controlled process spawning, and desktop-level integrations.

2. `src/renderer/`
   Owns the React renderer UI: user input, view state, screen composition, interaction feedback, and presentation of research cards, paper projects, build status, and preview actions.

3. `src/application/`
   Owns application-layer orchestration and use-case flows: research-card generation coordination, convert-to-project flow, template selection flow, build triggering, error summarization, and cross-domain coordination.

4. `src/worker/`
   Owns the isolated local worker runtime for heavy execution tasks, especially the controlled LaTeX build pipeline and related filesystem-safe execution steps.

5. `src/shared/`
   Owns runtime-shared contracts: TypeScript schemas, IPC contracts, DTOs, enums, status models, validation helpers, and shared constants needed by more than one runtime boundary.

6. `docs/`
   Owns implementation-facing engineering notes that are not memory-bank source-of-truth documents.

7. `tests/`
   Owns focused automated tests and regression cases for the base game.

8. `memory_bank/`
   Owns product, architecture, planning, scope, and milestone source-of-truth documents.

9. `assets/`
   Owns repository-managed static assets needed by the application itself, such as icons or packaged template fixtures. It does not own user project assets.

TypeScript is the default implementation language for every runtime-owned codepath in `src/`.
Python may exist only in auxiliary scripts or analysis tooling outside the main runtime path.

## 2. Runtime Ownership Per Runtime

### Electron Main Process

The Electron main process owns:

1. Desktop application lifecycle.
2. Native window creation and top-level navigation bootstrap.
3. Native file and folder pickers.
4. Resolution of app-data directories and project path access handoff.
5. Registration of controlled IPC entry points.
6. Spawning and supervising the local worker process.
7. Launching external preview helpers when the system PDF viewer is used.
8. Guarding privileged desktop capabilities so they are not executed directly in the renderer.

The main process does **not** own heavy LaTeX builds, domain orchestration, or UI rendering.

### Renderer Process

The renderer owns:

1. Screen rendering and interaction state.
2. User-driven actions such as entering research input, reviewing a research card, converting to project, selecting a template, editing normalized structure, triggering a build, and opening preview/export actions.
3. Display of loading, success, failure, and empty states.
4. Rendering human-readable build feedback that has already been prepared by the application layer.

The renderer does **not** own heavy build execution, direct database control, or filesystem/process privileges beyond approved IPC calls.

### Local Worker Runtime

The local worker owns:

1. Controlled LaTeX build execution.
2. Toolchain invocation through the managed `latexmk + xelatex + BibTeX` pipeline.
3. Build workspace preparation from a project revision snapshot.
4. Collection of raw build logs, artifact outputs, and execution-level failure details.
5. Returning structured execution results back to the application layer.

The worker does **not** own desktop windowing, long-lived UI state, or product-level screen decisions.

### Optional Online Services

Optional online services are managed separately from the local desktop runtimes.

They may include:

1. AI provider access for structured summarization or repair suggestions.
2. Optional remote error aggregation.
3. Optional retrieval-related network access required to resolve supported research inputs.

These services are supporting dependencies, not the primary runtime host of the app.

## 3. Environment Boundary List

Only the following environment dependency categories are required for Step 2:

1. `local_database`
   The local relational store used by the desktop app, implemented with SQLite.

2. `local_filesystem_storage`
   The filesystem boundary used for project folders, project-local metadata, build artifacts, global asset storage, template materialization, logs, and caches.

3. `ai_provider`
   The model-facing dependency used when the product needs structured summarization or readable repair suggestions.

4. `local_worker_runtime`
   The isolated local execution environment that runs the managed LaTeX toolchain and related heavy work.

5. `optional_error_tracking`
   A conditional remote error-reporting dependency that may be enabled without becoming a hard base-game requirement.

No additional future-only service categories should be frozen here.
In particular, Step 2 does not add collaboration backends, sync services, auth platforms, queue infrastructure, or remote build infrastructure.

## 4. Local Storage Layout

The local storage boundary is frozen into two layers.

### Project-Local Storage

Each paper project folder owns the user-visible project files plus a project-local metadata directory:

1. `.hso/`
   Project-local metadata, revision-relevant state, build-relevant local bookkeeping, and project-scoped outputs that should move with the project folder.

2. Project-visible content files
   The normalized paper content, project-specific materials, and generated outputs that the user expects to travel with the project.

Project-local storage must remain portable with the project folder.
If the user moves the project directory to another machine with the same supported app environment, the project-local metadata and outputs should move with it.

### Global App-Data Storage

Global app-data owns resources that should not be duplicated per project:

1. Global SQLite database.
2. Global asset store for reusable assets under the frozen ownership model.
3. Managed LaTeX toolchain installation.
4. App-level caches.
5. Cross-project logs and diagnostics.

Global app-data is machine-local support infrastructure.
It is not required to move with one specific project folder.

## 5. Quality Boundary List

The minimum required quality infrastructure for v1 is:

1. Structured logs.
   Every major application and worker action should emit machine-readable logs suitable for local debugging.

2. Trace IDs.
   Cross-runtime actions should be traceable from UI-triggered request to worker outcome and visible failure.

3. Focused automated tests.
   The repository should include small, purpose-built automated tests for contracts, orchestration boundaries, and critical regressions rather than waiting for a late broad test phase.

4. Manual regression checklist.
   The base game flow should have a maintained manual checklist that can be run before milestone acceptance.

5. Bug-to-test workflow.
   When a failure mode is discovered, the team should capture a reproducible regression case or explicit checklist item so the same bug is less likely to recur silently.

These items are required engineering infrastructure, not deferred polish.

## 6. Out-Of-Scope For Step 2

The following topics would prematurely enter Step 3 and must not be frozen in this document:

1. The final entity list for the domain model.
2. Required fields for domain entities.
3. Database table definitions or schema details.
4. Relationship diagrams between domain entities.
5. Screen-specific data payload schemas.
6. Exact IPC payload field sets beyond the fact that shared contracts exist.

Step 2 defines boundaries and ownership only.
Step 3 will define the domain model that lives within those boundaries.

## 7. Verification Notes

Step 2 should be validated against the following checks:

1. Every top-level repository part has one clear responsibility.
2. No heavy LaTeX build step is assigned to the renderer.
3. The environment list contains only required runtime dependency categories.
4. Project-local `.hso/` data and project outputs can move with the project folder.
5. Global SQLite, global asset storage, toolchain files, and caches do not need to be duplicated per project.
6. The quality boundary is treated as required infrastructure rather than optional later hardening.
7. This document does not define Step 3 entities, fields, or relationships.
