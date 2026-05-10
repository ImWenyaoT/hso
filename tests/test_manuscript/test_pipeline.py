"""DraftPipeline 编排测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from hso.manuscript.assembler import ManuscriptAssembler
from hso.manuscript.drafter import SectionDrafter
from hso.manuscript.outline import OutlineBuilder
from hso.manuscript.pipeline import DraftPipeline
from hso.models import (
    DraftedSection,
    Experiment,
    Outline,
    Paper,
    SectionPlan,
    SectionProfile,
)


class TestDraftPipeline:
    def test_runs_outline_drafter_and_assembler(
        self,
        monkeypatch,
        tmp_path,
        sample_papers: list[Paper],
    ) -> None:
        outline = Outline(
            title="Draft",
            abstract_focus="Focus",
            sections=[
                SectionPlan(
                    section_id="intro",
                    title="Introduction",
                    cited_paper_ids=[sample_papers[0].paper_id],
                )
            ],
        )
        seen_papers: list[list[Paper]] = []

        def fake_build(
            self: OutlineBuilder,
            section_profile: SectionProfile,
            experiment: Experiment,
            candidate_papers: list[Paper],
        ) -> Outline:
            """Return a stable outline and prove inputs are passed through."""
            assert section_profile.field_query == "diffusion"
            assert experiment.title == "Experiment"
            assert candidate_papers == sample_papers
            return outline

        def fake_draft(
            self: SectionDrafter,
            plan: SectionPlan,
            experiment: Experiment,
            cited_papers: list[Paper],
        ) -> DraftedSection:
            """Return deterministic section text and capture paper filtering."""
            seen_papers.append(cited_papers)
            return DraftedSection(
                section_id=plan.section_id,
                title=plan.title,
                body="Drafted body.",
            )

        monkeypatch.setattr(OutlineBuilder, "build", fake_build)
        monkeypatch.setattr(SectionDrafter, "draft", fake_draft)

        result = DraftPipeline(MagicMock(), assembler=ManuscriptAssembler()).run(
            section_profile=SectionProfile(field_query="diffusion", n_papers=1),
            experiment=Experiment(title="Experiment"),
            papers=sample_papers,
            output_dir=tmp_path / "draft",
        )

        assert result.outline == outline
        assert len(result.drafted_sections) == 1
        assert seen_papers == [[sample_papers[0]]]
        assert result.assembly.main_tex_path.exists()
