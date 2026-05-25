"""Settings behavior for selectable LLM providers."""

from __future__ import annotations

from hso.config import Settings


def test_settings_prefers_gpt_provider_defaults(monkeypatch):
    """Settings resolves GPT as the default Responses API provider."""
    monkeypatch.delenv("HSO_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    backend = Settings(_env_file=None).active_llm_backend()

    assert backend.provider == "gpt"
    assert backend.auth_mode == "api_key"
    assert backend.api_surface == "responses"
    assert backend.api_key == "openai-key"
    assert backend.base_url == "https://api.openai.com/v1"
    assert backend.model == "gpt-5.4-mini"


def test_settings_resolves_deepseek_provider_aliases(monkeypatch):
    """Settings keeps DEEPSEEK_* aliases for the chat-completions provider."""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    backend = Settings(_env_file=None).active_llm_backend()

    assert backend.provider == "deepseek"
    assert backend.api_surface == "chat_completions"
    assert backend.api_key == "deepseek-key"
    assert backend.base_url == "https://api.deepseek.com"


def test_settings_resolves_custom_openai_compatible_provider(monkeypatch):
    """Settings resolves a user-supplied OpenAI-compatible endpoint."""
    monkeypatch.setenv("LLM_PROVIDER", "custom")
    monkeypatch.setenv("LLM_API_KEY", "custom-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("LLM_MODEL", "local-model")

    backend = Settings(_env_file=None).active_llm_backend()

    assert backend.provider == "custom"
    assert backend.auth_mode == "api_key"
    assert backend.api_surface == "chat_completions"
    assert backend.api_key == "custom-key"
    assert backend.base_url == "http://localhost:8000/v1"
    assert backend.model == "local-model"


def test_settings_resolves_oauth_provider(monkeypatch):
    """Settings resolves OAuth provider without requiring an API key."""
    monkeypatch.setenv("LLM_PROVIDER", "oauth")
    monkeypatch.setenv("OAUTH_MODEL", "gpt-5.2")

    backend = Settings(_env_file=None).active_llm_backend()

    assert backend.provider == "oauth"
    assert backend.auth_mode == "oauth"
    assert backend.api_surface == "responses"
    assert backend.api_key == ""
    assert backend.model == "gpt-5.2"


def test_settings_keeps_hso_prefixed_legacy_provider(monkeypatch):
    """Settings keeps HSO_LLM_* compatibility for existing .env files."""
    monkeypatch.setenv("HSO_LLM_PROVIDER", "legacy")
    monkeypatch.setenv("HSO_LLM_API_KEY", "legacy-key")
    monkeypatch.setenv("HSO_LLM_BASE_URL", "https://legacy.example/v1")
    monkeypatch.setenv("HSO_LLM_MODEL", "legacy-model")

    backend = Settings(_env_file=None).active_llm_backend()

    assert backend.provider == "legacy"
    assert backend.auth_mode == "api_key"
    assert backend.api_surface == "chat_completions"
    assert backend.api_key == "legacy-key"
    assert backend.base_url == "https://legacy.example/v1"
    assert backend.model == "legacy-model"
