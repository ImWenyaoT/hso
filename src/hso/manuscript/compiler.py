"""LaTeX compiler wrapper for assembled manuscript projects."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

LatexEngine = Literal["latexmk", "tectonic"]


class CompileResult(BaseModel):
    """Structured result for one LaTeX compile attempt."""

    success: bool
    engine: LatexEngine | None
    pdf_path: Path | None = None
    log_path: Path | None = None
    returncode: int | None = None
    error_summary: str | None = None


class LatexCompiler:
    """Compile ``main.tex`` with latexmk or tectonic when available."""

    def compile(
        self,
        main_tex_path: Path,
        *,
        engine: LatexEngine | None = None,
        timeout_seconds: int = 120,
    ) -> CompileResult:
        """Compile a LaTeX entrypoint and return a structured result."""
        selected = engine or self._detect_engine()
        if selected is None:
            return CompileResult(
                success=False,
                engine=None,
                error_summary="No LaTeX compiler found. Install latexmk or tectonic.",
            )

        if selected == "latexmk":
            return self._run_latexmk(main_tex_path, timeout_seconds=timeout_seconds)
        return self._run_tectonic(main_tex_path, timeout_seconds=timeout_seconds)

    def _detect_engine(self) -> LatexEngine | None:
        """Choose the preferred available LaTeX engine."""
        if shutil.which("latexmk"):
            return "latexmk"
        if shutil.which("tectonic"):
            return "tectonic"
        return None

    def _run_latexmk(self, main_tex_path: Path, *, timeout_seconds: int) -> CompileResult:
        """Run latexmk in nonstop mode."""
        project_dir = main_tex_path.parent
        command = [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            main_tex_path.name,
        ]
        return _run_command(
            command=command,
            cwd=project_dir,
            engine="latexmk",
            pdf_path=main_tex_path.with_suffix(".pdf"),
            log_path=main_tex_path.with_suffix(".log"),
            timeout_seconds=timeout_seconds,
        )

    def _run_tectonic(self, main_tex_path: Path, *, timeout_seconds: int) -> CompileResult:
        """Run tectonic and keep logs next to the entrypoint."""
        project_dir = main_tex_path.parent
        command = ["tectonic", "--keep-logs", main_tex_path.name]
        return _run_command(
            command=command,
            cwd=project_dir,
            engine="tectonic",
            pdf_path=main_tex_path.with_suffix(".pdf"),
            log_path=main_tex_path.with_suffix(".log"),
            timeout_seconds=timeout_seconds,
        )


def _run_command(
    *,
    command: list[str],
    cwd: Path,
    engine: LatexEngine,
    pdf_path: Path,
    log_path: Path,
    timeout_seconds: int,
) -> CompileResult:
    """Run a compiler command and normalize stdout/stderr/logs into CompileResult."""
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        combined = _combine_output(exc.stdout, exc.stderr)
        return CompileResult(
            success=False,
            engine=engine,
            pdf_path=pdf_path if pdf_path.exists() else None,
            log_path=log_path if log_path.exists() else None,
            returncode=None,
            error_summary=f"Timed out after {timeout_seconds}s. {_extract_error_summary(combined)}",
        )

    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    combined = "\n".join(part for part in (completed.stdout, completed.stderr, log_text) if part)
    success = completed.returncode == 0 and pdf_path.exists()
    return CompileResult(
        success=success,
        engine=engine,
        pdf_path=pdf_path if pdf_path.exists() else None,
        log_path=log_path if log_path.exists() else None,
        returncode=completed.returncode,
        error_summary=None if success else _extract_error_summary(combined),
    )


def _combine_output(stdout: str | bytes | None, stderr: str | bytes | None) -> str:
    """Combine timeout stdout/stderr values that may be bytes or strings."""
    return "\n".join(_decode_output(part) for part in (stdout, stderr) if part)


def _decode_output(value: str | bytes) -> str:
    """Decode subprocess output into text."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _extract_error_summary(output: str) -> str:
    """Extract the first useful LaTeX error line from compiler output."""
    if not output.strip():
        return "LaTeX compile failed without output."

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("! LaTeX Error:"):
            return stripped
        if stripped.startswith("!") and len(stripped) > 1:
            return stripped
        if "Fatal error" in stripped or "error:" in stripped.lower():
            return stripped
    return output.strip().splitlines()[-1][:500]
