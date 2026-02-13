import re
from datetime import UTC, datetime
from typing import Optional

from app.database import get_database
from app.loads.models import Load


def _score_load(
    load: Load,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
) -> float:
    """Calculate a relevance score for a load based on how well it matches the search.

    Scoring breakdown (0.0 to 1.0 scale):
    - Origin match:      40% of score — how well the load's origin matches the search
    - Destination match:  40% of score — how well the load's destination matches
    - Rate per mile:      20% of score — higher $/mile = better value for the carrier

    Within origin/destination matching, we reward exact city matches over partial matches.
    For example, searching "Dallas" against "Dallas, TX" is an exact city match (full score),
    while "Dal" against "Dallas, TX" is only a partial match (half score).
    """
    score = 0.0

    # --- Origin relevance (0.0 to 0.4) ---
    if origin:
        origin_lower = origin.lower()
        load_origin_lower = load.origin.lower()
        # Extract just the city name (before the comma) for exact matching.
        # "Dallas, TX" → "dallas"
        load_city = load_origin_lower.split(",")[0].strip()
        if origin_lower == load_city:
            # Exact city match: carrier said "Dallas", load is from "Dallas, TX"
            score += 0.4
        elif origin_lower in load_origin_lower:
            # Partial match: carrier said "Dal", load is from "Dallas, TX"
            score += 0.2

    # --- Destination relevance (0.0 to 0.4) ---
    if destination:
        dest_lower = destination.lower()
        load_dest_lower = load.destination.lower()
        load_city = load_dest_lower.split(",")[0].strip()
        if dest_lower == load_city:
            score += 0.4
        elif dest_lower in load_dest_lower:
            score += 0.2

    # --- Rate per mile bonus (0.0 to 0.2) ---
    # Carriers prefer loads that pay more per mile. We normalize by dividing
    # by $4/mile (a high rate in US freight) to keep the score in 0.0-0.2 range.
    # Example: $2800 rate / 1320 miles = $2.12/mile → 2.12/4 * 0.2 = 0.106
    if load.miles > 0:
        rate_per_mile = load.loadboard_rate / load.miles
        # Cap at $4/mile to keep the normalized value between 0 and 1
        normalized_rpm = min(rate_per_mile / 4.0, 1.0)
        score += normalized_rpm * 0.2

    return score


def _escape_regex(value: str) -> str:
    """Escape special regex characters in user input.

    Prevents regex injection — without this, input like ".*" would match
    everything, and patterns like "(a+)+$" could cause catastrophic
    backtracking (ReDoS). After escaping, user input is treated as a
    literal string inside MongoDB's $regex.
    """
    return re.escape(value)


async def search_loads(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    equipment_type: Optional[str] = None,
    min_rate: Optional[float] = None,
    max_rate: Optional[float] = None,
    max_weight: Optional[float] = None,
    pickup_date: Optional[str] = None,
) -> list[Load]:
    """Search for loads in MongoDB using optional filters.

    Builds a query dynamically — only non-null parameters become filters.
    If no parameters are provided, the query is {} which matches all loads.

    How each filter works:
    - origin/destination/equipment_type: Case-insensitive partial match via regex.
      This is critical because carriers say "Denver" on the phone, but the DB
      stores "Denver, CO". The regex lets "Denver" match "Denver, CO".
    - min_rate/max_rate: Numeric range filter on the loadboard_rate field.
      Lets the voice AI filter loads within a carrier's budget.
    - max_weight: Filters out loads heavier than the carrier's truck can handle.
    - pickup_date: Only shows loads with pickup on or after this date.
      Carrier says "I'm available starting Thursday" → filters accordingly.

    Returns up to 100 loads as a safety cap to prevent huge responses.
    """
    db = get_database()

    # Start with base filters that always apply — we never want to show
    # loads that are already booked or have a pickup date in the past.
    # Note: All datetimes are stored as ISO 8601 strings in MongoDB (no timezone).
    # For this PoC we assume all times are in the same timezone (UTC).
    # String comparison works for ISO 8601 because it's lexicographically sortable.
    # datetime.now(UTC) returns timezone-aware UTC time. We strip the timezone
    # info with [:-6] because our DB stores naive ISO strings (no "+00:00" suffix).
    now = datetime.now(UTC).isoformat()[:-6]
    query: dict = {
        # Only show loads that haven't been booked yet
        "status": "available",
        # Only show loads with a future pickup date — a carrier can't pick up
        # a load that was supposed to leave yesterday
        "pickup_datetime": {"$gte": now},
    }

    # --- Text filters: case-insensitive partial matching ---
    # "$regex" does substring matching, "$options": "i" makes it case-insensitive.
    # Example: origin="dallas" matches "Dallas, TX" in the database.
    if origin:
        query["origin"] = {"$regex": _escape_regex(origin), "$options": "i"}
    if destination:
        query["destination"] = {"$regex": _escape_regex(destination), "$options": "i"}
    if equipment_type:
        query["equipment_type"] = {"$regex": _escape_regex(equipment_type), "$options": "i"}

    # --- Rate range filter ---
    # Supports min-only, max-only, or both. Skipped entirely if neither is set.
    # Example: min_rate=1500, max_rate=3000 → loads priced between $1,500-$3,000.
    if min_rate is not None or max_rate is not None:
        rate_filter = {}
        if min_rate is not None:
            rate_filter["$gte"] = min_rate  # Greater than or equal to min
        if max_rate is not None:
            rate_filter["$lte"] = max_rate  # Less than or equal to max
        query["loadboard_rate"] = rate_filter

    # --- Weight filter ---
    # Carriers have a truck weight limit. A dry van rated for 25,000 lbs
    # can't haul a 40,000 lb load. Filters out loads that are too heavy.
    if max_weight is not None:
        query["weight"] = {"$lte": max_weight}

    # --- Pickup date filter ---
    # "I'm available starting Thursday" → only show loads with pickup on or after
    # that date. The base query already filters out past pickups; this narrows it
    # further to the carrier's availability window.
    # Expected format: "2026-02-15" or "2026-02-15T08:00:00" (ISO 8601).
    if pickup_date is not None:
        # Override the base pickup_datetime filter with the carrier's date,
        # since it's guaranteed to be >= now (carrier is available in the future).
        query["pickup_datetime"] = {"$gte": pickup_date}

    # Execute the query:
    # - {"_id": 0} excludes MongoDB's internal _id field from results
    # - length=100 caps results to prevent returning thousands of documents
    cursor = db.loads.find(query, {"_id": 0})
    results = await cursor.to_list(length=100)

    # Convert raw MongoDB dicts into validated Pydantic Load models
    loads = [Load(**doc) for doc in results]

    # --- Relevance ranking ---
    # Sort loads by how well they match the carrier's search criteria.
    # Best matches (highest score) come first so the voice AI can offer
    # the top result immediately. Only scores when origin or destination
    # is provided — otherwise all loads are equally relevant.
    if origin or destination:
        loads.sort(
            key=lambda load: _score_load(load, origin, destination),
            reverse=True,  # Highest score first
        )

    return loads


async def get_load_by_id(load_id: str) -> Optional[Load]:
    """Fetch a single load by its load_id.

    Returns None if no load exists with that ID, which the router
    converts into a 404 HTTP response.
    """
    db = get_database()

    # find_one returns a single document or None if not found.
    # {"_id": 0} excludes the MongoDB internal _id field.
    doc = await db.loads.find_one({"load_id": load_id}, {"_id": 0})
    if not doc:
        return None
    return Load(**doc)
