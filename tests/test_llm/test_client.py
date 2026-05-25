"""LLMClient 测试：覆盖 Responses API、Chat Completions 兼容层、缓存与重试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import RateLimitError
from pydantic import BaseModel

from hso.llm.client import LLMClient


class DemoSchema(BaseModel):
    """OpenAI structured output 用 schema。"""

    answer: str
    score: int


def _make_client(tmp_path: Path | None = None) -> LLMClient:
    """构造 LLMClient，禁用系统代理（避免 SOCKS 报错）。"""
    return LLMClient(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        timeout=5.0,
        cache_dir=tmp_path,
        trust_env=False,
    )


def _make_chat_client(tmp_path: Path | None = None) -> LLMClient:
    """构造 Chat Completions 兼容 provider 的 LLMClient。"""
    return LLMClient(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        timeout=5.0,
        cache_dir=tmp_path,
        trust_env=False,
        api_surface="chat_completions",
    )


def _stub_parsed_response(parsed: BaseModel) -> Any:
    """构造一个 fake Responses parse 返回对象。"""
    obj = MagicMock()
    obj.output_parsed = parsed
    obj.output_text = parsed.model_dump_json()
    return obj


def _stub_chat_response(parsed: BaseModel) -> Any:
    """构造一个 fake chat completion 返回对象。"""
    obj = MagicMock()
    obj.choices = [MagicMock(message=MagicMock(content=parsed.model_dump_json()))]
    return obj


def _stub_text_response(content: str | None) -> Any:
    """构造一个带 message.content 的 fake chat completion 返回对象。"""
    obj = MagicMock()
    obj.choices = [MagicMock(message=MagicMock(content=content))]
    return obj


class TestParse:
    def test_rejects_unknown_auth_mode(self) -> None:
        """LLMClient should reject invalid auth modes before constructing clients."""
        with pytest.raises(ValueError, match="未知 auth_mode"):
            LLMClient(auth_mode="bad")  # type: ignore[arg-type]

    def test_rejects_unknown_api_surface(self) -> None:
        """LLMClient should reject unknown API surface names."""
        with pytest.raises(ValueError, match="未知 api_surface"):
            LLMClient(api_surface="bad")  # type: ignore[arg-type]

    def test_calls_responses_parse_with_text_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OpenAI API-key provider should use Responses parse for structured output."""
        client = _make_client()
        fake = _stub_parsed_response(DemoSchema(answer="hi", score=1))
        mock_parse = MagicMock(return_value=fake)
        monkeypatch.setattr(client._client.responses, "parse", mock_parse)

        result = client.parse(
            text_format=DemoSchema,
            instructions="be concise",
            user_input="say hi",
        )
        assert isinstance(result, DemoSchema)
        assert result.answer == "hi"
        kwargs = mock_parse.call_args.kwargs
        assert kwargs["text_format"] is DemoSchema
        assert kwargs["instructions"] == "be concise"
        assert kwargs["input"] == [{"role": "user", "content": "say hi"}]
        assert kwargs["store"] is False
        assert kwargs["model"] == "gpt-4o-mini"

    def test_raises_when_responses_parse_returns_no_parsed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Responses parse should fail closed when no parsed object is available."""
        client = _make_client()
        empty = MagicMock(output_parsed=None, output_text="<refusal>")
        monkeypatch.setattr(client._client.responses, "parse", MagicMock(return_value=empty))

        with pytest.raises(RuntimeError, match="未返回可解析结果"):
            client.parse(
                text_format=DemoSchema,
                instructions="x",
                user_input="y",
            )

    def test_chat_surface_calls_chat_completions_with_json_response_format(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Chat-compatible providers should keep using JSON-mode chat completions."""
        client = _make_chat_client()
        fake = _stub_chat_response(DemoSchema(answer="hi", score=1))
        mock_create = MagicMock(return_value=fake)
        monkeypatch.setattr(client._client.chat.completions, "create", mock_create)

        result = client.parse(
            text_format=DemoSchema,
            instructions="be concise",
            user_input="say hi",
        )

        assert result == DemoSchema(answer="hi", score=1)
        kwargs = mock_create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        assert kwargs["messages"][0]["role"] == "system"
        assert "json" in kwargs["messages"][0]["content"].lower()
        assert kwargs["messages"][1] == {"role": "user", "content": "say hi"}
        assert kwargs["model"] == "deepseek-v4-flash"

    def test_chat_surface_raises_when_no_chat_content(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Chat-compatible parsing should reject empty assistant content."""
        client = _make_chat_client()
        monkeypatch.setattr(
            client._client.chat.completions,
            "create",
            MagicMock(return_value=_stub_text_response("")),
        )

        with pytest.raises(RuntimeError, match="未返回可解析 JSON"):
            client.parse(text_format=DemoSchema, instructions="x", user_input="y")

    def test_raises_when_chat_content_is_invalid_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Structured parsing should fail closed on malformed JSON."""
        client = _make_chat_client()
        monkeypatch.setattr(
            client._client.chat.completions,
            "create",
            MagicMock(return_value=_stub_text_response("{bad json")),
        )

        with pytest.raises(RuntimeError, match="JSON 解析失败"):
            client.parse(text_format=DemoSchema, instructions="x", user_input="y")


class TestCache:
    def test_cache_hit_avoids_api_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _make_client(tmp_path=tmp_path)
        fake = _stub_parsed_response(DemoSchema(answer="cached", score=42))
        mock_parse = MagicMock(return_value=fake)
        monkeypatch.setattr(client._client.responses, "parse", mock_parse)

        # 第一次：会调 API 并写缓存
        r1 = client.parse(text_format=DemoSchema, instructions="i", user_input="u")
        # 第二次：相同入参，应命中缓存
        r2 = client.parse(text_format=DemoSchema, instructions="i", user_input="u")

        assert r1.answer == r2.answer == "cached"
        assert mock_parse.call_count == 1, "缓存未命中"

    def test_different_input_misses_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _make_client(tmp_path=tmp_path)
        fake = _stub_parsed_response(DemoSchema(answer="x", score=1))
        mock_parse = MagicMock(return_value=fake)
        monkeypatch.setattr(client._client.responses, "parse", mock_parse)

        client.parse(text_format=DemoSchema, instructions="a", user_input="u1")
        client.parse(text_format=DemoSchema, instructions="a", user_input="u2")
        assert mock_parse.call_count == 2


class TestRetry:
    def test_retries_on_rate_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client()
        fake = _stub_parsed_response(DemoSchema(answer="ok", score=1))

        # 前两次抛 RateLimitError，第三次成功
        rate_err = RateLimitError(
            message="rate", response=MagicMock(status_code=429), body=None
        )
        mock_parse = MagicMock(side_effect=[rate_err, rate_err, fake])
        monkeypatch.setattr(client._client.responses, "parse", mock_parse)

        # 同时把 retry 的 wait 时间清零，避免测试慢
        monkeypatch.setattr("hso.llm.client.wait_exponential", lambda **_: lambda *_a: 0)

        result = client.parse(text_format=DemoSchema, instructions="i", user_input="u")
        assert result.answer == "ok"
        assert mock_parse.call_count == 3


class TestClientLifecycle:
    def test_close_closes_underlying_openai_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMClient exposes explicit cleanup for its underlying HTTP client."""
        client = _make_client()
        close = MagicMock()
        monkeypatch.setattr(client._client, "close", close)

        client.close()

        close.assert_called_once_with()

    def test_context_manager_closes_underlying_openai_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLMClient should close network resources when leaving a with block."""
        client = _make_client()
        close = MagicMock()
        monkeypatch.setattr(client._client, "close", close)

        with client as entered:
            assert entered is client

        close.assert_called_once_with()


class TestRespond:
    def test_respond_calls_responses_create(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OpenAI plain text replies should call the Responses API."""
        client = _make_client()
        fake = MagicMock(output_text="hello")
        mock_create = MagicMock(return_value=fake)
        monkeypatch.setattr(client._client.responses, "create", mock_create)

        result = client.respond(instructions="be brief", user_input="say hello")

        assert result == "hello"
        kwargs = mock_create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["instructions"] == "be brief"
        assert kwargs["input"] == [{"role": "user", "content": "say hello"}]
        assert kwargs["store"] is False

    def test_chat_surface_respond_calls_chat_completions_create(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Chat-compatible plain text replies should call chat completions."""
        client = _make_chat_client()
        mock_create = MagicMock(return_value=_stub_text_response("hello"))
        monkeypatch.setattr(client._client.chat.completions, "create", mock_create)

        assert client.respond(instructions="be brief", user_input="say hello") == "hello"
        assert mock_create.call_args.kwargs["messages"] == [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "say hello"},
        ]

    def test_respond_via_stream_collects_text_deltas(self) -> None:
        """OAuth plain text streaming should concatenate output_text deltas."""
        client = _make_client()

        class Event:
            """Fake streaming event."""

            def __init__(self, event_type: str, delta: str) -> None:
                """Create an event with SDK-like attributes."""
                self.type = event_type
                self.delta = delta

        class TextStream:
            """Context manager that yields mixed streaming events."""

            def __enter__(self):
                return iter(
                    (
                        Event("response.output_text.delta", "hel"),
                        Event("response.ignored", "ignored"),
                        Event("response.output_text.delta", "lo"),
                    )
                )

            def __exit__(self, *_exc_info: object) -> None:
                return None

        client._auth_mode = "oauth"
        client._client.responses.stream = MagicMock(return_value=TextStream())

        assert client.respond(instructions="i", user_input="u") == "hello"


class TestOAuthStreaming:
    def test_parse_via_stream_returns_none_for_empty_stream(self) -> None:
        """OAuth structured parsing should treat an empty stream as no parsed result."""
        client = _make_client()

        class EmptyStream:
            """Context manager that yields no streaming events."""

            def __enter__(self):
                return iter(())

            def __exit__(self, *_exc_info: object) -> None:
                return None

        client._auth_mode = "oauth"
        client._client.responses.stream = MagicMock(return_value=EmptyStream())

        assert (
            client._parse_via_stream(
                text_format=DemoSchema,
                instructions="i",
                user_input="u",
                temperature=0.1,
            )
            is None
        )

    def test_parse_via_stream_returns_none_for_invalid_json(self) -> None:
        """OAuth structured parsing should fail closed on malformed JSON."""
        client = _make_client()

        class Event:
            """Fake streaming text delta."""

            type = "response.output_text.delta"
            delta = "{bad json"

        class BadJsonStream:
            """Context manager that yields malformed JSON."""

            def __enter__(self):
                return iter((Event(),))

            def __exit__(self, *_exc_info: object) -> None:
                return None

        client._auth_mode = "oauth"
        client._client.responses.stream = MagicMock(return_value=BadJsonStream())

        assert (
            client._parse_via_stream(
                text_format=DemoSchema,
                instructions="i",
                user_input="u",
                temperature=0.1,
            )
            is None
        )

    def test_parse_via_stream_validates_json_payload(self) -> None:
        """OAuth structured streaming should parse valid JSON into the target schema."""
        client = _make_client()

        class Event:
            """Fake streaming text delta."""

            type = "response.output_text.delta"
            delta = '{"answer":"ok","score":7}'

        class JsonStream:
            """Context manager that yields valid JSON."""

            def __enter__(self):
                return iter((Event(),))

            def __exit__(self, *_exc_info: object) -> None:
                return None

        client._auth_mode = "oauth"
        client._client.responses.stream = MagicMock(return_value=JsonStream())

        result = client._parse_via_stream(
            text_format=DemoSchema,
            instructions="i",
            user_input="u",
            temperature=0.1,
        )

        assert result == DemoSchema(answer="ok", score=7)
