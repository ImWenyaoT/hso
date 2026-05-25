"""把 ExperimentTimeSeries 渲染成 PDF 图，供 LaTeX \\includegraphics 引用。

设计：用 matplotlib 默认 backend 直接导出 PDF，避免 tikzplotlib 维护风险。
LaTeX 端通过 \\includegraphics{path/to/file.pdf} 引入即可。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 测试 / CI 无显示环境
import matplotlib.pyplot as plt

from hso.models import ExperimentTimeSeries

logger = logging.getLogger(__name__)


def render_timeseries_figure(
    timeseries: list[ExperimentTimeSeries],
    output_path: Path,
    *,
    series_name: str | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (5.0, 3.0),
) -> Path:
    """把同名时序数据按方法叠加在一张图上，导出 PDF。

    Args:
        timeseries: 候选 TimeSeries 列表，可包含多种 ``name``。
        output_path: 输出 PDF 路径（含扩展名）。父目录会自动创建。
        series_name: 仅渲染此名字的曲线；None 时取列表中第一个的 name。
        title: 图标题。None 时使用 ``series_name``。
        figsize: 单位英寸。

    Returns:
        实际写入路径。
    """
    if not timeseries:
        raise ValueError("timeseries 不能为空")

    name = series_name or timeseries[0].name
    chosen = [t for t in timeseries if t.name == name]
    if not chosen:
        raise ValueError(f"未找到 series_name={name!r} 的曲线")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=figsize)
    try:
        # 同一方法的多条曲线（如重复实验）画在一起；这里按 method 聚合
        by_method: dict[str, list[ExperimentTimeSeries]] = defaultdict(list)
        for t in chosen:
            by_method[t.method].append(t)

        for method, group in by_method.items():
            for t in group:
                ax.plot(t.x, t.y, label=method)

        first = chosen[0]
        ax.set_xlabel(first.x_label)
        ax.set_ylabel(first.y_label)
        ax.set_title(title or name)
        ax.legend(loc="best", frameon=False)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_path, format="pdf")
    finally:
        plt.close(fig)
    logger.info("figure 写入：%s", output_path)
    return output_path
