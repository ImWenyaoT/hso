"""LatexCompiler 测试。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from hso.manuscript.compiler import LatexCompiler, _combine_output, _extract_error_summary


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

    def test_detect_engine_prefers_latexmk(self, monkeypatch) -> None:
        """Engine detection should prefer latexmk when both engines are available."""
        monkeypatch.setattr("hso.manuscript.compiler.shutil.which", lambda _name: "/bin/tool")

        assert LatexCompiler()._detect_engine() == "latexmk"

    def test_detect_engine_falls_back_to_tectonic(self, monkeypatch) -> None:
        """Engine detection should use tectonic when latexmk is unavailable."""
        monkeypatch.setattr(
            "hso.manuscript.compiler.shutil.which",
            lambda name: "/bin/tectonic" if name == "tectonic" else None,
        )

        assert LatexCompiler()._detect_engine() == "tectonic"

    def test_tectonic_success_uses_requested_engine(self, monkeypatch, tmp_path: Path) -> None:
        """Explicit tectonic compilation should run the tectonic command."""
        main = tmp_path / "main.tex"
        main.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")
        pdf = tmp_path / "main.pdf"
        seen: dict[str, object] = {}

        def fake_run(command, **kwargs):
            """Pretend tectonic produced a PDF and capture command arguments."""
            seen["command"] = command
            seen["cwd"] = kwargs["cwd"]
            pdf.write_text("pdf", encoding="utf-8")
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr("hso.manuscript.compiler.subprocess.run", fake_run)

        result = LatexCompiler().compile(main, engine="tectonic")

        assert result.success is True
        assert result.engine == "tectonic"
        assert seen["command"] == ["tectonic", "--keep-logs", "main.tex"]
        assert seen["cwd"] == tmp_path

    def test_timeout_returns_structured_failure(self, monkeypatch, tmp_path: Path) -> None:
        """Compiler timeouts should preserve partial output in the error summary."""
        main = tmp_path / "main.tex"
        main.write_text("bad", encoding="utf-8")

        def fake_run(*_args, **_kwargs):
            """Pretend the compiler timed out with byte output."""
            raise subprocess.TimeoutExpired(
                cmd=["latexmk"],
                timeout=3,
                output=b"! Emergency stop.",
                stderr=None,
            )

        monkeypatch.setattr("hso.manuscript.compiler.subprocess.run", fake_run)

        result = LatexCompiler().compile(main, engine="latexmk", timeout_seconds=3)

        assert result.success is False
        assert result.returncode is None
        assert result.error_summary == "Timed out after 3s. ! Emergency stop."

    def test_error_summary_handles_empty_output(self) -> None:
        """Empty compiler output should produce a useful fallback summary."""
        assert _extract_error_summary(" \n ") == "LaTeX compile failed without output."

    def test_error_summary_prefers_fatal_error_line(self) -> None:
        """Fatal compiler lines should be extracted before generic trailing output."""
        output = "first line\nFatal error occurred, no output PDF file produced!\nlast line"

        assert _extract_error_summary(output) == "Fatal error occurred, no output PDF file produced!"

    def test_error_summary_falls_back_to_truncated_last_line(self) -> None:
        """Generic compiler output should fall back to the final line with a length cap."""
        long_line = "x" * 600

        assert _extract_error_summary(f"intro\n{long_line}") == "x" * 500

    def test_combine_output_decodes_mixed_subprocess_output(self) -> None:
        """Timeout output may arrive as bytes or text depending on subprocess internals."""
        assert _combine_output(b"stdout", "stderr") == "stdout\nstderr"
