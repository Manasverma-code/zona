"""
config.py — Every knob of the Zona backend lives here, in one place.

If you want to change HOW the app behaves (how long posts live, how big
the campus is, how strict the gate is), you change it here — not in the routes.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Core Zona constants
# ---------------------------------------------------------------------------

# How long a post survives before it evaporates. 24 hours = the core loop.
POST_LIFETIME_HOURS = int(os.getenv("ZONA_POST_LIFETIME_HOURS", "24"))

# A location fix is only accepted if it is FRESH — the phone sent it
# within this many seconds. Stops people from replaying an old "inside" fix.
MAX_FIX_AGE_SECONDS = int(os.getenv("ZONA_MAX_FIX_AGE_SECONDS", "120"))

# GPS accuracy is not perfect (phones drift 10-50 m indoors).
# If the phone reports an accuracy worse than this, we ask it to move
# to a better spot instead of trusting the position.
MAX_GPS_ACCURACY_METERS = int(os.getenv("ZONA_MAX_GPS_ACCURACY_METERS", "50"))

# Spoof-proofing level 2: every post MUST include hashes of the WiFi
# networks the phone can see. Those networks only exist on campus, and you
# cannot see them from outside, so this is a strong "I am physically here" signal.
#
# OFF by default for the pilot: Expo Go has no BSSID API, so the app sends an
# empty fingerprint list. Flip to 1 when the app is built with the wifi
# dev-build plugin (see app/src/location.ts collectBssids).
REQUIRE_BSSID_PROOF = os.getenv("ZONA_REQUIRE_BSSID_PROOF", "0") == "1"

# THE gate's master switch. ON means only devices physically inside the
# campus polygon (plus fresh, accurate GPS) can see or write anything.
# OFF (default for now) means the app works from anywhere — no location
# checks at all. Flip to 1 when the real campus polygon is in place
# (ZONA_CAMPUS_POLYGON) and location proof is wanted again.
GEOFENCE_ENABLED = os.getenv("ZONA_GEOFENCE_ENABLED", "0") == "1"

# Anonymous handle format: an adjective + a number, e.g. "Violet-384".
# It is re-rolled every week so nothing is traceable long-term.
# (wordlists live in auth.py)

# ---------------------------------------------------------------------------
# Rate limits (anti-spam) — per device
# ---------------------------------------------------------------------------

# A device may create at most this many posts per rolling hour.
MAX_POSTS_PER_HOUR = int(os.getenv("ZONA_MAX_POSTS_PER_HOUR", "5"))

# A device must wait at least this many seconds between two posts.
MIN_POST_GAP_SECONDS = int(os.getenv("ZONA_MIN_POST_GAP_SECONDS", "60"))

# Server rooms: max 1 new server per hour, max 5 per device, period.
MAX_SERVERS_PER_HOUR = int(os.getenv("ZONA_MAX_SERVERS_PER_HOUR", "1"))
MAX_SERVERS_PER_DEVICE = int(os.getenv("ZONA_MAX_SERVERS_PER_DEVICE", "5"))

# After this many reports, a post is hidden automatically.
REPORTS_TO_HIDE = int(os.getenv("ZONA_REPORTS_TO_HIDE", "5"))

# ---------------------------------------------------------------------------
# Campus boundary (THE gate)
# ---------------------------------------------------------------------------

# Option 1 — the easy way: give us the CENTER of your campus and its size.
# The server builds a rectangle around it. Good enough to start.
#   45 acres ≈ 182,000 m² ≈ a square of ~427 m per side → use ~214 m half-size.
CAMPUS_CENTER_LAT = float(os.getenv("ZONA_CENTER_LAT", "28.5445"))   # demo location
CAMPUS_CENTER_LON = float(os.getenv("ZONA_CENTER_LON", "77.1926"))   # demo location
CAMPUS_HALF_WIDTH_METERS = float(os.getenv("ZONA_HALF_WIDTH_METERS", "250"))
CAMPUS_HALF_HEIGHT_METERS = float(os.getenv("ZONA_HALF_HEIGHT_METERS", "250"))

# Option 2 — the accurate way: paste a full polygon from Google Maps
# ("Draw polygon → copy coordinates") as  "lat,lon|lat,lon|...".  If set,
# this OVERRIDES the rectangle above.
# e.g. ZONA_CAMPUS_POLYGON="28.5410,77.1880|28.5410,77.1960|28.5480,77.1960|28.5480,77.1880"
CAMPUS_POLYGON_RAW = os.getenv("ZONA_CAMPUS_POLYGON", "")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# SQLite file next to this file — perfect for local development.
# For production, set DATABASE_URL=postgresql+psycopg://user:pass@host/db
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{Path(__file__).resolve().parent.parent / 'zona.db'}")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

# Signs the auth tokens. CHANGE THIS in production (never ship the default).
TOKEN_SECRET = os.getenv("ZONA_TOKEN_SECRET", "dev-secret-change-me")

# Tokens expire after this long. The app re-pings every few minutes anyway.
TOKEN_LIFETIME_SECONDS = int(os.getenv("ZONA_TOKEN_LIFETIME_SECONDS", "3600"))
