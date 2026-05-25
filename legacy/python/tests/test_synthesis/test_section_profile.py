"""SectionProfileBuilder 测试：mock LLMClient.parse，验证 prompt 拼装与映射。"""

from __future__ import annotations

from unittest.mock import MagicMock

from hso.models import Paper
from hso.synthesis.section_profile import (
    SectionProfileBuilder,
    _SectionProfileLLM,
    _SectionStructureLLM,
)


def _make_llm(parsed: _SectionProfileLLM | None) -> MagicMock:
    """伪造 LLMClient：parse() 直接返回 _SectionProfileLLM 实例。"""
    llm = MagicMock()
    llm.model = "stub-model"
    llm.parse.return_value = parsed
    return llm


class TestSectionProfileBuilder:
    def test_empty_papers_short_circuits(self) -> None:
        llm = _make_llm(_SectionProfileLLM(sections=[]))
        builder = SectionProfileBuilder(llm)
        profile = builder.build("diffusion editing", [])
        assert profile.n_papers == 0
        assert profile.sections == []
        llm.parse.assert_not_called()

    def test_parses_full_response(self, sample_papers: list[Paper]) -> None:
        parsed = _SectionProfileLLM(
            sections=[
                _SectionStructureLLM(
                    section="introduction",
                    common_subtopics=["task definition", "challenges"],
                    typical_opening="Briefly motivate the task.",
                    underexplored=["fairness"],
                    recommended_artifacts=["teaser figure"],
                    evidence_paper_ids=[sample_papers[0].paper_id],
                ),
                _SectionStructureLLM(
                    section="experiment",
                    common_subtopics=["benchmark", "ablation"],
                    typical_opening="Datasets and baselines.",
                    underexplored=[],
                    recommended_artifacts=["ablation table", "convergence curve"],
                    evidence_paper_ids=[],
                ),
            ]
        )
        llm = _make_llm(parsed)
        builder = SectionProfileBuilder(llm)
        profile = builder.build("diffusion editing", sample_papers, max_zone=2)
        assert profile.n_papers == len(sample_papers)
        assert len(profile.sections) == 2
        assert profile.sections[1].recommended_artifacts == [
            "ablation table",
            "convergence curve",
        ]

    def test_corpus_truncates_long_abstracts(self, sample_papers: list[Paper]) -> None:
        sample_papers[0].abstract = "A" * 2000
        llm = _make_llm(_SectionProfileLLM(sections=[]))
        builder = SectionProfileBuilder(llm)
        builder.build("x", sample_papers)
        called_user_input = llm.parse.call_args.kwargs["user_input"]
        assert "..." in called_user_input
        assert "A" * 1000 not in called_user_input

    def test_includes_jcr_zone_in_corpus(self, sample_papers: list[Paper]) -> None:
        sample_papers[0].jcr_zone = 1
        llm = _make_llm(_SectionProfileLLM(sections=[]))
        builder = SectionProfileBuilder(llm)
        builder.build("x", [sample_papers[0]])
        called_user_input = llm.parse.call_args.kwargs["user_input"]
        assert "Q1" in called_user_input

    def test_passes_text_format_to_llm(self, sample_papers: list[Paper]) -> None:
        llm = _make_llm(_SectionProfileLLM(sections=[]))
        builder = SectionProfileBuilder(llm)
        builder.build("x", sample_papers[:1])
        kwargs = llm.parse.call_args.kwargs
        assert kwargs["text_format"] is _SectionProfileLLM


class TestPromptStructure:
    def test_user_prompt_includes_query_and_n(self, sample_papers: list[Paper]) -> None:
        llm = _make_llm(_SectionProfileLLM(sections=[]))
        builder = SectionProfileBuilder(llm)
        builder.build("diffusion editing", sample_papers[:2])
        user_input = llm.parse.call_args.kwargs["user_input"]
        assert "diffusion editing" in user_input
        assert "2 recent papers" in user_input

    def test_instructions_grounds_in_corpus(self, sample_papers: list[Paper]) -> None:
        llm = _make_llm(_SectionProfileLLM(sections=[]))
        builder = SectionProfileBuilder(llm)
        builder.build("x", sample_papers[:1])
        instructions = llm.parse.call_args.kwargs["instructions"]
        assert "grounded" in instructions.lower() or "specific" in instructions.lower()
