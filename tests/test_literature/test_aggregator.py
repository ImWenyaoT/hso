"""SearchAggregator 单元测试：去重、provider 容错、JCR 串联。"""

from __future__ import annotations

from datetime import date

from hso.literature.aggregator import SearchAggregator
from hso.literature.base import PaperProvider
from hso.literature.jcr_filter import JCRFilter
from hso.models import Paper, SearchQuery, Venue


class _StubProvider(PaperProvider):
    """测试用 stub。"""

    def __init__(self, name: str, papers: list[Paper], raise_exc: bool = False) -> None:
        self.name = name
        self._papers = papers
        self._raise = raise_exc

    def search(self, query: SearchQuery) -> list[Paper]:
        if self._raise:
            raise RuntimeError("simulated provider failure")
        return self._papers


def _make_paper(
    pid: str,
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    title: str = "Sample title",
    citations: int = 0,
    venue_name: str = "arxiv",
) -> Paper:
    return Paper(
        paper_id=pid,
        doi=doi,
        arxiv_id=arxiv_id,
        title=title,
        abstract="abstract",
        venue=Venue(name=venue_name, type="preprint" if venue_name == "arxiv" else "journal"),
        published_at=date(2025, 1, 1),
        citation_count=citations,
        source="arxiv" if venue_name == "arxiv" else "semanticscholar",
    )


class TestDeduplication:
    def test_dedup_by_doi(self) -> None:
        p1 = _make_paper("arxiv:1", arxiv_id="1234.5678", title="Same paper", citations=5)
        p2 = _make_paper("doi:10.1/x", doi="10.1/x", title="Same paper", citations=20)
        agg = SearchAggregator([_StubProvider("a", [p1]), _StubProvider("b", [p2])])
        out = agg.search(SearchQuery(query="x"))
        # 标题指纹相同 → 去重，保留高引版本
        assert len(out) == 1
        assert out[0].citation_count == 20

    def test_dedup_by_arxiv_id(self) -> None:
        p1 = _make_paper("arxiv:9999.0001", arxiv_id="9999.0001", citations=1)
        p2 = _make_paper("arxiv:9999.0001b", arxiv_id="9999.0001", citations=10)
        agg = SearchAggregator([_StubProvider("a", [p1, p2])])
        out = agg.search(SearchQuery(query="x"))
        assert len(out) == 1
        assert out[0].citation_count == 10

    def test_dedup_keeps_distinct(self) -> None:
        p1 = _make_paper("arxiv:1", arxiv_id="1.1", title="A")
        p2 = _make_paper("arxiv:2", arxiv_id="2.2", title="B")
        agg = SearchAggregator([_StubProvider("a", [p1, p2])])
        out = agg.search(SearchQuery(query="x"))
        assert len(out) == 2


class TestProviderResilience:
    def test_failed_provider_does_not_crash(self) -> None:
        good = _make_paper("arxiv:1", arxiv_id="1.1")
        agg = SearchAggregator(
            [
                _StubProvider("bad", [], raise_exc=True),
                _StubProvider("good", [good]),
            ]
        )
        out = agg.search(SearchQuery(query="x"))
        assert len(out) == 1


class TestJCRIntegration:
    def test_aggregator_applies_jcr_filter(self, jcr_filter: JCRFilter) -> None:
        q1 = _make_paper(
            "doi:tpami",
            doi="10.1109/TPAMI.2025.0001",
            title="Q1 paper",
            venue_name="ieee transactions on pattern analysis and machine intelligence",
        )
        # 注意 venue_name 要与 JCRRecord.journal（已 normalize）匹配
        q1.venue = Venue(name="IEEE Transactions on Pattern Analysis and Machine Intelligence",
                          issn="0162-8828", type="journal")
        q3 = _make_paper(
            "doi:neuro",
            doi="10.1016/NEUCOM.2024.0003",
            title="Q3 paper",
            venue_name="neurocomputing",
        )
        q3.venue = Venue(name="Neurocomputing", issn="0925-2312", type="journal")

        agg = SearchAggregator([_StubProvider("s2", [q1, q3])], jcr_filter=jcr_filter)
        out = agg.search(SearchQuery(query="x", max_zone=2))
        ids = {p.paper_id for p in out}
        assert "doi:tpami" in ids
        assert "doi:neuro" not in ids
