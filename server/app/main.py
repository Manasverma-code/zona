"""
main.py — The entire Zona API, in one readable file.

Every route follows the same pattern:
    1. Authenticate  → who is calling? (bearer token → Device)
    2. Locate        → where are they? (headers → LocationEvidence)
    3. Gate          → if the route needs to be ON campus, run require_inside()
    4. Do the thing  → read/write the database
    5. Respond       → typed JSON the app can trust

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import config, models, streaks
from .auth import ensure_handle, issue_token, verify_token
from .database import SessionLocal, get_db, init_db
from .geofence import is_inside_campus
from .models import utcnow
from .schemas import (
    AuthResponse,
    CreateServerRequest,
    DeviceInfo,
    FeedResponse,
    GateStatus,
    HealthResponse,
    NewPostRequest,
    PingResponse,
    PostOut,
    RegisterRequest,
    ServerListResponse,
    ServerOut,
)
from .verify import LocationEvidence, OUTSIDE_ZONE_RESPONSE, parse_location, require_inside

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

app = FastAPI(title="Zona API", version="0.2.0", description="The campus-gated feed backend.")


@app.on_event("startup")
def startup() -> None:
    """Run once when the server starts: make sure the database tables exist
    and the default servers are seeded."""
    init_db()
    seed_default_servers()


# The rooms every campus gets on day one. Students can make their own on top.
DEFAULT_SERVERS = [
    ("Food", "What's good today — mess, dhabas, canteens, deliveries."),
    ("Lost & Found", "Lost your charger? Found an ID card? Post it here."),
    ("Classes", "Assignments, quiz alerts, prof gossip, attendance swaps."),
    ("Rumors", "Unverified. Handle with salt. That's the point."),
    ("Events", "Fests, hackathons, club meets, free food signals."),
    ("Misc", "Everything that doesn't fit anywhere else."),
]


def seed_default_servers() -> None:
    """Create the default rooms on first run (and only then)."""
    db = SessionLocal()
    try:
        existing = {
            s.name for s in db.query(models.Server).filter(models.Server.is_default.is_(True))
        }
        for name, description in DEFAULT_SERVERS:
            if name not in existing:
                db.add(models.Server(name=name, description=description, is_default=True))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers (used by the routes below)
# ---------------------------------------------------------------------------

def current_device(db: Session, token: str | None) -> models.Device:
    """Turn a bearer token into a Device row (or 401).

    This is the "who are you?" step of every request.
    """
    if not token or not token.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    payload = verify_token(token[7:].strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    device = db.query(models.Device).filter(
        models.Device.device_id == payload["device_id"]
    ).first()
    if device is None:
        raise HTTPException(status_code=401, detail="Unknown device")

    return device


def location_evidence(
    x_zona_lat: str | None = Header(default=None),
    x_zona_lon: str | None = Header(default=None),
    x_zona_fix_epoch: str | None = Header(default=None),
    x_zona_accuracy_m: str | None = Header(default=None),
    x_zona_bssids: str | None = Header(default=None),
) -> LocationEvidence:
    """FastAPI dependency: collect + parse all location headers into one object.

    The app MUST send these headers on every call (see app/constants.ts).
    """
    return parse_location(x_zona_lat, x_zona_lon, x_zona_fix_epoch, x_zona_accuracy_m, x_zona_bssids)


def expires_at(post: models.Post) -> datetime:
    """When does this post die? created_at + lifetime (both naive UTC).

    Stored values are naive UTC (SQLite has no tz support), so stamp the
    timezone back on here — the client always receives real UTC timestamps.
    """
    return (post.created_at + timedelta(hours=config.POST_LIFETIME_HOURS)).replace(
        tzinfo=timezone.utc
    )


def post_to_out(db: Session, post: models.Post, viewer_id: int | None = None) -> PostOut:
    """Convert a Post row into the JSON shape the feed expects.

    Counts reactions into a {emoji: count} map and adds the viewer's own
    reaction so the app can highlight it.
    """
    # Count each emoji: {"🔥": 3, "😂": 1, ...}
    # (🚩 was briefly used for reports in an earlier schema — never show it.)
    counts: dict[str, int] = {}
    my_reaction: str | None = None
    for reaction in post.reactions:
        if reaction.emoji == "🚩":
            continue
        counts[reaction.emoji] = counts.get(reaction.emoji, 0) + 1
        if reaction.device_id == viewer_id:
            my_reaction = reaction.emoji

    return PostOut(
        id=post.id,
        server_id=post.server_id,
        body=post.body,
        handle=post.author.handle,
        created_at=post.created_at.replace(tzinfo=timezone.utc),
        expires_at=expires_at(post),
        reactions=counts,
        my_reaction=my_reaction,
    )


def server_to_out(db: Session, server: models.Server, viewer_id: int | None = None) -> ServerOut:
    """Convert a Server row into the JSON shape the server list expects."""
    post_count = query_visible_posts(db, server_id=server.id).count()
    return ServerOut(
        id=server.id,
        name=server.name,
        description=server.description,
        post_count=post_count,
        is_default=server.is_default,
        created_at=server.created_at.replace(tzinfo=timezone.utc),
        is_creator=viewer_id is not None and server.creator_id == viewer_id,
    )


def gate_status(evidence: LocationEvidence) -> GateStatus:
    """Non-throwing version of the gate — used by routes that work both
    inside AND outside (register, ping). Reports WHY instead of raising."""
    if not config.GEOFENCE_ENABLED:
        return GateStatus(inside=True)
    if evidence.lat is None or evidence.lon is None:
        return GateStatus(inside=False, reason="no_position")
    if evidence.fix_age_seconds is None or evidence.fix_age_seconds > config.MAX_FIX_AGE_SECONDS:
        return GateStatus(inside=False, reason="fix_too_old")
    if evidence.accuracy_meters is None or evidence.accuracy_meters > config.MAX_GPS_ACCURACY_METERS:
        return GateStatus(inside=False, reason="accuracy_too_low")
    if not is_inside_campus(evidence.lat, evidence.lon):
        return GateStatus(inside=False, reason="outside_polygon")
    return GateStatus(inside=True)


def query_visible_posts(db: Session, include_hidden: bool = False, server_id: int | None = None):
    """All unexpired, non-hidden posts, newest first. Optionally one server's."""
    cutoff = utcnow() - timedelta(hours=config.POST_LIFETIME_HOURS)
    query = db.query(models.Post).filter(models.Post.created_at >= cutoff)
    if server_id is not None:
        query = query.filter(models.Post.server_id == server_id)
    if not include_hidden:
        query = query.filter(models.Post.hidden.is_(False))
    return query.order_by(models.Post.created_at.desc())


