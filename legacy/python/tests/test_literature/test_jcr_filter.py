"""JCRFilter 单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hso.literature.jcr_filter import JCRFilter
from hso.models import Paper


class TestJCRFilterFromJson:
    def test_load_showjcr_format(self, fixtures_dir: Path) -> None:
        f = JCRFilter.from_json(fixtures_dir / "jcr_showjcr_sample.json")
        # 'Bad Entry No Zone' 应该被跳过 → 4 条留 4 条
        assert len(f._by_name) == 4

    def test_skips_entries_missing_zone(self, fixtures_dir: Path) -> None:
        f = JCRFilter.from_json(fixtures_dir / "jcr_showjcr_sample.json")
        assert "bad entry no zone" not in f._by_name

    def test_lookup_by_issn(self, fixtures_dir: Path, sample_papers: list[Paper]) -> None:
        f = JCRFilter.from_json(fixtures_dir / "jcr_showjcr_sample.json")
        # 第一篇 TPAMI 通过 ISSN 命中
        rec = f.lookup(sample_papers[0])
        assert rec is not None
        assert rec.zone == 1
        assert rec.is_top is True


class TestJCRFilterAnnotate:
    def test_annotate_fills_zone(self, jcr_filter: JCRFilter, sample_papers: list[Paper]) -> None:
        jcr_filter.annotate(sample_papers)
        assert sample_papers[0].jcr_zone == 1
        assert sample_papers[1].jcr_zone == 2
        assert sample_papers[2].jcr_zone is None  # arxiv preprint
        assert sample_papers[3].jcr_zone == 3


class TestJCRFilterFilter:
    def test_max_zone_2_keeps_q1_q2(
        self, jcr_filter: JCRFilter, sample_papers: list[Paper]
    ) -> None:
        out = jcr_filter.filter(sample_papers, max_zone=2)
        ids = {p.paper_id for p in out}
        assert "doi:10.1109/tpami.2025.0001" in ids
        assert "doi:10.1016/pr.2024.0002" in ids
        assert "doi:10.1016/neucom.2024.0003" not in ids
        assert "arxiv:2505.12345" not in ids  # preprint 默认被剔除

    def test_max_zone_1_only_keeps_q1(
        self, jcr_filter: JCRFilter, sample_papers: list[Paper]
    ) -> None:
        out = jcr_filter.filter(sample_papers, max_zone=1)
        assert len(out) == 1
        assert out[0].jcr_zone == 1

    def test_allow_preprint(self, jcr_filter: JCRFilter, sample_papers: list[Paper]) -> None:
        out = jcr_filter.filter(sample_papers, max_zone=2, require_q_zone=False)
        ids = {p.paper_id for p in out}
        assert "arxiv:2505.12345" in ids


class TestJCRFilterUnknownFormat:
    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("42", encoding="utf-8")
        with pytest.raises(ValueError):
            JCRFilter.from_json(bad)
