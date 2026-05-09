"""manuscript 起草模块：大纲、章节起草、模板填充、表格/图、bibtex。"""

from hso.manuscript.bibliography import (
    check_citation_consistency,
    papers_to_bib_entries,
    render_bibfile,
    resolve_citekeys,
)
from hso.manuscript.drafter import SectionDrafter
from hso.manuscript.figures import render_timeseries_figure
from hso.manuscript.loader import ExperimentLoader
from hso.manuscript.outline import OutlineBuilder
from hso.manuscript.tables import results_to_latex_table
from hso.manuscript.template import ElsevierTemplate, ManuscriptSection

__all__ = [
    "ElsevierTemplate",
    "ExperimentLoader",
    "ManuscriptSection",
    "OutlineBuilder",
    "SectionDrafter",
    "check_citation_consistency",
    "papers_to_bib_entries",
    "render_bibfile",
    "render_timeseries_figure",
    "resolve_citekeys",
    "results_to_latex_table",
]