# ---------------------------------------------------------------------------
# Public routes (no auth needed)
# ---------------------------------------------------------------------------

@app.get("/v1/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Ops check: is the server up, and roughly how alive is the feed?"""
    return HealthResponse(
        status="ok",
        posts_alive=query_visible_posts(db).count(),
        devices=db.query(models.Device).count(),
    )


@app.post("/v1/register", response_model=AuthResponse)
def register(
    body: RegisterRequest,
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Called ONCE when the app is installed.

    Creates the anonymous device identity, mints a token, and tells the
    app whether it's standing inside the zone right now.
    """
    # Find-or-create the device.
    device = db.query(models.Device).filter(
        models.Device.device_id == body.device_id
    ).first()
    if device is None:
        device = models.Device(device_id=body.device_id)
        db.add(device)

    # Refresh the weekly anonymous handle if needed.
    ensure_handle(db, device)
    db.commit()

    return AuthResponse(
        token=issue_token(body.device_id),
        handle=device.handle,
        gate=gate_status(evidence),
    )


# ---------------------------------------------------------------------------
# Authenticated routes
# ---------------------------------------------------------------------------

@app.post("/v1/ping", response_model=PingResponse)
def ping(
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> PingResponse:
    """The heartbeat — the app calls this every time it opens or returns
    to the foreground.

    * Updates the weekly handle (auto re-roll)
    * Grows the streak IF the user is inside the zone
    * Reports gate status so the app can flip blank ↔ feed instantly
    """
    device = current_device(db, authorization)
    ensure_handle(db, device)

    gate = gate_status(evidence)
    if gate.inside:
        streaks.register_streak_day(device)

    db.commit()
    return PingResponse(gate=gate, handle=device.handle, streak=device.streak)


@app.get("/v1/feed", response_model=FeedResponse)
def get_feed(
    server_id: int | None = None,
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> FeedResponse:
    """The feed. ONLY readable from inside the zone.

    With ?server_id= you get that one room's feed; without it, everything
    alive on campus. Outside → 403 + the exact blank-screen message.
    """
    # GATE: outside the zone means NO FEED. Hard fail, no partial data.
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=False,  # reading is OK with GPS alone
    )

    device = current_device(db, authorization)

    # A server feed must point at a real, unhidden server.
    if server_id is not None:
        server = db.query(models.Server).filter(models.Server.id == server_id).first()
        if server is None or server.hidden:
            raise HTTPException(status_code=404, detail="Server not found")

    posts = query_visible_posts(db, server_id=server_id).all()
    return FeedResponse(
        posts=[post_to_out(db, post, viewer_id=device.id) for post in posts],
        post_count=len(posts),
        streak=device.streak,
    )


@app.post("/v1/posts", response_model=PostOut, status_code=201)
def create_post(
    body: NewPostRequest,
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> PostOut:
    """Create a post. The most protected route — demands EVERYTHING:
    fresh fix, good accuracy, inside polygon, AND campus Wi-Fi fingerprint.
    """
    # 1) Gate — writing is where fakes hurt most, so BSSID proof is required.
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=config.REQUIRE_BSSID_PROOF,
    )

    device = current_device(db, authorization)

    # 2) The server must exist and be visible (you can't post into a hidden room).
    server = db.query(models.Server).filter(models.Server.id == body.server_id).first()
    if server is None or server.hidden:
        raise HTTPException(status_code=404, detail="Server not found")

    # 3) Rate limits (anti-spam): max N per hour + min gap between posts.
    hour_ago = utcnow() - timedelta(hours=1)
    recent_count = db.query(models.Post).filter(
        models.Post.author_id == device.id,
        models.Post.created_at >= hour_ago,
    ).count()
    if recent_count >= config.MAX_POSTS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Slow down — too many posts this hour")

    if (
        device.last_post_at is not None
        and (utcnow() - device.last_post_at).total_seconds()
        < config.MIN_POST_GAP_SECONDS
    ):
        raise HTTPException(status_code=429, detail="Wait a minute between posts")

    # 4) Create it. Streak counts this as an active day too.
    post = models.Post(
        server_id=server.id,
        author_id=device.id,
        body=body.body,
    )
    db.add(post)
    device.last_post_at = utcnow()
    streaks.register_streak_day(device)
    db.commit()
    db.refresh(post)

    return post_to_out(db, post, viewer_id=device.id)


# ---------------------------------------------------------------------------
# Server rooms (the Discord-style part)
# ---------------------------------------------------------------------------

@app.get("/v1/servers", response_model=ServerListResponse)
def list_servers(
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> ServerListResponse:
    """Every room on campus, newest first (defaults seeded first).

    Read-only, so GPS proof is enough — same gate as the feed.
    """
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=False,
    )

    device = current_device(db, authorization)
    servers = db.query(models.Server).filter(models.Server.hidden.is_(False)).order_by(
        models.Server.created_at.desc()
    ).all()

    return ServerListResponse(
        servers=[server_to_out(db, s, viewer_id=device.id) for s in servers],
        count=len(servers),
    )


@app.post("/v1/servers", response_model=ServerOut, status_code=201)
def create_server(
    body: CreateServerRequest,
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> ServerOut:
    """A student makes their own room — "Hostel Wing B", whatever.

    A write, so it demands the full gate (BSSID proof) + its own rate limits:
    one server per hour, five per device, ever.
    """
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=config.REQUIRE_BSSID_PROOF,
    )

    device = current_device(db, authorization)

    # Rate limits: 1/hour, 5 total. Keeps the server list from drowning.
    hour_ago = utcnow() - timedelta(hours=1)
    this_hour = db.query(models.Server).filter(
        models.Server.creator_id == device.id,
        models.Server.created_at >= hour_ago,
    ).count()
    if this_hour >= config.MAX_SERVERS_PER_HOUR:
        raise HTTPException(status_code=429, detail="One new room per hour is enough")

    total = db.query(models.Server).filter(
        models.Server.creator_id == device.id,
    ).count()
    if total >= config.MAX_SERVERS_PER_DEVICE:
        raise HTTPException(status_code=429, detail="You've hit your room limit (5)")

    server = models.Server(
        name=body.name.strip(),
        description=body.description.strip(),
        creator_id=device.id,
    )
    db.add(server)
    device.last_server_at = utcnow()
    db.commit()
    db.refresh(server)

    return server_to_out(db, server, viewer_id=device.id)


@app.delete("/v1/servers/{server_id}", status_code=204)
def delete_server(
    server_id: int,
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> Response:
    """The creator can retire their own room (soft delete).

    Default seeded servers have no creator, so nobody can delete those.
    """
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=config.REQUIRE_BSSID_PROOF,
    )

    device = current_device(db, authorization)
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    if server.creator_id != device.id:
        raise HTTPException(status_code=403, detail="Only the creator can delete this room")

    server.hidden = True
    db.commit()
    return Response(status_code=204)


@app.post("/v1/servers/{server_id}/report", status_code=204)
def report_server(
    server_id: int,
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> Response:
    """Report a room. 5 reports → hidden, same rule as posts."""
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=False,
    )

    device = current_device(db, authorization)
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    existing = db.query(models.Report).filter(
        models.Report.server_id == server.id,
        models.Report.device_id == device.id,
    ).first()
    if existing:
        raise HTTPException(status_code=429, detail="Already reported")

    db.add(models.Report(server_id=server.id, device_id=device.id))
    db.flush()  # the count below must include THIS report (autoflush is off)

    report_count = db.query(models.Report).filter(
        models.Report.server_id == server.id,
    ).count()
    if report_count >= config.REPORTS_TO_HIDE:
        server.hidden = True

    db.commit()
    return Response(status_code=204)


@app.post("/v1/posts/{post_id}/react", response_model=PostOut)
def react(
    post_id: int,
    emoji: str = Header(alias="X-Zona-Emoji", default="🔥"),
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> PostOut:
    """React with one emoji. Inside-zone only.

    One reaction per device per post — reacting again just CHANGES your emoji.
    """
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=False,
    )

    device = current_device(db, authorization)

    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if post is None or post.hidden:
        raise HTTPException(status_code=404, detail="Post not found")

    # Limit emoji length so only real reactions get stored.
    # Headers are latin-1 only, so the app sends the emoji percent-encoded
    # (encodeURIComponent) — decode it here.
    emoji = unquote(emoji).strip()[:8]
    if not emoji:
        raise HTTPException(status_code=422, detail="Empty emoji")

    # Find any existing reaction from this device → update it (upsert).
    reaction = db.query(models.Reaction).filter(
        models.Reaction.post_id == post.id,
        models.Reaction.device_id == device.id,
    ).first()
    if reaction is None:
        reaction = models.Reaction(post_id=post.id, device_id=device.id, emoji=emoji)
        db.add(reaction)
    else:
        reaction.emoji = emoji

    db.commit()
    db.refresh(post)
    return post_to_out(db, post, viewer_id=device.id)


@app.post("/v1/posts/{post_id}/report", status_code=204)
def report(
    post_id: int,
    authorization: str | None = Header(default=None),
    evidence: LocationEvidence = Depends(location_evidence),
    db: Session = Depends(get_db),
) -> Response:
    """Report a post. 5 reports → hidden automatically (moderation).

    204 = success with no body; the app doesn't need anything back.
    """
    require_inside(
        evidence.lat,
        evidence.lon,
        evidence.fix_age_seconds,
        evidence.accuracy_meters,
        evidence.bssid_hashes,
        require_bssid=False,
    )

    device = current_device(db, authorization)
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # One report per device per post (a separate table, so a device that
    # already REACTED can still REPORT — the reaction table is unique on
    # post+device and would otherwise collide).
    existing = db.query(models.Report).filter(
        models.Report.post_id == post.id,
        models.Report.device_id == device.id,
    ).first()
    if existing:
        raise HTTPException(status_code=429, detail="Already reported")

    db.add(models.Report(post_id=post.id, device_id=device.id))
    # Flush now — the count below must include THIS report (sessions run with
    # autoflush=False, so the query wouldn't see it otherwise).
    db.flush()

    # Auto-hide when reports pile up.
    report_count = db.query(models.Report).filter(
        models.Report.post_id == post.id,
    ).count()
    if report_count >= config.REPORTS_TO_HIDE:
        post.hidden = True

    db.commit()

    # Return an explicit empty response so FastAPI knows 204 has no body.
    return Response(status_code=204)


@app.get("/v1/me", response_model=DeviceInfo)
def me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> DeviceInfo:
    """The app's own identity card — handle + streak. No location needed."""
    device = current_device(db, authorization)
    ensure_handle(db, device)
    db.commit()
    return DeviceInfo(handle=device.handle, streak=device.streak)
