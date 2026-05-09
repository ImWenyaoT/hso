"""ExperimentLoader 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hso.manuscript import ExperimentLoader


class TestFromJson:
    def test_loads_full_experiment(self, fixtures_dir: Path) -> None:
        exp = ExperimentLoader.from_json(fixtures_dir / "experiment.json")
        assert exp.title.startswith("Diffusion")
        assert len(exp.results) == 3
        assert exp.results[0].method == "Ours"
        assert exp.results[0].metrics["FID"] == 8.21
        assert len(exp.timeseries) == 2
        assert exp.contributions[0].startswith("A novel")


class TestFromResultsCsv:
    def test_loads_csv_with_metadata_column(self, fixtures_dir: Path) -> None:
        exp = ExperimentLoader.from_results_csv(
            fixtures_dir / "results.csv", title="My Title"
        )
        assert exp.title == "My Title"
        assert len(exp.results) == 3
        ours = next(r for r in exp.results if r.method == "Ours")
        assert ours.dataset == "CelebA-HQ"
        assert ours.metrics["FID"] == 8.21
        # 'note' 列是字符串 → metadata
        assert ours.metadata.get("note") == "best"

    def test_missing_method_col_raises(self, tmp_path: Path) -> None:
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="method"):
            ExperimentLoader.from_results_csv(bad_csv, title="x")

    def test_handles_missing_dataset_col(self, tmp_path: Path) -> None:
        no_ds = tmp_path / "no_ds.csv"
        no_ds.write_text("method,acc\nOurs,0.9\n", encoding="utf-8")
        exp = ExperimentLoader.from_results_csv(
            no_ds, title="x", dataset_col="dataset"
        )
        assert exp.results[0].dataset is None
        assert exp.results[0].metrics["acc"] == 0.9


class TestFromTimeseriesCsv:
    def test_loads_curves_per_method_and_metric(self, fixtures_dir: Path) -> None:
        ts_list = ExperimentLoader.from_timeseries_csv(
            fixtures_dir / "timeseries.csv"
        )
        # 2 methods × 2 metrics = 4 curves
        assert len(ts_list) == 4
        names = {(t.method, t.name) for t in ts_list}
        assert ("Ours", "train_loss") in names
        assert ("Baseline-A", "val_acc") in names

        ours_loss = next(t for t in ts_list if t.method == "Ours" and t.name == "train_loss")
        assert ours_loss.x == [1.0, 2.0, 3.0, 4.0, 5.0]
        assert ours_loss.y[-1] == 0.8
