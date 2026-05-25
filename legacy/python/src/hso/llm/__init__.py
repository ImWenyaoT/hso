"""LLM 抽象层：GPT 走 Responses API，兼容 provider 走 Chat Completions。"""

from hso.llm.auth_storage import StoredAuth, clear_auth, load_auth
from hso.llm.client import OAUTH_BASE_URL, APISurface, AuthMode, LLMClient
from hso.llm.oauth import login, refresh_and_save

__all__ = [
    "OAUTH_BASE_URL",
    "APISurface",
    "AuthMode",
    "LLMClient",
    "StoredAuth",
    "clear_auth",
    "load_auth",
    "login",
    "refresh_and_save",
]
