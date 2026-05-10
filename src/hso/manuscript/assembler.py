"""Manuscript project assembler.

This module turns drafted manuscript pieces into a concrete LaTeX project
directory. It deliberately does not call an LLM; it only resolves citations,
renders deterministic artifacts, and writes files.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from hso.manuscript.bibliography import papers_to_bib_entries, render_bibfile, resolve_citekeys
from hso.manuscript.figures import render_timeseries_figure
from hso.manuscript.tables import results_to_latex_table
from hso.manuscript.template import (
    Affiliation,
    ElsevierTemplate,
    ManuscriptDocument,
    ManuscriptSection,
    TemplateAuthor,
)
from hso.models import DraftedSection, Experiment, Outline, Paper


class AssemblyResult(BaseModel):
    """Result of assembling a manuscript LaTeX project."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    output_dir: Path
    main_tex_path: Path
    refs_bib_path: Path
    table_paths: list[Path] = Field(default_factory=list)
    figure_paths: list[Path] = Field(default_factory=list)
    document: ManuscriptDocument
    unresolved_citations: list[str] = Field(default_factory=list)
    missing_artifacts: list[str] = Field(default_factory=list)


class ManuscriptAssembler:
    """Assemble an outline and drafted sections into an Elsevier LaTeX project."""

    def __init__(self, template: ElsevierTemplate | None = None) -> None:
        """Create an assembler with an optional custom template renderer."""
        self._template = template or ElsevierTemplate()

    def assemble(
        self,
        *,
        outline: Outline,
        drafted_sections: list[DraftedSection],
        experiment: Experiment,
        papers: list[Paper],
        output_dir: Path,
        authors: list[TemplateAuthor] | None = None,
        affiliations: list[Affiliation] | None = None,
        journal: str = "Journal Name",
    ) -> AssemblyResult:
        """Write a complete LaTeX project and return its file manifest.

        Args:
            outline: Manuscript outline that defines section order and planned artifacts.
            drafted_sections: Drafted section bodies keyed by ``section_id``.
            experiment: User experiment facts used for deterministic tables and figures.
            papers: Candidate papers used to generate ``refs.bib`` and resolve citations.
            output_dir: Target directory for ``main.tex``, ``refs.bib``, ``figs/``, and
                ``tables/``.
            authors: Optional template authors. A conservative anonymous placeholder is
                used when omitted.
            affiliations: Optional author affiliations.
            journal: Elsevier journal label rendered into the template.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        table_dir = output_dir / "tables"
        figure_dir = output_dir / "figs"

        entries = papers_to_bib_entries(papers)
        refs_bib_path = output_dir / "refs.bib"
        refs_bib_path.write_text(render_bibfile(entries), encoding="utf-8")

        drafted_by_id = {section.section_id: section for section in drafted_sections}
        table_paths: list[Path] = []
        figure_paths: list[Path] = []
        unresolved: list[str] = []
        missing_artifacts: list[str] = []
        sections: list[ManuscriptSection] = []

        for plan in outline.sections:
            drafted = drafted_by_id.get(plan.section_id)
            body = drafted.body if drafted is not None else ""
            resolved_body, section_unresolved = resolve_citekeys(body, entries)
            unresolved.extend(section_unresolved)

            artifacts = _artifact_ids_for_section(plan.planned_artifacts, drafted)
            artifact_body, section_tables, section_figures, section_missing = self._render_artifacts(
                artifacts=artifacts,
                experiment=experiment,
                table_dir=table_dir,
                figure_dir=figure_dir,
            )
            table_paths.extend(section_tables)
            figure_paths.extend(section_figures)
            missing_artifacts.extend(section_missing)

            body_parts = [resolved_body.strip()]
            if artifact_body:
                body_parts.append(artifact_body)
            sections.append(
                ManuscriptSection(
                    id=_latex_safe_id(plan.section_id),
                    title=plan.title,
                    body="\n\n".join(part for part in body_parts if part),
                )
            )

        document = ManuscriptDocument(
            title=outline.title or experiment.title,
            authors=authors or [TemplateAuthor(name="Anonymous Author", affiliation_id="a")],
            affiliations=affiliations
            or [Affiliation(id="a", organization="Anonymous Institution", country="")],
            abstract=experiment.abstract or outline.abstract_focus,
            keywords=outline.keywords or experiment.keywords,
            sections=sections,
            journal=journal,
        )
        main_tex_path = self._template.render_to_file(document, output_dir / "main.tex")
        return AssemblyResult(
            output_dir=output_dir,
            main_tex_path=main_tex_path,
            refs_bib_path=refs_bib_path,
            table_paths=_dedupe_paths(table_paths),
            figure_paths=_dedupe_paths(figure_paths),
            document=document,
            unresolved_citations=_dedupe_strings(unresolved),
            missing_artifacts=_dedupe_strings(missing_artifacts),
        )

    def _render_artifacts(
        self,
        *,
        artifacts: list[str],
        experiment: Experiment,
        table_dir: Path,
        figure_dir: Path,
    ) -> tuple[str, list[Path], list[Path], list[str]]:
        """Render requested artifacts and return LaTeX snippets plus file manifests."""
        snippets: list[str] = []
        table_paths: list[Path] = []
        figure_paths: list[Path] = []
        missing: list[str] = []

        for artifact_id in artifacts:
            kind, name = _split_artifact_id(artifact_id)
            if kind == "table":
                if not experiment.results:
                    missing.append(artifact_id)
                    continue
                table_dir.mkdir(parents=True, exist_ok=True)
                table_path = table_dir / f"{_latex_safe_id(name)}.tex"
                table_path.write_text(
                    results_to_latex_table(
                        experiment.results,
                        caption=_title_from_id(name),
                        label=_latex_safe_id(name),
                    ),
                    encoding="utf-8",
                )
                table_paths.append(table_path)
                snippets.append(f"\\input{{tables/{table_path.name}}}")
            elif kind == "fig":
                matching = [series for series in experiment.timeseries if series.name == name]
                if not matching:
                    missing.append(artifact_id)
                    continue
                figure_dir.mkdir(parents=True, exist_ok=True)
                figure_path = figure_dir / f"{_latex_safe_id(name)}.pdf"
                render_timeseries_figure(
                    experiment.timeseries,
                    figure_path,
                    series_name=name,
                    title=_title_from_id(name),
                )
                figure_paths.append(figure_path)
                snippets.append(_figure_snippet(name=name, filename=figure_path.name))
            else:
                missing.append(artifact_id)

        return "\n\n".join(_dedupe_strings(snippets)), table_paths, figure_paths, missing


def _artifact_ids_for_section(
    planned_artifacts: list[str],
    drafted: DraftedSection | None,
) -> list[str]:
    """Choose artifact ids for one section, preserving plan order."""
    used = drafted.used_artifact_ids if drafted is not None else []
    if used:
        allowed = set(planned_artifacts)
        ordered = [artifact for artifact in planned_artifacts if artifact in set(used)]
        extras = [artifact for artifact in used if artifact not in allowed]
        return ordered + extras
    return planned_artifacts


def _split_artifact_id(artifact_id: str) -> tuple[str, str]:
    """Split ``kind:name`` artifact ids into kind and name."""
    if ":" not in artifact_id:
        return "", artifact_id
    kind, name = artifact_id.split(":", 1)
    return kind, name


def _figure_snippet(*, name: str, filename: str) -> str:
    """Return a deterministic LaTeX figure environment for a rendered PDF."""
    label = _latex_safe_id(name)
    return (
        "\\begin{figure}[htbp]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.85\\linewidth]{{figs/{filename}}}\n"
        f"\\caption{{{_title_from_id(name)}}}\n"
        f"\\label{{fig:{label}}}\n"
        "\\end{figure}"
    )


def _title_from_id(value: str) -> str:
    """Convert snake-case ids to compact human-readable titles."""
    return value.replace("_", " ").replace("-", " ").strip().title() or "Artifact"


def _latex_safe_id(value: str) -> str:
    """Make a string safe for LaTeX labels and local artifact file names."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned.strip("_") or "artifact"


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """Deduplicate paths while preserving order."""
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def _dedupe_strings(values: list[str]) -> list[str]:
    """Deduplicate strings while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
