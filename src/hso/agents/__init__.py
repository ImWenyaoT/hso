"""OpenAI Agents SDK 集成层。

把 hso 现有的 OAuth backend / cache / settings 注入 Agents SDK，让 ``Agent`` /
``Runner`` 能复用我们已有的 ChatGPT 后端协议（store=False / stream / 自定义
header / model name 转换）。
"""

from hso.agents.runtime import (
    HSOAgentRuntime,
    build_runtime,
    set_default_runtime,
)

__all__ = [
    "HSOAgentRuntime",
    "build_runtime",
    "set_default_runtime",
]
