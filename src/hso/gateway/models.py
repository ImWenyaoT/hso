"""Pydantic models shared by the gateway API and runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SessionRecord(BaseModel):
    """One local gateway session."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"ses_{uuid4().hex}")
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GatewayEvent(BaseModel):
    """One event emitted by the gateway or an agent run."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    session_id: str
    type: str
    message: str
    agent_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CreateSessionRequest(BaseModel):
    """Request body for creating a gateway session."""

    title: str = "Untitled session"


class SendMessageRequest(BaseModel):
    """Request body for sending a user message to a session."""

    content: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    """Response body returned after a session message is processed."""

    session: SessionRecord
    events: list[GatewayEvent]
