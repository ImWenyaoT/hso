"""arXiv provider：用 lukasschwab/arxiv.py 包装。"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

import arxiv

from hso.literature.base import PaperProvider
from hso.models import Author, Paper, SearchQuery, Venue

logger = logging.getLogger(__name__)


class ArxivProvider(PaperProvider):
    """arXiv 检索源。注意 arXiv 没有 venue/分区概念，所有命中默认标 preprint。"""

    name = "arxiv"

    def __init__(self, client: arxiv.Client | None = None) -> None:
        """允许注入 client 以便测试时 mock。"""
        self._client = client or arxiv.Client(page_size=50, delay_seconds=3, num_retries=3)

    def search(self, query: SearchQuery) -> list[Paper]:
        """执行检索。年份过滤通过 published_at 字段在结果上做后置过滤。"""
        cutoff = date(date.today().year - query.years, 1, 1)
        search = arxiv.Search(
            query=query.query,
            max_results=query.top_k_per_provider * 3,  # 多取再按年份后置过滤
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )
        papers: list[Paper] = []
        for result in self._client.results(search):
            published = self._to_date(result.published)
            if published is None or published < cutoff:
                continue
            papers.append(self._to_paper(result, published))
        return papers

    @staticmethod
    def _to_date(value: Any) -> date | None:
        """arxiv.Result.published 是 datetime；保险起见兼容 None / str。"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.astimezone(UTC).date()
        if isinstance(value, date):
            return value
        return None

    @staticmethod
    def _to_paper(result: Any, published: date) -> Paper:
        """把 arxiv 单条 Result 映射为标准 Paper。"""
        arxiv_id = result.entry_id.rsplit("/", 1)[-1] if result.entry_id else None
        return Paper(
            paper_id=f"arxiv:{arxiv_id}" if arxiv_id else f"arxiv:{result.title[:40]}",
            arxiv_id=arxiv_id,
            doi=getattr(result, "doi", None),
            title=result.title.strip(),
            abstract=(result.summary or "").strip() or None,
            authors=[Author(name=a.name) for a in result.authors or []],
            venue=Venue(name="arxiv", raw_name="arXiv", type="preprint"),
            published_at=published,
            url=result.entry_id,
            pdf_url=result.pdf_url,
            source="arxiv",
        )
