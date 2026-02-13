from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import verify_api_key
from app.negotiations.models import NegotiationRequest, NegotiationResponse
from app.negotiations.service import (
    evaluate_negotiation,
    get_load_for_negotiation,
    is_load_available,
)

# All routes under /api/negotiations require a valid API key in the X-API-Key header.
router = APIRouter(
    prefix="/api/negotiations",
    tags=["negotiations"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/evaluate", response_model=NegotiationResponse)
async def evaluate(request: NegotiationRequest):
    """Evaluate whether a carrier's price offer is safe to accept.

    Called by the voice AI during a negotiation. Looks up the load's
    real loadboard_rate from the DB and checks the carrier's offer
    against it. Returns the decision plus margin context so the
    voice agent can make informed strategic decisions.

    Flow:
    1. Look up the load → 404 if not found
    2. Check load is available and not expired → 400 if not
    3. Compare carrier_offer against loadboard_rate → accept or reject
    """
    # Step 1: Verify the load exists in our database
    load = await get_load_for_negotiation(request.load_id)
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")

    # Step 2: Verify the load is still available for negotiation
    if not is_load_available(load):
        raise HTTPException(
            status_code=400,
            detail="Load is not available for negotiation (booked or expired)",
        )

    # Step 3: Evaluate the offer against our loadboard rate
    return evaluate_negotiation(load, request)
