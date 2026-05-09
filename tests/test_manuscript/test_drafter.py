"""SectionDrafter 测试。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from hso.manuscript.drafter import (
    SectionDrafter,
    _DraftedSectionLLM,
)
from hso.models import (
    Author,
    Experiment,
    ExperimentResult,
    Paper,
    SectionPlan,
    Venue,
)


def _stub(parsed: _DraftedSectionLLM) -> MagicMock:
    llm = MagicMock()
    llm.model = "stub"
    llm.parse.return_value = parsed
    return llm


def _papers() -> list[Paper]:
    return [
        Paper(
            paper_id="doi:10.1/a",
            doi="10.1/a",
            title="Paper A",
            abstract="abstract A",
            authors=[Author(name="Alice")],
            venue=Venue(name="TPAMI", type="journal"),
            published_at=date(2024, 1, 1),
            source="semanticscholar",
        ),
        Paper(
            paper_id="doi:10.1/b",
            doi="10.1/b",
            title="Paper B",
            abstract="abstract B",
            authors=[Author(name="Bob")],
            venue=Venue(name="PR", type="journal"),
            published_at=date(2024, 6, 1),
            source="semanticscholar",
        ),
    ]


def _exp() -> Experiment:
    return Experiment(
        title="Diffusion editing",
        contributions=["foo"],
        results=[ExperimentResult(method="Ours", metrics={"FID": 8.2})],
    )


def _plan() -> SectionPlan:
    return SectionPlan(
        section_id="introduction",
        title="Introduction",
        subtopics=["motivation"],
        planned_artifacts=["fig:teaser"],
        cited_paper_ids=["doi:10.1/a"],
        notes="open with the task",
    )


class TestSectionDrafter:
    def test_returns_drafted_section(self) -> None:
        parsed = _DraftedSectionLLM(
            body=r"Intro \cite{paper:doi:10.1/a} \autoref{fig:teaser}.",
            used_paper_ids=["doi:10.1/a"],
            used_artifact_ids=["fig:teaser"],
        )
        llm = _stub(parsed)
        result = SectionDrafter(llm).draft(_plan(), _exp(), _papers())
        assert result.section_id == "introduction"
        assert "\\cite{paper:doi:10.1/a}" in result.body
        assert "fig:teaser" in result.used_artifact_ids

    def test_prompt_only_exposes_allowed_papers(self) -> None:
        parsed = _DraftedSectionLLM(body="x", used_paper_ids=[], used_artifact_ids=[])
        llm = _stub(parsed)
        SectionDrafter(llm).draft(_plan(), _exp(), _papers())
        user_input = llm.parse.call_args.kwargs["user_input"]
        # plan 只允许 a，paper b 应被剔除
        assert "doi:10.1/a" in user_input
        assert "doi:10.1/b" not in user_input

    def test_prompt_lists_artifact_label_hint(self) -> None:
        parsed = _DraftedSectionLLM(body="x", used_paper_ids=[], used_artifact_ids=[])
        llm = _stub(parsed)
        SectionDrafter(llm).draft(_plan(), _exp(), _papers())
        user_input = llm.parse.call_args.kwargs["user_input"]
        # artifact "fig:teaser" 应该转换成 \autoref{fig:teaser} 提示
        assert "\\autoref{fig:teaser}" in user_input

    def test_no_artifacts_no_papers_prompts_correctly(self) -> None:
        plan = SectionPlan(
            section_id="conclusion",
            title="Conclusion",
            subtopics=[],
            planned_artifacts=[],
            cited_paper_ids=[],
        )
        parsed = _DraftedSectionLLM(body="x", used_paper_ids=[], used_artifact_ids=[])
        llm = _stub(parsed)
        SectionDrafter(llm).draft(plan, _exp(), _papers())
        user_input = llm.parse.call_args.kwargs["user_input"]
        assert "do not insert any" in user_input
        assert "do not reference any" in user_input
