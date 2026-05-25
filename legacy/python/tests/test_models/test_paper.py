"""Paper / SearchQuery schema 单元测试。"""

from __future__ import annotations

import pytest

from hso.models import Paper, SearchQuery


class TestPaperNormalization:
    def test_doi_strips_url_prefix(self) -> None:
        p = Paper(paper_id="x", title="t", doi="https://doi.org/10.1109/Foo.2025.001")
        assert p.doi == "10.1109/foo.2025.001"

    def test_doi_lowercased(self) -> None:
        p = Paper(paper_id="x", title="t", doi="10.1109/FOO.2025.001")
        assert p.doi == "10.1109/foo.2025.001"

    def test_doi_doi_prefix(self) -> None:
        p = Paper(paper_id="x", title="t", doi="doi:10.1234/abc")
        assert p.doi == "10.1234/abc"

    def test_doi_empty_becomes_none(self) -> None:
        p = Paper(paper_id="x", title="t", doi="   ")
        assert p.doi is None

    def test_arxiv_id_strips_url(self) -> None:
        p = Paper(paper_id="x", title="t", arxiv_id="https://arxiv.org/abs/2505.12345")
        assert p.arxiv_id == "2505.12345"

    def test_arxiv_id_strips_version(self) -> None:
        p = Paper(paper_id="x", title="t", arxiv_id="2505.12345v3")
        assert p.arxiv_id == "2505.12345"

    def test_arxiv_id_handles_uppercase_prefix(self) -> None:
        p = Paper(paper_id="x", title="t", arxiv_id="arXiv:2505.12345")
        assert p.arxiv_id == "2505.12345"


class TestSearchQuery:
    def test_defaults(self) -> None:
        q = SearchQuery(query="diffusion")
        assert q.years == 2
        assert q.max_zone == 2
        assert q.require_q_zone is True

    def test_query_must_be_nonempty(self) -> None:
        with pytest.raises(ValueError):
            SearchQuery(query="")

    def test_max_zone_range(self) -> None:
        with pytest.raises(ValueError):
            SearchQuery(query="x", max_zone=5)
        with pytest.raises(ValueError):
            SearchQuery(query="x", max_zone=0)

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValueError):
            SearchQuery.model_validate({"query": "x", "unknown": 1})
