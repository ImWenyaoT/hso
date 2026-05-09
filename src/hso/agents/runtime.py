"""Agents SDK runtime 配置：OAuth / api_key 两种 backend 的统一入口。

调用 ``build_runtime()`` 一次性把 SDK 配置好：
- 注入 ``AsyncOpenAI`` client（OAuth 模式走 chatgpt.com/backend-api/codex）
- 关掉默认 tracing 上传（避免 OAuth token 暴露给 OpenAI traces dashboard）
- 提供 ``ModelSettings`` 默认值（store=False、temperature 不传等 7 处怪癖）

下游 agent 定义只需要 ``Agent(name=..., instructions=..., model=runtime.model)``。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from agents import (
    ModelSettings,
    OpenAIResponsesModel,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

from hso.llm.auth_storage import StoredAuth, load_auth
from hso.llm.oauth import ORIGINATOR

logger = logging.getLogger(__name__)

AuthMode = Literal["api_key", "oauth"]
_VERSION = "0.2.0"
_OAUTH_BASE_URL = "https://chatgpt.com/backend-api/codex"

# OAuth 模式的默认模型（来自 /codex/models slug 列表，2026-05 实测）
_OAUTH_DEFAULT_MODEL = "gpt-5.2"
_API_KEY_DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class HSOAgentRuntime:
    """封装一次"配置好的 SDK 状态"。

    通常一个进程只需要一个 runtime，调用 ``set_default_runtime()`` 装到全局。
    """

    auth_mode: AuthMode
    model: OpenAIResponsesModel
    model_settings: ModelSettings
    stored_auth: StoredAuth | None  # OAuth 模式下持有；api_key 模式 None


def _build_async_client(
    *,
    api_key: str,
    base_url: str,
    timeout: float,
    trust_env: bool,
    extra_headers: dict[str, str] | None = None,
) -> AsyncOpenAI:
    """构造 AsyncOpenAI；带统一的 httpx.AsyncClient（trust_env / 代理可控）。"""
    http_client = httpx.AsyncClient(timeout=timeout, trust_env=trust_env)
    return AsyncOpenAI(
        api_key=api_key or "sk-noop",
        base_url=base_url,
        timeout=timeout,
        http_client=http_client,
        default_headers=extra_headers or {},
    )


def build_runtime(
    *,
    auth_mode: AuthMode = "oauth",
    api_key: str = "",
    api_base_url: str = "https://api.openai.com/v1",
    model_name: str | None = None,
    timeout: float = 120.0,
    trust_env: bool = True,
    disable_tracing: bool = True,
) -> HSOAgentRuntime:
    """装配 Agents SDK runtime。

    Args:
        auth_mode: 'oauth' 走 ChatGPT 后端；'api_key' 走标准 OpenAI API。
        api_key: api_key 模式必填。
        api_base_url: api_key 模式下端点（默认 OpenAI）。
        model_name: 覆盖默认模型；None 时按 auth_mode 选合适默认。
        timeout: HTTP 请求超时（秒）。
        trust_env: httpx 是否读系统代理。OAuth 模式下用户机器有 SOCKS 代理时常需 True。
        disable_tracing: 是否关掉 SDK 默认 tracing 上传。**OAuth 模式必须 True**，
            否则 trace 会带着 access_token 发到 OpenAI traces dashboard，相当于自毁。

    Returns:
        HSOAgentRuntime：包含装配好的 model + 默认 ModelSettings + 状态。
    """
    if disable_tracing:
        set_tracing_disabled(True)

    stored: StoredAuth | None = None
    if auth_mode == "oauth":
        stored = load_auth()
        if stored is None:
            raise RuntimeError(
                "OAuth 模式但未登录。请先运行 `hso login`。"
            )
        chosen_model = model_name or _OAUTH_DEFAULT_MODEL
        client = _build_async_client(
            api_key=stored.access_token,
            base_url=_OAUTH_BASE_URL,
            timeout=timeout,
            trust_env=trust_env,
            extra_headers={
                "ChatGPT-Account-ID": stored.account_id,
                "originator": ORIGINATOR,
                "User-Agent": f"{ORIGINATOR}/{_VERSION}",
            },
        )
        # ChatGPT 后端 7 处怪癖：store=False、不传 temperature、必须 stream
        # SDK 的 ModelSettings 控制前两项；stream 由 Runner.run_streamed 控制
        model_settings = ModelSettings(
            store=False,
            temperature=None,
            include_usage=False,
        )
    else:
        if not api_key:
            raise ValueError("auth_mode='api_key' 但 api_key 为空")
        chosen_model = model_name or _API_KEY_DEFAULT_MODEL
        client = _build_async_client(
            api_key=api_key,
            base_url=api_base_url,
            timeout=timeout,
            trust_env=trust_env,
        )
        model_settings = ModelSettings()

    set_default_openai_client(client, use_for_tracing=False)

    model = OpenAIResponsesModel(model=chosen_model, openai_client=client)
    return HSOAgentRuntime(
        auth_mode=auth_mode,
        model=model,
        model_settings=model_settings,
        stored_auth=stored,
    )


_current_runtime: HSOAgentRuntime | None = None


def set_default_runtime(runtime: HSOAgentRuntime) -> None:
    """记录全局 runtime，方便没显式传 model 的 agent 也能拿到默认配置。"""
    global _current_runtime
    _current_runtime = runtime


def get_default_runtime() -> HSOAgentRuntime:
    """取全局 runtime；未配置时抛错。"""
    if _current_runtime is None:
        raise RuntimeError("runtime 尚未配置；先调用 build_runtime() + set_default_runtime()")
    return _current_runtime
