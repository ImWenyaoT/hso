"""全局配置：从 .env / 环境变量读取，集中管理 LLM / 检索 / 缓存路径。"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """定位项目根目录（apps/hso/），用于落 data/cache/output。"""
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """应用配置。所有环境变量以 `HSO_` 前缀加载。"""

    model_config = SettingsConfigDict(
        env_prefix="HSO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- LLM ----
    llm_api_key: str = Field(default="", description="OpenAI 兼容端点 API key")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI 兼容端点基址；可指向 Anthropic / DeepSeek / 本地 vLLM",
    )
    llm_model: str = Field(default="gpt-4o-mini", description="默认模型名")
    llm_timeout: float = Field(default=120.0)

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


def load_settings() -> Settings:
    """构造配置实例；副作用：确保 data/output/cache 目录存在。"""
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.output_dir.mkdir(parents=True, exist_ok=True)
    s.cache_dir.mkdir(parents=True, exist_ok=True)
    return s
