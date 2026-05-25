"""用户实验材料 schema：起草 manuscript 时的输入侧主体。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperimentResult(BaseModel):
    """单次实验运行的标量指标结果。

    用于 results table。每个 ``ExperimentResult`` 是表格中的一行。
    """

    model_config = ConfigDict(extra="ignore")

    method: str = Field(description="模型/方法名，会作为表格行的 'Method' 列")
    dataset: str | None = Field(default=None, description="数据集名；可空（单数据集场景）")
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="指标键值对，例如 {'accuracy': 92.4, 'f1': 0.91}",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="自由元数据：超参、随机种子等，不进表格"
    )


class ExperimentTimeSeries(BaseModel):
    """时序型实验数据：训练 loss / accuracy 曲线、学习率曲线等。"""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="曲线名，如 'train_loss' / 'val_acc'")
    method: str = Field(description="所属方法；同名曲线不同方法画到同一张图")
    x: list[float]
    y: list[float]
    x_label: str = "Epoch"
    y_label: str = "Value"

    @field_validator("y")
    @classmethod
    def _len_must_match(cls, v: list[float], info: Any) -> list[float]:
        """x / y 长度必须一致。"""
        x = info.data.get("x")
        if x is not None and len(x) != len(v):
            raise ValueError(f"timeseries x/y 长度不一致：x={len(x)} y={len(v)}")
        return v


class Experiment(BaseModel):
    """用户提交的一份完整实验材料。

    既可以从 JSON 一把加载，也可以从多个 CSV 拼装。
    Phase 2 起草 manuscript 时，agent 只能引用此对象中的事实，不得编造。
    """

    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="manuscript 标题")
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    contributions: list[str] = Field(
        default_factory=list,
        description="作者亲自总结的核心贡献；agent 在 intro / conclusion 引用此列表",
    )
    results: list[ExperimentResult] = Field(default_factory=list)
    timeseries: list[ExperimentTimeSeries] = Field(default_factory=list)
    notes: str | None = Field(
        default=None, description="自由实验笔记；agent 用作 method 章节素材"
    )

    @property
    def all_methods(self) -> list[str]:
        """results / timeseries 中出现过的所有方法名（保序去重）。"""
        seen: dict[str, None] = {}
        for r in self.results:
            seen.setdefault(r.method, None)
        for t in self.timeseries:
            seen.setdefault(t.method, None)
        return list(seen)

    @property
    def all_metric_names(self) -> list[str]:
        """results 中出现过的所有指标名（保序）。"""
        seen: dict[str, None] = {}
        for r in self.results:
            for k in r.metrics:
                seen.setdefault(k, None)
        return list(seen)
