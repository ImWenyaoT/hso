"""Semantic Scholar provider：直接走 REST，避免 SDK 版本耦合。"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from hso.literature.base import PaperProvider
from hso.models import Author, Paper, SearchQuery, Venue

logger = logging.getLogger(__name__)

_S2_BASE = "https://api.semanticscholar.org/graph/v1"
_FIELDS = (
    "paperId,title,abstract,year,publicationDate,externalIds,"
    "venue,publicationVenue,authors.name,citationCount,openAccessPdf"
)


class SemanticScholarProvider(PaperProvider):
    """Semantic Scholar Graph API。提供 venue 字段，便于后续 JCR 匹配。"""

    name = "semanticscholar"

    def __init__(
        self,
        api_key: str = "",
        client: httpx.Client | None = None,
    ) -> None:
        """初始化。client 注入用于测试时 mock。"""
        self._headers = {"x-api-key": api_key} if api_key else {}
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=30.0, headers=self._headers)

    def close(self) -> None:
        """Close the owned HTTP client."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> SemanticScholarProvider:
        """Return this provider when used as a context manager."""
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Close network resources when leaving a context manager."""
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError,)),
        reraise=True,
    )
    def _fetch(self, query: SearchQuery) -> dict[str, Any]:
        """调用 S2 paper/search 接口，处理速率限制重试。"""
        cutoff_year = date.today().year - query.years
        params: dict[str, str | int] = {
            "query": query.query,
            "fields": _FIELDS,
            "limit": min(query.top_k_per_provider, 100),
            "year": f"{cutoff_year}-",
        }
        resp = self._client.get(f"{_S2_BASE}/paper/search", params=params)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    def search(self, query: SearchQuery) -> list[Paper]:
        """调用 S2 并映射为 Paper 列表。"""
        try:
            data = self._fetch(query)
        except httpx.HTTPError as e:
            logger.warning("Semantic Scholar 检索失败：%s", e)
            return []

        results = data.get("data", []) or []
        papers: list[Paper] = []
        for raw in results:
            paper = self._to_paper(raw)
            if paper is not None:
                papers.append(paper)
        return papers

    @staticmethod
    def _to_paper(raw: dict[str, Any]) -> Paper | None:
        """把 S2 单条 paper 映射为标准 Paper。缺关键字段返回 None。"""
        title = raw.get("title")
        if not title:
            return None

        external_ids = raw.get("externalIds") or {}
        doi = external_ids.get("DOI")
        arxiv_id = external_ids.get("ArXiv")

        published_at: date | None = None
        if raw.get("publicationDate"):
            try:
                published_at = date.fromisoformat(raw["publicationDate"])
            except ValueError:
                published_at = None
        if published_at is None and raw.get("year"):
            try:
                published_at = date(int(raw["year"]), 1, 1)
            except (TypeError, ValueError):
                published_at = None

        venue: Venue | None = None
        pub_venue = raw.get("publicationVenue") or {}
        venue_name = pub_venue.get("name") or raw.get("venue")
        if venue_name:
            venue = Venue(
                name=venue_name,
                raw_name=venue_name,
                issn=pub_venue.get("issn"),
                type="journal" if pub_venue.get("type") == "journal" else "unknown",
            )

        s2_id = raw.get("paperId")
        primary_id = (
            f"doi:{doi.lower()}"
            if doi
            else f"arxiv:{arxiv_id}"
            if arxiv_id
            else f"s2:{s2_id}"
        )

        return Paper(
            paper_id=primary_id,
            doi=doi,
            arxiv_id=arxiv_id,
            s2_id=s2_id,
            title=title.strip(),
            abstract=(raw.get("abstract") or "").strip() or None,
            authors=[Author(name=a["name"]) for a in raw.get("authors") or [] if a.get("name")],
            venue=venue,
            published_at=published_at,
            url=f"https://www.semanticscholar.org/paper/{s2_id}" if s2_id else None,
            pdf_url=(raw.get("openAccessPdf") or {}).get("url"),
            citation_count=raw.get("citationCount"),
            source="semanticscholar",
        )
