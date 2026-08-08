"""
models.py — The database tables Zona needs.

Think of each class as a spreadsheet tab:
    Device   → one row per phone that installed the app
    Server   → one row per Discord-style room (Food, Lost & Found, user-made...)
    Post     → one row per thing someone shared (always inside a server)
    Reaction → one row per emoji reaction
    Report   → one row per moderation report

Nothing clever here — just plain columns and relationships.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Convenience: "right now" in UTC.

    Stored NAIVE on purpose: SQLite has no timezone support, so every value
    comes back from the DB without tzinfo. Keeping them naive everywhere
    inside the app avoids "can't subtract naive and aware" bugs. The API
    layer (post_to_out) stamps UTC back on when serializing to clients.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Device(Base):
    """A phone that installed Zona. No email, no password — just a random id
    the phone generated once and keeps forever."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The phone's random id (UUID generated on the device). Unique per phone.
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Anonymous identity. "Violet-384". Re-rolled weekly by auth.py.
    handle: Mapped[str] = mapped_column(String(64), default="anon")

    # The week this handle was issued (ISO year-week, e.g. "2026-W32").
    # Used to roll a fresh handle each week.
    handle_week: Mapped[str] = mapped_column(String(16), default="")

    # Streak = consecutive days the user did something inside the zone.
    streak: Mapped[int] = mapped_column(Integer, default=0)
    # The last day (YYYY-MM-DD, UTC) that counted toward the streak.
    last_streak_day: Mapped[str] = mapped_column(String(10), default="")

    # Timestamps for rate limiting (kept simple at pilot scale).
    last_post_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_server_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Batch moderators can be flagged by an admin (not built yet, column ready).
    is_moderator: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship: all posts + reactions this device made.
    posts: Mapped[list["Post"]] = relationship(back_populates="author")
    reactions: Mapped[list["Reaction"]] = relationship(back_populates="author")
    servers: Mapped[list["Server"]] = relationship(back_populates="creator")


class Server(Base):
    """A Discord-style room: "Food", "Lost & Found", or anything a student
    creates. Posts live inside a server; the feed is per-server.

    creator_id is NULL for the seeded default servers (system-made). User
    servers are anonymous like everything else — we remember the creator's
    device only so they can delete their own room.
    """

    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(String(160), default="")

    # Which device made it (None = a seeded default server).
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    # Seeded by the system at startup (can't be deleted by users).
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Soft delete: hidden by reports (5) or by its creator.
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    creator: Mapped["Device | None"] = relationship(back_populates="servers")
    posts: Mapped[list["Post"]] = relationship(back_populates="server")


class Report(Base):
    """A moderation report. Separate from Reaction on purpose: a device that
    reacted to a post must STILL be able to report it. (The Reaction table's
    unique post_id+device_id constraint would make that impossible.)

    Can point at a post (post_id) OR a server (server_id) — never both.
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id"), nullable=True, index=True
    )
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id"), nullable=True, index=True
    )
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # One report per device per thing — no spam-reporting.
    __table_args__ = (
        UniqueConstraint("post_id", "device_id", name="uq_report_post_device"),
        UniqueConstraint("server_id", "device_id", name="uq_report_server_device"),
    )


class Post(Base):
    """One anonymous post. Born inside the zone, dead 24h later."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Which server/room it lives in (every post belongs to one).
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), index=True)

    # Who wrote it (a Device row). Anonymous by design — we never know a real name.
    author_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)

    # The message. Max 300 chars (checked again in schemas.py).
    body: Mapped[str] = mapped_column(Text)

    # When it was created — expiry = created_at + POST_LIFETIME_HOURS.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    # Soft delete: when reports pass the limit we set hidden=True.
    # The row stays (for moderation forensics) but no one sees it.
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    author: Mapped["Device"] = relationship(back_populates="posts")
    server: Mapped["Server"] = relationship(back_populates="posts")
    reactions: Mapped[list["Reaction"]] = relationship(back_populates="post")


class Reaction(Base):
    """An emoji reaction. One per device per post (you can change it, not stack it)."""

    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))

    # The emoji itself, e.g. "🔥". Plain text is fine.
    emoji: Mapped[str] = mapped_column(String(8))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # The same device can react to the same post only ONCE.
    # On a second reaction we UPSERT (change the emoji instead of adding a row).
    __table_args__ = (
        UniqueConstraint("post_id", "device_id", name="uq_reaction_post_device"),
    )

    post: Mapped["Post"] = relationship(back_populates="reactions")
    author: Mapped["Device"] = relationship(back_populates="reactions")
