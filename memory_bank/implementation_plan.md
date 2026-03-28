# HSO Base Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use a plan-execution workflow and implement this document task-by-task. Every step below uses checkbox syntax and includes a validation test.

**Goal:** Build the HSO base game: a user can enter a research starting point, get a structured research card, convert it into a paper project, organize a minimal paper structure, run a LaTeX build, and preview or export the resulting PDF in the desktop app.

**Architecture:** Build a single desktop application around the paper project as the core object. Keep the UI thin, keep orchestration in the application layer, use a local relational database for structured data, local filesystem storage for build-relevant files, and a separate local LaTeX worker for builds.

**Tech Stack:** Electron, React, Tailwind CSS, shadcn/ui, TypeScript, Node.js, Vercel AI SDK, SQLite, Drizzle, local filesystem, local worker process, `latexmk + xelatex + BibTeX`, structured logging, with Python only for auxiliary scripts and analysis tooling.

---

## Decision Freeze

The following decisions are already locked for the base game and should not be reopened during implementation unless the product direction changes:

1. Research card generation uses **real retrieval plus structured summarization**, not pure LLM generation.
2. Supported research inputs are **DOI, arXiv ID, paper title, and paper URL**.
3. The research card must separate **project-importable structured content** from **notes/noise that must not be imported**.
4. The paper project uses an **ordered section model**, not a free-form editor and not a raw LaTeX IDE.
5. Templates are **predefined template packages with slot-filling and mapping rules**, not arbitrary user-imported LaTeX projects.
6. The first release should support a **small honest template set**. Start with `generic article`, `IEEE`, and `Elsevier`. Add at most one more only if it fits the same structure model cleanly.
7. PDF files used during retrieval are **ingestion inputs for information extraction**, not first-class paper assets by default.
8. Build execution should bind to a **project revision snapshot** and record the source revision used for each build.
9. Build job states for the first release are **queued**, **running**, **succeeded**, and **failed**. Cancellation is out of scope for v1.
10. Preview should rely on the embedded desktop view or the system PDF viewer where appropriate, while always offering direct open and export actions.
11. The first release is allowed to run as a **local single-user assistant** with no full authentication system.
12. Build failure UX must provide **error location, readable summary, and repair suggestion**. Agent-assisted repair is an extension, not a required v1 baseline.
13. Desktop packaging targets **distribution level 1-2**: local use and small-scale internal testing, not app-store-grade public distribution.
14. Test planning and regression capture are **required from the beginning**, not a late hardening phase.
15. The default LaTeX toolchain for v1 is **`latexmk + xelatex + BibTeX`**.
16. Asset ownership must support **`project_only`**, **`selected_projects`**, and **`all_projects`** visibility modes.
17. Retrieval priority should be frozen as **DOI -> arXiv ID -> title search -> URL parsing helper -> user confirmation**.
18. The app must detect the controlled LaTeX toolchain before first build and guide the user through a managed installation if it is missing.
19. Project-local metadata must live under **`.hso`** inside each project folder, while global SQLite, global asset store, toolchain, and caches must live under app data.
20. Windows remains in v1 scope, and the formal release gate must pass on both macOS and Windows.
21. **TypeScript** is the primary implementation language for the desktop shell, renderer, orchestration layer, shared contracts, and local worker; **Python** is auxiliary only and may be used for scripts, analysis, or offline tooling.

## Base Game Scope

This plan only covers the minimum usable product loop:

1. User enters a keyword or a seed paper reference.
2. System retrieves objective paper data and generates a structured research card.
3. User converts selected structured content into a paper project.
4. User selects a supported template and edits a basic paper structure.
5. User attaches a small set of build-relevant assets.
6. System runs a LaTeX build and shows preview, status, and human-readable errors inside the desktop experience.

This plan does **not** cover collaboration, advanced real-time sync, rich analytics, machine learning, arbitrary LaTeX project import, complex template compatibility, or full IDE behavior.

## Working Rules For AI Developers

1. Keep each task small and independently reviewable.
2. Do not introduce any feature not required for the base game.
3. Preserve clear boundaries between information retrieval, paper project management, and LaTeX build execution.
4. Treat every validation step as mandatory.
5. If a step fails validation, stop and fix it before moving on.
6. Do not replace any frozen decision above with a “temporary flexible design.”
7. When a bug or failure mode is discovered, leave behind a reproducible test case or regression checklist whenever possible.

## Task 1: Lock The Base Game Contract

**Target outcome:** The team agrees on the exact user journey, object names, and non-goals for the first build.

