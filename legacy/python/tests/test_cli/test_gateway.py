"""hso gateway/start CLI tests."""

from __future__ import annotations

from typer.testing import CliRunner

from hso.cli import app

runner = CliRunner()


def test_start_runs_gateway_server(monkeypatch):
    """The start command launches the Python gateway via uvicorn."""
    calls: list[dict[str, object]] = []

    def fake_run(app_path: str, **kwargs: object) -> None:
        calls.append({"app_path": app_path, **kwargs})

    monkeypatch.setattr("hso.cli.uvicorn.run", fake_run)

    result = runner.invoke(app, ["start", "--host", "127.0.0.1", "--port", "8765"])

    assert result.exit_code == 0
    assert calls == [
        {
            "app_path": "hso.gateway.app:create_app",
            "factory": True,
            "host": "127.0.0.1",
            "port": 8765,
            "reload": False,
        }
    ]
    assert "hso gateway" in result.output


def test_status_reports_gateway_url():
    """The status command prints the local gateway health URL."""
    result = runner.invoke(app, ["status", "--host", "127.0.0.1", "--port", "8765"])

    assert result.exit_code == 0
    assert "http://127.0.0.1:8765/api/health" in result.output
