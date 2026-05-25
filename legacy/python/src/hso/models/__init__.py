"""跨模块共享的 pydantic schema。"""

from hso.models.experiment import (
    Experiment,
    ExperimentResult,
    ExperimentTimeSeries,
)
from hso.models.jcr import JCRRecord, JCRZone
from hso.models.manuscript import (
    BibEntry,
    DraftedSection,
    Outline,
    SectionPlan,
)
from hso.models.paper import Author, Paper, SearchQuery, Venue
from hso.models.profile import SectionProfile, SectionStructure

__all__ = [
    "Author",
    "BibEntry",
    "DraftedSection",
    "Experiment",
    "ExperimentResult",
    "ExperimentTimeSeries",
    "JCRRecord",
    "JCRZone",
    "Outline",
    "Paper",
    "SearchQuery",
    "SectionPlan",
    "SectionProfile",
    "SectionStructure",
    "Venue",
]
