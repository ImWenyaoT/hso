# HSO Base Game Contract

## 1. Base Game Brief

This document is the single source of truth for Step 1 of the HSO base game contract. It freezes the first-release user loop, the core object vocabulary, and the explicit non-goals for implementation.

The base game contains exactly six user actions, in this order:

1. **Enter research input**
   The user starts from a keyword or a supported seed paper reference. The goal is to provide a low-barrier research starting point rather than ask the user to prepare a full paper project first.

2. **Receive a research card**
   The system retrieves objective paper data and returns a structured research card. This card is a preparation artifact that helps the user understand the starting area and select project-ready material.

3. **Convert to a paper project**
   After reviewing the research card, the user converts selected structured content into a paper project. This is the moment where the main working object of the product is created.

4. **Choose a template**
   The user attaches one supported template package to the paper project. Template choice is controlled and limited to the supported catalog frozen in the implementation plan.

5. **Edit the paper structure**
   The user works on the normalized paper structure inside the paper project. This includes managing ordered sections and the minimum set of build-relevant materials needed to continue toward a build.

6. **Build and preview**
   The system runs the controlled LaTeX build flow and returns a previewable result. The user can inspect the PDF, understand success or failure, and continue iterating inside the desktop app.

The base game does not contain a seventh hidden action. In particular, it does not assume collaboration, arbitrary template engineering, open-ended IDE behavior, or independent research-product workflows outside the paper project loop.

## 2. Core Object Vocabulary

### `research input`

The user-provided starting point for research generation. In v1 this means a keyword, DOI, arXiv ID, paper title, or paper URL, aligned with the implementation plan.

### `research card`

A structured, objective, pre-project research artifact created from retrieval plus summarization. It exists to help the user move from a vague topic or seed paper into a usable project starting point.

It is **not** the main working object of HSO. It is upstream material that can feed a paper project, but it does not own template selection, section management, build execution, or preview status.

### `paper project`

The core working object of the base game. A paper project organizes the ongoing materials required to produce a paper in the supported workflow, including template choice, section structure, build-relevant assets, reference sources, and build history.

Unlike a research card, a paper project is designed for continuous progression through writing structure, build execution, and preview.

### `template`

A controlled template package from the supported v1 catalog. A template defines rendering and mapping rules for how normalized paper-project content is expressed in a supported publication format.

### `section`

An ordered normalized unit of paper-project structure, such as title, abstract, introduction, method, or conclusion. Sections belong to the paper project model, not to the research card.

### `asset`

A build-relevant file attached to a paper project under the controlled v1 asset model. In the first release, assets refer to supported figure/image files used during the paper workflow. A generic asset is not the same as a reference source.

### `build job`

One execution record for a LaTeX build triggered from a paper project. A build job binds execution to a specific project revision snapshot and moves through the frozen v1 states: `queued`, `running`, `succeeded`, and `failed`.

### `build result`

The recorded outcome of one build job. It includes the observable result of that single execution, such as artifact paths, summaries, status, and timestamps. It is **not** the same thing as the paper project itself or the total state of the project.

### `reference source`

A structured record of an external paper or citation-relevant source associated with the paper project. It is not a generic uploaded file and should not be modeled as a general asset. Source PDFs may assist ingestion, but `reference source` remains the structured citation-side object.

## 3. First-Release Non-Goals

The following items are explicitly outside the Step 1 base game contract and must not be implied as partially supported in v1:

1. **No collaboration workflow**
   The first release is a local single-user assistant, not a multi-user collaborative platform.

2. **No arbitrary LaTeX project import**
   The app does not promise compatibility with arbitrary existing LaTeX repositories or uncontrolled document engineering setups.

3. **No subjective academic judgment**
   The information retrieval domain provides objective, traceable material. It does not decide whether a topic is valuable or whether a research direction is academically correct.

4. **No full-featured editor or LaTeX IDE**
   The product does not attempt to replace Overleaf, TeXstudio, or a free-form editing environment in v1.

5. **No build cancellation**
   Build cancellation is not part of the frozen first-release build state model.

6. **No custom user template upload**
   Users cannot upload arbitrary template packages and expect them to work in the first release.

7. **No app-store-grade distribution workflow**
   The first release targets local use and small-scale internal testing, not a fully hardened public app-store distribution standard.

8. **No polishing or rewriting as a primary workflow**
   Editing assistance (paraphrase, expand, rewrite) may exist as auxiliary capability but is not a first-release core narrative or primary user action.

9. **No standalone information-retrieval product**
   The research retrieval domain exists to feed paper projects, not to operate as an independent product line separate from the paper project workflow.

These non-goals are frozen guardrails for Step 1. If a future release wants to include one of them, it must be introduced as new scope rather than treated as something silently present in the base game.

## 4. Verification Notes

Step 1 should be validated against the following checks:

1. The six user actions above must map directly to `memory_bank/PRD.md` with no extra hidden capability added here.
2. Another developer should be able to explain the difference between `research card` and `paper project` using this document alone, without contradicting the PRD.
3. The non-goals must stay aligned with section 8 of `memory_bank/PRD.md` and must not imply “soft support” for out-of-scope features.
4. This document defines Step 1 only. It must not contain Step 2 repository structure, runtime ownership, or storage layout decisions.
