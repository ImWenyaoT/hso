"""End-to-end manuscript drafting pipeline."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from hso.llm import LLMClient
from hso.manuscript.assembler import AssemblyResult, ManuscriptAssembler
from hso.manuscript.drafter import SectionDrafter
from hso.manuscript.outline import OutlineBuilder
from hso.manuscript.template import Affiliation, TemplateAuthor
from hso.models import DraftedSection, Experiment, Outline, Paper, SectionProfile


class DraftPipelineResult(BaseModel):
    """Structured output from the draft pipeline."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    outline: Outline
    drafted_sections: list[DraftedSection]
    assembly: AssemblyResult


class DraftPipeline:
    """Draft an outline, draft each section, then assemble the LaTeX project."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        assembler: ManuscriptAssembler | None = None,
    ) -> None:
        """Create a pipeline around one LLM client."""
        self._outline_builder = OutlineBuilder(llm)
        self._section_drafter = SectionDrafter(llm)
        self._assembler = assembler or ManuscriptAssembler()

    def run(
        self,
        *,
        section_profile: SectionProfile,
        experiment: Experiment,
        papers: list[Paper],
        output_dir: Path,
        authors: list[TemplateAuthor] | None = None,
        affiliations: list[Affiliation] | None = None,
        journal: str = "Journal Name",
    ) -> DraftPipelineResult:
        """Run the deterministic Phase 2.3 pipeline around the existing LLM utilities."""
        outline = self._outline_builder.build(section_profile, experiment, papers)
        drafted_sections: list[DraftedSection] = []

        for plan in outline.sections:
            section_papers = _papers_for_section(papers, plan.cited_paper_ids)
            drafted_sections.append(
                self._section_drafter.draft(
                    plan=plan,
                    experiment=experiment,
                    cited_papers=section_papers,
                )
            )

        assembly = self._assembler.assemble(
            outline=outline,
            drafted_sections=drafted_sections,
            experiment=experiment,
            papers=papers,
            output_dir=output_dir,
            authors=authors,
            affiliations=affiliations,
            journal=journal,
        )
        return DraftPipelineResult(
            outline=outline,
            drafted_sections=drafted_sections,
            assembly=assembly,
        )


def _papers_for_section(papers: list[Paper], cited_paper_ids: list[str]) -> list[Paper]:
    """Filter candidate papers to the ids requested by one section plan."""
    allowed = set(cited_paper_ids)
    return [paper for paper in papers if paper.paper_id in allowed]