- [ ] **Step 1: Create a one-page base game brief**
Write a short project brief that defines the six core user actions in order: enter input, receive research card, convert to paper project, choose template, edit structure, build and preview.

Test:
- Review the brief and confirm every action maps directly to a sentence in [PRD.md](/Users/edward/Documents/hso/memory_bank/PRD.md).
- Confirm the brief contains no features outside the base game.

- [ ] **Step 2: Freeze the core object vocabulary**
Document the exact meaning of these objects: `research input`, `research card`, `paper project`, `template`, `section`, `asset`, `build job`, `build result`, `reference source`.

Test:
- Ask a second developer to explain the difference between `research card` and `paper project` using only the document.
- The explanation must match the PRD without ambiguity.

- [ ] **Step 3: Freeze non-goals**
Create an explicit non-goals list for the first implementation: no collaboration, no arbitrary LaTeX project import, no subjective academic judgment, no full-featured editor, no build cancellation, no custom user template upload, no app-store-grade distribution workflow in v1.

Test:
- Review the list against [PRD.md](/Users/edward/Documents/hso/memory_bank/PRD.md) section 8.
- Confirm no out-of-scope feature remains implied as “maybe included now.”

## Task 2: Define Repository Skeleton And Delivery Boundaries

**Target outcome:** AI developers know what top-level apps and services exist before writing implementation code.

- [ ] **Step 1: Define the minimum repository structure**
Document the initial app and service layout for the base game: Electron desktop shell, renderer UI, application/orchestration layer, LaTeX worker, shared schema/contracts, and docs. Treat TypeScript as the default implementation language across all runtime-owned codepaths.

Test:
- Review the layout and verify every top-level part has exactly one clear responsibility.
- Confirm there is no duplicate responsibility between desktop UI and worker.
- Confirm no core runtime module silently introduces Python as a parallel mainline implementation language.

- [ ] **Step 2: Define deployment ownership per runtime**
Document which parts run inside the Electron main process, which parts run in the renderer, which parts run in the local worker runtime, and which optional online services are managed separately.

Test:
- Review the mapping against [tech_stack.md](/Users/edward/Documents/hso/memory_bank/tech_stack.md).
- Confirm no heavy LaTeX build step is assigned to the renderer process.

- [ ] **Step 3: Define environment boundary list**
List the required environment categories only: local database, local filesystem storage, AI provider, local worker runtime, and optional error tracking.

Test:
- Confirm every category maps to a required runtime dependency.
- Confirm no optional future-only service is included.

- [ ] **Step 4: Define local storage layout**
Document the frozen directory split between project-local storage and global app-data storage. Project-local metadata must live under `.hso/`, while global SQLite, global asset store, controlled toolchain, and caches live under app data.

Test:
- Confirm project-local build outputs and metadata can move with the project folder.
- Confirm shared assets and toolchain data do not need to be duplicated per project.

- [ ] **Step 5: Define quality boundary list**
Document the minimum quality infrastructure for v1: structured logs, trace ids, focused automated tests, manual regression checklist, and a bug-to-test workflow.

Test:
- Confirm each item supports either local debugging or regression prevention.
- Confirm the list is treated as required infrastructure rather than deferred polish.

## Task 3: Model The Core Domain

**Target outcome:** The base game data model is stable enough to support the full first user loop.

- [ ] **Step 1: Define the minimum entities**
Document the minimum entities required for the base game: `research_card`, `paper_project`, `paper_section`, `template`, `asset`, `reference_source`, `build_job`, `build_artifact`, and `error_event`. Treat `user` as optional infrastructure for later expansion, not a required v1 domain object.

Test:
- Check that each entity directly supports at least one step of the base game flow.
- Remove any entity that does not support a first-release user action.

- [ ] **Step 2: Define required fields for each entity**
List only the fields needed to make the first release work, including identifiers, status fields, timestamps, revision fields, and minimal metadata.

Test:
- For each field, ask “what first-release behavior breaks if this field does not exist?”
- If there is no concrete answer, remove the field.

- [ ] **Step 3: Define entity relationships**
Document the relationships between research card and paper project, paper project and template, paper project and sections, paper project and assets, paper project and reference sources, paper project and build job, and build job and build artifact.

Test:
- Walk through the base game flow using only the relationship diagram or table.
- Confirm the flow can be explained without inventing extra objects.

## Task 4: Plan The User-Facing Screens

**Target outcome:** The desktop app includes only the minimum screens needed to complete the base game loop.

- [ ] **Step 1: Define the minimum route list**
Document the minimum routes or screens: input screen, research card result screen, paper project detail screen, template selection area, asset area, build status area, and PDF preview/export area.

