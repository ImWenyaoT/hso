"""中科院期刊分区匹配与过滤。

数据来源：hitfyd/ShowJCR 官方 JSON。本模块只做"加载 + 名字归一化匹配 + 过滤"，
不做爬取。用户可通过环境变量 / 参数指定本地 JSON 路径。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import SupportsFloat, SupportsIndex, cast

from hso.models import JCRRecord, Paper

logger = logging.getLogger(__name__)


def _normalize(name: str) -> str:
    """归一化期刊名：小写 + 折叠空白 + 去常见标点。"""
    s = name.lower().strip()
    for ch in (".", ",", ":", ";", "(", ")", "[", "]", "&"):
        s = s.replace(ch, " ")
    return " ".join(s.split())


class JCRFilter:
    """加载 ShowJCR 类 JSON，并按 max_zone 过滤 Paper 列表。"""

    def __init__(self, records: list[JCRRecord]) -> None:
        """从已经构造好的记录列表初始化。"""
        self._by_name: dict[str, JCRRecord] = {r.journal: r for r in records}
        self._by_issn: dict[str, JCRRecord] = {}
        for r in records:
            for issn in (r.issn, r.eissn):
                if issn:
                    self._by_issn[issn.upper().replace("-", "")] = r

    @classmethod
    def from_json(cls, path: Path) -> JCRFilter:
        """从 JSON 文件加载。

        支持两种结构：
        1. ShowJCR 风格：{"journal_name": {"分区": "1区", "影响因子": "5.6", ...}, ...}
        2. 自定义扁平结构：[{"journal": "...", "zone": 1, ...}, ...]
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        records: list[JCRRecord] = []
        if isinstance(raw, dict):
            for raw_name, info in raw.items():
                rec = cls._parse_showjcr_entry(raw_name, info)
                if rec is not None:
                    records.append(rec)
        elif isinstance(raw, list):
            for entry in raw:
                records.append(JCRRecord(**entry))
        else:
            raise ValueError(f"无法识别的 JCR JSON 结构：{type(raw).__name__}")
        logger.info("JCR 数据加载完毕，共 %d 条", len(records))
        return cls(records)

    @staticmethod
    def _parse_showjcr_entry(raw_name: str, info: dict[str, object]) -> JCRRecord | None:
        """ShowJCR 字段中文，需要映射。容错：分区缺失则跳过。"""
        zone_raw = info.get("分区") or info.get("zone")
        if zone_raw is None:
            return None
        zone_int: int | None = None
        if isinstance(zone_raw, int):
            zone_int = zone_raw
        elif isinstance(zone_raw, str):
            for ch in zone_raw:
                if ch.isdigit():
                    zone_int = int(ch)
                    break
        if zone_int not in (1, 2, 3, 4):
            return None

        if_raw = info.get("影响因子") or info.get("if_2024")
        try:
            if if_raw in (None, ""):
                if_2024 = None
            else:
                if_value = cast(str | bytes | SupportsFloat | SupportsIndex, if_raw)
                if_2024 = float(if_value)
        except (TypeError, ValueError):
            if_2024 = None

        return JCRRecord(
            journal=raw_name,
            raw_name=raw_name,
            issn=str(info["issn"]) if info.get("issn") else None,
            eissn=str(info["eissn"]) if info.get("eissn") else None,
            zone=zone_int,  # type: ignore[arg-type]
            if_2024=if_2024,
            is_top=bool(info.get("Top") or info.get("is_top")),
            is_warning=bool(info.get("预警") or info.get("is_warning")),
        )

    def lookup(self, paper: Paper) -> JCRRecord | None:
        """匹配单篇论文对应的 JCR 记录。先 ISSN 后名字。"""
        if paper.venue is None:
            return None
        for issn in (paper.venue.issn, paper.venue.eissn):
            if issn:
                rec = self._by_issn.get(issn.upper().replace("-", ""))
                if rec is not None:
                    return rec
        target = _normalize(paper.venue.name)
        return self._by_name.get(target)

    def annotate(self, papers: list[Paper]) -> list[Paper]:
        """给每篇 Paper 填充 jcr_zone 字段（不过滤）。"""
        for p in papers:
            rec = self.lookup(p)
            if rec is not None:
                p.jcr_zone = rec.zone
        return papers

    def filter(self, papers: list[Paper], max_zone: int, require_q_zone: bool = True) -> list[Paper]:
        """按分区上限过滤。max_zone=2 表示保留一区+二区。

        Args:
            papers: 候选论文。
            max_zone: 1-4，越小越严。
            require_q_zone: True 时未匹配到分区的论文（如 arXiv）会被剔除。
        """
        self.annotate(papers)
        out: list[Paper] = []
        for p in papers:
            if p.jcr_zone is None:
                if not require_q_zone:
                    out.append(p)
                continue
            if p.jcr_zone <= max_zone:
                out.append(p)
        return out
