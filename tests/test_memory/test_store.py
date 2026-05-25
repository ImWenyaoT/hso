"""Memory store behavior for the local-first gateway runtime."""

from __future__ import annotations

import json

import pytest

from hso.memory import MemoryStore


@pytest.mark.asyncio
async def test_memory_store_appends_and_lists_records(tmp_path):
    """MemoryStore persists session-scoped records in append order."""
    store = MemoryStore(tmp_path / "memory.jsonl")

    first = await store.append(
        session_id="session-1",
        role="user",
        content="Draft a paper outline.",
        metadata={"source": "test"},
    )
    second = await store.append(
        session_id="session-1",
        role="assistant",
        content="I will create a research workflow.",
    )

    records = await store.list(session_id="session-1")
    assert [record.id for record in records] == [first.id, second.id]
    assert records[0].metadata == {"source": "test"}
    assert records[1].content == "I will create a research workflow."

    reloaded = MemoryStore(tmp_path / "memory.jsonl")
    assert [record.content for record in await reloaded.list(session_id="session-1")] == [
        "Draft a paper outline.",
        "I will create a research workflow.",
    ]


@pytest.mark.asyncio
async def test_memory_store_filters_records_by_session(tmp_path):
    """MemoryStore returns only records for the requested session."""
    store = MemoryStore(tmp_path / "memory.jsonl")

    await store.append(session_id="session-1", role="user", content="one")
    await store.append(session_id="session-2", role="user", content="two")

    assert [record.content for record in await store.list(session_id="session-1")] == ["one"]
    assert [record.content for record in await store.list(session_id="session-2")] == ["two"]


@pytest.mark.asyncio
async def test_memory_store_migrates_legacy_jsonl_records(tmp_path):
    """MemoryStore imports legacy JSONL records when the SQLite store is empty."""
    legacy = tmp_path / "memory.jsonl"
    legacy.write_text(
        json.dumps(
            {
                "id": "mem_legacy",
                "session_id": "session-1",
                "role": "user",
                "content": "legacy",
                "metadata": {"source": "jsonl"},
                "created_at": "2026-05-22T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    store = MemoryStore(tmp_path / "memory.sqlite3", legacy_jsonl_path=legacy)

    records = await store.list(session_id="session-1")
    assert [record.id for record in records] == ["mem_legacy"]
    assert records[0].metadata == {"source": "jsonl"}
