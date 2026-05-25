"""figures 模块测试：验证 PDF 写入与异常路径。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hso.manuscript import render_timeseries_figure
from hso.models import ExperimentTimeSeries


def _ts(method: str, name: str = "loss") -> ExperimentTimeSeries:
    return ExperimentTimeSeries(
        name=name, method=method, x=[1.0, 2.0, 3.0], y=[1.0, 0.8, 0.6]
    )


class TestRenderTimeseries:
    def test_writes_pdf(self, tmp_path: Path) -> None:
        out = tmp_path / "fig.pdf"
        result = render_timeseries_figure(
            [_ts("Ours"), _ts("Baseline")], out, series_name="loss"
        )
        assert result == out
        assert out.exists()
        # 简单确认是 PDF（前缀 magic）
        assert out.read_bytes()[:5] == b"%PDF-"

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "deep" / "nested" / "fig.pdf"
        render_timeseries_figure([_ts("Ours")], out)
        assert out.exists()

    def test_empty_list_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="不能为空"):
            render_timeseries_figure([], tmp_path / "x.pdf")

    def test_unknown_series_name_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="未找到"):
            render_timeseries_figure(
                [_ts("Ours", name="loss")], tmp_path / "x.pdf", series_name="acc"
            )

    def test_default_series_name_picks_first(self, tmp_path: Path) -> None:
        # 第一条 name='loss'，第二条 name='acc'，默认渲染 loss
        ts = [_ts("Ours", name="loss"), _ts("Ours", name="acc")]
        out = tmp_path / "x.pdf"
        render_timeseries_figure(ts, out)
        assert out.exists()
