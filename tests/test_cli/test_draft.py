"""hso draft CLI 测试。"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from hso.cli import app

runner = CliRunner()


class _FakePipeline:
    """Fake DraftPipeline that avoids real LLM calls."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def run(self, **kwargs):
        """Return a minimal pipeline result shaped like DraftPipelineResult."""
        out = kwargs["output_dir"]
        out.mkdir(parents=True, exist_ok=True)
        main = out / "main.tex"
        refs = out / "refs.bib"
        main.write_text("main", encoding="utf-8")
        refs.write_text("refs", encoding="utf-8")
        return SimpleNamespace(
            drafted_sections=[object()],
            assembly=SimpleNamespace(
                output_dir=out,
                main_tex_path=main,
                refs_bib_path=refs,
                unresolved_citations=[],
                missing_artifacts=[],
            ),
        )


class TestDraftCommand:
    def test_draft_generates_project(self, monkeypatch, tmp_path: Path) -> None:
        profile, experiment, papers = _write_inputs(tmp_path)
        monkeypatch.setattr("hso.cli._build_llm", lambda *args, **kwargs: object())
        monkeypatch.setattr("hso.cli.DraftPipeline", _FakePipeline)

        result = runner.invoke(
            app,
            [
                "draft",
                "--profile",
                str(profile),
                "--experiment",
                str(experiment),
                "--papers",
                str(papers),
                "--out",
                str(tmp_path / "draft"),
                "--auth-mode",
                "api_key",
            ],
        )

        assert result.exit_code == 0
        assert "Manuscript project" in result.output
        assert (tmp_path / "draft" / "main.tex").exists()

    def test_compile_failure_returns_nonzero(self, monkeypatch, tmp_path: Path) -> None:
        profile, experiment, papers = _write_inputs(tmp_path)
        monkeypatch.setattr("hso.cli._build_llm", lambda *args, **kwargs: object())
        monkeypatch.setattr("hso.cli.DraftPipeline", _FakePipeline)
        monkeypatch.setattr("hso.cli.LatexCompiler", lambda: _FailingCompiler())

        result = runner.invoke(
            app,
            [
                "draft",
                "--profile",
                str(profile),
                "--experiment",
                str(experiment),
                "--papers",
                str(papers),
                "--out",
                str(tmp_path / "draft"),
                "--compile",
            ],
        )

        assert result.exit_code == 3
        assert "PDF 编译失败" in result.output


class _FailingCompiler:
    """Fake compiler that simulates a LaTeX failure."""

    def compile(self, main_tex_path: Path):
        """Return a failed compile result."""
        return SimpleNamespace(success=False, error_summary="boom", pdf_path=None)


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Write profile, experiment, and papers JSON files for CLI tests."""
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps({"field_query": "diffusion", "n_papers": 0, "sections": []}),
        encoding="utf-8",
    )
    experiment = tmp_path / "experiment.json"
    experiment.write_text(json.dumps({"title": "Experiment"}), encoding="utf-8")
    papers = tmp_path / "papers.json"
    papers.write_text(json.dumps({"papers": []}), encoding="utf-8")
    return profile, experiment, papers
