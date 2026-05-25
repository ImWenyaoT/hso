"""论文相关 schema：检索请求、检索结果、作者、刊物。"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Author(BaseModel):
    """论文作者。"""

    model_config = ConfigDict(extra="ignore")

    name: str
    affiliation: str | None = None
    s2_author_id: str | None = None


class Venue(BaseModel):
    """发表刊物 / 会议。"""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="标准化后的刊物名（用于 JCR 匹配）")
    raw_name: str | None = Field(default=None, description="provider 原始字段")
    issn: str | None = None
    eissn: str | None = None
    type: Literal["journal", "conference", "preprint", "unknown"] = "unknown"


class Paper(BaseModel):
    """聚合检索结果的标准论文记录。来自不同 provider 的字段统一到这里。"""

    model_config = ConfigDict(extra="ignore")

    # 标识
    paper_id: str = Field(description="跨 provider 主键，优先 DOI，其次 arxiv id，最后 hash(title)")
    doi: str | None = None
    arxiv_id: str | None = None
    s2_id: str | None = None

    # 内容
    title: str
    abstract: str | None = None
    authors: list[Author] = Field(default_factory=list)
    venue: Venue | None = None
    published_at: date | None = None
    url: str | None = None
    pdf_url: str | None = None

    # 度量
    citation_count: int | None = None

    # 来源
    source: Literal["arxiv", "semanticscholar", "openalex", "user_upload"] = "arxiv"

    # 分区（检索后才填充）
    jcr_zone: int | None = Field(default=None, description="中科院 1-4 区；None 表示未匹配到")

    @field_validator("doi")
    @classmethod
    def _normalize_doi(cls, v: str | None) -> str | None:
        """标准化 DOI：去 https 前缀、转小写。"""
        if v is None:
            return None
        v = v.strip().lower()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if v.startswith(prefix):
                v = v[len(prefix) :]
        return v or None

    @field_validator("arxiv_id")
    @classmethod
    def _normalize_arxiv(cls, v: str | None) -> str | None:
        """标准化 arXiv id：去 URL 前缀、去版本号。"""
        if v is None:
            return None
        v = v.strip()
        for prefix in ("https://arxiv.org/abs/", "http://arxiv.org/abs/", "arXiv:"):
            if v.lower().startswith(prefix.lower()):
                v = v[len(prefix) :]
        if "v" in v and v.split("v")[-1].isdigit():
            v = "v".join(v.split("v")[:-1])
        return v or None


class SearchQuery(BaseModel):
    """检索入参。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    years: int = Field(default=2, ge=1, le=10, description="近 N 年")
    max_zone: int = Field(default=2, ge=1, le=4, description="中科院分区上限（1=只要一区, 2=一区+二区...）")
    top_k_per_provider: int = Field(default=30, ge=1, le=200)
    require_q_zone: bool = Field(
        default=True,
        description="是否强制 JCR 命中；False 则保留未匹配论文（如 arXiv preprint）",
    )
