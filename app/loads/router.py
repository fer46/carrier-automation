from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import verify_api_key
from app.loads.models import Load, LoadResponse
from app.loads.service import get_load_by_id, search_loads

# All routes under /api/loads require a valid API key in the X-API-Key header.
# The verify_api_key dependency runs before every endpoint in this router.
router = APIRouter(prefix="/api/loads", tags=["loads"], dependencies=[Depends(verify_api_key)])


@router.get("/search", response_model=LoadResponse)
async def search(
    # All search params are optional — omitting all returns every load in the DB.
    # These come from the voice AI after extracting carrier preferences from the call.
    origin: Optional[str] = Query(None),  # e.g. "Denver" — where the carrier is now
    destination: Optional[str] = Query(None),  # e.g. "Chicago" — where they want to go
    equipment_type: Optional[str] = Query(None),  # e.g. "Dry Van" — what truck they have
    min_rate: Optional[float] = Query(None),  # Minimum acceptable rate in USD
    max_rate: Optional[float] = Query(None),  # Maximum acceptable rate in USD
    max_weight: Optional[float] = Query(None),  # Carrier's truck weight limit in lbs
    pickup_date: Optional[str] = Query(None),  # Earliest pickup date, e.g. "2026-02-15"
):
    """Search for available loads matching carrier preferences.

    The voice AI calls this after asking the carrier about their location,
    desired destination, and equipment type. Returns all matching loads
    so the AI can offer the best options to the carrier.
    """
    loads = await search_loads(
        origin=origin,
        destination=destination,
        equipment_type=equipment_type,
        min_rate=min_rate,
        max_rate=max_rate,
        max_weight=max_weight,
        pickup_date=pickup_date,
    )
    return LoadResponse(loads=loads, total=len(loads))


@router.get("/{load_id}", response_model=Load)
async def get_load(load_id: str):
    """Retrieve a specific load by its ID.

    Used when the voice AI or a client already knows which load they want
    to inspect (e.g. during negotiation or booking).
    """
    load = await get_load_by_id(load_id)
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    return load
