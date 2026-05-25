"""章节结构归纳产物：SectionProfile."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class SectionStructure(BaseModel):
    """单一章节的写作套路总结。"""

    model_config = ConfigDict(extra="ignore")

    section: str = Field(description="如 introduction / related_work / method / experiment / conclusion")
    common_subtopics: list[str] = Field(
        default_factory=list,
        description="该领域作者在此章节通常会展开的子话题，按出现频率降序",
    )
    typical_opening: str | None = Field(
        default=None, description="常见开篇套路（背景 / 痛点 / 方法概述 / ...）"
    )
    underexplored: list[str] = Field(
        default_factory=list,
        description="较少被讨论但本工作可以贡献的角度",
    )
    recommended_artifacts: list[str] = Field(
        default_factory=list,
        description="该章节常配的图表（如 ablation table / convergence curve / loss landscape）",
    )
    evidence_paper_ids: list[str] = Field(
        default_factory=list,
        description="支撑此归纳的 paper_id 列表",
    )


class SectionProfile(BaseModel):
    """完整 manuscript 章节级写作 profile，agent 后续用它指导 outline 与起草。"""

    model_config = ConfigDict(extra="ignore")

    field_query: str = Field(description="原始研究方向查询")
    n_papers: int = Field(description="参与归纳的论文数")
    sections: list[SectionStructure] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    llm_model: str | None = None
