"""Local agent orchestrator pure event-draft behavior."""

from __future__ import annotations

from hso.agents.local import LocalAgentOrchestrator


def test_local_agent_returns_immutable_event_drafts_for_message() -> None:
    """Local agent should derive an immutable event stream from the input message."""
    drafts = LocalAgentOrchestrator().run("  Draft a migration plan.  ")

    assert isinstance(drafts, tuple)
    assert [draft.type for draft in drafts] == [
        "agent.started",
        "subagent.completed",
        "subagent.completed",
        "agent.completed",
    ]
    assert drafts[0].payload == {"topic": "Draft a migration plan."}


def test_local_agent_uses_fallback_topic_for_blank_message() -> None:
    """Blank input should still produce deterministic agent event drafts."""
    drafts = LocalAgentOrchestrator().run("   ")

    assert drafts[0].payload == {"topic": "untitled task"}
    assert drafts[-1].payload == {"summary": "Prepared a gateway workflow for: untitled task"}
