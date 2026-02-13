from typing import Optional

from pydantic import BaseModel, Field


class NegotiationRequest(BaseModel):
    """Request body for evaluating a carrier's price offer.

    Sent by the voice AI when a carrier proposes a rate for a load.
    The loadboard_rate is NOT included here — it's looked up from the DB
    so the voice agent can never bypass our pricing limits.
    """

    load_id: str  # The load being negotiated, e.g. "LD-001"
    carrier_offer: float = Field(
        ..., gt=0  # What the carrier wants to be paid in USD; must be positive
    )
    negotiation_round: int = Field(
        ..., ge=1  # Which round of negotiation (1-based, tracked by voice agent)
    )


class NegotiationResponse(BaseModel):
    """Result of evaluating a carrier's negotiation offer.

    Returned to the voice AI so it knows whether the offer is safe to accept.
    Includes the loadboard_rate and margin so the voice agent has context
    for its own negotiation strategy (counter-offers, etc.).

    The API enforces one hard rule: carrier_offer must not exceed loadboard_rate.
    Everything else (when to counter, what price to suggest) is the voice agent's job.
    """

    decision: str  # "accept" (safe to book) or "reject" (over our limit)
    loadboard_rate: float  # Our max rate from the DB — the ceiling for any deal
    margin_percent: float  # How much below our rate the offer is, as a percentage
    reasoning: str  # Human-readable explanation for the voice agent
