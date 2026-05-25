"""CLI LLM provider selection behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from hso.cli import _build_llm
from hso.config import Settings


def test_build_llm_uses_active_deepseek_provider(monkeypatch):
    """_build_llm resolves auto mode to the configured DeepSeek provider."""
    calls: list[dict[str, object]] = []

    def fake_client(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("hso.cli.LLMClient", fake_client)
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_api_key="deepseek-key",
        llm_base_url="https://api.deepseek.com",
        cache_dir=Path("cache"),
    )

    _build_llm(settings, auth_mode="auto")

    assert calls == [
        {
            "api_key": "deepseek-key",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
            "timeout": 120.0,
            "cache_dir": Path("cache") / "llm",
            "api_surface": "chat_completions",
        }
    ]


def test_build_llm_uses_gpt_responses_provider(monkeypatch):
    """_build_llm resolves GPT provider to the Responses API surface."""
    calls: list[dict[str, object]] = []

    def fake_client(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("hso.cli.LLMClient", fake_client)
    settings = Settings(
        _env_file=None,
        llm_provider="gpt",
        gpt_api_key="openai-key",
        gpt_base_url="https://api.openai.com/v1",
        gpt_model="gpt-5.4-mini",
        cache_dir=Path("cache"),
    )

    _build_llm(settings, auth_mode="auto")

    assert calls == [
        {
            "api_key": "openai-key",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-5.4-mini",
            "timeout": 120.0,
            "cache_dir": Path("cache") / "llm",
            "api_surface": "responses",
        }
    ]


def test_build_llm_can_force_custom_provider(monkeypatch):
    """_build_llm can override the active provider from CLI options."""
    calls: list[dict[str, object]] = []

    def fake_client(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("hso.cli.LLMClient", fake_client)
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_api_key="custom-key",
        llm_base_url="http://localhost:8000/v1",
        llm_model="local-model",
        cache_dir=Path("cache"),
    )

    _build_llm(settings, auth_mode="custom")

    assert calls[0]["api_key"] == "custom-key"
    assert calls[0]["base_url"] == "http://localhost:8000/v1"
    assert calls[0]["model"] == "local-model"
    assert calls[0]["api_surface"] == "chat_completions"


def test_build_llm_can_force_oauth_provider(monkeypatch):
    """_build_llm can force OAuth-backed personal Codex usage."""
    calls: list[dict[str, object]] = []

    def fake_client(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("hso.cli.LLMClient", fake_client)
    settings = Settings(_env_file=None, oauth_model="gpt-5.2", cache_dir=Path("cache"))

    _build_llm(settings, auth_mode="oauth")

    assert calls == [
        {
            "auth_mode": "oauth",
            "model": "gpt-5.2",
            "timeout": 120.0,
            "cache_dir": Path("cache") / "llm",
        }
    ]


def test_build_llm_rejects_missing_api_key():
    """_build_llm fails early when the selected API-key provider has no key."""
    settings = Settings(_env_file=None, llm_provider="gpt", gpt_api_key="")

    with pytest.raises(typer.Exit):
        _build_llm(settings, auth_mode="auto")
