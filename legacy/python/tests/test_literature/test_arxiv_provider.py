"""ArxivProvider 单元测试：mock arxiv.Client.results。"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from hso.literature.arxiv_provider import ArxivProvider
from hso.models import SearchQuery


def _stub_result(
    title: str,
    arxiv_id: str,
    published: datetime,
    summary: str = "abs",
    doi: str | None = None,
) -> SimpleNamespace:
    """构造 arxiv.Result-like 对象。"""
    return SimpleNamespace(
        title=title,
        summary=summary,
        published=published,
        authors=[SimpleNamespace(name="A1"), SimpleNamespace(name="A2")],
        entry_id=f"http://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"http://arxiv.org/pdf/{arxiv_id}.pdf",
        doi=doi,
    )


class TestArxivProvider:
    def test_filters_by_year_cutoff(self) -> None:
        client = MagicMock()
        now = datetime.now(UTC)
        old = now.replace(year=now.year - 5)
        recent = now.replace(year=now.year - 1)
        client.results.return_value = iter(
            [
                _stub_result("Old paper", "2020.0001", old),
                _stub_result("Recent paper", "2025.0001", recent),
            ]
        )
        provider = ArxivProvider(client=client)
        papers = provider.search(SearchQuery(query="diffusion", years=2))
        assert len(papers) == 1
        assert papers[0].title == "Recent paper"

    def test_maps_metadata(self) -> None:
        client = MagicMock()
        now = datetime.now(UTC)
        client.results.return_value = iter(
            [_stub_result("Title", "2505.12345", now, doi="10.1234/abc")]
        )
        provider = ArxivProvider(client=client)
        papers = provider.search(SearchQuery(query="x", years=2))
        p = papers[0]
        assert p.arxiv_id == "2505.12345"
        assert p.doi == "10.1234/abc"
        assert p.source == "arxiv"
        assert len(p.authors) == 2
        assert p.venue is not None
        assert p.venue.type == "preprint"
