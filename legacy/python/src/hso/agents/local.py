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

    def run(self, message: str) -> tuple[AgentEventDraft, ...]:
        """Return the event stream for one user message."""
        return _event_drafts_for_topic(_topic_from_message(message))


def _topic_from_message(message: str) -> str:
    """Derive a stable operator-facing topic from one user message."""
    return message.strip()[:120] or "untitled task"


def _event_drafts_for_topic(topic: str) -> tuple[AgentEventDraft, ...]:
    """Create immutable agent event drafts for a normalized topic."""
    return (
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
    )
