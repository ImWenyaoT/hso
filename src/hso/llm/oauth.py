"""OpenAI "Sign in with ChatGPT" OAuth 流程：PKCE + 本地 callback + token exchange/refresh。

复刻 Codex CLI 的 client_id 与 endpoints；详见 ``auth_storage`` 模块顶部 ToS 警告。
端口 1455 / 1457 是 OpenAI Hydra allow-list 写死的，**不可改**。
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from hso.llm.auth_storage import StoredAuth, save_auth

logger = logging.getLogger(__name__)

# Codex CLI 复用：值来自 openai/codex 仓库 codex-rs/login/src/auth/manager.rs:921
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
ISSUER = "https://auth.openai.com"
AUTHORIZE_URL = f"{ISSUER}/oauth/authorize"
TOKEN_URL = f"{ISSUER}/oauth/token"

# OpenAI Hydra allow-list 写死的 redirect URI；改端口会被服务端拒绝
DEFAULT_PORT = 1455
FALLBACK_PORT = 1457

# Codex CLI 一模一样的 scope；少任何一项都过不了授权
SCOPES = "openid profile email offline_access api.connectors.read api.connectors.invoke"

# 我们对 OpenAI 自报的身份；不要用 "codex_cli" / "codex_cli_rs"，那是伪装
ORIGINATOR = "hso"


@dataclass(frozen=True)
class PKCEPair:
    """PKCE verifier / challenge 一对。"""

    verifier: str
    challenge: str


def generate_pkce() -> PKCEPair:
    """生成 PKCE pair（与 codex-rs/login/src/pkce.rs 等价）。

    verifier = URL_SAFE_NO_PAD(64 random bytes)
    challenge = URL_SAFE_NO_PAD(SHA256(verifier))
    """
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return PKCEPair(verifier=verifier, challenge=challenge)


def generate_state() -> str:
    """OAuth state 防 CSRF：32 字节随机 URL_SAFE_NO_PAD base64。"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")


def build_authorize_url(*, pkce: PKCEPair, state: str, port: int = DEFAULT_PORT) -> str:
    """组装授权 URL；参数顺序 / 字段都对齐 codex-rs/login/src/server.rs:480-516。"""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": f"http://localhost:{port}/auth/callback",
        "scope": SCOPES,
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "state": state,
        "originator": ORIGINATOR,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def decode_jwt_payload(jwt: str) -> dict[str, Any]:
    """不校验签名，只解 JWT payload（拿 claim 用）。"""
    parts = jwt.split(".")
    if len(parts) < 2:
        raise ValueError("不是合法 JWT 格式")
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    decoded = base64.urlsafe_b64decode(payload_b64 + padding)
    parsed: dict[str, Any] = json.loads(decoded)
    return parsed


def extract_account_id(id_token: str) -> str:
    """从 id_token JWT 取 chatgpt_account_id。"""
    payload = decode_jwt_payload(id_token)
    auth_claim = payload.get("https://api.openai.com/auth") or {}
    account_id = auth_claim.get("chatgpt_account_id")
    if not isinstance(account_id, str) or not account_id:
        raise ValueError("id_token 中找不到 chatgpt_account_id")
    return account_id


# --------------- HTTP 调用 ---------------


