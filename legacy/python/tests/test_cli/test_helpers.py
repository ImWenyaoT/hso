"""CLI helper behavior for serialization and provider assembly."""

from __future__ import annotations

from pathlib import Path

from hso import cli
from hso.models import Paper


def test_papers_to_jsonable_serializes_dates(sample_papers: list[Paper]) -> None:
    """Paper serialization should produce JSON-ready primitive dictionaries."""
    payload = cli._papers_to_jsonable(sample_papers[:1])

    assert payload[0]["paper_id"] == sample_papers[0].paper_id
    assert payload[0]["published_at"] == "2025-06-01"


def test_load_papers_from_search_accepts_wrapped_payload(
    tmp_path: Path, sample_papers: list[Paper]
) -> None:
    """Search output with a top-level papers field should load into Paper models."""
    path = tmp_path / "search.json"
    path.write_text(
        '{"papers": [' + sample_papers[0].model_dump_json() + "]}",
        encoding="utf-8",
    )

    papers = cli._load_papers_from_search(path)

    assert [paper.paper_id for paper in papers] == [sample_papers[0].paper_id]


def test_load_papers_from_search_accepts_top_level_list(
    tmp_path: Path, sample_papers: list[Paper]
) -> None:
    """Legacy search output as a top-level list should still load."""
    path = tmp_path / "papers.json"
    path.write_text("[" + sample_papers[0].model_dump_json() + "]", encoding="utf-8")

    papers = cli._load_papers_from_search(path)

    assert len(papers) == 1
    assert papers[0].title == sample_papers[0].title


def test_build_aggregator_ignores_missing_jcr_file(monkeypatch, tmp_path: Path) -> None:
    """Aggregator assembly should skip JCR filtering when the configured file is absent."""
    calls: dict[str, object] = {}

    monkeypatch.setattr("hso.cli.ArxivProvider", lambda: "arxiv")
    monkeypatch.setattr("hso.cli.SemanticScholarProvider", lambda api_key: f"s2:{api_key}")

    def fake_aggregator(**kwargs: object) -> str:
        """Capture aggregator construction arguments."""
        calls["kwargs"] = kwargs
        return "aggregator"

    monkeypatch.setattr("hso.cli.SearchAggregator", fake_aggregator)

    result = cli._build_aggregator(tmp_path / "missing.json", s2_api_key="key")

    assert result == "aggregator"
    assert calls["kwargs"]["providers"] == ["arxiv", "s2:key"]
    assert calls["kwargs"]["jcr_filter"] is None


def test_build_aggregator_loads_existing_jcr_file(monkeypatch, tmp_path: Path) -> None:
    """Aggregator assembly should attach a JCR filter when the file exists."""
    jcr_path = tmp_path / "jcr.json"
    jcr_path.write_text("{}", encoding="utf-8")
    calls: dict[str, object] = {}

    monkeypatch.setattr("hso.cli.ArxivProvider", lambda: "arxiv")
    monkeypatch.setattr("hso.cli.SemanticScholarProvider", lambda api_key: f"s2:{api_key}")
    monkeypatch.setattr("hso.cli.JCRFilter.from_json", lambda path: f"jcr:{path.name}")

    def fake_aggregator(**kwargs: object) -> str:
        """Capture aggregator construction arguments."""
        calls["kwargs"] = kwargs
        return "aggregator"

    monkeypatch.setattr("hso.cli.SearchAggregator", fake_aggregator)

    result = cli._build_aggregator(jcr_path, s2_api_key="")

    assert result == "aggregator"
    assert calls["kwargs"]["jcr_filter"] == "jcr:jcr.json"


def test_print_papers_handles_empty_results(monkeypatch) -> None:
    """Empty result printing should emit a warning instead of building a table."""
    messages: list[str] = []
    monkeypatch.setattr("hso.cli.console.print", messages.append)

    cli._print_papers([])

    assert messages == ["[yellow]没有命中。[/yellow]"]
