"""Session runtime behavior for gateway-backed agent runs."""

from __future__ import annotations

from hso.gateway.runtime import GatewayRuntime


def test_runtime_creates_session_and_records_agent_events(tmp_path):
    """GatewayRuntime creates a session and records main/sub-agent events."""
    runtime = GatewayRuntime(data_dir=tmp_path)

    session = runtime.create_session(title="Migration planning")
    events = runtime.send_message(
        session.id,
        "Plan the hso gateway migration.",
    )

    assert session.title == "Migration planning"
    assert [event.type for event in events] == [
        "message.received",
        "agent.started",
        "subagent.completed",
        "subagent.completed",
        "agent.completed",
    ]
    assert {event.agent_name for event in events if event.agent_name} == {
        "main",
        "researcher",
        "writer",
    }

    memory_records = runtime.list_memory(session.id)
    assert [record.role for record in memory_records] == ["user", "assistant"]
    assert memory_records[-1].metadata["event_count"] == len(events)


def test_runtime_rejects_unknown_session(tmp_path):
    """GatewayRuntime raises KeyError when a message targets an unknown session."""
    runtime = GatewayRuntime(data_dir=tmp_path)

    try:
        runtime.send_message("missing", "hello")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected KeyError for missing session")
