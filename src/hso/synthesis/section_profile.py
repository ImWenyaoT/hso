"""根据 N 篇论文 abstract 生成章节级写作 profile（用 Responses API structured output）。"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from hso.llm import LLMClient
from hso.models import Paper, SectionProfile, SectionStructure

logger = logging.getLogger(__name__)

_DEFAULT_SECTIONS = ("introduction", "related_work", "method", "experiment", "conclusion")

_SYSTEM_PROMPT = (
    "You are a senior reviewer for top-tier journals (CAS Q1/Q2). "
    "Given abstracts and titles of recent papers in a research direction, "
    "summarize the conventions for each manuscript section. "
    "Be specific and grounded in the provided corpus. "
    "When you cannot extract a confident pattern, leave the field as an empty list "
    "or empty string."
)

_USER_TEMPLATE = """Research direction: {query}

Below are {n} recent papers (CAS Q{max_zone} or above). For each section in {sections},
analyze the corpus and produce:
- common_subtopics: ordered list of subtopics authors typically cover
- typical_opening: one-sentence summary of how authors usually open this section
- underexplored: angles rarely discussed but where novel work could contribute
- recommended_artifacts: figure/table types commonly used (e.g. "ablation table",
  "convergence curve", "qualitative comparison grid")
- evidence_paper_ids: list of paper_id values from the corpus that support your summary

Papers:
{corpus}
"""


class _SectionStructureLLM(BaseModel):
    """LLM 直接产出的章节结构 schema（OpenAI strict 模式兼容）。

    与 ``hso.models.SectionStructure`` 同构，但所有字段必填、不带
    default，便于 Responses API 严格 JSON Schema 校验。
    """

    section: str = Field(
        description=(
            "章节标识：introduction / related_work / method / experiment / conclusion"
        )
    )
    common_subtopics: list[str]
    typical_opening: str
    underexplored: list[str]
    recommended_artifacts: list[str]
    evidence_paper_ids: list[str]


class _SectionProfileLLM(BaseModel):
    """LLM 顶层响应 schema。"""

    sections: list[_SectionStructureLLM]


class SectionProfileBuilder:
    """把检索后的论文集合喂给 LLM，产出 SectionProfile。"""

    def __init__(self, llm: LLMClient, sections: tuple[str, ...] = _DEFAULT_SECTIONS) -> None:
        """初始化。

        Args:
            llm: LLMClient 实例。
            sections: 要分析的章节列表，将原样传给 prompt。
        """
        self._llm = llm
        self._sections = sections

    def build(self, query: str, papers: list[Paper], max_zone: int = 2) -> SectionProfile:
        """构造 SectionProfile。

        Args:
            query: 研究方向描述。
            papers: 候选论文，必须含 paper_id / title；abstract 越完整效果越好。
            max_zone: 在 prompt 中告知 LLM 候选论文的 JCR 等级。
        """
        if not papers:
            return SectionProfile(
                field_query=query, n_papers=0, sections=[], llm_model=self._llm.model
            )

        corpus = self._format_corpus(papers)
        user = _USER_TEMPLATE.format(
            query=query,
            n=len(papers),
            max_zone=max_zone,
            sections=list(self._sections),
            corpus=corpus,
        )

        llm_response = self._llm.parse(
            text_format=_SectionProfileLLM,
            instructions=_SYSTEM_PROMPT,
            user_input=user,
        )

        # _SectionStructureLLM → SectionStructure 字段同构，直接透传
        sections = [SectionStructure(**s.model_dump()) for s in llm_response.sections]
        return SectionProfile(
            field_query=query,
            n_papers=len(papers),
            sections=sections,
            llm_model=self._llm.model,
        )

    @staticmethod
    def _format_corpus(papers: list[Paper]) -> str:
        """把论文格式化为简短的 prompt 上下文，控制 token 用量。"""
        lines: list[str] = []
        for p in papers[:50]:
            abstract = (p.abstract or "").replace("\n", " ").strip()
            if len(abstract) > 800:
                abstract = abstract[:800] + "..."
            venue = p.venue.name if p.venue else "unknown"
            zone = f"Q{p.jcr_zone}" if p.jcr_zone else "preprint/unranked"
            year = str(p.published_at.year) if p.published_at else "?"
            lines.append(
                f"- id={p.paper_id} | venue={venue} ({zone}) | year={year}\n"
                f"  title: {p.title}\n"
                f"  abstract: {abstract or 'N/A'}"
            )
        return "\n".join(lines)
