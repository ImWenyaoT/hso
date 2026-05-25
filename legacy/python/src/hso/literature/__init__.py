"""文献检索 + JCR 过滤 + 聚合去重。"""

from hso.literature.aggregator import SearchAggregator
from hso.literature.arxiv_provider import ArxivProvider
from hso.literature.base import PaperProvider
from hso.literature.jcr_filter import JCRFilter
from hso.literature.s2_provider import SemanticScholarProvider

__all__ = [
    "ArxivProvider",
    "JCRFilter",
    "PaperProvider",
    "SearchAggregator",
    "SemanticScholarProvider",
]
