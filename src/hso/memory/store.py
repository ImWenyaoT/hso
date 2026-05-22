"""Append-only JSONL memory store used by the local gateway."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
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
    """Small append-only JSONL store for local-first memory."""

    def __init__(self, path: Path) -> None:
        """Create a store at ``path`` without touching raw project data."""
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(
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
        with self._path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        return record

    def list(self, *, session_id: str | None = None) -> MemoryRecordList:
        """List memory records, optionally filtered by session id."""
        records = self._read_all()
        if session_id is None:
            return records
        return [record for record in records if record.session_id == session_id]

    def _read_all(self) -> MemoryRecordList:
        """Read all records from disk, skipping blank lines."""
        if not self._path.exists():
            return []
        records: MemoryRecordList = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(MemoryRecord.model_validate(json.loads(line)))
        return records
