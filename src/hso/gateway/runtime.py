"""Gateway runtime for sessions, memory, and local agent execution."""

from __future__ import annotations

from pathlib import Path

from hso.agents.local import LocalAgentOrchestrator
from hso.gateway.models import GatewayEvent, SessionRecord
from hso.memory import MemoryRecord, MemoryStore


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
        self._memory = MemoryStore(data_dir / "memory.jsonl")
        self._agent = agent or LocalAgentOrchestrator()
        self._sessions: dict[str, SessionRecord] = {}
        self._events: dict[str, list[GatewayEvent]] = {}

    def create_session(self, *, title: str = "Untitled session") -> SessionRecord:
        """Create and register a new gateway session."""
        session = SessionRecord(title=title)
        self._sessions[session.id] = session
        self._events[session.id] = []
        return session

    def list_sessions(self) -> list[SessionRecord]:
        """Return all sessions currently known by this runtime."""
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> SessionRecord:
        """Return one session or raise KeyError when it does not exist."""
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown session: {session_id}") from exc

    def send_message(self, session_id: str, content: str) -> list[GatewayEvent]:
        """Record a user message and run the local agent orchestrator."""
        session = self.get_session(session_id)
        user_record = self._memory.append(
            session_id=session.id,
            role="user",
            content=content,
        )
        events = [
            self._record_event(
                session_id=session.id,
                event_type="message.received",
                message="Gateway received a user message.",
                payload={"memory_id": user_record.id},
            )
        ]
        for draft in self._agent.run(content):
            events.append(
                self._record_event(
                    session_id=session.id,
                    event_type=draft.type,
                    message=draft.message,
                    agent_name=draft.agent_name,
                    payload=draft.payload or {},
                )
            )
        self._memory.append(
            session_id=session.id,
            role="assistant",
            content=events[-1].message,
            metadata={"event_count": len(events)},
        )
        return events

    def list_events(self, session_id: str) -> list[GatewayEvent]:
        """Return all events for a session."""
        self.get_session(session_id)
        return list(self._events[session_id])

    def list_memory(self, session_id: str) -> list[MemoryRecord]:
        """Return memory records for a session."""
        self.get_session(session_id)
        return self._memory.list(session_id=session_id)

    def _record_event(
        self,
        *,
        session_id: str,
        event_type: str,
        message: str,
        agent_name: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> GatewayEvent:
        """Create, store, and return one gateway event."""
        event = GatewayEvent(
            session_id=session_id,
            type=event_type,
            message=message,
            agent_name=agent_name,
            payload=payload or {},
        )
        self._events.setdefault(session_id, []).append(event)
        return event
