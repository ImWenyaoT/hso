"""Agent runtime primitives and OpenAI Agents SDK integration.

The gateway starts with a deterministic local orchestrator for offline development
and keeps the existing OpenAI Agents SDK runtime available for the next migration
step.
"""

from hso.agents.local import AgentEventDraft, LocalAgentOrchestrator
from hso.agents.runtime import (
    HSOAgentRuntime,
    build_runtime,
    set_default_runtime,
)

__all__ = [
    "AgentEventDraft",
    "HSOAgentRuntime",
    "LocalAgentOrchestrator",
    "build_runtime",
    "set_default_runtime",
]
