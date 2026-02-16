"""Lane parsing and city coordinate resolution for geography analytics.

Provides ~50 major US freight cities with lat/lng coordinates, and functions
to normalize free-form city names and parse lane strings like
"Chicago, IL -> Dallas, TX" into structured (origin, destination) tuples.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# City coordinates: ~50 major US freight hubs
# ---------------------------------------------------------------------------

CITY_COORDS: dict[str, tuple[float, float]] = {
    "Atlanta, GA": (33.749, -84.388),
    "Austin, TX": (30.267, -97.743),
    "Baltimore, MD": (39.290, -76.612),
    "Birmingham, AL": (33.521, -86.802),
    "Boise, ID": (43.615, -116.202),
    "Boston, MA": (42.360, -71.059),
    "Buffalo, NY": (42.887, -78.879),
    "Charlotte, NC": (35.227, -80.843),
    "Chicago, IL": (41.878, -87.630),
    "Cincinnati, OH": (39.103, -84.512),
    "Cleveland, OH": (41.500, -81.694),
    "Columbus, OH": (39.961, -82.999),
    "Dallas, TX": (32.777, -96.797),
    "Denver, CO": (39.739, -104.990),
    "Des Moines, IA": (41.586, -93.625),
    "Detroit, MI": (42.331, -83.046),
    "El Paso, TX": (31.762, -106.485),
    "Fort Worth, TX": (32.755, -97.331),
    "Fresno, CA": (36.737, -119.787),
    "Houston, TX": (29.760, -95.370),
    "Indianapolis, IN": (39.768, -86.158),
    "Jacksonville, FL": (30.332, -81.656),
    "Kansas City, MO": (39.100, -94.578),
    "Laredo, TX": (27.506, -99.507),
    "Las Vegas, NV": (36.169, -115.140),
    "Little Rock, AR": (34.746, -92.290),
    "Los Angeles, CA": (34.052, -118.244),
    "Louisville, KY": (38.253, -85.759),
    "Memphis, TN": (35.150, -90.049),
    "Miami, FL": (25.762, -80.192),
    "Milwaukee, WI": (43.039, -87.907),
    "Minneapolis, MN": (44.978, -93.265),
    "Nashville, TN": (36.163, -86.781),
    "New Orleans, LA": (29.951, -90.072),
    "New York, NY": (40.713, -74.006),
    "Newark, NJ": (40.736, -74.172),
    "Norfolk, VA": (36.851, -76.286),
    "Oklahoma City, OK": (35.468, -97.522),
    "Omaha, NE": (41.257, -95.934),
    "Orlando, FL": (28.538, -81.379),
    "Philadelphia, PA": (39.953, -75.164),
    "Phoenix, AZ": (33.449, -112.074),
    "Pittsburgh, PA": (40.441, -79.996),
    "Portland, OR": (45.505, -122.675),
    "Raleigh, NC": (35.780, -78.639),
    "Richmond, VA": (37.541, -77.436),
    "Sacramento, CA": (38.582, -121.494),
    "Salt Lake City, UT": (40.761, -111.891),
    "San Antonio, TX": (29.425, -98.494),
    "San Diego, CA": (32.716, -117.161),
    "San Francisco, CA": (37.775, -122.419),
    "Savannah, GA": (32.081, -81.091),
    "Seattle, WA": (47.606, -122.332),
    "St. Louis, MO": (38.627, -90.199),
    "Tampa, FL": (27.951, -82.458),
    "Tucson, AZ": (32.222, -110.975),
    "Tulsa, OK": (36.154, -95.993),
}


# ---------------------------------------------------------------------------
# Reverse lookup index for fuzzy city resolution
# ---------------------------------------------------------------------------

def _build_city_lookup() -> dict[str, str]:
    """Build a normalised lookup: multiple forms -> canonical "City, ST"."""
    lookup: dict[str, str] = {}
    for canonical in CITY_COORDS:
        city, state = canonical.split(", ")
        low_city = city.lower()
        low_state = state.lower()
        # "chicago, il", "chicago il", "chicago"
        lookup[f"{low_city}, {low_state}"] = canonical
        lookup[f"{low_city} {low_state}"] = canonical
        lookup[low_city] = canonical
    return lookup


_CITY_LOOKUP: dict[str, str] = _build_city_lookup()


def resolve_city(text: str) -> Optional[str]:
    """Fuzzy-match a free-form city string to canonical "City, ST".

    Tries exact normalised match against several forms:
      - "Chicago, IL" / "chicago, il"
      - "Chicago IL" / "chicago il"
      - "Chicago" / "chicago"

    Returns None if no match found.
    """
    if not text:
        return None
    cleaned = text.strip().lower()
    if not cleaned:
        return None
    return _CITY_LOOKUP.get(cleaned)


# ---------------------------------------------------------------------------
# Lane parser
# ---------------------------------------------------------------------------

# Separators tried in order; first match wins.
_LANE_SEPARATORS = [
    " \u2192 ",    # " → "  (unicode arrow)
    " -> ",        # " -> " (ASCII arrow)
    " - ",         # " - "  (dash)
]

# Regex for case-insensitive " to " separator (word boundary aware)
_TO_PATTERN = re.compile(r"\s+to\s+", re.IGNORECASE)


def parse_lane(raw: str) -> Optional[tuple[str, str]]:
    """Split a free-form lane string into (origin, destination) canonical names.

    Supported separators (tried in order):
      - " → "  (unicode arrow)
      - " -> " (ASCII arrow)
      - " - "  (dash)
      - " to " (case-insensitive)

    Both sides are resolved via resolve_city(). Returns None if the lane
    can't be parsed or either side doesn't resolve to a known city.
    """
    if not raw:
        return None

    origin_raw = None
    dest_raw = None

    for sep in _LANE_SEPARATORS:
        if sep in raw:
            parts = raw.split(sep, 1)
            origin_raw, dest_raw = parts[0], parts[1]
            break

    if origin_raw is None:
        # Try " to " separator
        match = _TO_PATTERN.search(raw)
        if match:
            origin_raw = raw[:match.start()]
            dest_raw = raw[match.end():]

    if origin_raw is None or dest_raw is None:
        return None

    origin = resolve_city(origin_raw)
    dest = resolve_city(dest_raw)

    if not origin or not dest:
        return None

    return (origin, dest)
