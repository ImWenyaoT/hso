"""SQLite-backed memory store used by the local gateway."""

from __future__ import annotations

import json
import sqlite3
from asyncio import to_thread
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class MemoryRecord(BaseModel):
    """One session-scoped memory record."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"mem_{uuid4().hex}")
    session_id: str
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


type MemoryRecordList = list[MemoryRecord]


class MemoryStore:
    """Small SQLite store for local-first memory."""

    def __init__(self, path: Path, legacy_jsonl_path: Path | None = None) -> None:
        """Create a store at ``path`` without touching raw project data."""
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = Lock()
        self._schema_ready = False
        self._ensure_schema()
        if legacy_jsonl_path is not None:
            self._migrate_legacy_jsonl(legacy_jsonl_path)

    async def append(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """Append one memory record and return the persisted object."""
        record = MemoryRecord(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        await to_thread(self._append_record, record)
        return record

    async def list(self, *, session_id: str | None = None) -> MemoryRecordList:
        """List memory records, optionally filtered by session id."""
        return await to_thread(self._list_records, session_id)

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection configured for memory access."""
        conn = sqlite3.connect(self._path, timeout=30.0)
        conn.row_factory = sqlite3.Row
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
                    CREATE TABLE IF NOT EXISTS memory_records (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_memory_records_session_created
                        ON memory_records(session_id, created_at, id);
                    """
                )
                conn.commit()
            self._schema_ready = True

    def _append_record(self, record: MemoryRecord) -> None:
        """Write one memory record to SQLite."""
        payload = record.model_dump(mode="json")
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO memory_records (
                    id,
                    session_id,
                    role,
                    content,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["session_id"],
                    payload["role"],
                    payload["content"],
                    json.dumps(payload["metadata"], ensure_ascii=False),
                    payload["created_at"],
                ),
            )
            conn.commit()

    def _migrate_legacy_jsonl(self, path: Path) -> None:
        """Import legacy JSONL memory records when the SQLite store is empty."""
        if not path.exists() or self._has_records():
            return
        records: list[MemoryRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(MemoryRecord.model_validate(json.loads(line)))
        if not records:
            return
        with closing(self._connect()) as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO memory_records (
                    id,
                    session_id,
                    role,
                    content,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        payload["id"],
                        payload["session_id"],
                        payload["role"],
                        payload["content"],
                        json.dumps(payload["metadata"], ensure_ascii=False),
                        payload["created_at"],
                    )
                    for payload in (record.model_dump(mode="json") for record in records)
                ],
            )
            conn.commit()

    def _has_records(self) -> bool:
        """Return whether the SQLite memory table already has records."""
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT 1 FROM memory_records LIMIT 1").fetchone()
        return row is not None

    def _list_records(self, session_id: str | None) -> MemoryRecordList:
        """Read memory records from SQLite."""
        sql = """
            SELECT id, session_id, role, content, metadata_json, created_at
            FROM memory_records
        """
        params: tuple[str, ...] = ()
        if session_id is not None:
            sql += " WHERE session_id = ?"
            params = (session_id,)
        sql += " ORDER BY created_at ASC, id ASC"
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            MemoryRecord.model_validate(
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata_json"]),
                    "created_at": row["created_at"],
                }
            )
            for row in rows
        ]
