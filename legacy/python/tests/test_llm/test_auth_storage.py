"""auth_storage 测试。"""

from __future__ import annotations

import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

from hso.llm.auth_storage import (
    StoredAuth,
    clear_auth,
    default_auth_path,
    load_auth,
    save_auth,
)


def _make_auth(*, expires_in_seconds: int = 3600) -> StoredAuth:
    now = datetime.now(UTC)
    return StoredAuth(
        access_token="acc",
        refresh_token="ref",
        id_token="id",
        account_id="account-123",
        expires_at=now + timedelta(seconds=expires_in_seconds),
        last_refresh=now,
    )


class TestSaveLoad:
    def test_round_trip(self, tmp_path: Path) -> None:
        target = tmp_path / "auth.json"
        original = _make_auth()
        save_auth(original, path=target)
        loaded = load_auth(path=target)
        assert loaded is not None
        assert loaded.account_id == "account-123"
        assert loaded.access_token == "acc"

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        assert load_auth(path=tmp_path / "missing.json") is None

    def test_load_corrupt_returns_none(self, tmp_path: Path) -> None:
        bad = tmp_path / "auth.json"
        bad.write_text("this is not json", encoding="utf-8")
        assert load_auth(path=bad) is None

    def test_save_chmod_0600_on_posix(self, tmp_path: Path) -> None:
        if os.name != "posix":
            return
        target = tmp_path / "auth.json"
        save_auth(_make_auth(), path=target)
        mode = stat.S_IMODE(target.stat().st_mode)
        assert mode == 0o600


class TestExpiry:
    def test_is_access_expired_true_when_past(self) -> None:
        auth = StoredAuth(
            access_token="x",
            refresh_token="y",
            id_token="z",
            account_id="a",
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
            last_refresh=datetime.now(UTC),
        )
        assert auth.is_access_expired()

    def test_is_access_expired_false_when_future(self) -> None:
        auth = _make_auth(expires_in_seconds=3600)
        assert not auth.is_access_expired()

    def test_needs_proactive_refresh_true_when_old(self) -> None:
        auth = StoredAuth(
            access_token="x",
            refresh_token="y",
            id_token="z",
            account_id="a",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            last_refresh=datetime.now(UTC) - timedelta(days=10),
        )
        assert auth.needs_proactive_refresh()

    def test_needs_proactive_refresh_false_when_recent(self) -> None:
        auth = _make_auth()
        assert not auth.needs_proactive_refresh()


class TestClearAuth:
    def test_returns_true_when_existed(self, tmp_path: Path) -> None:
        target = tmp_path / "auth.json"
        save_auth(_make_auth(), path=target)
        assert clear_auth(path=target) is True
        assert not target.exists()

    def test_returns_false_when_missing(self, tmp_path: Path) -> None:
        assert clear_auth(path=tmp_path / "missing.json") is False


class TestDefaultPath:
    def test_uses_xdg_config_home(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        path = default_auth_path()
        assert path == tmp_path / "hso" / "auth.json"

    def test_falls_back_to_home_config(self, monkeypatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        path = default_auth_path()
        assert path.name == "auth.json"
        assert path.parent.name == "hso"
        assert ".config" in path.parts
