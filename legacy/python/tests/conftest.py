"""pytest fixtures：构造常用 Paper / JCRFilter / mock LLM。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from hso.literature.jcr_filter import JCRFilter
from hso.models import Author, JCRRecord, Paper, Venue


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def jcr_records() -> list[JCRRecord]:
    """三条手工构造的分区记录，覆盖 1/2/3 区。"""
    return [
        JCRRecord(journal="ieee transactions on pattern analysis and machine intelligence",
                  raw_name="IEEE Transactions on Pattern Analysis and Machine Intelligence",
                  issn="0162-8828", zone=1, if_2024=20.8, is_top=True),
        JCRRecord(journal="pattern recognition", raw_name="Pattern Recognition",
                  issn="0031-3203", zone=2, if_2024=8.5),
        JCRRecord(journal="neurocomputing", raw_name="Neurocomputing",
                  issn="0925-2312", zone=3, if_2024=5.5),
    ]


@pytest.fixture
def jcr_filter(jcr_records: list[JCRRecord]) -> JCRFilter:
    return JCRFilter(jcr_records)


@pytest.fixture
def sample_papers() -> list[Paper]:
    """构造覆盖三种来源 / 三种 venue 的 Paper 列表。"""
    return [
        Paper(
            paper_id="doi:10.1109/tpami.2025.0001",
            doi="10.1109/TPAMI.2025.0001",
            title="A novel diffusion model for image editing",
            abstract="We propose a new method...",
            authors=[Author(name="Alice")],
            venue=Venue(name="IEEE Transactions on Pattern Analysis and Machine Intelligence",
                        issn="0162-8828", type="journal"),
            published_at=date(2025, 6, 1),
            citation_count=42,
            source="semanticscholar",
        ),
        Paper(
            paper_id="doi:10.1016/pr.2024.0002",
            doi="10.1016/PR.2024.0002",
            title="Pattern recognition via transformers",
            abstract="We benchmark...",
            authors=[Author(name="Bob")],
            venue=Venue(name="Pattern Recognition", issn="0031-3203", type="journal"),
            published_at=date(2024, 11, 1),
            citation_count=10,
            source="semanticscholar",
        ),
        Paper(
            paper_id="arxiv:2505.12345",
            arxiv_id="2505.12345",
            title="Some preprint with no venue match",
            abstract="abstract...",
            authors=[Author(name="Carol")],
            venue=Venue(name="arxiv", type="preprint"),
            published_at=date(2025, 5, 1),
            source="arxiv",
        ),
        Paper(
            paper_id="doi:10.1016/neucom.2024.0003",
            doi="10.1016/NEUCOM.2024.0003",
            title="A neurocomputing study",
            abstract="abstract...",
            authors=[Author(name="Dan")],
            venue=Venue(name="Neurocomputing", issn="0925-2312", type="journal"),
            published_at=date(2024, 8, 1),
            citation_count=3,
            source="semanticscholar",
        ),
    ]
