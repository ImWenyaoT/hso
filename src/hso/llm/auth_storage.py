"""OAuth token 持久化：~/.config/hso/auth.json。

⚠️  此模块涉及反向工程 OpenAI Codex CLI 的 OAuth 流程（复用其 client_id
``app_EMoamEEZ73f0CkXaXp7hrann``）。OpenAI 端没有官方授权，OpenAI 一旦修改
auth check / Hydra allow-list 即失效。**用户账号配额会被消耗，但账号本身风险低**；
本应用因此可能停止工作。详见 README 的 ToS 警告。
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


def default_auth_path() -> Path:
    """auth.json 的默认存放路径（遵循 XDG Base Directory）。"""
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_home) if xdg_home else Path.home() / ".config"
    return base / "hso" / "auth.json"


class StoredAuth(BaseModel):
    """持久化的 OAuth token + 元信息。"""

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(description="JWT 形式 OpenAI access token")
    refresh_token: str = Field(description="opaque refresh token")
    id_token: str = Field(description="JWT id_token，含 chatgpt_account_id claim")
    account_id: str = Field(description="ChatGPT account id，调 API 时作 header")
    expires_at: datetime = Field(description="access_token 过期时间（UTC）")
    last_refresh: datetime = Field(description="上次成功 refresh 的时间")
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_access_expired(self, leeway_seconds: int = 60) -> bool:
        """access_token 是否已过期（含提前刷新窗口）。"""
        return datetime.now(UTC) + timedelta(seconds=leeway_seconds) >= self.expires_at

    def needs_proactive_refresh(self, max_age_days: int = 8) -> bool:
        """超过 max_age_days 没刷过就主动 refresh，与 Codex CLI 对齐。"""
        return datetime.now(UTC) - self.last_refresh > timedelta(days=max_age_days)


def save_auth(auth: StoredAuth, path: Path | None = None) -> Path:
    """写入 auth.json，文件权限 0600。"""
    target = path or default_auth_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(auth.model_dump_json(indent=2), encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError as e:  # Windows / 非 POSIX 容错
        logger.warning("无法设置 %s 权限为 0600：%s", target, e)
    return target


def load_auth(path: Path | None = None) -> StoredAuth | None:
    """读 auth.json；不存在或损坏则返回 None。"""
    target = path or default_auth_path()
    if not target.exists():
        return None
    try:
        return StoredAuth.model_validate_json(target.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("auth.json 解析失败，按未登录处理：%s", e)
        return None


def clear_auth(path: Path | None = None) -> bool:
    """删除 auth.json，返回是否删除了文件。"""
    target = path or default_auth_path()
    if not target.exists():
        return False
    target.unlink()
    return True
