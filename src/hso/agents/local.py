"""Deterministic local agent orchestrator used by the gateway MVP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentEventDraft:
    """Agent event data before the gateway assigns ids and timestamps."""

    type: str
    message: str
    agent_name: str | None = None
    payload: dict[str, object] | None = None


class LocalAgentOrchestrator:
    """Run a small main-agent plus sub-agent flow without network calls."""

    def run(self, message: str) -> list[AgentEventDraft]:
        """Return the event stream for one user message."""
        stripped = message.strip()
        topic = stripped[:120] or "untitled task"
        return [
            AgentEventDraft(
                type="agent.started",
                agent_name="main",
                message="Main agent accepted the task.",
                payload={"topic": topic},
            ),
            AgentEventDraft(
                type="subagent.completed",
                agent_name="researcher",
                message="Researcher sub-agent identified source and architecture context.",
                payload={"focus": "context"},
            ),
            AgentEventDraft(
                type="subagent.completed",
                agent_name="writer",
                message="Writer sub-agent prepared the operator-facing summary.",
                payload={"focus": "summary"},
            ),
            AgentEventDraft(
                type="agent.completed",
                agent_name="main",
                message="Main agent completed the local gateway MVP run.",
                payload={"summary": f"Prepared a gateway workflow for: {topic}"},
            ),
        ]
