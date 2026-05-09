"""检索聚合 + 去重。"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable

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
        """串行调用所有 provider，去重，再按 JCR 过滤。"""
        all_papers: list[Paper] = []
        for provider in self._providers:
            try:
                results = provider.search(query)
                logger.info("provider=%s 返回 %d 条", provider.name, len(results))
                all_papers.extend(results)
            except Exception as e:
                logger.warning("provider=%s 失败：%s", provider.name, e)

        deduped = self._deduplicate(all_papers)
        logger.info("聚合后 %d 条 → 去重后 %d 条", len(all_papers), len(deduped))

        if self._jcr is not None:
            filtered = self._jcr.filter(
                deduped, max_zone=query.max_zone, require_q_zone=query.require_q_zone
            )
            logger.info("JCR 过滤后 %d 条（max_zone=%d）", len(filtered), query.max_zone)
            return filtered
        return deduped

    @staticmethod
    def _deduplicate(papers: list[Paper]) -> list[Paper]:
        """三级去重：DOI / arXiv id / 标题指纹中任一 key 共享则视为同篇。

        实现：union-find，每组保留 citation_count 最高者，并补全缺失字段。
        """
        n = len(papers)
        if n == 0:
            return []

        keys_per_paper: list[list[str]] = []
        for p in papers:
            keys: list[str] = []
            if p.doi:
                keys.append(f"doi:{p.doi.lower()}")
            if p.arxiv_id:
                keys.append(f"arxiv:{p.arxiv_id}")
            keys.append(f"title:{_title_fingerprint(p.title)}")
            keys_per_paper.append(keys)

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
        for i, keys in enumerate(keys_per_paper):
            for k in keys:
                if k in key_to_idx:
                    union(key_to_idx[k], i)
                else:
                    key_to_idx[k] = i

        groups: dict[int, list[Paper]] = {}
        for i, p in enumerate(papers):
            groups.setdefault(find(i), []).append(p)

        out: list[Paper] = []
        for group in groups.values():
            best = max(group, key=lambda p: p.citation_count or 0)
            for other in group:
                if other is best:
                    continue
                if not best.abstract and other.abstract:
                    best.abstract = other.abstract
                if best.doi is None and other.doi:
                    best.doi = other.doi
                if best.arxiv_id is None and other.arxiv_id:
                    best.arxiv_id = other.arxiv_id
            out.append(best)
        return out