Test:
- Trace the full user journey from start to preview.
- Confirm every route exists for a reason and no extra route is needed.

- [ ] **Step 2: Define each screen’s single responsibility**
For every screen, write one sentence for its main job and one sentence for what it must not do.

Test:
- Review the list and confirm no screen owns both orchestration logic and heavy domain logic.
- If a screen appears to “know too much,” move that responsibility back to the application layer.

- [ ] **Step 3: Define empty, loading, success, and error states**
Document the state variants needed for each screen in the first release.

Test:
- For every screen, verify there is a visible behavior for “nothing yet,” “in progress,” “finished,” and “failed.”
- Confirm no state depends on future collaboration or always-online behavior.

## Task 5: Plan The Research Input Flow

**Target outcome:** A user can start from a keyword or seed paper and receive a structured research card.

- [ ] **Step 1: Define supported input types**
Document the exact first-release input types: keyword text, DOI, arXiv ID, paper title, and paper URL. Explicitly reject arbitrary free-form reference text.

Test:
- Confirm all supported input types align with the product decision freeze.
- Confirm no sixth input type is silently added.

- [ ] **Step 2: Define retrieval priority and confirmation flow**
Document the first-release lookup order as DOI lookup, arXiv ID lookup, title search, URL parsing helper, and candidate confirmation by the user before solidifying a `reference_source`.

Test:
- Confirm URL is treated only as a parsing helper rather than the primary retrieval path.
- Confirm title search can fall back to a candidate list rather than assuming a single exact match.

- [ ] **Step 3: Define the research card output contract**
Document the minimum research card sections for the base game:
`topic_label`, `key_papers`, `trend_summary`, `distribution_summary`, `project_importable_sections`, `reference_candidates`, `notes`, and `convert_to_project_action`.
Mark which fields are importable into the paper project and which are not.

Test:
- Confirm the output is structured and objective rather than opinionated.
- Confirm each fact-bearing section can be traced back to retrieved sources.

- [ ] **Step 4: Define failure behavior for research generation**
Document what happens when the system cannot generate a usable research card: visible error, retry action, and preserved user input.

Test:
- Run a tabletop review of a failed research request.
- Confirm the user is never dropped into a dead end with no recovery path.

## Task 6: Plan The Convert-To-Project Flow

**Target outcome:** A research card can become a paper project without hidden manual work.

- [ ] **Step 1: Define the conversion action**
Document exactly what data moves from research card into paper project creation. Import only project-ready structured sections, selected title candidate, and selected reference candidates. Do not import raw notes, retrieval traces, or agent reasoning.

Test:
- Confirm the conversion does not copy unnecessary research-only metadata.
- Confirm the paper project starts with enough context to be usable immediately.

- [ ] **Step 2: Define the initial paper project state**
Document the required initial state for a new paper project: title placeholder or imported title candidate, selected source card, ordered sections, no assets yet, no completed builds yet, template unselected or defaulted, and initial revision `1`.

Test:
- Review the initial state and confirm a user can continue the flow without hidden setup steps.

- [ ] **Step 3: Define project creation failure handling**
Document what happens if project creation fails after the user clicks convert.

Test:
- Confirm the user can retry without losing the source research card.
- Confirm the failure state is visible in the UI and in logs.

## Task 7: Plan The Template Selection Flow

**Target outcome:** A paper project can be attached to a supported template in a controlled way.

- [ ] **Step 1: Define the initial template catalog**
Start the first release with `generic article`, `IEEE`, and `Elsevier`. Add at most one additional template only if it can reuse the same normalized section model and worker pipeline.

Test:
- Confirm every listed template is supportable by the worker and preview flow.
- Remove any template that requires special-case logic not yet planned.

- [ ] **Step 2: Define template selection behavior**
Document when a template is selected, replaced, or reset. The project should preserve normalized content and assets while applying template-specific title labels, section labels, and rendering rules. If a template cannot map a section cleanly, the system must surface that mismatch explicitly.

Test:
- Review the behavior and confirm template changes do not silently destroy user-managed content or assets.

- [ ] **Step 3: Define unsupported-template behavior**
Document how the system responds when a user wants something outside the supported catalog.

Test:
- Confirm the UX clearly says “not supported yet” instead of pretending broader compatibility exists.

## Task 8: Plan The Paper Structure Flow

**Target outcome:** A user can manage the minimum paper structure without needing a full free-form editor.

- [ ] **Step 1: Define the editable structure units**
Document the first-release editable units as ordered normalized sections, such as `title`, `abstract`, `introduction`, `related_work`, `method`, `results`, `conclusion`, and `references_placeholder`. Template-facing display labels may differ, but the project model should keep stable normalized section types.

