"""检索聚合 + 去重。"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import chain

from hso.literature.base import PaperProvider
from hso.literature.jcr_filter import JCRFilter
from hso.models import Paper, SearchQuery

logger = logging.getLogger(__name__)


def _title_fingerprint(title: str) -> str:
    """对标题做模糊指纹，用于无 DOI / arXiv id 时的去重。"""
    norm = "".join(ch.lower() for ch in title if ch.isalnum())
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:16]


class SearchAggregator:
    """编排多个 provider，做聚合 + 去重 + JCR 过滤。"""

    def __init__(
        self,
        providers: Iterable[PaperProvider],
        jcr_filter: JCRFilter | None = None,
    ) -> None:
        """构造器。

        Args:
            providers: 实现 PaperProvider 的检索源。
            jcr_filter: 可选的 JCR 过滤器；None 时跳过分区过滤。
        """
        self._providers = list(providers)
        self._jcr = jcr_filter

    def search(self, query: SearchQuery) -> list[Paper]:
        """并行调用所有 provider，去重，再按 JCR 过滤。"""
        provider_results: list[list[Paper]] = [[] for _ in self._providers]
        with ThreadPoolExecutor(max_workers=max(1, len(self._providers))) as executor:
            future_to_provider = {
                executor.submit(provider.search, query): (idx, provider)
                for idx, provider in enumerate(self._providers)
            }
            for future in as_completed(future_to_provider):
                idx, provider = future_to_provider[future]
                try:
                    results = future.result()
                    logger.info("provider=%s 返回 %d 条", provider.name, len(results))
                    provider_results[idx] = results
                except Exception as e:
                    logger.warning("provider=%s 失败：%s", provider.name, e)

        raw_count = sum(len(results) for results in provider_results)
        deduped = self._deduplicate(chain.from_iterable(provider_results))
        logger.info("聚合后 %d 条 → 去重后 %d 条", raw_count, len(deduped))

        if self._jcr is not None:
            filtered = self._jcr.filter(
                deduped, max_zone=query.max_zone, require_q_zone=query.require_q_zone
            )
            logger.info("JCR 过滤后 %d 条（max_zone=%d）", len(filtered), query.max_zone)
            return filtered
        return deduped

    @staticmethod
    def _deduplicate(papers: Iterable[Paper]) -> list[Paper]:
        """三级去重：DOI / arXiv id / 标题指纹中任一 key 共享则视为同篇。

        实现：union-find，每组保留 citation_count 最高者，并补全缺失字段。
        """
        papers = list(papers)
        n = len(papers)
        if n == 0:
            return []

        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        key_to_idx: dict[str, int] = {}
        for i, paper in enumerate(papers):
            for k in _dedupe_keys(paper):
                if k in key_to_idx:
                    union(key_to_idx[k], i)
                else:
                    key_to_idx[k] = i

        best_by_root: dict[int, Paper] = {}
        for i, paper in enumerate(papers):
            root = find(i)
            best = best_by_root.get(root)
            if best is None or (paper.citation_count or 0) > (best.citation_count or 0):
                best_by_root[root] = paper

        for i, paper in enumerate(papers):
            best = best_by_root[find(i)]
            if paper is best:
                continue
            if not best.abstract and paper.abstract:
                best.abstract = paper.abstract
            if best.doi is None and paper.doi:
                best.doi = paper.doi
            if best.arxiv_id is None and paper.arxiv_id:
                best.arxiv_id = paper.arxiv_id

        return list(best_by_root.values())


def _dedupe_keys(paper: Paper) -> Iterable[str]:
    """Yield deduplication keys for one paper without allocating a per-paper list."""
    if paper.doi:
        yield f"doi:{paper.doi.lower()}"
    if paper.arxiv_id:
        yield f"arxiv:{paper.arxiv_id}"
    yield f"title:{_title_fingerprint(paper.title)}"
