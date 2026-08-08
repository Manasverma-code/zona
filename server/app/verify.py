"""
verify.py — The spoof-proofing layer. "Are you REALLY on campus?"

A single GPS point can be faked by an app. So we demand a bundle of evidence
on every write request (post, react, report):

    1. GPS position ............ is it inside the campus polygon?
    2. Fix freshness ........... was it measured just now (not 3 days ago)?
    3. Accuracy ................ is the phone confident in its position?
    4. WiFi BSSID fingerprints . hashes of the Wi-Fi networks the phone can
                               actually SEE. These networks exist only on
                               campus, and you can't see them from outside.
                               This is the "you are physically here" proof.

Rule: a request that fails any check gets 403 — same "outside the zone"
message, whether you're genuinely off-campus or just faking it.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException

from . import config
from .geofence import is_inside_campus

# The exact response body the app shows on its blank screen.
OUTSIDE_ZONE_RESPONSE = {
    "detail": {
        "code": "outside_zone",
        "message": "You're outside the zone. Nothing to see.",
    }
}


@dataclass
class LocationEvidence:
    """Everything the phone told us about where it is."""
    lat: float
    lon: float
    fix_age_seconds: float | None   # None if the phone didn't send a timestamp
    accuracy_meters: float | None   # None if the phone didn't send accuracy
    bssid_hashes: list[str]         # hashed Wi-Fi fingerprints (may be empty)


def parse_location(
    x_zona_lat: str | None,
    x_zona_lon: str | None,
    x_zona_fix_epoch: str | None,
    x_zona_accuracy_m: str | None,
    x_zona_bssids: str | None,
) -> LocationEvidence:
    """Turn the raw headers into a typed LocationEvidence.

    Headers are always strings, so we parse + sanity-check them here.
    Anything weird just becomes None — the gate checks catch it later.
    """

    def _to_float(value: str | None) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    lat = _to_float(x_zona_lat)
    lon = _to_float(x_zona_lon)
    fix_epoch = _to_float(x_zona_fix_epoch)
    accuracy = _to_float(x_zona_accuracy_m)

    # BSSIDs arrive comma-separated. Keep only plausible hashes (64 hex chars)
    # so garbage headers can't sneak through.
    bssids: list[str] = []
    if x_zona_bssids:
        for raw in x_zona_bssids.split(","):
            candidate = raw.strip().lower()
            if len(candidate) == 64 and all(c in "0123456789abcdef" for c in candidate):
                bssids.append(candidate)

    return LocationEvidence(
        lat=lat if lat is not None and -90 <= lat <= 90 else None,
        lon=lon if lon is not None and -180 <= lon <= 180 else None,
        fix_age_seconds=None if fix_epoch is None else time.time() - fix_epoch,
        accuracy_meters=accuracy,
        bssid_hashes=bssids,
    )


def require_inside(
    lat: float | None,
    lon: float | None,
    fix_age_seconds: float | None,
    accuracy_meters: float | None,
    bssid_hashes: list[str],
    require_bssid: bool,
) -> None:
    """THE gate. Raise 403 if the evidence doesn't prove "inside campus".

    Each check fails with the SAME polite message — we never tell a faker
    which check tripped, so they can't learn what to fake next.
    """

    reason = None

    if not config.GEOFENCE_ENABLED:
        reason = None  # gate off → everyone is "inside"
    elif lat is None or lon is None:
        reason = "no_position"
    elif fix_age_seconds is None:
        reason = "no_fix_timestamp"
    elif fix_age_seconds > config.MAX_FIX_AGE_SECONDS:
        reason = "fix_too_old"  # replaying an old "inside" fix
    elif accuracy_meters is None:
        reason = "no_accuracy"
    elif accuracy_meters > config.MAX_GPS_ACCURACY_METERS:
        reason = "accuracy_too_low"  # phone itself isn't sure where it is
    elif not is_inside_campus(lat, lon):
        reason = "outside_polygon"
    elif require_bssid and not bssid_hashes:
        reason = "no_bssid_proof"  # can't see campus Wi-Fi → not really there

    if reason is not None:
        raise HTTPException(status_code=403, detail={
            "code": "outside_zone",
            "message": "You're outside the zone. Nothing to see.",
        })


def hash_bssid(bssid: str) -> str:
    """Hash a WiFi MAC so the server never stores raw network addresses.

    The hash is enough to compare ("same Wi-Fi as last time") but not
    enough to reverse into the real address.
    """
    return hashlib.sha256(bssid.strip().upper().encode()).hexdigest()
