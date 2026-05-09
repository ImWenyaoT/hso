"""LLMClient 测试：通过 monkeypatch SDK 的 responses 验证 parse / 缓存 / 重试。"""

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


def _stub_parsed_response(parsed: BaseModel) -> Any:
    """构造一个 fake Responses parse 返回对象。"""
    obj = MagicMock()
    obj.output_parsed = parsed
    obj.output_text = parsed.model_dump_json()
    return obj


class TestParse:
    def test_calls_responses_parse_with_text_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
        assert kwargs["model"] == "gpt-4o-mini"

    def test_raises_when_no_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client()
        empty = MagicMock()
        empty.output_parsed = None
        empty.output_text = "<refusal>"
        monkeypatch.setattr(client._client.responses, "parse", MagicMock(return_value=empty))

        with pytest.raises(RuntimeError, match="未返回可解析结果"):
            client.parse(
                text_format=DemoSchema,
                instructions="x",
                user_input="y",
            )


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
