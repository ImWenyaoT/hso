"""Session runtime behavior for gateway-backed agent runs."""

from __future__ import annotations

import pytest

from hso.gateway.runtime import EventDispatcher, GatewayRuntime


def test_event_dispatcher_chains_events_without_mutating_inputs():
    """EventDispatcher should derive follow-up events from immutable event batches."""
    source = ("input",)
    seen: list[tuple[str, ...]] = []

    def first_handler(events: tuple[str, ...]) -> tuple[str, ...]:
        """Derive one event from the original batch."""
        seen.append(events)
        return ("derived",)

    def second_handler(events: tuple[str, ...]) -> tuple[str, ...]:
        """Derive one event from the expanded batch."""
        seen.append(events)
        return ("completed",)

    dispatcher = EventDispatcher(
        {
            "input": (first_handler,),
            "derived": (second_handler,),
        }
    )

    result = dispatcher.dispatch(source, event_type=lambda event: event)

    assert source == ("input",)
    assert result == ("input", "derived", "completed")
    assert seen == [("input",), ("input", "derived")]


def test_event_dispatcher_ignores_unhandled_events():
    """Unhandled event types should pass through without side effects."""
    dispatcher = EventDispatcher({})

    assert dispatcher.dispatch(("unknown",), event_type=lambda event: event) == ("unknown",)


@pytest.mark.asyncio
async def test_runtime_creates_session_and_records_agent_events(tmp_path):
    """GatewayRuntime creates a session and records main/sub-agent events."""
    runtime = GatewayRuntime(data_dir=tmp_path)

    session = await runtime.create_session(title="Migration planning")
    events = await runtime.send_message(
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

    memory_records = await runtime.list_memory(session.id)
    assert [record.role for record in memory_records] == ["user", "assistant"]
    assert memory_records[-1].metadata["event_count"] == len(events)


@pytest.mark.asyncio
async def test_runtime_processes_messages_through_event_dispatcher(tmp_path):
    """GatewayRuntime should publish a received event and let handlers derive agent events."""
    runtime = GatewayRuntime(data_dir=tmp_path)
    session = await runtime.create_session(title="Event driven")

    result = await runtime.process_message(session.id, "Plan event flow.")

    assert result.session.id == session.id
    assert result.events[0].type == "message.received"
    assert [event.type for event in await runtime.list_events(session.id)] == [
        event.type for event in result.events
    ]


@pytest.mark.asyncio
async def test_runtime_restores_sessions_and_events_from_sqlite(tmp_path):
    """GatewayRuntime restores session and event state after process restart."""
    first_runtime = GatewayRuntime(data_dir=tmp_path)
    session = await first_runtime.create_session(title="Durable agent session")
    await first_runtime.send_message(session.id, "Persist this session.")

    second_runtime = GatewayRuntime(data_dir=tmp_path)
    assert [record.id for record in await second_runtime.list_sessions()] == [session.id]
    assert len(await second_runtime.list_events(session.id)) == 5


@pytest.mark.asyncio
async def test_runtime_rejects_unknown_session(tmp_path):
    """GatewayRuntime raises KeyError when a message targets an unknown session."""
    runtime = GatewayRuntime(data_dir=tmp_path)

    try:
        await runtime.send_message("missing", "hello")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected KeyError for missing session")