Test:
- Confirm the unit list is enough to create a meaningful paper draft.
- Confirm it does not imply full arbitrary LaTeX editing.

- [ ] **Step 2: Define the minimum editing operations**
Document the allowed operations for first release: create section, rename display label when allowed, reorder section, edit content, attach figure asset, remove section.

Test:
- Walk through a simple paper setup and confirm each required action is covered.
- Confirm no unnecessary “power user” editing mode is included.

- [ ] **Step 3: Define structure validation rules**
Document a small set of validation rules, such as required title, no empty section labels, supported file types for figure uploads, and maximum asset count for first release.

Test:
- Review each rule and confirm it prevents a realistic failure in build or preview.
- Remove any rule that exists only for theoretical completeness.

## Task 9: Plan The Asset And Reference Flow

**Target outcome:** Users can attach the minimum build-relevant files and keep reference data separate from noisy ingestion inputs.

- [ ] **Step 1: Define supported asset types**
Document the first-release supported build assets as figure images only. Model external paper references separately as structured `reference_source` records rather than generic file assets. Treat source PDFs as optional ingestion inputs, not first-class project assets by default, and store them locally only when needed.

Test:
- Confirm each asset or reference type supports a concrete base-game action.
- Exclude any type that is not used by the first paper flow.

- [ ] **Step 2: Define asset ownership scope**
Document the first-release asset visibility modes as `project_only`, `selected_projects`, and `all_projects`. `selected_projects` must allow the user to explicitly choose multiple projects. `all_projects` must expose the asset to every project without duplicating the file.

Test:
- Confirm the same asset can be reused across multiple projects without redundant storage.
- Confirm the UI model supports both “share to all” and “share to selected projects.”

- [ ] **Step 2.5: Define shared asset storage behavior**
Document that shared assets are copied into the global controlled asset store under app data, while projects record only asset references and never depend on external original file paths.

Test:
- Confirm shared assets remain valid even if the source import path disappears.
- Confirm project references can resolve against the global asset store without duplicating files.

- [ ] **Step 3: Define upload lifecycle**
Document the upload states for build-relevant files: selected, uploading, stored, linked to project, failed.

Test:
- Confirm every upload state has a visible UI state and a persistent system state.

- [ ] **Step 4: Define asset failure handling**
Document behavior for wrong file type, oversize file, upload failure, and broken linked asset.

Test:
- Review each case and confirm the user is told what happened and what to do next.

## Task 10: Plan The Build Job Flow

**Target outcome:** Users can trigger a build from a paper project and track its outcome.

- [ ] **Step 1: Define build trigger rules**
Document when a build can start, what minimum project state is required, and how duplicate clicks are handled. Each build must bind to a specific source revision snapshot.

Test:
- Confirm the rules prevent invalid or duplicate builds from being created accidentally.

- [ ] **Step 2: Freeze build toolchain contract**
Document the v1 build contract as `latexmk + xelatex + BibTeX`, and require supported templates to conform to this toolchain rather than introducing per-template build paths.

Test:
- Confirm the initial template catalog can be compiled through the same toolchain.
- Confirm unsupported templates are rejected before they create toolchain fragmentation.

- [ ] **Step 2.5: Define toolchain installation contract**
Document that the app detects the controlled toolchain before first build, does not depend on a user-managed system TeX install, and provides an app-guided installation flow backed by a controlled installer script.

Test:
- Confirm first-run build UX can succeed without prior manual TeX setup.
- Confirm the controlled toolchain installs under app data rather than inside a project folder.

- [ ] **Step 3: Define build job states**
Document the build states as `queued`, `running`, `succeeded`, and `failed`.

Test:
- Confirm every state maps to a visible UI message and a stored backend status.

- [ ] **Step 4: Define build outputs**
Document the minimum outputs: previewable PDF path, open-in-viewer action, export action, build log summary, failure summary, timestamp, and source project revision reference.

Test:
- Review the output contract and confirm it is enough for a user to understand what happened after a build.

## Task 11: Plan The LaTeX Worker Boundary

**Target outcome:** The local LaTeX worker is isolated and only handles execution concerns.

- [ ] **Step 1: Define worker inputs**
Document the exact worker input package: project revision snapshot, selected template package, linked build assets, build identifier, and local output destination.

Test:
- Confirm the worker input contains everything needed for build execution and nothing that requires UI knowledge.

- [ ] **Step 2: Define worker outputs**
Document the exact worker outputs: success/failure state, artifact locations, log summary, error location, readable error summary, repair suggestion, and elapsed time.

