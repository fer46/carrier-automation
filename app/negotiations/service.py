from datetime import UTC, datetime
from typing import Optional

from app.database import get_database
from app.loads.models import Load
from app.negotiations.models import NegotiationRequest, NegotiationResponse


async def get_load_for_negotiation(load_id: str) -> Optional[Load]:
    """Fetch a load from the DB and validate it's eligible for negotiation.

    Returns the Load if it exists, or None if not found.
    The router checks the returned load's status and pickup date to decide
    whether negotiation is allowed (available + not expired).
    """
    db = get_database()
    doc = await db.loads.find_one({"load_id": load_id}, {"_id": 0})
    if not doc:
        return None
    return Load(**doc)


def is_load_available(load: Load) -> bool:
    """Check if a load is eligible for negotiation.

    A load must be:
    1. status == "available" (not already booked)
    2. pickup_datetime in the future (not expired)

    Returns False if the load can't be negotiated on.
    """
    if load.status != "available":
        return False

    # Compare pickup time against current UTC time.
    # Both are naive datetimes (no timezone) — consistent with how we store them.
    now = datetime.now(UTC).replace(tzinfo=None)
    if load.pickup_datetime <= now:
        return False

    return True


def evaluate_negotiation(
    load: Load,
    request: NegotiationRequest,
) -> NegotiationResponse:
    """Evaluate whether a carrier's offer is safe to accept.

    This is the safety guardrail: the carrier_offer must not exceed the
    loadboard_rate stored in our DB. The voice agent handles negotiation
    strategy (counters, timing) — we just enforce the hard limit.

    Logic:
    - carrier_offer > loadboard_rate → REJECT (would cost us more than budgeted)
    - carrier_offer <= loadboard_rate → ACCEPT (safe, within our budget)

    The margin_percent tells the voice agent how much room it has:
    - 0% margin means the carrier is asking exactly our rate (acceptable but tight)
    - 20% margin means the carrier is 20% below our rate (great deal)
    - Negative margin means the carrier wants more than our rate (rejected)
    """
    loadboard_rate = load.loadboard_rate

    # margin = how much we save vs. our listed rate, as a percentage.
    # Positive = carrier is below our rate (good). Negative = above (bad).
    margin = (loadboard_rate - request.carrier_offer) / loadboard_rate
    margin_percent = round(margin * 100, 1)

    if request.carrier_offer > loadboard_rate:
        # Hard limit: carrier wants more than our budget. Non-negotiable reject.
        return NegotiationResponse(
            decision="reject",
            loadboard_rate=loadboard_rate,
            margin_percent=margin_percent,
            reasoning=(
                f"Carrier offer ${request.carrier_offer:,.2f} exceeds our rate "
                f"${loadboard_rate:,.2f}. Cannot book above loadboard rate."
            ),
        )

    # Carrier is at or below our rate — safe to accept.
    return NegotiationResponse(
        decision="accept",
        loadboard_rate=loadboard_rate,
        margin_percent=margin_percent,
        reasoning=(
            f"Carrier offer ${request.carrier_offer:,.2f} is within our rate "
            f"${loadboard_rate:,.2f} ({margin_percent}% margin). Safe to book."
        ),
    )
