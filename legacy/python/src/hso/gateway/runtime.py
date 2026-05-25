"""Gateway runtime for sessions, memory, and local agent execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from hso.agents.local import AgentEventDraft, LocalAgentOrchestrator
from hso.gateway.models import GatewayEvent, SessionRecord
from hso.gateway.store import GatewaySQLiteStore
from hso.memory import MemoryRecord, MemoryStore

type EventType[EventT] = Callable[[EventT], str]
type EventHandler[EventT] = Callable[[tuple[EventT, ...]], tuple[EventT, ...]]


@dataclass(frozen=True)
class SendMessageResult:
    """Runtime result that keeps the loaded session with emitted events."""

    session: SessionRecord
    events: list[GatewayEvent]


@dataclass(frozen=True)
class EventDispatcher[EventT]:
    """Small synchronous event dispatcher for deriving follow-up events."""

    handlers: dict[str, tuple[EventHandler[EventT], ...]]

    def dispatch(
        self,
        events: tuple[EventT, ...],
        *,
        event_type: EventType[EventT],
    ) -> tuple[EventT, ...]:
        """Dispatch events through handlers and return a new immutable event batch."""
        return _dispatch_events(
            events=events,
            handlers=self.handlers,
            event_type=event_type,
            cursor=0,
        )


class GatewayRuntime:
    """In-process runtime behind the FastAPI gateway."""

    def __init__(
        self,
        *,
        data_dir: Path,
        agent: LocalAgentOrchestrator | None = None,
    ) -> None:
        """Create a runtime rooted in a local data directory."""
        self._data_dir = data_dir
        self._memory = MemoryStore(
            data_dir / "memory.sqlite3",
            legacy_jsonl_path=data_dir / "memory.jsonl",
        )
        self._store = GatewaySQLiteStore(data_dir / "gateway.sqlite3")
        self._agent = agent or LocalAgentOrchestrator()

    async def create_session(self, *, title: str = "Untitled session") -> SessionRecord:
        """Create and register a new gateway session."""
        session = SessionRecord(title=title)
        await self._store.save_session(session)
        return session

    async def list_sessions(self) -> list[SessionRecord]:
        """Return all sessions currently known by this runtime."""
        return await self._store.list_sessions()

    async def get_session(self, session_id: str) -> SessionRecord:
        """Return one session or raise KeyError when it does not exist."""
        return await self._store.get_session(session_id)

    async def send_message(self, session_id: str, content: str) -> list[GatewayEvent]:
        """Record a user message and run the local agent orchestrator."""
        return (await self.process_message(session_id, content)).events

    async def process_message(self, session_id: str, content: str) -> SendMessageResult:
        """Publish a user-message event and return the resulting event batch."""
        session = await self.get_session(session_id)
        user_record = await self._memory.append(
            session_id=session.id,
            role="user",
            content=content,
        )
        initial_events = (
            self._build_event(
                session_id=session.id,
                event_type="message.received",
                message="Gateway received a user message.",
                payload={"memory_id": user_record.id},
            ),
        )
        dispatcher = EventDispatcher(
            {
                "message.received": (
                    lambda _events: _agent_events_for_message(
                        session_id=session.id,
                        content=content,
                        agent=self._agent,
                        build_event=self._build_event,
                    ),
                ),
            }
        )
        events = dispatcher.dispatch(initial_events, event_type=lambda event: event.type)
        await self._store.save_events(list(events))
        await self._memory.append(
            session_id=session.id,
            role="assistant",
            content=events[-1].message,
            metadata={"event_count": len(events)},
        )
        return SendMessageResult(session=session, events=list(events))

    async def list_events(self, session_id: str) -> list[GatewayEvent]:
        """Return all events for a session."""
        return await self._store.list_events(session_id)

    async def list_memory(self, session_id: str) -> list[MemoryRecord]:
        """Return memory records for a session."""
        await self.get_session(session_id)
        return await self._memory.list(session_id=session_id)

    def _build_event(
        self,
        *,
        session_id: str,
        event_type: str,
        message: str,
        agent_name: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> GatewayEvent:
        """Create one gateway event before persistence."""
        return GatewayEvent(
            session_id=session_id,
            type=event_type,
            message=message,
            agent_name=agent_name,
            payload=payload or {},
        )


def _dispatch_events[EventT](
    *,
    events: tuple[EventT, ...],
    handlers: dict[str, tuple[EventHandler[EventT], ...]],
    event_type: EventType[EventT],
    cursor: int,
) -> tuple[EventT, ...]:
    """Recursively dispatch event handlers without mutating the event batch."""
    if cursor >= len(events):
        return events
    current = events[cursor]
    followups = tuple(
        event
        for handler in handlers.get(event_type(current), ())
        for event in handler(events)
    )
    return _dispatch_events(
        events=events + followups,
        handlers=handlers,
        event_type=event_type,
        cursor=cursor + 1,
    )


def _agent_events_for_message(
    *,
    session_id: str,
    content: str,
    agent: LocalAgentOrchestrator,
    build_event: Callable[..., GatewayEvent],
) -> tuple[GatewayEvent, ...]:
    """Convert agent event drafts into immutable gateway events for one message."""
    return tuple(
        _event_from_draft(session_id=session_id, draft=draft, build_event=build_event)
        for draft in agent.run(content)
    )


def _event_from_draft(
    *,
    session_id: str,
    draft: AgentEventDraft,
    build_event: Callable[..., GatewayEvent],
) -> GatewayEvent:
    """Build one persisted gateway event from a pure agent draft."""
    return build_event(
        session_id=session_id,
        event_type=draft.type,
        message=draft.message,
        agent_name=draft.agent_name,
        payload=draft.payload or {},
    )
