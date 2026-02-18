import re
from datetime import UTC, datetime
from typing import Optional

from app.database import get_database
from app.loads.models import Load


async def _get_call_pressure(load_ids: list[str]) -> dict[str, dict]:
    """Batch query: get rate-rejection stats per load from call history.

    Returns {load_id: {"total_calls": N, "rate_rejections": N}} for loads
    that have at least one call record.
    """
    if not load_ids:
        return {}
    db = get_database()
    pipeline: list[dict] = [
        {"$match": {"load_data.load_id_discussed": {"$in": load_ids}}},
        {
            "$group": {
                "_id": "$load_data.load_id_discussed",
                "total_calls": {"$sum": 1},
                "rate_rejections": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$eq": ["$transcript_extraction.call_outcome", "rejected"]},
                                    {
                                        "$eq": [
                                            "$transcript_extraction.rejection_reason",
                                            "Rate too low",
                                        ]
                                    },
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        },
    ]
    results = await db.call_records.aggregate(pipeline).to_list(length=None)
    return {r["_id"]: r for r in results}


def _apply_pricing(load: Load, total_calls: int = 0, rate_rejections: int = 0) -> Load:
    """Dynamic pricing based on pickup urgency and carrier rejection history.

    Mimics a freight broker's decision-making:
    - Urgent pickups or high rate-rejection counts → raise target toward loadboard rate
    - Cold loads (distant pickup, few calls) → tighten cap toward loadboard rate

    Pressure formula (0.0 = cold, 1.0 = hot):
    - Urgency: linear 0→1 over 72 hours until pickup
    - Rejection pressure: linear 0→1 over 5 "Rate too low" rejections
    - Combined: max(urgency, rejection_pressure)

    Rate multipliers:
    - target: 0.95 + pressure × 0.05 → range [0.95, 1.0] (never exceeds loadboard)
    - cap:    1.0 + min(pressure × 0.06, 0.05) → range [1.0, 1.05]
    """
    # Naive UTC comparison — stored datetimes are naive ISO strings
    now = datetime.now(UTC).replace(tzinfo=None)
    hours_to_pickup = max((load.pickup_datetime - now).total_seconds() / 3600, 0)

    urgency = max(1.0 - hours_to_pickup / 72, 0.0)
    rejection_pressure = min(rate_rejections / 5, 1.0)
    pressure = max(urgency, rejection_pressure)

    target_mult = 0.95 + pressure * 0.05
    cap_mult = 1.0 + min(pressure * 0.06, 0.05)

    load.target_carrier_rate = round(load.loadboard_rate * target_mult, 2)
    load.cap_carrier_rate = round(load.loadboard_rate * cap_mult, 2)
    return load


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
        origin_lower = origin.strip().lower()
        load_origin_lower = load.origin.lower()
        load_city = load_origin_lower.split(",")[0].strip()
        if _is_state_abbreviation(origin):
            # State abbreviation: extract state from "City, ST" and compare
            parts = load_origin_lower.split(",")
            if len(parts) >= 2 and origin_lower == parts[-1].strip():
                score += 0.4
        elif origin_lower == load_city:
            # Exact city match: "Dallas" → "Dallas, TX"
            score += 0.4
        elif origin_lower in load_origin_lower:
            # Partial match: "Dal" → "Dallas, TX"
            score += 0.2

    # --- Destination relevance (0.0 to 0.4) ---
    if destination:
        dest_lower = destination.strip().lower()
        load_dest_lower = load.destination.lower()
        load_city = load_dest_lower.split(",")[0].strip()
        if _is_state_abbreviation(destination):
            parts = load_dest_lower.split(",")
            if len(parts) >= 2 and dest_lower == parts[-1].strip():
                score += 0.4
        elif dest_lower == load_city:
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


def _is_state_abbreviation(value: str) -> bool:
    """Check if the input looks like a US state abbreviation (exactly 2 letters)."""
    stripped = value.strip()
    return len(stripped) == 2 and stripped.isalpha()


def _build_location_regex(value: str) -> str:
    """Build a MongoDB regex for origin/destination matching.

    State abbreviation (2 letters like "CA") → anchored to the state portion
    after the comma: ',\\s*CA$'. Prevents "CA" from matching "Chicago".

    Everything else (city names, "City, ST" combos) → escaped substring match,
    same as the original behavior.
    """
    stripped = value.strip()
    if _is_state_abbreviation(stripped):
        return r",\s*" + re.escape(stripped) + "$"
    return re.escape(stripped)


async def search_loads(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    equipment_type: Optional[str] = None,
    min_rate: Optional[float] = None,
    max_rate: Optional[float] = None,
    max_weight: Optional[float] = None,
    pickup_date: Optional[str] = None,
    delivery_date: Optional[str] = None,
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
    - delivery_date: Only shows loads with delivery on or before this date.
      Carrier says "I need to deliver by Friday" → filters accordingly.

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

    # --- Text filters: case-insensitive matching ---
    # City names use substring matching ("dallas" → "Dallas, TX").
    # 2-letter state abbreviations anchor to the state portion after the comma
    # ("CA" → ",\s*CA$") so "CA" won't match "Chicago, IL".
    if origin:
        query["origin"] = {"$regex": _build_location_regex(origin), "$options": "i"}
    if destination:
        query["destination"] = {"$regex": _build_location_regex(destination), "$options": "i"}
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

    # --- Delivery date filter ---
    # "I need to deliver by Friday" → only show loads with delivery on or before
    # that date. Ensures the carrier can meet their scheduling constraints.
    # When the voice AI sends a date-only string like "2026-02-17", we append
    # "T23:59:59" so that loads delivering any time on that day are included.
    # Without this, "2026-02-17T14:00:00" <= "2026-02-17" is FALSE
    # lexicographically because 'T' > end-of-string.
    if delivery_date is not None:
        if "T" not in delivery_date:
            delivery_date += "T23:59:59"
        query["delivery_datetime"] = {"$lte": delivery_date}

    # Execute the query:
    # - {"_id": 0} excludes MongoDB's internal _id field from results
    # - length=100 caps results to prevent returning thousands of documents
    cursor = db.loads.find(query, {"_id": 0})
    results = await cursor.to_list(length=100)

    # Convert raw MongoDB dicts into validated Pydantic Load models
    # and apply dynamic pricing based on call pressure
    loads = [Load(**doc) for doc in results]
    pressure = await _get_call_pressure([ld.load_id for ld in loads])
    for load in loads:
        stats = pressure.get(load.load_id, {})
        _apply_pricing(
            load,
            total_calls=stats.get("total_calls", 0),
            rate_rejections=stats.get("rate_rejections", 0),
        )

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
    load = Load(**doc)
    pressure = await _get_call_pressure([load_id])
    stats = pressure.get(load_id, {})
    return _apply_pricing(
        load,
        total_calls=stats.get("total_calls", 0),
        rate_rejections=stats.get("rate_rejections", 0),
    )
