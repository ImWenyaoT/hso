"""全局配置：从 .env / 环境变量读取，集中管理 LLM / 检索 / 缓存路径。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """定位项目根目录（apps/hso/），用于落 data/cache/output。"""
    return Path(__file__).resolve().parents[2]


LLMProvider = Literal["deepseek", "custom", "oauth", "legacy", "gpt", "xai"]
LLMAuthMode = Literal["api_key", "oauth"]
LLMAPISurface = Literal["responses", "chat_completions"]


@dataclass(frozen=True)
class LLMBackend:
    """Resolved active LLM backend configuration."""

    provider: LLMProvider
    auth_mode: LLMAuthMode
    api_surface: LLMAPISurface
    api_key: str
    base_url: str
    model: str


class Settings(BaseSettings):
    """应用配置。所有环境变量以 `HSO_` 前缀加载。"""

    model_config = SettingsConfigDict(
        env_prefix="HSO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ---- LLM ----
    llm_provider: LLMProvider = Field(
        default="gpt",
        description="Active LLM provider",
        validation_alias=AliasChoices("LLM_PROVIDER", "HSO_LLM_PROVIDER"),
    )
    llm_api_key: str = Field(
        default="",
        description="OpenAI-compatible API key",
        validation_alias=AliasChoices("LLM_API_KEY", "HSO_LLM_API_KEY", "DEEPSEEK_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://api.deepseek.com",
        description="OpenAI-compatible chat completions base URL",
        validation_alias=AliasChoices("LLM_BASE_URL", "HSO_LLM_BASE_URL", "DEEPSEEK_BASE_URL"),
    )
    llm_model: str = Field(
        default="deepseek-v4-flash",
        description="Default chat completions model",
        validation_alias=AliasChoices("LLM_MODEL", "HSO_LLM_MODEL", "DEEPSEEK_MODEL"),
    )
    llm_timeout: float = Field(default=120.0)
    gpt_api_key: str = Field(
        default="",
        description="OpenAI API key for the Responses API provider",
        validation_alias=AliasChoices("GPT_API_KEY", "HSO_GPT_API_KEY", "OPENAI_API_KEY"),
    )
    gpt_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("GPT_BASE_URL", "HSO_GPT_BASE_URL", "OPENAI_BASE_URL"),
    )
    gpt_model: str = Field(
        default="gpt-5.4-mini",
        validation_alias=AliasChoices("GPT_MODEL", "HSO_GPT_MODEL", "OPENAI_MODEL"),
    )
    xai_api_key: str = Field(
        default="",
        description="xAI API key",
        validation_alias=AliasChoices("XAI_API_KEY", "HSO_XAI_API_KEY"),
    )
    xai_base_url: str = Field(
        default="https://api.x.ai/v1",
        validation_alias=AliasChoices("XAI_BASE_URL", "HSO_XAI_BASE_URL"),
    )
    xai_model: str = Field(
        default="grok-4.3",
        validation_alias=AliasChoices("XAI_MODEL", "HSO_XAI_MODEL"),
    )
    oauth_model: str = Field(
        default="gpt-5.2",
        validation_alias=AliasChoices("OAUTH_MODEL", "HSO_OAUTH_MODEL"),
    )

    # ---- Semantic Scholar ----
    s2_api_key: str = Field(default="", description="可选；申请后提升 RPS")

    # ---- 路径 ----
    data_dir: Path = Field(default_factory=lambda: _project_root() / "data")
    output_dir: Path = Field(default_factory=lambda: _project_root() / "output")
    cache_dir: Path = Field(default_factory=lambda: _project_root() / "data" / ".cache")

    # ---- 检索 ----
    default_years: int = Field(default=2, description="近 N 年的论文")
    default_max_zone: int = Field(default=2, description="中科院分区阈值；2 = 含一区二区")
    default_top_k: int = Field(default=30, description="单次检索每个 provider 返回上限")

    def active_llm_backend(self) -> LLMBackend:
        """Resolve the selected LLM provider into concrete client settings."""
        if self.llm_provider == "oauth":
            return LLMBackend(
                provider="oauth",
                auth_mode="oauth",
                api_surface="responses",
                api_key="",
                base_url="https://chatgpt.com/backend-api/codex",
                model=self.oauth_model,
            )
        if self.llm_provider in ("deepseek", "custom"):
            return LLMBackend(
                provider=self.llm_provider,
                auth_mode="api_key",
                api_surface="chat_completions",
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
                model=self.llm_model,
            )
        if self.llm_provider == "xai":
            return LLMBackend(
                provider="xai",
                auth_mode="api_key",
                api_surface="chat_completions",
                api_key=self.xai_api_key,
                base_url=self.xai_base_url,
                model=self.xai_model,
            )
        if self.llm_provider == "legacy":
            return LLMBackend(
                provider="legacy",
                auth_mode="api_key",
                api_surface="chat_completions",
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
                model=self.llm_model,
            )
        return LLMBackend(
            provider="gpt",
            auth_mode="api_key",
            api_surface="responses",
            api_key=self.gpt_api_key or self.llm_api_key,
            base_url=self.gpt_base_url,
            model=self.gpt_model,
        )


def load_settings() -> Settings:
    """构造配置实例；副作用：确保 data/output/cache 目录存在。"""
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.output_dir.mkdir(parents=True, exist_ok=True)
    s.cache_dir.mkdir(parents=True, exist_ok=True)
    return s
