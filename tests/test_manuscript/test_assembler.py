"""ManuscriptAssembler 离线装配测试。"""

from __future__ import annotations

from hso.manuscript.assembler import ManuscriptAssembler
from hso.models import DraftedSection, Experiment, Outline, Paper, SectionPlan


def _outline() -> Outline:
    """构造含引用、表格、时序图的最小 outline。"""
    return Outline(
        title="Draft Title",
        abstract_focus="We summarize the method and findings.",
        keywords=["diffusion", "editing"],
        sections=[
            SectionPlan(
                section_id="introduction",
                title="Introduction",
                planned_artifacts=["fig:train_loss"],
                cited_paper_ids=["doi:10.1109/tpami.2025.0001"],
            ),
            SectionPlan(
                section_id="experiment",
                title="Experiments",
                planned_artifacts=["table:main_results"],
                cited_paper_ids=[],
            ),
        ],
    )


def _drafted_sections() -> list[DraftedSection]:
    """构造两个已经起草好的章节。"""
    return [
        DraftedSection(
            section_id="introduction",
            title="Introduction",
            body=r"Prior work \cite{paper:doi:10.1109/tpami.2025.0001} motivates this.",
            used_paper_ids=["doi:10.1109/tpami.2025.0001"],
            used_artifact_ids=["fig:train_loss"],
        ),
        DraftedSection(
            section_id="experiment",
            title="Experiments",
            body=r"We report the main comparison in \autoref{tab:main_results}.",
            used_artifact_ids=["table:main_results"],
        ),
    ]


class TestManuscriptAssembler:
    def test_writes_latex_project(
        self,
        tmp_path,
        sample_papers: list[Paper],
    ) -> None:
        result = ManuscriptAssembler().assemble(
            outline=_outline(),
            drafted_sections=_drafted_sections(),
            experiment=_fallback_experiment(),
            papers=sample_papers[:1],
            output_dir=tmp_path / "draft",
        )

        assert result.main_tex_path.exists()
        assert result.refs_bib_path.exists()
        assert result.table_paths and result.table_paths[0].exists()
        assert result.figure_paths and result.figure_paths[0].exists()

        main_tex = result.main_tex_path.read_text(encoding="utf-8")
        assert r"\cite{alice2025novel}" in main_tex
        assert r"\cite{paper:" not in main_tex
        assert r"\input{tables/main_results.tex}" in main_tex
        assert r"\includegraphics" in main_tex
        assert result.unresolved_citations == []

    def test_reports_unresolved_citations(self, tmp_path, sample_papers: list[Paper]) -> None:
        drafted = [
            DraftedSection(
                section_id="introduction",
                title="Introduction",
                body=r"Unknown citation \cite{paper:missing}.",
            )
        ]
        result = ManuscriptAssembler().assemble(
            outline=_outline(),
            drafted_sections=drafted,
            experiment=_fallback_experiment(),
            papers=sample_papers[:1],
            output_dir=tmp_path / "draft",
        )

        assert result.unresolved_citations == ["missing"]
        assert r"\cite{paper:missing}" in result.main_tex_path.read_text(encoding="utf-8")

    def test_reports_missing_artifacts(self, tmp_path, sample_papers: list[Paper]) -> None:
        outline = Outline(
            title="Draft",
            abstract_focus="Focus",
            sections=[
                SectionPlan(
                    section_id="experiment",
                    title="Experiments",
                    planned_artifacts=["fig:not_available"],
                )
            ],
        )
        result = ManuscriptAssembler().assemble(
            outline=outline,
            drafted_sections=[
                DraftedSection(
                    section_id="experiment",
                    title="Experiments",
                    body="No figure data.",
                    used_artifact_ids=["fig:not_available"],
                )
            ],
            experiment=_fallback_experiment(),
            papers=sample_papers[:1],
            output_dir=tmp_path / "draft",
        )

        assert result.missing_artifacts == ["fig:not_available"]


def _fallback_experiment() -> Experiment:
    """构造不依赖外部文件的实验 fixture。"""
    return Experiment.model_validate(
        {
            "title": "Diffusion-Based Image Editing",
            "abstract": "We propose a method.",
            "results": [
                {"method": "Ours", "dataset": "CelebA-HQ", "metrics": {"FID": 8.21}},
                {"method": "Baseline", "dataset": "CelebA-HQ", "metrics": {"FID": 12.4}},
            ],
            "timeseries": [
                {
                    "name": "train_loss",
                    "method": "Ours",
                    "x": [1, 2],
                    "y": [2.0, 1.0],
                    "x_label": "Epoch",
                    "y_label": "Loss",
                }
            ],
        }
    )
