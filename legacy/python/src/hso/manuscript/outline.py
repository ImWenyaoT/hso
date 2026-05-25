"""OutlineBuilder：基于 SectionProfile + Experiment + 候选 papers 生成 Outline。

走 Chat Completions JSON mode structured output；LLM schema 与业务 schema 解耦
（``_SectionPlanLLM`` / ``_OutlineLLM`` strict 兼容，所有字段必填）。
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from hso.llm import LLMClient
from hso.models import Experiment, Outline, Paper, SectionPlan, SectionProfile

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You are an experienced corresponding author for top-tier (CAS Q1/Q2) Elsevier journals. "
    "Given a field profile (writing conventions), the user's experiment material, "
    "and a candidate reference list, produce an Outline that:\n"
    "1. Mirrors conventions captured in the section profile;\n"
    "2. Grounds every claim in the user's experiment or in cited papers — never invent results;\n"
    "3. Distributes citations across sections such that each cited paper is used where it fits best;\n"
    "4. Lists artifact placeholders (table:main_results / fig:<series_name>) that we will later "
    "render. Use stable, lowercase, snake_case ids."
)

_USER_TEMPLATE = """## Field profile
{profile_summary}

## User experiment
Title: {title}
Contributions:
{contributions}
Methods compared: {methods}
Reported metrics: {metrics}
Time-series available: {timeseries}
Notes: {notes}

## Candidate references ({n_papers})
{papers}

Produce an Outline with sections {section_ids}.
"""


class _SectionPlanLLM(BaseModel):
    """LLM-side strict schema（与 SectionPlan 同构，所有字段必填）。"""

    section_id: str
    title: str
    subtopics: list[str]
    planned_artifacts: list[str]
    cited_paper_ids: list[str]
    notes: str = Field(description="自由写作要点；可空字符串")


class _OutlineLLM(BaseModel):
    """LLM-side strict outline schema."""

    title: str
    abstract_focus: str
    keywords: list[str]
    sections: list[_SectionPlanLLM]


class OutlineBuilder:
    """根据领域 profile + 用户实验生成 manuscript outline。"""

    DEFAULT_SECTION_IDS = (
        "introduction",
        "related_work",
        "method",
        "experiment",
        "conclusion",
    )

    def __init__(self, llm: LLMClient, section_ids: tuple[str, ...] | None = None) -> None:
        """初始化。

        Args:
            llm: LLMClient 实例。
            section_ids: 期望的章节顺序；None 走 DEFAULT_SECTION_IDS。
        """
        self._llm = llm
        self._section_ids = section_ids or self.DEFAULT_SECTION_IDS

    def build(
        self,
        section_profile: SectionProfile,
        experiment: Experiment,
        candidate_papers: list[Paper],
    ) -> Outline:
        """生成 Outline。

        Args:
            section_profile: Phase 1 产出的章节惯例。
            experiment: 用户实验材料。
            candidate_papers: 检索阶段筛出的高质量 papers，全部喂给 LLM。
        """
        user_input = _USER_TEMPLATE.format(
            profile_summary=self._format_profile(section_profile),
            title=experiment.title,
            contributions=_format_bullets(experiment.contributions) or "(none provided)",
            methods=", ".join(experiment.all_methods) or "(none)",
            metrics=", ".join(experiment.all_metric_names) or "(none)",
            timeseries=(
                ", ".join(sorted({t.name for t in experiment.timeseries})) or "(none)"
            ),
            notes=experiment.notes or "(none)",
            n_papers=len(candidate_papers),
            papers=self._format_papers(candidate_papers),
            section_ids=list(self._section_ids),
        )

        result = self._llm.parse(
            text_format=_OutlineLLM,
            instructions=_SYSTEM_PROMPT,
            user_input=user_input,
        )

        sections = [
            SectionPlan(
                section_id=s.section_id,
                title=s.title,
                subtopics=s.subtopics,
                planned_artifacts=s.planned_artifacts,
                cited_paper_ids=s.cited_paper_ids,
                notes=s.notes or None,
            )
            for s in result.sections
        ]
        return Outline(
            title=result.title,
            abstract_focus=result.abstract_focus,
            keywords=result.keywords,
            sections=sections,
        )

    @staticmethod
    def _format_profile(profile: SectionProfile) -> str:
        """把 SectionProfile 压缩成 prompt 友好的简短格式。"""
        if not profile.sections:
            return "(no field profile available)"
        chunks: list[str] = []
        for s in profile.sections:
            opening = s.typical_opening or "(unspecified)"
            chunks.append(
                f"### {s.section}\n"
                f"  typical_opening: {opening}\n"
                f"  common_subtopics: {', '.join(s.common_subtopics) or '(none)'}\n"
                f"  underexplored: {', '.join(s.underexplored) or '(none)'}\n"
                f"  recommended_artifacts: {', '.join(s.recommended_artifacts) or '(none)'}"
            )
        return "\n".join(chunks)

    @staticmethod
    def _format_papers(papers: list[Paper]) -> str:
        """每篇论文一行：id / venue / year / title / 截断 abstract。"""
        if not papers:
            return "(no candidate papers; outline must rely on experiment only)"
        lines: list[str] = []
        for p in papers[:50]:
            year = str(p.published_at.year) if p.published_at else "?"
            venue = p.venue.name if p.venue else "?"
            zone = f"Q{p.jcr_zone}" if p.jcr_zone else "preprint"
            abstract = (p.abstract or "").replace("\n", " ").strip()
            if len(abstract) > 400:
                abstract = abstract[:400] + "..."
            lines.append(
                f"- id={p.paper_id} | {venue} ({zone}) {year}\n  {p.title}\n  {abstract or 'N/A'}"
            )
        return "\n".join(lines)


def _format_bullets(items: list[str]) -> str:
    """把字符串列表打印成 bullet。"""
    return "\n".join(f"  - {x}" for x in items)
