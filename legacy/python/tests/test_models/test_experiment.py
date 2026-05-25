"""Experiment / ExperimentResult / ExperimentTimeSeries schema 测试。"""

from __future__ import annotations

import pytest

from hso.models import Experiment, ExperimentResult, ExperimentTimeSeries


class TestExperimentResult:
    def test_minimal_construction(self) -> None:
        r = ExperimentResult(method="Ours", metrics={"acc": 0.9})
        assert r.method == "Ours"
        assert r.metrics["acc"] == 0.9
        assert r.dataset is None

    def test_metadata_separate_from_metrics(self) -> None:
        r = ExperimentResult(
            method="Ours", metrics={"acc": 0.9}, metadata={"seed": 42, "lr": 1e-4}
        )
        assert "seed" not in r.metrics
        assert r.metadata["seed"] == 42


class TestExperimentTimeSeries:
    def test_xy_length_match_required(self) -> None:
        with pytest.raises(ValueError, match="x/y 长度不一致"):
            ExperimentTimeSeries(
                name="loss", method="Ours", x=[1, 2, 3], y=[0.1, 0.2]
            )

    def test_construction(self) -> None:
        t = ExperimentTimeSeries(
            name="loss", method="Ours", x=[1.0, 2.0], y=[0.5, 0.3]
        )
        assert t.x_label == "Epoch"
        assert t.y_label == "Value"


class TestExperiment:
    def test_all_methods_dedupe_preserves_order(self) -> None:
        exp = Experiment(
            title="t",
            results=[
                ExperimentResult(method="Ours", metrics={"a": 1}),
                ExperimentResult(method="Baseline", metrics={"a": 2}),
                ExperimentResult(method="Ours", metrics={"a": 3}),
            ],
            timeseries=[
                ExperimentTimeSeries(name="loss", method="Baseline", x=[1], y=[2]),
                ExperimentTimeSeries(name="loss", method="Other", x=[1], y=[3]),
            ],
        )
        assert exp.all_methods == ["Ours", "Baseline", "Other"]

    def test_all_metric_names_preserves_first_seen_order(self) -> None:
        exp = Experiment(
            title="t",
            results=[
                ExperimentResult(method="Ours", metrics={"FID": 1, "LPIPS": 2}),
                ExperimentResult(method="Baseline", metrics={"FID": 3, "CLIP": 4}),
            ],
        )
        assert exp.all_metric_names == ["FID", "LPIPS", "CLIP"]
