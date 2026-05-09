"""OAuth flow 测试：PKCE / 授权 URL / token exchange / refresh / callback handler。"""

from __future__ import annotations

import base64
import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import httpx
import pytest
import respx

from hso.llm.auth_storage import StoredAuth, save_auth
from hso.llm.oauth import (
    AUTHORIZE_URL,
    CLIENT_ID,
    DEFAULT_PORT,
    ORIGINATOR,
    SCOPES,
    TOKEN_URL,
    build_authorize_url,
    decode_jwt_payload,
    exchange_code_for_token,
    extract_account_id,
    generate_pkce,
    generate_state,
    refresh_access_token,
    refresh_and_save,
    stored_auth_from_response,
    wait_for_callback,
)


def _make_id_token(account_id: str = "acc-123") -> str:
    """构造一个 fake JWT（header.payload.signature 全是 base64 字符串）。"""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode("ascii")
    payload = json.dumps({"https://api.openai.com/auth": {"chatgpt_account_id": account_id}})
    payload_b64 = (
        base64.urlsafe_b64encode(payload.encode("utf-8")).rstrip(b"=").decode("ascii")
    )
    return f"{header}.{payload_b64}.signature"


class TestPKCE:
    def test_generates_pair(self) -> None:
        pair = generate_pkce()
        assert pair.verifier
        assert pair.challenge
        assert pair.verifier != pair.challenge

    def test_verifiers_are_random(self) -> None:
        pairs = {generate_pkce().verifier for _ in range(20)}
        assert len(pairs) == 20

    def test_challenge_url_safe(self) -> None:
        pair = generate_pkce()
        # URL_SAFE_NO_PAD：不能含 '+' '/' '='
        for ch in pair.challenge:
            assert ch.isalnum() or ch in "-_"


class TestAuthorizeURL:
    def test_contains_required_params(self) -> None:
        pair = generate_pkce()
        state = generate_state()
        url = build_authorize_url(pkce=pair, state=state, port=1455)
        parsed = urlparse(url)
        assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == AUTHORIZE_URL
        qs = parse_qs(parsed.query)
        assert qs["response_type"] == ["code"]
        assert qs["client_id"] == [CLIENT_ID]
        assert qs["redirect_uri"] == ["http://localhost:1455/auth/callback"]
        assert qs["scope"] == [SCOPES]
        assert qs["code_challenge"] == [pair.challenge]
        assert qs["code_challenge_method"] == ["S256"]
        assert qs["id_token_add_organizations"] == ["true"]
        assert qs["codex_cli_simplified_flow"] == ["true"]
        assert qs["state"] == [state]
        assert qs["originator"] == [ORIGINATOR]

    def test_uses_localhost_not_127(self) -> None:
        url = build_authorize_url(pkce=generate_pkce(), state="x", port=DEFAULT_PORT)
        assert "redirect_uri=http%3A%2F%2Flocalhost" in url


class TestJWTDecode:
    def test_extract_account_id(self) -> None:
        token = _make_id_token("acc-xyz")
        assert extract_account_id(token) == "acc-xyz"

    def test_decode_jwt_payload_returns_claim_dict(self) -> None:
        token = _make_id_token("foo")
        payload = decode_jwt_payload(token)
        assert "https://api.openai.com/auth" in payload

    def test_invalid_jwt_raises(self) -> None:
        with pytest.raises(ValueError):
            decode_jwt_payload("notajwt")

    def test_missing_account_id_raises(self) -> None:
        # 构造一个没有 chatgpt_account_id 的 id_token
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode("ascii")
        payload = base64.urlsafe_b64encode(b"{}").rstrip(b"=").decode("ascii")
        token = f"{header}.{payload}.sig"
        with pytest.raises(ValueError, match="chatgpt_account_id"):
            extract_account_id(token)


