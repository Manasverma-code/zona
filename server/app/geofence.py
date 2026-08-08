"""
geofence.py — THE GATE. Everything about "are you inside the campus?"

How it works:
    1. The campus is stored as a POLYGON (a list of [lat, lon] corners).
       A polygon is better than a circle — it can follow the real campus shape.
    2. The phone sends its GPS position with every request.
    3. We ask: is this point inside the polygon? (ray-casting algorithm below)
    4. If yes → the request is allowed. If no → 403, "You're outside the zone."

If you set ZONA_CAMPUS_POLYGON in config, that polygon is used.
Otherwise we auto-build a rectangle from the center + half-size config.
"""

from __future__ import annotations

from . import config


# ---------------------------------------------------------------------------
# Building the campus polygon
# ---------------------------------------------------------------------------

def _build_campus_polygon() -> list[list[float]]:
    """Return the campus polygon as [[lat, lon], [lat, lon], ...].

    Two ways to define it (see config.py for the env vars):
      * rectangle from center + half sizes (the easy default)
      * a real polygon pasted from Google Maps (more accurate)
    """

    # Prefer the explicit polygon if someone set it.
    if config.CAMPUS_POLYGON_RAW:
        corners: list[list[float]] = []
        for pair in config.CAMPUS_POLYGON_RAW.split("|"):
            lat, lon = pair.split(",")
            corners.append([float(lat.strip()), float(lon.strip())])
        # Make sure the polygon is closed (last corner = first corner).
        if corners and corners[0] != corners[-1]:
            corners.append(corners[0])
        return corners

    # Otherwise: build a rectangle around the campus center.
    # Convert "meters" to "degrees" (1 deg lat ≈ 111,320 m, 1 deg lon shrinks with cos(lat)).
    lat = config.CAMPUS_CENTER_LAT
    lon = config.CAMPUS_CENTER_LON
    d_lat = config.CAMPUS_HALF_HEIGHT_METERS / 111_320.0
    d_lon = config.CAMPUS_HALF_WIDTH_METERS / (111_320.0 * 0.9986)  # 0.9986 ≈ cos(28.5°)

    # Four corners of the rectangle, then close it.
    return [
        [lat - d_lat, lon - d_lon],
        [lat - d_lat, lon + d_lon],
        [lat + d_lat, lon + d_lon],
        [lat + d_lat, lon - d_lon],
        [lat - d_lat, lon - d_lon],  # same as first corner → closes the shape
    ]


# The one polygon used for the whole app lifetime. Built once at import.
CAMPUS_POLYGON: list[list[float]] = _build_campus_polygon()


# ---------------------------------------------------------------------------
# The point-in-polygon test (ray casting)
# ---------------------------------------------------------------------------

def point_inside_polygon(lat: float, lon: float, polygon: list[list[float]]) -> bool:
    """Classic ray-casting algorithm.

    Idea: draw an imaginary horizontal line from our point to the right edge of
    the map. Count how many times it crosses the polygon's edges.
        - odd number of crossings  → the point is INSIDE
        - even number of crossings → the point is OUTSIDE

    (This is how computer graphics decides which pixels are inside a shape.)
    No libraries needed — pure math, so you can read every line.
    """

    # "x" here means longitude (left/right), "y" means latitude (up/down).
    x, y = lon, lat

    # The polygon is a list of corners, so edges go from corner[i] to corner[i+1].
    # Corners are stored as [lat, lon] — swap to (x=lon, y=lat) for the math.
    inside = False
    for i in range(len(polygon) - 1):
        lat1, lon1 = polygon[i]      # start of this edge
        lat2, lon2 = polygon[i + 1]  # end of this edge
        x1, y1 = lon1, lat1
        x2, y2 = lon2, lat2

        # We only care about edges that STRADDLE our point vertically,
        # i.e. one end of the edge is above our point and the other is below.
        crosses_band = (y1 > y) != (y2 > y)

        if crosses_band:
            # Where exactly does the edge cross our horizontal line?
            # Linear interpolation: how far along the edge is that crossing?
            t = (y - y1) / (y2 - y1)   # 0→start of edge, 1→end of edge
            cross_x = x1 + t * (x2 - x1)

            # If the crossing is to our RIGHT, flip the inside/outside state.
            if cross_x > x:
                inside = not inside

    return inside


# ---------------------------------------------------------------------------
# The public gate check
# ---------------------------------------------------------------------------

def is_inside_campus(lat: float, lon: float) -> bool:
    """Convenience wrapper: is this GPS position inside the campus polygon?"""
    return point_inside_polygon(lat, lon, CAMPUS_POLYGON)
