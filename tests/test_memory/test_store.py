"""Memory store behavior for the local-first gateway runtime."""

from __future__ import annotations

from hso.memory import MemoryStore


def test_memory_store_appends_and_lists_records(tmp_path):
    """MemoryStore persists session-scoped records in append order."""
    store = MemoryStore(tmp_path / "memory.jsonl")

    first = store.append(
        session_id="session-1",
        role="user",
        content="Draft a paper outline.",
        metadata={"source": "test"},
    )
    second = store.append(
        session_id="session-1",
        role="assistant",
        content="I will create a research workflow.",
    )

    records = store.list(session_id="session-1")
    assert [record.id for record in records] == [first.id, second.id]
    assert records[0].metadata == {"source": "test"}
    assert records[1].content == "I will create a research workflow."

    reloaded = MemoryStore(tmp_path / "memory.jsonl")
    assert [record.content for record in reloaded.list(session_id="session-1")] == [
        "Draft a paper outline.",
        "I will create a research workflow.",
    ]


def test_memory_store_filters_records_by_session(tmp_path):
    """MemoryStore returns only records for the requested session."""
    store = MemoryStore(tmp_path / "memory.jsonl")

    store.append(session_id="session-1", role="user", content="one")
    store.append(session_id="session-2", role="user", content="two")

    assert [record.content for record in store.list(session_id="session-1")] == ["one"]
    assert [record.content for record in store.list(session_id="session-2")] == ["two"]
