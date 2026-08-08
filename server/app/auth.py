"""
auth.py — Anonymous identity + signed tokens.

Zona has NO accounts. A phone installs the app, generates a random device_id,
and from then on it is known only as a weekly handle like "Violet-384".

Tokens are signed with a secret (HMAC-SHA256) so no one can forge a token —
you can only get one from us, and it expires after an hour.

All crypto here uses the Python standard library. Readable > clever.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from . import config

# ---------------------------------------------------------------------------
# Handle generation (the anonymous name)
# ---------------------------------------------------------------------------

# A pool of friendly adjectives. Pair with a number → "Violet-384".
# (Real product: a few hundred adjectives so handles rarely collide.)
ADJECTIVES = [
    "Violet", "Crimson", "Amber", "Sable", "Azure", "Mossy", "Onyx", "Coral",
    "Ivory", "Lunar", "Solar", "Ember", "Frosty", "Velvet", "Indigo", "Sage",
    "Cinder", "Drift", "Quiet", "Rusty", "Shady", "Nimble", "Snappy", "Brisk",
]


def current_week_key() -> str:
    """The current ISO year-week, e.g. "2026-W32".

    We use it to re-roll handles weekly: same phone, same week → same handle.
    Next week → a NEW handle. Fresh anonymity, zero state.
    """
    # time.strftime %V = ISO week number, %G = ISO year.
    return time.strftime("%G-W%V")


def make_handle(device_id: str) -> tuple[str, str]:
    """Generate (or regenerate) an anonymous handle for a device.

    Returns: (handle, week_key)
    The handle is deterministic within a week: hash the device_id with the
    week key, then map the hash to one adjective + a 3-digit number.
    """
    week = current_week_key()

    # hashlib.sha256 gives us a stable 64-char hex string for any input.
    digest = hashlib.sha256(f"{week}:{device_id}".encode()).hexdigest()

    # First 8 hex chars → an integer → pick an adjective by index.
    adj_index = int(digest[:8], 16) % len(ADJECTIVES)
    # Next 8 hex chars → a number 0..999.
    number = int(digest[8:16], 16) % 1000

    return f"{ADJECTIVES[adj_index]}-{number:03d}", week


def ensure_handle(db, device) -> None:
    """Give the device a current handle (re-roll if the week changed).

    Call this on every login/ping so the handle updates automatically
    when the calendar flips to a new week.
    """
    from .models import Device  # local import to avoid circular imports

    week = current_week_key()
    if device.handle_week != week:
        device.handle, device.handle_week = make_handle(device.device_id)


# ---------------------------------------------------------------------------
# Signed tokens (proof that a request came from a known device)
# ---------------------------------------------------------------------------

def sign_token(payload: dict) -> str:
    """Sign a payload so it cannot be tampered with.

    token = base64(payload_json) + "." + base64(HMAC-SHA256(payload, secret))
    Anyone can read the payload (it's just base64) but no one can EDIT it
    without the secret — and the secret lives only on the server.
    """

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    body = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    signature = hmac.new(
        config.TOKEN_SECRET.encode(), payload_json.encode(), hashlib.sha256
    ).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{body}.{sig}"


def verify_token(token: str) -> dict | None:
    """Validate a token. Returns the payload dict, or None if invalid/expired."""

    try:
        body, sig = token.split(".")
        # Re-decode the body to the exact JSON string we signed.
        padding = "=" * (-len(body) % 4)
        payload_json = base64.urlsafe_b64decode(body + padding).decode()

        # Recompute the signature; if it matches, the token was never edited.
        expected = hmac.new(
            config.TOKEN_SECRET.encode(), payload_json.encode(), hashlib.sha256
        ).digest()
        given_padding = "=" * (-len(sig) % 4)
        given = base64.urlsafe_b64decode(sig + given_padding)

        if not hmac.compare_digest(expected, given):
            return None  # tampered

        payload = json.loads(payload_json)

        # Expired? (checked with the raw epoch to keep it simple)
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None  # malformed in any way → treat as invalid


def issue_token(device_id: str) -> str:
    """Create a fresh token for a device."""
    payload = {
        "device_id": device_id,
        "exp": int(time.time()) + config.TOKEN_LIFETIME_SECONDS,
        # A random nonce so two tokens for the same device still differ.
        "nonce": secrets.token_hex(8),
    }
    return sign_token(payload)
