"""SemanticScholar provider 单元测试：用 respx mock HTTP。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from hso.literature.s2_provider import SemanticScholarProvider
from hso.models import SearchQuery


@pytest.fixture
def s2_fixture(fixtures_dir: Path) -> dict:
    return json.loads((fixtures_dir / "s2_response.json").read_text(encoding="utf-8"))


class TestSemanticScholarProvider:
    @respx.mock
    def test_search_maps_full_record(self, s2_fixture: dict) -> None:
        respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
            return_value=httpx.Response(200, json=s2_fixture)
        )
        provider = SemanticScholarProvider(client=httpx.Client(timeout=5.0, trust_env=False))
        papers = provider.search(SearchQuery(query="diffusion"))
        # 第三条无 title 应被丢弃
        assert len(papers) == 2

        first = papers[0]
        assert first.doi == "10.1109/tpami.2025.0001"
        assert first.s2_id == "abc123"
        assert first.citation_count == 42
        assert first.venue is not None
        assert first.venue.name == "IEEE Transactions on Pattern Analysis and Machine Intelligence"
        assert first.venue.issn == "0162-8828"
        assert first.published_at is not None
        assert first.published_at.year == 2025
        assert first.pdf_url == "https://example.com/paper.pdf"
        assert len(first.authors) == 2

    @respx.mock
    def test_arxiv_id_extracted(self, s2_fixture: dict) -> None:
        respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
            return_value=httpx.Response(200, json=s2_fixture)
        )
        provider = SemanticScholarProvider(client=httpx.Client(timeout=5.0, trust_env=False))
        papers = provider.search(SearchQuery(query="diffusion"))
        preprint = papers[1]
        assert preprint.arxiv_id == "2505.12345"
        assert preprint.doi is None

    @respx.mock
    def test_http_error_returns_empty_list(self) -> None:
        respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
            return_value=httpx.Response(429)
        )
        provider = SemanticScholarProvider(client=httpx.Client(timeout=5.0, trust_env=False))
        papers = provider.search(SearchQuery(query="x"))
        # 经过 tenacity 3 次重试后依然 429 → 返回空列表
        assert papers == []

    def test_close_only_closes_owned_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SemanticScholarProvider closes clients it creates internally."""
        provider = SemanticScholarProvider()
        mock_close = MagicMock()
        monkeypatch.setattr(provider._client, "close", mock_close)

        provider.close()

        mock_close.assert_called_once_with()

    def test_close_keeps_injected_client_open(self) -> None:
        """SemanticScholarProvider does not own test or shared injected clients."""
        client = httpx.Client(timeout=5.0, trust_env=False)
        provider = SemanticScholarProvider(client=client)

        provider.close()

        assert not client.is_closed
        client.close()
