"""SQLite-backed gateway session store behavior."""

from __future__ import annotations

import pytest

from hso.gateway.models import GatewayEvent, SessionRecord
from hso.gateway.store import GatewaySQLiteStore


@pytest.mark.asyncio
async def test_gateway_sqlite_store_persists_sessions_and_events(tmp_path):
    """GatewaySQLiteStore restores session and event records from disk."""
    db_path = tmp_path / "gateway.db"
    store = GatewaySQLiteStore(db_path)
    session = SessionRecord(title="SQLite session")
    event = GatewayEvent(
        session_id=session.id,
        type="agent.completed",
        message="Session state persisted.",
        agent_name="main",
        payload={"ok": True},
    )

    await store.save_session(session)
    await store.save_events([event])

    reloaded = GatewaySQLiteStore(db_path)
    assert [record.id for record in await reloaded.list_sessions()] == [session.id]
    assert (await reloaded.get_session(session.id)).title == "SQLite session"

    events = await reloaded.list_events(session.id)
    assert [record.id for record in events] == [event.id]
    assert events[0].payload == {"ok": True}


@pytest.mark.asyncio
async def test_gateway_sqlite_store_saves_events_in_one_batch(tmp_path):
    """GatewaySQLiteStore persists multiple events through the batch API."""
    store = GatewaySQLiteStore(tmp_path / "gateway.db")
    session = SessionRecord(title="Batch session")
    events = [
        GatewayEvent(session_id=session.id, type="agent.started", message="start"),
        GatewayEvent(session_id=session.id, type="agent.completed", message="done"),
    ]

    await store.save_session(session)
    await store.save_events(events)

    reloaded = await store.list_events(session.id)
    assert [event.type for event in reloaded] == ["agent.started", "agent.completed"]


@pytest.mark.asyncio
async def test_gateway_sqlite_store_caches_session_after_first_lookup(tmp_path, monkeypatch):
    """Repeated session lookups should reuse the in-process session cache."""
    store = GatewaySQLiteStore(tmp_path / "gateway.db")
    session = SessionRecord(title="Cached session")
    calls = {"count": 0}
    original_get_session = store._get_session

    def counting_get_session(session_id: str):
        """Count cache-miss database lookups."""
        calls["count"] += 1
        return original_get_session(session_id)

    await store.save_session(session)
    store._session_cache.clear()
    monkeypatch.setattr(store, "_get_session", counting_get_session)

    assert (await store.get_session(session.id)).title == "Cached session"
    assert (await store.get_session(session.id)).title == "Cached session"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_gateway_sqlite_store_updates_session_cache_on_save(tmp_path, monkeypatch):
    """Saving a session should refresh the cached value for that session id."""
    store = GatewaySQLiteStore(tmp_path / "gateway.db")
    session = SessionRecord(title="Old title")
    await store.save_session(session)
    assert (await store.get_session(session.id)).title == "Old title"

    updated = session.model_copy(update={"title": "New title"})
    await store.save_session(updated)
    monkeypatch.setattr(
        store,
        "_get_session",
        lambda _session_id: (_ for _ in ()).throw(AssertionError("cache miss")),
    )

    assert (await store.get_session(session.id)).title == "New title"
