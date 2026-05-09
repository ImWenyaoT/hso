"""SectionDrafter：基于 SectionPlan + 实验事实 + 引用 papers 起草单章节正文。

正文中所有引用必须用 \\cite{paper:<paper_id>} 占位，由后续 CiteKeyResolver
替换为真实 BibTeX key。所有 artifact 引用必须出现在 plan.planned_artifacts 内。
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from hso.llm import LLMClient
from hso.models import (
    DraftedSection,
    Experiment,
    Paper,
    SectionPlan,
)

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You are drafting one section of an Elsevier manuscript. Strict rules:\n"
    "1. Output LaTeX body only — no \\section header, no \\begin{document}.\n"
    "2. Cite using \\cite{paper:<paper_id>} EXACTLY as given (we resolve later). "
    "Do NOT invent paper ids.\n"
    "3. Reference artifacts using \\autoref{tab:<id>} or \\autoref{fig:<id>} where the "
    "ids match the plan's planned_artifacts list. Do NOT invent artifact ids.\n"
    "4. Quantitative claims must be grounded in the provided experiment data; do not "
    "fabricate numbers.\n"
    "5. Keep prose tight and Q1/Q2 publishable in tone."
)

_USER_TEMPLATE = """## Section to draft
section_id: {section_id}
title: {title}
subtopics: {subtopics}
notes: {notes}

## Allowed artifacts
{artifacts}

## Experiment facts
Title: {exp_title}
Contributions:
{contributions}
Methods: {methods}
Metrics: {metrics}
Notes: {exp_notes}

## Cited papers
{papers}

Write the LaTeX body now. Reuse the exact paper_id strings inside \\cite{{paper:<paper_id>}}.
"""


class _DraftedSectionLLM(BaseModel):
    """LLM-side strict schema."""

    body: str = Field(description="LaTeX 正文")
    used_paper_ids: list[str]
    used_artifact_ids: list[str]


class SectionDrafter:
    """单章节起草器。"""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def draft(
        self,
        plan: SectionPlan,
        experiment: Experiment,
        cited_papers: list[Paper],
    ) -> DraftedSection:
        """起草一个章节。

        Args:
            plan: 章节计划，决定 cited papers / artifacts / subtopics。
            experiment: 用户实验材料；prompt 仅暴露事实层（contributions / metrics / notes）。
            cited_papers: 实际可引用的 papers，**必须**是 plan.cited_paper_ids 的超集；
                调用方应预过滤为相关子集。
        """
        user_input = _USER_TEMPLATE.format(
            section_id=plan.section_id,
            title=plan.title,
            subtopics=", ".join(plan.subtopics) or "(none)",
            notes=plan.notes or "(none)",
            artifacts=_format_artifacts(plan.planned_artifacts),
            exp_title=experiment.title,
            contributions=_format_bullets(experiment.contributions) or "(none)",
            methods=", ".join(experiment.all_methods) or "(none)",
            metrics=", ".join(experiment.all_metric_names) or "(none)",
            exp_notes=experiment.notes or "(none)",
            papers=_format_cited_papers(cited_papers, plan.cited_paper_ids),
        )

        result = self._llm.parse(
            text_format=_DraftedSectionLLM,
            instructions=_SYSTEM_PROMPT,
            user_input=user_input,
        )

        return DraftedSection(
            section_id=plan.section_id,
            title=plan.title,
            body=result.body,
            used_paper_ids=result.used_paper_ids,
            used_artifact_ids=result.used_artifact_ids,
        )


def _format_artifacts(artifact_ids: list[str]) -> str:
    """把 'table:main_results' / 'fig:train_loss' 列出，加 LaTeX label 格式提示。"""
    if not artifact_ids:
        return "(none — do not reference any \\autoref artifacts)"
    lines: list[str] = []
    for aid in artifact_ids:
        if ":" not in aid:
            continue
        kind, name = aid.split(":", 1)
        latex_label = f"{'tab' if kind == 'table' else 'fig'}:{name}"
        lines.append(f"- {aid} → \\autoref{{{latex_label}}}")
    return "\n".join(lines) or "(none)"


def _format_cited_papers(papers: list[Paper], allowed_ids: list[str]) -> str:
    """只展示 plan 允许引用的 papers，避免 LLM 引到无关论文。"""
    allowed = set(allowed_ids)
    chosen = [p for p in papers if p.paper_id in allowed]
    if not chosen:
        return "(no papers; do not insert any \\cite{} commands)"
    lines: list[str] = []
    for p in chosen:
        year = str(p.published_at.year) if p.published_at else "?"
        venue = p.venue.name if p.venue else "?"
        abstract = (p.abstract or "").replace("\n", " ").strip()
        if len(abstract) > 300:
            abstract = abstract[:300] + "..."
        lines.append(
            f"- paper_id={p.paper_id} | {venue} {year}\n  {p.title}\n  {abstract or 'N/A'}"
        )
    return "\n".join(lines)


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"  - {x}" for x in items)
