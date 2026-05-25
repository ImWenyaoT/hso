"""FastAPI gateway surface used by the Next.js operator UI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from hso.gateway.app import create_app
from hso.gateway.runtime import GatewayRuntime


class _CountingRuntime(GatewayRuntime):
    """Runtime test double that counts session lookups made during request handling."""

    def __init__(self, **kwargs) -> None:
        """Create a runtime that tracks get_session calls."""
        super().__init__(**kwargs)
        self.get_session_calls = 0

    async def get_session(self, session_id: str):
        """Count every direct session lookup."""
        self.get_session_calls += 1
        return await super().get_session(session_id)


def test_gateway_health_and_session_message_flow(tmp_path):
    """Gateway API exposes health, session creation, messages, events, and memory."""
    runtime = GatewayRuntime(data_dir=tmp_path)
    client = TestClient(create_app(runtime=runtime))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    created = client.post("/api/sessions", json={"title": "Demo"})
    assert created.status_code == 201
    session_id = created.json()["id"]

    sent = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Sketch the gateway plan."},
    )
    assert sent.status_code == 200
    assert sent.json()["events"][-1]["type"] == "agent.completed"

    events = client.get(f"/api/sessions/{session_id}/events")
    assert events.status_code == 200
    assert len(events.json()) == 5

    memory = client.get(f"/api/sessions/{session_id}/memory")
    assert memory.status_code == 200
    assert [record["role"] for record in memory.json()] == ["user", "assistant"]


def test_send_message_handler_reuses_runtime_session_lookup(tmp_path):
    """Message handler should not fetch the same session twice in one request."""
    runtime = _CountingRuntime(data_dir=tmp_path)
    client = TestClient(create_app(runtime=runtime))
    session_id = client.post("/api/sessions", json={"title": "Demo"}).json()["id"]

    sent = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Sketch the gateway plan."},
    )

    assert sent.status_code == 200
    assert runtime.get_session_calls == 1
