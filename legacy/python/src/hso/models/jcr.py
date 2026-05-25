"""中科院期刊分区 schema。数据源：ShowJCR（hitfyd/ShowJCR），2025 是最后一版。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

JCRZone = Literal[1, 2, 3, 4]


class JCRRecord(BaseModel):
    """单条期刊分区记录。"""

    model_config = ConfigDict(extra="ignore")

    journal: str = Field(description="规范化后的期刊全名（小写、去标点）")
    raw_name: str = Field(description="原始期刊名")
    issn: str | None = None
    eissn: str | None = None
    zone: JCRZone = Field(description="中科院大类分区 1-4")
    if_2024: float | None = Field(default=None, description="2024 年影响因子（最近一次官方发布）")
    is_top: bool = Field(default=False, description="ShowJCR 'Top' 期刊标记")
    is_warning: bool = Field(default=False, description="ShowJCR 预警名单")

    @field_validator("journal")
    @classmethod
    def _normalize_journal(cls, v: str) -> str:
        """规范化：去多余空格、转小写。匹配时用此字段。"""
        return " ".join(v.lower().split())