class TestTokenExchange:
    @respx.mock
    def test_exchange_form_encoded(self) -> None:
        captured: dict[str, str] = {}

        def _record(request: httpx.Request) -> httpx.Response:
            captured["content_type"] = request.headers["content-type"]
            captured["body"] = request.content.decode("utf-8")
            return httpx.Response(
                200,
                json={
                    "access_token": "acc",
                    "refresh_token": "ref",
                    "id_token": _make_id_token(),
                    "expires_in": 3600,
                },
            )

        respx.post(TOKEN_URL).mock(side_effect=_record)
        client = httpx.Client(timeout=5.0, trust_env=False)
        resp = exchange_code_for_token(
            code="abc",
            code_verifier="ver",
            redirect_uri="http://localhost:1455/auth/callback",
            http_client=client,
        )
        assert resp["access_token"] == "acc"
        assert "x-www-form-urlencoded" in captured["content_type"]
        body = parse_qs(captured["body"])
        assert body["grant_type"] == ["authorization_code"]
        assert body["client_id"] == [CLIENT_ID]
        assert body["code"] == ["abc"]
        assert body["code_verifier"] == ["ver"]
        # PKCE public client：no client_secret
        assert "client_secret" not in body

    @respx.mock
    def test_refresh_uses_json_body(self) -> None:
        captured: dict[str, str] = {}

        def _record(request: httpx.Request) -> httpx.Response:
            captured["content_type"] = request.headers["content-type"]
            captured["body"] = request.content.decode("utf-8")
            return httpx.Response(
                200,
                json={
                    "access_token": "newacc",
                    "refresh_token": "newref",
                    "expires_in": 7200,
                },
            )

        respx.post(TOKEN_URL).mock(side_effect=_record)
        client = httpx.Client(timeout=5.0, trust_env=False)
        resp = refresh_access_token(refresh_token="oldref", http_client=client)
        assert resp["access_token"] == "newacc"
        assert "application/json" in captured["content_type"]
        body = json.loads(captured["body"])
        assert body == {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": "oldref",
        }


class TestStoredAuthFromResponse:
    def test_basic_construction(self) -> None:
        payload = {
            "access_token": "acc",
            "refresh_token": "ref",
            "id_token": _make_id_token("acc-123"),
            "expires_in": 3600,
        }
        auth = stored_auth_from_response(payload)
        assert auth.account_id == "acc-123"
        assert auth.access_token == "acc"
        assert auth.expires_at > datetime.now(UTC)

    def test_uses_previous_refresh_when_missing(self) -> None:
        payload = {
            "access_token": "newacc",
            "id_token": _make_id_token(),
            "expires_in": 3600,
        }
        auth = stored_auth_from_response(payload, previous_refresh_token="oldref")
        assert auth.refresh_token == "oldref"


class TestRefreshAndSave:
    @respx.mock
    def test_refresh_persists_to_disk(self, tmp_path: Path) -> None:
        target = tmp_path / "auth.json"
        old = StoredAuth(
            access_token="oldacc",
            refresh_token="oldref",
            id_token=_make_id_token("acc-1"),
            account_id="acc-1",
            expires_at=datetime.now(UTC),
            last_refresh=datetime.now(UTC),
        )
        save_auth(old, path=target)

        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "newacc",
                    "refresh_token": "newref",
                    # refresh 响应不带 id_token 时应保留旧的
                    "expires_in": 7200,
                },
            )
        )
        client = httpx.Client(timeout=5.0, trust_env=False)
        new_auth = refresh_and_save(old, http_client=client, auth_path=target)
        assert new_auth.access_token == "newacc"
        assert new_auth.refresh_token == "newref"
        assert new_auth.account_id == "acc-1"
        assert new_auth.id_token == old.id_token
        # 落盘
        from hso.llm.auth_storage import load_auth

        loaded = load_auth(path=target)
        assert loaded is not None
        assert loaded.access_token == "newacc"


class TestCallbackServer:
    def test_receives_code_and_state(self) -> None:
        port = 14550  # 随机端口；OpenAI allow-list 仅作用于真实授权

        result_holder: list = []

        def _wait() -> None:
            r = wait_for_callback(port=port, timeout_seconds=5)
            result_holder.append(r)

        thread = threading.Thread(target=_wait, daemon=True)
        thread.start()
        time.sleep(0.2)  # 等 server 起来

        urlopen(
            f"http://127.0.0.1:{port}/auth/callback?code=mycode&state=mystate"
        ).read()
        thread.join(timeout=5)
        assert result_holder, "callback 未触发"
        cb = result_holder[0]
        assert cb.code == "mycode"
        assert cb.state == "mystate"
        assert cb.error is None
