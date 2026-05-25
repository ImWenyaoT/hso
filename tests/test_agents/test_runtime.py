"""Agents SDK runtime configuration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hso.agents import runtime as runtime_module
from hso.agents.runtime import build_runtime, get_default_runtime, set_default_runtime
from hso.llm.auth_storage import StoredAuth


class _FakeAsyncClient:
    """Minimal async client fake used by runtime configuration tests."""

    def __init__(self) -> None:
        """Create a client fake that records close calls."""
        self.closed = False

    async def close(self) -> None:
        """Record async cleanup."""
        self.closed = True


def test_build_runtime_rejects_empty_api_key() -> None:
    """API-key runtime should fail before constructing clients when the key is empty."""
    with pytest.raises(ValueError, match="api_key 为空"):
        build_runtime(auth_mode="api_key", api_key="", disable_tracing=False)


def test_build_runtime_rejects_missing_oauth_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """OAuth runtime should fail early when no stored login exists."""
    monkeypatch.setattr("hso.agents.runtime.load_auth", lambda: None)

    with pytest.raises(RuntimeError, match="未登录"):
        build_runtime(auth_mode="oauth", disable_tracing=False)


def test_build_runtime_configures_api_key_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """API-key runtime should build the standard OpenAI backend with explicit settings."""
    calls: dict[str, object] = {}
    fake_client = _FakeAsyncClient()

    def fake_build_client(**kwargs: object) -> _FakeAsyncClient:
        """Capture AsyncOpenAI construction parameters."""
        calls["client_kwargs"] = kwargs
        return fake_client

    monkeypatch.setattr("hso.agents.runtime._build_async_client", fake_build_client)
    monkeypatch.setattr(
        "hso.agents.runtime.OpenAIChatCompletionsModel",
        lambda **kwargs: {"model_kwargs": kwargs},
    )
    monkeypatch.setattr(
        "hso.agents.runtime.set_default_openai_client",
        lambda *args, **kwargs: calls.setdefault("default_client", (args, kwargs)),
    )

    runtime = build_runtime(
        auth_mode="api_key",
        api_key="sk-test",
        api_base_url="https://example.test/v1",
        model_name="custom-model",
        timeout=3.0,
        trust_env=False,
        disable_tracing=False,
    )

    assert runtime.auth_mode == "api_key"
    assert runtime.stored_auth is None
    assert runtime.openai_client is fake_client
    assert calls["client_kwargs"] == {
        "api_key": "sk-test",
        "base_url": "https://example.test/v1",
        "timeout": 3.0,
        "trust_env": False,
    }


def test_build_runtime_configures_oauth_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """OAuth runtime should inject account headers and restrictive model settings."""
    calls: dict[str, object] = {}
    fake_client = _FakeAsyncClient()
    stored = StoredAuth(
        access_token="access",
        refresh_token="refresh",
        id_token="id",
        account_id="acct_123",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        last_refresh=datetime.now(UTC),
    )

    def fake_build_client(**kwargs: object) -> _FakeAsyncClient:
        """Capture OAuth AsyncOpenAI construction parameters."""
        calls["client_kwargs"] = kwargs
        return fake_client

    monkeypatch.setattr("hso.agents.runtime.load_auth", lambda: stored)
    monkeypatch.setattr("hso.agents.runtime._build_async_client", fake_build_client)
    monkeypatch.setattr(
        "hso.agents.runtime.OpenAIChatCompletionsModel",
        lambda **kwargs: {"model_kwargs": kwargs},
    )
    monkeypatch.setattr("hso.agents.runtime.set_default_openai_client", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "hso.agents.runtime.set_tracing_disabled",
        lambda value: calls.setdefault("tracing_disabled", value),
    )

    runtime = build_runtime(auth_mode="oauth")

    client_kwargs = calls["client_kwargs"]
    assert runtime.auth_mode == "oauth"
    assert runtime.stored_auth is stored
    assert runtime.model_settings.store is False
    assert runtime.model_settings.temperature is None
    assert calls["tracing_disabled"] is True
    assert client_kwargs["api_key"] == "access"
    assert client_kwargs["extra_headers"]["ChatGPT-Account-ID"] == "acct_123"


def test_get_default_runtime_rejects_unconfigured_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_default_runtime should report an invalid state before setup."""
    monkeypatch.setattr(runtime_module, "_current_runtime", None)

    with pytest.raises(RuntimeError, match="runtime 尚未配置"):
        get_default_runtime()


@pytest.mark.asyncio
async def test_set_default_runtime_and_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default runtime access should return the configured runtime and support cleanup."""
    fake_client = _FakeAsyncClient()
    monkeypatch.setattr(runtime_module, "_current_runtime", None)
    monkeypatch.setattr("hso.agents.runtime._build_async_client", lambda **_kwargs: fake_client)
    monkeypatch.setattr("hso.agents.runtime.OpenAIChatCompletionsModel", lambda **kwargs: kwargs)
    monkeypatch.setattr("hso.agents.runtime.set_default_openai_client", lambda *_a, **_k: None)

    runtime = build_runtime(auth_mode="api_key", api_key="sk-test", disable_tracing=False)
    set_default_runtime(runtime)

    assert get_default_runtime() is runtime
    await runtime.aclose()
    assert fake_client.closed is True
