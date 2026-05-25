"""LaTeX 表格生成测试。"""

from __future__ import annotations

from hso.manuscript.tables import (
    results_to_dataframe,
    results_to_latex_table,
)
from hso.models import ExperimentResult


def _sample() -> list[ExperimentResult]:
    return [
        ExperimentResult(
            method="Ours", dataset="CelebA-HQ",
            metrics={"FID": 8.21, "LPIPS": 0.142},
        ),
        ExperimentResult(
            method="Baseline-A", dataset="CelebA-HQ",
            metrics={"FID": 12.4, "LPIPS": 0.176},
        ),
        ExperimentResult(
            method="Baseline-B", dataset="CelebA-HQ",
            metrics={"FID": 9.55, "LPIPS": 0.155},
        ),
    ]


class TestDataFrame:
    def test_columns_include_method_dataset_metrics(self) -> None:
        df = results_to_dataframe(_sample())
        assert list(df.columns) == ["Method", "Dataset", "FID", "LPIPS"]
        assert len(df) == 3

    def test_metric_subset(self) -> None:
        df = results_to_dataframe(_sample(), metrics=["FID"])
        assert "FID" in df.columns
        assert "LPIPS" not in df.columns

    def test_empty_results(self) -> None:
        assert results_to_dataframe([]).empty


class TestLatexTable:
    def test_uses_booktabs_rules(self) -> None:
        out = results_to_latex_table(_sample(), caption="Main results", label="main")
        assert "\\toprule" in out
        assert "\\midrule" in out
        assert "\\bottomrule" in out

    def test_label_and_caption(self) -> None:
        out = results_to_latex_table(_sample(), caption="My caption", label="main")
        assert "\\label{tab:main}" in out
        assert "My caption" in out

    def test_default_direction_min_bolds_min_for_fid(self) -> None:
        out = results_to_latex_table(
            _sample(),
            caption="x",
            label="x",
            metrics=["FID"],
            default_direction="min",
        )
        # Ours 的 FID=8.21 应该被加粗
        assert "\\textbf{8.210}" in out
        assert "\\textbf{12.400}" not in out

    def test_default_direction_max_bolds_max(self) -> None:
        out = results_to_latex_table(
            _sample(),
            caption="x",
            label="x",
            metrics=["LPIPS"],
            default_direction="max",
        )
        assert "\\textbf{0.176}" in out

    def test_per_metric_directions_mixed(self) -> None:
        # FID 越小越好 → 加粗 8.21；LPIPS 越小越好 → 加粗 0.142
        out = results_to_latex_table(
            _sample(),
            caption="x",
            label="x",
            metrics=["FID", "LPIPS"],
            directions={"FID": "min", "LPIPS": "min"},
        )
        assert "\\textbf{8.210}" in out
        assert "\\textbf{0.142}" in out
        # 12.4 / 0.176 不该被加粗
        assert "\\textbf{12.400}" not in out
        assert "\\textbf{0.176}" not in out

    def test_unspecified_metric_uses_default_direction(self) -> None:
        # 给 FID 指定 min，不给 LPIPS 指定 → LPIPS 走 default="max" → 加粗 0.176
        out = results_to_latex_table(
            _sample(),
            caption="x",
            label="x",
            metrics=["FID", "LPIPS"],
            directions={"FID": "min"},
            default_direction="max",
        )
        assert "\\textbf{8.210}" in out  # FID min
        assert "\\textbf{0.176}" in out  # LPIPS max (default)

    def test_bold_best_disabled(self) -> None:
        out = results_to_latex_table(
            _sample(), caption="x", label="x", bold_best=False
        )
        assert "\\textbf" not in out

    def test_empty_results_emits_placeholder_table(self) -> None:
        out = results_to_latex_table([], caption="x", label="x")
        assert "no results" in out
        assert "\\toprule" in out
