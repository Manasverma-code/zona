"""
schemas.py — What data is ALLOWED to come in, and what we PROMISE to send out.

FastAPI uses these to:
    * validate request bodies (auto-reject bad input with a 422)
    * document every endpoint at /docs
All "business" shape decisions live here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request bodies (what the app SENDS us)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Called once when the app is installed."""
    device_id: str = Field(min_length=8, max_length=64)


class NewPostRequest(BaseModel):
    """Called every time someone posts."""
    server_id: int = Field(gt=0, description="Which server/room this post lives in")
    body: str = Field(min_length=1, max_length=300, description="The message (1-300 chars)")


class CreateServerRequest(BaseModel):
    """Called when a student creates a Discord-style room."""
    name: str = Field(min_length=3, max_length=40, description="e.g. 'Hostel Wing B'")
    description: str = Field(default="", max_length=160)


# ---------------------------------------------------------------------------
# Response bodies (what the app RECEIVES from us)
# ---------------------------------------------------------------------------

class DeviceInfo(BaseModel):
    """Who you are, right now."""
    handle: str
    streak: int


class GateStatus(BaseModel):
    """The answer to "am I inside?" — returned by almost every endpoint."""
    inside: bool
    reason: str | None = None  # e.g. "accuracy_too_low", "fix_too_old", "outside_polygon"


class AuthResponse(BaseModel):
    token: str
    handle: str
    gate: GateStatus


class PostOut(BaseModel):
    """A post as seen by the feed. Reactions are a simple {emoji: count} map."""
    id: int
    server_id: int
    body: str
    handle: str
    created_at: datetime
    expires_at: datetime
    reactions: dict[str, int] = Field(default_factory=dict)
    my_reaction: str | None = None


class ServerOut(BaseModel):
    """A Discord-style room as seen in the server list."""
    id: int
    name: str
    description: str
    post_count: int
    is_default: bool
    created_at: datetime
    is_creator: bool = False  # true only if YOU created this server


class ServerListResponse(BaseModel):
    servers: list[ServerOut]
    count: int


class FeedResponse(BaseModel):
    posts: list[PostOut]
    post_count: int
    streak: int


class PingResponse(BaseModel):
    """Answer to the app's heartbeat (sent every time the app opens)."""
    gate: GateStatus
    handle: str
    streak: int


class HealthResponse(BaseModel):
    status: str
    posts_alive: int
    devices: int