Test:
- Confirm the output package is enough for the application layer to update the project without parsing raw worker internals.

- [ ] **Step 3: Define worker restrictions**
Document what the worker must never do: user orchestration, project creation logic, UI state management, academic reasoning, and arbitrary project mutation.

Test:
- Review the restriction list and confirm the worker remains a pure execution service.

## Task 12: Plan Error Reporting And Recovery

**Target outcome:** The base game remains debuggable and recoverable when things go wrong.

- [ ] **Step 1: Define traceability fields**
Document the minimum IDs to carry through the system: request id, decision id, project id, project revision, and build job id.

Test:
- Walk one sample request from input to build preview.
- Confirm every major step can be traced using IDs alone.

- [ ] **Step 2: Define user-visible error classes**
Document the first-release error classes: research generation failure, project creation failure, upload failure, build failure, unsupported template, unsupported input, and validation failure.

Test:
- Confirm each error class maps to exactly one user-facing message pattern and one logging category.

- [ ] **Step 3: Define retry rules**
Document which actions are safe to retry and which require explicit user confirmation.

Test:
- Review the retry table and confirm no destructive action is retried silently.

## Task 13: Plan End-To-End Acceptance Tests

**Target outcome:** The team has a concrete checklist proving the base game works.

- [ ] **Step 1: Define the happy-path acceptance test**
Write a manual or automated end-to-end scenario: launch the desktop app, enter keyword or supported seed paper input, receive research card, convert to paper project, select template, add one figure asset, build, preview success.

Test:
- Confirm the scenario covers the full base game loop and nothing beyond it.

- [ ] **Step 2: Define the recovery-path acceptance test**
Write one end-to-end scenario where the build fails first, the user sees a clear error location, readable summary, and repair suggestion, fixes the issue, and successfully rebuilds.

Test:
- Confirm the recovery path validates both visibility and retry behavior.

- [ ] **Step 3: Define the non-goal guardrail test**
Write a checklist proving unsupported features are explicitly rejected, such as arbitrary LaTeX import, unsupported template upload, and unsupported free-form seed reference input.

Test:
- Confirm the product fails gracefully and honestly instead of appearing partially supported.

- [ ] **Step 4: Define the bug-to-regression workflow**
Document how a discovered bug should become a stable local repro and then a regression check: capture trace id and logs, isolate root cause, add a focused test or explicit regression checklist, and verify the fix against that artifact.

Test:
- Confirm the workflow can be followed without inventing a new QA process each time.
- Confirm the workflow matches the v1 goal of planning testing from the beginning.

## Task 14: Prepare Implementation Handoff

**Target outcome:** AI developers can start execution without reinterpreting the plan.

- [ ] **Step 1: Order the implementation sequence**
Arrange the final implementation order as: skeleton, domain model, routes, research flow, project conversion, template flow, structure flow, asset/reference flow, build flow, worker, error handling, acceptance tests.

Test:
- Review the sequence and confirm each later step depends only on earlier completed work.

- [ ] **Step 2: Mark independent work streams**
Identify which tasks can run in parallel without creating merge conflicts, such as route planning versus worker boundary planning.

Test:
- Confirm each parallel stream has a separate ownership boundary.

- [ ] **Step 2.5: Freeze platform release boundary**
Document the platform policy as `macOS first in development, Windows still required for v1 release, Linux deferred`.

Test:
- Confirm the development order and the formal release gate do not conflict.
- Confirm the v1 release checklist explicitly requires both macOS and Windows to pass.

- [ ] **Step 3: Add shipping criteria**
Document the minimum release gate: full happy path works, one failure path works, supported-template list is honest, logs and trace IDs are visible, desktop preview and export both work, there is no known blocker in the build-preview loop, and both macOS and Windows pass the formal release checklist.

Test:
- Review the release gate and confirm it measures product readiness rather than implementation effort.

## Self-Review Checklist

Before implementation begins, verify the plan against this checklist:

- [ ] Every step is small enough for an AI developer to execute without inventing extra scope.
- [ ] Every step includes a validation test.
- [ ] The plan stays inside the base game boundary.
- [ ] The plan treats the paper project as the core object.
- [ ] The plan preserves high cohesion and low coupling between desktop UI, application layer, and LaTeX worker.
- [ ] The plan does not imply a full LaTeX IDE or research super-app.
- [ ] The plan reflects the frozen product decisions already agreed in discussion.
- [ ] The plan treats tests, logs, and regression capture as first-class engineering work rather than end-stage polish.
