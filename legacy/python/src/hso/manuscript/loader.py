"""从 JSON / CSV 加载用户实验材料为 Experiment 对象。

设计原则：
- JSON 是首选格式，结构与 Experiment schema 一一对应
- CSV 仅用于 results 表（多行 = 多个方法 × 多个数据集），meta（title / abstract / contributions）
  仍要走 JSON 边路；CSV 不强求列名固定，列即指标
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from hso.models import Experiment, ExperimentResult, ExperimentTimeSeries

logger = logging.getLogger(__name__)


class ExperimentLoader:
    """实验数据加载器。"""

    @staticmethod
    def from_json(path: Path) -> Experiment:
        """从单个 JSON 文件加载完整 Experiment。

        Args:
            path: JSON 路径。结构按 Experiment 字段，缺省字段会以 schema default 兜底。
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Experiment.model_validate(raw)

    @staticmethod
    def from_results_csv(
        path: Path,
        title: str,
        method_col: str = "method",
        dataset_col: str | None = "dataset",
        ignore_cols: tuple[str, ...] = (),
    ) -> Experiment:
        """从 CSV 加载实验 results 表。

        - ``method_col`` / ``dataset_col`` 是元信息列；其余数值列都进 ``metrics``。
        - 非数值列（除元信息）会自动进入 ``metadata``。
        - ``title`` / ``abstract`` 等仍需用户后续手工填，本方法只填 results。

        Args:
            path: CSV 路径。
            title: manuscript 标题（CSV 没有此信息）。
            method_col: 方法名所在列名。
            dataset_col: 数据集列名；None 表示单数据集，跳过。
            ignore_cols: 要忽略的列名。
        """
        df = pd.read_csv(path)
        if method_col not in df.columns:
            raise ValueError(f"CSV 缺少 method 列：{method_col!r}（已有列：{list(df.columns)}）")

        results: list[ExperimentResult] = []
        columns = list(df.columns)
        for values in df.itertuples(index=False, name=None):
            row = dict(zip(columns, values, strict=True))
            metrics: dict[str, float] = {}
            metadata: dict[str, Any] = {}
            for col, value in row.items():
                if col in (method_col, dataset_col) or col in ignore_cols:
                    continue
                if pd.isna(value):
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    metrics[str(col)] = float(value)
                else:
                    metadata[str(col)] = value
            results.append(
                ExperimentResult(
                    method=str(row[method_col]),
                    dataset=(str(row[dataset_col]) if dataset_col and dataset_col in df.columns else None),
                    metrics=metrics,
                    metadata=metadata,
                )
            )
        logger.info("CSV 加载完毕：%d 条 results", len(results))
        return Experiment(title=title, results=results)

    @staticmethod
    def from_timeseries_csv(
        path: Path,
        method_col: str = "method",
        x_col: str = "epoch",
        x_label: str | None = None,
    ) -> list[ExperimentTimeSeries]:
        """从 CSV 加载时序数据；除 method/x 外每个数值列各自成一条 TimeSeries。

        Args:
            path: CSV 路径。
            method_col: 方法名列。
            x_col: 横轴列。
            x_label: 横轴标签；None 时使用 ``x_col`` 名首字母大写。
        """
        df = pd.read_csv(path)
        for required in (method_col, x_col):
            if required not in df.columns:
                raise ValueError(f"CSV 缺少 {required!r} 列（已有：{list(df.columns)}）")

        ts_list: list[ExperimentTimeSeries] = []
        value_cols = [c for c in df.columns if c not in (method_col, x_col)]
        x_label = x_label or x_col.replace("_", " ").title()
        for method, group in df.groupby(method_col):
            group_sorted = group.sort_values(x_col)
            x = group_sorted[x_col].astype(float).tolist()
            for col in value_cols:
                series = group_sorted[col]
                if not pd.api.types.is_numeric_dtype(series):
                    continue
                y = series.astype(float).tolist()
                ts_list.append(
                    ExperimentTimeSeries(
                        name=str(col),
                        method=str(method),
                        x=x,
                        y=y,
                        x_label=x_label,
                        y_label=str(col).replace("_", " ").title(),
                    )
                )
        return ts_list
