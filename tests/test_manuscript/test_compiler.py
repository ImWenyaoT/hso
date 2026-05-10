"""LatexCompiler 测试。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from hso.manuscript.compiler import LatexCompiler


class TestLatexCompiler:
    def test_reports_missing_engine(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr("hso.manuscript.compiler.shutil.which", lambda name: None)

        result = LatexCompiler().compile(tmp_path / "main.tex")

        assert result.success is False
        assert result.engine is None
        assert "No LaTeX compiler" in (result.error_summary or "")

    def test_latexmk_success(self, monkeypatch, tmp_path: Path) -> None:
        main = tmp_path / "main.tex"
        main.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")
        pdf = tmp_path / "main.pdf"

        def fake_run(*args, **kwargs):
            """Pretend latexmk produced a PDF."""
            pdf.write_text("pdf", encoding="utf-8")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr("hso.manuscript.compiler.subprocess.run", fake_run)

        result = LatexCompiler().compile(main, engine="latexmk")

        assert result.success is True
        assert result.engine == "latexmk"
        assert result.pdf_path == pdf

    def test_extracts_failure_summary(self, monkeypatch, tmp_path: Path) -> None:
        main = tmp_path / "main.tex"
        main.write_text("bad", encoding="utf-8")

        def fake_run(*args, **kwargs):
            """Pretend latexmk failed with a LaTeX error."""
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout="! LaTeX Error: File `elsarticle.cls' not found.",
                stderr="",
            )

        monkeypatch.setattr("hso.manuscript.compiler.subprocess.run", fake_run)

        result = LatexCompiler().compile(main, engine="latexmk")

        assert result.success is False
        assert result.engine == "latexmk"
        assert result.error_summary == "! LaTeX Error: File `elsarticle.cls' not found."
