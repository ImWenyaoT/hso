"""把 ExperimentResult 列表转成 booktabs 风格的 LaTeX 表格。"""

from __future__ import annotations

import logging
from typing import Literal, cast

import pandas as pd

from hso.models import ExperimentResult

logger = logging.getLogger(__name__)

MetricDirection = Literal["max", "min"]


def results_to_dataframe(
    results: list[ExperimentResult],
    metrics: list[str] | None = None,
) -> pd.DataFrame:
    """把 results 平铺成 DataFrame：行 = (method, dataset)，列 = metrics。

    Args:
        results: 实验结果列表。
        metrics: 要保留的指标名（保序）；None 时自动从所有 results 收集。
    """
    if not results:
        return pd.DataFrame()

    if metrics is None:
        seen: dict[str, None] = {}
        for r in results:
            for k in r.metrics:
                seen.setdefault(k, None)
        metrics = list(seen)

    rows: list[dict[str, object]] = []
    for r in results:
        row: dict[str, object] = {"Method": r.method}
        if r.dataset is not None:
            row["Dataset"] = r.dataset
        for m in metrics:
            row[m] = r.metrics.get(m)
        rows.append(row)
    return pd.DataFrame(rows)


def results_to_latex_table(
    results: list[ExperimentResult],
    *,
    caption: str,
    label: str,
    metrics: list[str] | None = None,
    float_fmt: str = "{:.3f}",
    bold_best: bool = True,
    directions: dict[str, MetricDirection] | None = None,
    default_direction: MetricDirection = "max",
) -> str:
    """生成 booktabs 风格 LaTeX 表格代码。

    Args:
        results: 实验结果列表。
        caption: 表格 caption。
        label: ``\\label{tab:...}`` 中的 label（不含前缀）。
        metrics: 要展示的指标列；None 自动收集。
        float_fmt: 浮点格式字符串。
        bold_best: 是否把每列最优值加粗。
        directions: 每个 metric 的方向 ``{"FID": "min", "CLIP-Score": "max"}``；未列出
            的 metric 走 ``default_direction``。
        default_direction: 没有显式 direction 的 metric 默认方向。``"max"`` = 最大值最优。
    """
    df = results_to_dataframe(results, metrics=metrics)
    if df.empty:
        return _empty_table(caption=caption, label=label)

    metric_cols = [c for c in df.columns if c not in ("Method", "Dataset")]
    formatted = df.copy()
    directions = directions or {}

    for col in metric_cols:
        series = pd.to_numeric(formatted[col], errors="coerce")
        if not bold_best or series.notna().sum() == 0:
            formatted[col] = [_fmt_value(v, float_fmt, bold=False) for _, v in series.items()]
            continue
        col_dir: MetricDirection = directions.get(col, default_direction)
        best_idx = series.idxmax() if col_dir == "max" else series.idxmin()
        formatted[col] = [
            _fmt_value(v, float_fmt, bold=(i == best_idx)) for i, v in series.items()
        ]

    column_format = "l" + ("l" if "Dataset" in df.columns else "") + "c" * len(metric_cols)
    body = formatted.to_latex(
        index=False,
        escape=False,
        column_format=column_format,
        caption=caption,
        label=f"tab:{label}",
        position="htbp",
    )
    # pandas 的 to_latex 用 \toprule / \midrule / \bottomrule 已是 booktabs；保留即可
    return cast(str, body)


def _fmt_value(value: object, float_fmt: str, *, bold: bool) -> str:
    """单元格格式化：数值用 float_fmt，NaN 显示为 '--'，可选加粗。"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "--"
    if isinstance(value, (int, float)):
        s = float_fmt.format(float(value))
    else:
        s = str(value)
    return f"\\textbf{{{s}}}" if bold else s


def _empty_table(*, caption: str, label: str) -> str:
    """results 为空时返回一个占位表格，避免编译炸。"""
    return (
        "\\begin{table}[htbp]\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{tab:{label}}}\n"
        "\\begin{tabular}{l}\n"
        "\\toprule\n"
        "(no results)\\\\\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n"
    )
