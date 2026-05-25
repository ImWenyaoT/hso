"""SQLite persistence for gateway sessions and events."""

from __future__ import annotations

import json
import sqlite3
from asyncio import to_thread
from collections import OrderedDict
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path
from threading import Lock

from hso.gateway.models import GatewayEvent, SessionRecord

SESSION_CACHE_MAX_SIZE = 256


class GatewaySQLiteStore:
    """Async facade around the local SQLite gateway state database."""

    def __init__(self, path: Path) -> None:
        """Create a store for gateway session state at ``path``."""
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = Lock()
        self._schema_ready = False
        self._session_cache: OrderedDict[str, SessionRecord] = OrderedDict()
        self._session_cache_lock = Lock()
        self._ensure_schema()

    async def save_session(self, session: SessionRecord) -> None:
        """Persist one gateway session record."""
        await to_thread(self._save_session, session)

    async def list_sessions(self) -> list[SessionRecord]:
        """Return all persisted sessions in creation order."""
        return await to_thread(self._list_sessions)

    async def get_session(self, session_id: str) -> SessionRecord:
        """Return one persisted session or raise KeyError."""
        cached = self._get_cached_session(session_id)
        if cached is not None:
            return cached
        session = await to_thread(self._get_session, session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")
        self._cache_session(session)
        return session

    async def save_event(self, event: GatewayEvent) -> None:
        """Persist one gateway event."""
        await self.save_events([event])

    async def save_events(self, events: list[GatewayEvent]) -> None:
        """Persist gateway events in one SQLite transaction."""
        if not events:
            return
        await to_thread(self._save_events, events)

    async def list_events(self, session_id: str) -> list[GatewayEvent]:
        """Return all events for one session in insertion order."""
        await self.get_session(session_id)
        return await to_thread(self._list_events, session_id)

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection configured for gateway state access."""
        conn = sqlite3.connect(self._path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        """Initialize SQLite schema once per store instance."""
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return
            with closing(self._connect()) as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS gateway_sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS gateway_events (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        agent_name TEXT,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (session_id)
                            REFERENCES gateway_sessions(id)
                            ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_gateway_events_session_created
                        ON gateway_events(session_id, created_at, id);
                    """
                )
                conn.commit()
            self._schema_ready = True

    def _save_session(self, session: SessionRecord) -> None:
        """Write one session row to SQLite."""
        payload = session.model_dump(mode="json")
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO gateway_sessions (id, title, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    created_at = excluded.created_at
                """,
                (payload["id"], payload["title"], payload["created_at"]),
            )
            conn.commit()
        self._cache_session(session)

    def _get_cached_session(self, session_id: str) -> SessionRecord | None:
        """Return a cached session and refresh its LRU position."""
        with self._session_cache_lock:
            session = self._session_cache.get(session_id)
            if session is not None:
                self._session_cache.move_to_end(session_id)
            return session

    def _cache_session(self, session: SessionRecord) -> None:
        """Store a session in the bounded in-process LRU cache."""
        with self._session_cache_lock:
            self._session_cache[session.id] = session
            self._session_cache.move_to_end(session.id)
            while len(self._session_cache) > SESSION_CACHE_MAX_SIZE:
                self._session_cache.popitem(last=False)

    def _list_sessions(self) -> list[SessionRecord]:
        """Read session rows from SQLite."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT id, title, created_at
                FROM gateway_sessions
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()
        return [SessionRecord.model_validate(dict(row)) for row in rows]

    def _get_session(self, session_id: str) -> SessionRecord | None:
        """Read one session row from SQLite."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT id, title, created_at
                FROM gateway_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionRecord.model_validate(dict(row))

    def _save_events(self, events: list[GatewayEvent]) -> None:
        """Write event rows to SQLite in one transaction."""
        with closing(self._connect()) as conn:
            conn.executemany(
                """
                INSERT INTO gateway_events (
                    id,
                    session_id,
                    type,
                    message,
                    agent_name,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    message = excluded.message,
                    agent_name = excluded.agent_name,
                    payload_json = excluded.payload_json,
                    created_at = excluded.created_at
                """,
                _event_rows(events),
            )
            conn.commit()

    def _list_events(self, session_id: str) -> list[GatewayEvent]:
        """Read event rows from SQLite."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, type, message, agent_name, payload_json, created_at
                FROM gateway_events
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            GatewayEvent.model_validate(
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "type": row["type"],
                    "message": row["message"],
                    "agent_name": row["agent_name"],
                    "payload": json.loads(row["payload_json"]),
                    "created_at": row["created_at"],
                }
            )
            for row in rows
        ]


def _event_rows(events: Iterable[GatewayEvent]) -> Iterable[tuple[str, str, str, str, str | None, str, str]]:
    """Yield SQLite row tuples for gateway events without building a full row list."""
    for event in events:
        payload = event.model_dump(mode="json")
        yield (
            payload["id"],
            payload["session_id"],
            payload["type"],
            payload["message"],
            payload["agent_name"],
            json.dumps(payload["payload"], ensure_ascii=False),
            payload["created_at"],
        )
