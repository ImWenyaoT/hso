"""FastAPI app factory for the hso local gateway."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from hso.config import load_settings
from hso.gateway.models import (
    CreateSessionRequest,
    GatewayEvent,
    SendMessageRequest,
    SendMessageResponse,
    SessionRecord,
)
from hso.gateway.runtime import GatewayRuntime
from hso.memory import MemoryRecord


def create_app(runtime: GatewayRuntime | None = None) -> FastAPI:
    """Create the FastAPI gateway application."""
    gateway_runtime = runtime or GatewayRuntime(data_dir=_default_gateway_dir())
    app = FastAPI(title="hso gateway", version="0.3.0")
    app.state.runtime = gateway_runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Return gateway readiness for CLI and UI checks."""
        return {"status": "ok", "service": "hso-gateway"}

    @app.get("/api/sessions")
    def list_sessions() -> list[SessionRecord]:
        """List known gateway sessions."""
        return gateway_runtime.list_sessions()

    @app.post("/api/sessions", status_code=status.HTTP_201_CREATED)
    def create_session(payload: CreateSessionRequest) -> SessionRecord:
        """Create a session for a UI or CLI operator."""
        return gateway_runtime.create_session(title=payload.title)

    @app.post("/api/sessions/{session_id}/messages")
    def send_message(session_id: str, payload: SendMessageRequest) -> SendMessageResponse:
        """Send a user message through the local agent runtime."""
        try:
            events = gateway_runtime.send_message(session_id, payload.content)
            session = gateway_runtime.get_session(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return SendMessageResponse(session=session, events=events)

    @app.get("/api/sessions/{session_id}/events")
    def list_events(session_id: str) -> list[GatewayEvent]:
        """List events for a session."""
        try:
            return gateway_runtime.list_events(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/sessions/{session_id}/memory")
    def list_memory(session_id: str) -> list[MemoryRecord]:
        """List memory records for a session."""
        try:
            return gateway_runtime.list_memory(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


def _default_gateway_dir() -> Path:
    """Return the default local gateway state directory."""
    return load_settings().data_dir / "gateway"
