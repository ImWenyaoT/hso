"""OutlineBuilder 测试：mock LLMClient.parse 返回伪造 Outline。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from hso.manuscript.outline import (
    OutlineBuilder,
    _OutlineLLM,
    _SectionPlanLLM,
)
from hso.models import (
    Author,
    Experiment,
    ExperimentResult,
    Paper,
    SectionProfile,
    SectionStructure,
    Venue,
)


def _llm_returning(parsed: _OutlineLLM) -> MagicMock:
    """返回 stub LLMClient。"""
    llm = MagicMock()
    llm.model = "stub"
    llm.parse.return_value = parsed
    return llm


def _sample_profile() -> SectionProfile:
    return SectionProfile(
        field_query="diffusion editing",
        n_papers=5,
        sections=[
            SectionStructure(
                section="introduction",
                common_subtopics=["task", "challenges"],
                typical_opening="Briefly motivate the task.",
                underexplored=["fairness"],
                recommended_artifacts=["teaser figure"],
            ),
            SectionStructure(
                section="experiment",
                common_subtopics=["benchmark"],
                typical_opening="Datasets and baselines.",
                recommended_artifacts=["ablation table"],
            ),
        ],
    )


def _sample_exp() -> Experiment:
    return Experiment(
        title="Diffusion editing",
        contributions=["A", "B"],
        results=[
            ExperimentResult(method="Ours", metrics={"FID": 8.2}),
            ExperimentResult(method="Baseline", metrics={"FID": 12.4}),
        ],
        notes="trained 36h",
    )


def _sample_papers() -> list[Paper]:
    return [
        Paper(
            paper_id="doi:10.1/x",
            doi="10.1/x",
            title="A method",
            abstract="abstract" * 3,
            authors=[Author(name="Alice")],
            venue=Venue(name="TPAMI", type="journal"),
            published_at=date(2024, 6, 1),
            jcr_zone=1,
            source="semanticscholar",
        )
    ]


def _sample_outline_response() -> _OutlineLLM:
    return _OutlineLLM(
        title="Diffusion-Based Editing",
        abstract_focus="Concise abstract intent.",
        keywords=["diffusion", "editing"],
        sections=[
            _SectionPlanLLM(
                section_id="introduction",
                title="Introduction",
                subtopics=["motivation", "contributions"],
                planned_artifacts=["fig:teaser"],
                cited_paper_ids=["doi:10.1/x"],
                notes="open with the task",
            ),
            _SectionPlanLLM(
                section_id="experiment",
                title="Experiments",
                subtopics=["main results", "ablation"],
                planned_artifacts=["table:main_results"],
                cited_paper_ids=[],
                notes="",
            ),
        ],
    )


class TestOutlineBuilder:
    def test_returns_outline_with_two_sections(self) -> None:
        llm = _llm_returning(_sample_outline_response())
        outline = OutlineBuilder(llm).build(
            _sample_profile(), _sample_exp(), _sample_papers()
        )
        assert outline.title == "Diffusion-Based Editing"
        assert len(outline.sections) == 2
        intro = outline.sections[0]
        assert intro.section_id == "introduction"
        assert "fig:teaser" in intro.planned_artifacts
        assert intro.notes == "open with the task"
        # 空字符串 notes 转成 None（业务模型友好）
        assert outline.sections[1].notes is None

    def test_passes_strict_schema_to_llm(self) -> None:
        llm = _llm_returning(_sample_outline_response())
        OutlineBuilder(llm).build(_sample_profile(), _sample_exp(), _sample_papers())
        kwargs = llm.parse.call_args.kwargs
        assert kwargs["text_format"] is _OutlineLLM

    def test_prompt_includes_methods_and_papers(self) -> None:
        llm = _llm_returning(_sample_outline_response())
        OutlineBuilder(llm).build(_sample_profile(), _sample_exp(), _sample_papers())
        user_input = llm.parse.call_args.kwargs["user_input"]
        # methods 与 metrics 应该都进了 prompt
        assert "Ours" in user_input and "Baseline" in user_input
        assert "FID" in user_input
        # paper id 在 prompt 里（agent 才能引用）
        assert "doi:10.1/x" in user_input
        # field profile 的 typical_opening 也在
        assert "Briefly motivate the task" in user_input

    def test_handles_no_candidate_papers(self) -> None:
        llm = _llm_returning(_sample_outline_response())
        OutlineBuilder(llm).build(_sample_profile(), _sample_exp(), [])
        user_input = llm.parse.call_args.kwargs["user_input"]
        assert "no candidate papers" in user_input

    def test_custom_section_ids(self) -> None:
        llm = _llm_returning(_sample_outline_response())
        OutlineBuilder(llm, section_ids=("intro", "method")).build(
            _sample_profile(), _sample_exp(), []
        )
        user_input = llm.parse.call_args.kwargs["user_input"]
        assert "['intro', 'method']" in user_input
