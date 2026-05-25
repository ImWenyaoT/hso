"""OpenAI Responses / Chat Completions 封装：type-safe structured output + 缓存 + 重试。

支持两种 backend：
- ``api_key`` (默认)：OpenAI Responses API；兼容 provider 可切 Chat Completions
- ``oauth``：复用 Codex CLI OAuth 流程，调 ``chatgpt.com/backend-api/codex``，
  消耗用户 ChatGPT Plus/Pro 订阅配额。**反 ToS 灰色地带，详见 README**
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, TypeVar, cast

import httpx
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from openai.types.responses import ResponseInputParam
from openai.types.shared_params import ResponseFormatJSONObject
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from hso.llm.auth_storage import StoredAuth, load_auth
from hso.llm.oauth import ORIGINATOR, refresh_and_save

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, httpx.HTTPError)

AuthMode = Literal["api_key", "oauth"]
APISurface = Literal["responses", "chat_completions"]

# OAuth 模式下走 ChatGPT 后端，base_url 与 ChatGPT-Account-ID header 由 Codex CLI 协议规定
OAUTH_BASE_URL = "https://chatgpt.com/backend-api/codex"
# OAuth 模式下不再传用户输入的 base_url；改 endpoint 会被 OpenAI 后端拒
_VERSION = "0.2.0"


class LLMClient:
    """OpenAI Responses API 优先的 LLM 客户端。"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-5.4-mini",
        timeout: float = 120.0,
        cache_dir: Path | None = None,
        trust_env: bool = True,
        auth_mode: AuthMode = "api_key",
        api_surface: APISurface = "responses",
        auth_path: Path | None = None,
    ) -> None:
        """初始化客户端。

        Args:
            api_key: ``auth_mode='api_key'`` 时必填。``oauth`` 模式忽略。
            base_url: ``api_key`` 模式下的 API 基址。``oauth`` 模式强制走 OAUTH_BASE_URL。
            model: 默认模型。OAuth 模式下要选 ChatGPT 后端实际可用的模型，
                例如 ``gpt-5`` / ``gpt-5-codex``，**不是** ``deepseek-v4-flash``。
            timeout: 单次请求超时（秒）。
            cache_dir: 磁盘缓存目录；None 表示禁用。
            trust_env: 是否读取系统代理；测试场景应传 False。
            auth_mode: 'api_key' 走 OpenAI API；'oauth' 走 Codex 协议消耗 ChatGPT 订阅。
            api_surface: ``responses`` 走 OpenAI Responses API；``chat_completions``
                只给 DeepSeek/xAI/custom/legacy 这类兼容 endpoint 使用。
            auth_path: ``oauth`` 模式下 auth.json 路径；None 用默认 XDG 路径。
        """
        if auth_mode not in ("api_key", "oauth"):
            raise ValueError(f"未知 auth_mode: {auth_mode!r}")
        if api_surface not in ("responses", "chat_completions"):
            raise ValueError(f"未知 api_surface: {api_surface!r}")

        self._auth_mode: AuthMode = auth_mode
        self._api_surface: APISurface = "responses" if auth_mode == "oauth" else api_surface
        self._auth_path = auth_path
        self._timeout = timeout
        self._trust_env = trust_env
        self._model = model
        self._cache_dir = cache_dir
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

        if auth_mode == "api_key":
            http_client = httpx.Client(timeout=timeout, trust_env=trust_env)
            self._client = OpenAI(
                api_key=api_key or "sk-noop",
                base_url=base_url,
                timeout=timeout,
                http_client=http_client,
            )
            self._stored: StoredAuth | None = None
        else:
            stored = load_auth(self._auth_path)
            if stored is None:
                raise RuntimeError(
                    "OAuth 模式但未登录。请先运行 `hso login`。"
                )
            self._stored = self._ensure_fresh(stored)
            self._client = self._build_oauth_client(self._stored)

    @property
    def model(self) -> str:
        return self._model

    @property
    def auth_mode(self) -> AuthMode:
        return self._auth_mode

    @property
    def api_surface(self) -> APISurface:
        """Return the active OpenAI SDK API surface."""
        return self._api_surface

    def close(self) -> None:
        """Close the underlying OpenAI HTTP client."""
        self._client.close()

    def __enter__(self) -> LLMClient:
        """Return this client when used as a context manager."""
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Close network resources when leaving a context manager."""
        self.close()

    # --------------- OAuth 内部辅助 ---------------

    def _build_oauth_client(self, stored: StoredAuth) -> OpenAI:
        """根据当前 token 构造 OAuth 模式下的 OpenAI client。"""
        http_client = httpx.Client(timeout=self._timeout, trust_env=self._trust_env)
        return OpenAI(
            api_key=stored.access_token,
            base_url=OAUTH_BASE_URL,
            timeout=self._timeout,
            http_client=http_client,
            default_headers={
                "ChatGPT-Account-ID": stored.account_id,
                "originator": ORIGINATOR,
                "User-Agent": f"{ORIGINATOR}/{_VERSION}",
            },
        )

    def _ensure_fresh(self, stored: StoredAuth) -> StoredAuth:
        """token 过期或临近过期则刷新并返回新 StoredAuth。"""
        if stored.is_access_expired() or stored.needs_proactive_refresh():
            logger.info("access_token 过期或陈旧，自动 refresh")
            return refresh_and_save(stored, auth_path=self._auth_path)
        return stored

    def _refresh_oauth_client(self) -> None:
        """收到 401 等鉴权失败时，强刷 token 并重建 OpenAI client。"""
        if self._auth_mode != "oauth" or self._stored is None:
            return
        self._stored = refresh_and_save(self._stored, auth_path=self._auth_path)
        self._client = self._build_oauth_client(self._stored)

    # --------------- 缓存 ---------------

    def _cache_path(self, key: str) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{key}.json"

    @staticmethod
    def _hash_request(
        *,
        instructions: str,
        user_input: str,
        model: str,
        schema_name: str,
    ) -> str:
        """对请求做稳定哈希，作为缓存 key。"""
        payload = json.dumps(
            {
                "instructions": instructions,
                "input": user_input,
                "model": model,
                "schema": schema_name,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    # --------------- 公共 API ---------------

    @staticmethod
    def _completion_content(response: object) -> str:
        """从 OpenAI-compatible chat completion 对象里取第一条 message.content。"""
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "") if message is not None else ""
        return content if isinstance(content, str) else ""

    @staticmethod
    def _response_output_text(response: object) -> str:
        """从 Responses API response 对象中读取聚合后的 output_text。"""
        content = getattr(response, "output_text", "")
        return content if isinstance(content, str) else ""

    @staticmethod
    def _responses_input(user_input: str) -> ResponseInputParam:
        """构造 Responses API 的 input message 列表。"""
        return cast(ResponseInputParam, [{"role": "user", "content": user_input}])

    @staticmethod
    def _structured_messages(
        *,
        text_format: type[BaseModel],
        instructions: str,
        user_input: str,
    ) -> list[ChatCompletionMessageParam]:
        """构造 JSON-mode prompt；DeepSeek 要求 prompt 中显式出现 JSON。"""
        schema = json.dumps(text_format.model_json_schema(), ensure_ascii=False)
        system_prompt = (
            f"{instructions}\n\n"
            "Return only valid JSON. Do not include markdown fences or commentary. "
            "The JSON must match this schema:\n"
            f"{schema}"
        )
        return cast(
            list[ChatCompletionMessageParam],
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )

    @staticmethod
    def _plain_messages(*, instructions: str, user_input: str) -> list[ChatCompletionMessageParam]:
        """构造普通文本 chat completion messages。"""
        return cast(
            list[ChatCompletionMessageParam],
            [
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_input},
            ],
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    def parse(
        self,
        *,
        text_format: type[T],
        instructions: str,
        user_input: str,
        temperature: float = 0.1,
    ) -> T:
        """type-safe structured output。"""
        schema_name = text_format.__name__
        cache_key = self._hash_request(
            instructions=instructions,
            user_input=user_input,
            model=self._model,
            schema_name=schema_name,
        )
        cache_path = self._cache_path(cache_key)
        if cache_path is not None and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return text_format.model_validate(cached)

        if self._auth_mode == "oauth":
            parsed = self._parse_via_stream(
                text_format=text_format,
                instructions=instructions,
                user_input=user_input,
                temperature=temperature,
            )
        elif self._api_surface == "responses":
            parsed_response = self._client.responses.parse(
                model=self._model,
                instructions=instructions,
                input=self._responses_input(user_input),
                text_format=text_format,
                temperature=temperature,
                store=False,
            )
            parsed = parsed_response.output_parsed
        else:
            chat_response = self._client.chat.completions.create(
                model=self._model,
                messages=self._structured_messages(
                    text_format=text_format,
                    instructions=instructions,
                    user_input=user_input,
                ),
                response_format=cast(ResponseFormatJSONObject, {"type": "json_object"}),
                temperature=temperature,
            )
            raw = self._completion_content(chat_response).strip()
            if not raw:
                raise RuntimeError("Chat Completions API 未返回可解析 JSON。")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Chat Completions JSON 解析失败：{e}") from e
            parsed = text_format.model_validate(payload)

        if parsed is None:
            raise RuntimeError(
                "LLM backend 未返回可解析结果（可能是 refusal）。"
            )

        if cache_path is not None:
            cache_path.write_text(parsed.model_dump_json(), encoding="utf-8")
        return parsed

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    def respond(
        self,
        *,
        instructions: str,
        user_input: str,
        temperature: float = 0.2,
    ) -> str:
        """普通文本响应（无 structured output）。"""
        if self._auth_mode == "oauth":
            return self._respond_via_stream(
                instructions=instructions, user_input=user_input, temperature=temperature
            )
        try:
            if self._api_surface == "responses":
                response_result = self._client.responses.create(
                    model=self._model,
                    instructions=instructions,
                    input=self._responses_input(user_input),
                    temperature=temperature,
                    store=False,
                )
                return self._response_output_text(response_result)
            chat_result = self._client.chat.completions.create(
                model=self._model,
                messages=self._plain_messages(
                    instructions=instructions,
                    user_input=user_input,
                ),
                temperature=temperature,
            )
        except APIStatusError as e:
            logger.error("LLM API 调用失败：%s", e)
            raise
        return self._completion_content(chat_result)

    # --------------- OAuth: stream 实现 ---------------

    def _respond_via_stream(
        self, *, instructions: str, user_input: str, temperature: float
    ) -> str:
        """ChatGPT 后端强制 ``stream=True`` 且不接受 temperature；收集 text deltas。"""
        del temperature  # ChatGPT 后端 reasoning model 不支持
        text_chunks: list[str] = []
        with self._client.responses.stream(
            model=self._model,
            instructions=instructions,
            input=[{"role": "user", "content": user_input}],
            store=False,
        ) as stream:
            for event in stream:
                if getattr(event, "type", "") == "response.output_text.delta":
                    text_chunks.append(getattr(event, "delta", ""))
        return "".join(text_chunks)

    def _parse_via_stream(
        self,
        *,
        text_format: type[T],
        instructions: str,
        user_input: str,
        temperature: float,
    ) -> T | None:
        """OAuth + structured output：手工收集 deltas + JSON 解析。

        SDK 的 ``get_final_response()`` 在 ChatGPT 后端下 ``output_text`` 为空
        （可能是 SDK 与 Codex 协议不完全一致），所以我们自己拼 deltas。
        """
        del temperature
        text_chunks: list[str] = []
        with self._client.responses.stream(
            model=self._model,
            instructions=instructions,
            input=[{"role": "user", "content": user_input}],
            text_format=text_format,
            store=False,
        ) as stream:
            for event in stream:
                if getattr(event, "type", "") == "response.output_text.delta":
                    text_chunks.append(getattr(event, "delta", ""))
        raw = "".join(text_chunks).strip()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("OAuth 模式 JSON 解析失败：%s\n原始：%s", e, raw[:300])
            return None
        return text_format.model_validate(payload)