_RETRYABLE = (httpx.HTTPError,)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
    reraise=True,
)
def exchange_code_for_token(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    """authorization_code → token。

    body 是 form encoded（与 codex 对齐：codex-rs/login/src/server.rs:711-782）。
    """
    client = http_client or httpx.Client(timeout=30.0, trust_env=False)
    try:
        resp = client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": CLIENT_ID,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    finally:
        if http_client is None:
            client.close()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
    reraise=True,
)
def refresh_access_token(
    *, refresh_token: str, http_client: httpx.Client | None = None
) -> dict[str, Any]:
    """refresh_token → 新 access_token + refresh_token。

    body 是 JSON（与 codex 对齐：codex-rs/login/src/auth/manager.rs:823）。
    """
    client = http_client or httpx.Client(timeout=30.0, trust_env=False)
    try:
        resp = client.post(
            TOKEN_URL,
            json={
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    finally:
        if http_client is None:
            client.close()


def _expires_at_from_response(payload: dict[str, Any]) -> datetime:
    """从 token endpoint 返回的 ``expires_in`` 字段算出过期时刻。"""
    expires_in = int(payload.get("expires_in") or 3600)
    return datetime.now(UTC) + timedelta(seconds=expires_in)


def stored_auth_from_response(
    payload: dict[str, Any],
    *,
    previous_refresh_token: str | None = None,
    previous_id_token: str | None = None,
    previous_account_id: str | None = None,
) -> StoredAuth:
    """把 token endpoint 返回值转换成 StoredAuth。

    refresh 流程通常不返回新 id_token，调用方必须传 ``previous_id_token`` /
    ``previous_account_id`` 兜底。
    """
    access_token = payload["access_token"]
    refresh_token = payload.get("refresh_token") or previous_refresh_token
    id_token = payload.get("id_token") or previous_id_token
    if refresh_token is None:
        raise ValueError("响应缺 refresh_token，且无历史 refresh_token 可保留")
    if id_token is None:
        raise ValueError("响应缺 id_token，且无历史 id_token 可保留")
    if payload.get("id_token"):
        account_id = extract_account_id(id_token)
    elif previous_account_id is not None:
        account_id = previous_account_id
    else:
        account_id = extract_account_id(id_token)
    now = datetime.now(UTC)
    return StoredAuth(
        access_token=access_token,
        refresh_token=refresh_token,
        id_token=id_token,
        account_id=account_id,
        expires_at=_expires_at_from_response(payload),
        last_refresh=now,
    )


# --------------- 本地 callback server ---------------


@dataclass
class _CallbackResult:
    code: str | None = None
    state: str | None = None
    error: str | None = None


class _Handler(BaseHTTPRequestHandler):
    """本地 server 处理 OAuth callback。"""

    result: _CallbackResult
    done_event: threading.Event

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/auth/callback":
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        self.result.code = (qs.get("code") or [None])[0]
        self.result.state = (qs.get("state") or [None])[0]
        self.result.error = (qs.get("error") or [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_success_page().encode("utf-8"))
        self.done_event.set()

    def log_message(self, *_args: Any) -> None:  # 静音 stderr
        return


def _success_page() -> str:
    return (
        "<!doctype html><html><head><title>Signed in</title>"
        "<meta charset='utf-8'><style>"
        "body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center}"
        "h1{font-weight:600}p{color:#555}</style></head><body>"
        "<h1>✅ 登录成功</h1>"
        "<p>已把 token 写入 <code>~/.config/hso/auth.json</code>。"
        "你可以关闭这个窗口，回到终端。</p></body></html>"
    )


def wait_for_callback(port: int = DEFAULT_PORT, timeout_seconds: int = 300) -> _CallbackResult:
    """启动本地 server 等 OAuth callback；超时未收到回调抛 TimeoutError。"""
    result = _CallbackResult()
    done = threading.Event()
    _Handler.result = result
    _Handler.done_event = done

    server = HTTPServer(("127.0.0.1", port), _Handler)

    def _serve() -> None:
        while not done.is_set():
            server.handle_request()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    if not done.wait(timeout=timeout_seconds):
        server.server_close()
        raise TimeoutError(f"OAuth callback 超时（{timeout_seconds}s 内未收到）")
    server.server_close()
    return result


# --------------- 顶层 login 流程 ---------------


def login(
    *,
    open_browser: bool = True,
    port: int = DEFAULT_PORT,
    timeout_seconds: int = 300,
    http_client: httpx.Client | None = None,
    auth_path: Path | None = None,  # noqa: F821 — 可选注入测试路径
) -> StoredAuth:
    """完整登录流程：弹浏览器 → 等回调 → 换 token → 落盘。

    Args:
        open_browser: 是否自动打开浏览器；False 时只打印 URL（适合 CI / SSH）。
        port: 本地 callback 端口；OpenAI Hydra 只允许 1455 / 1457。
        timeout_seconds: 等回调最长时间。
        http_client: 注入 httpx.Client；测试时使用。
        auth_path: 注入 auth.json 路径；测试时使用。

    Returns:
        StoredAuth：登录后的 token，已写入磁盘。
    """
    pkce = generate_pkce()
    state = generate_state()
    redirect_uri = f"http://localhost:{port}/auth/callback"
    url = build_authorize_url(pkce=pkce, state=state, port=port)

    print(f"\n请在浏览器中完成登录：\n  {url}\n")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.warning("无法自动打开浏览器：%s", e)

    callback = wait_for_callback(port=port, timeout_seconds=timeout_seconds)
    if callback.error:
        raise RuntimeError(f"OAuth 失败：{callback.error}")
    if callback.state != state:
        raise RuntimeError("state 不匹配，可能是 CSRF 攻击")
    if not callback.code:
        raise RuntimeError("未收到 authorization code")

    payload = exchange_code_for_token(
        code=callback.code,
        code_verifier=pkce.verifier,
        redirect_uri=redirect_uri,
        http_client=http_client,
    )
    auth = stored_auth_from_response(payload)
    save_auth(auth, path=auth_path)
    return auth


def refresh_and_save(
    auth: StoredAuth,
    *,
    http_client: httpx.Client | None = None,
    auth_path: Path | None = None,  # noqa: F821
) -> StoredAuth:
    """用现有 refresh_token 换新 access_token，并写回磁盘。"""
    payload = refresh_access_token(refresh_token=auth.refresh_token, http_client=http_client)
    new_auth = stored_auth_from_response(
        payload,
        previous_refresh_token=auth.refresh_token,
        previous_id_token=auth.id_token,
        previous_account_id=auth.account_id,
    )
    save_auth(new_auth, path=auth_path)
    return new_auth
