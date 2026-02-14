from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BeforeValidator

from app.dependencies import verify_api_key
from app.loads.models import Load, LoadResponse
from app.loads.service import get_load_by_id, search_loads


def _empty_to_none(v):
    """Coerce empty strings to None so Pydantic doesn't choke on \"\" for floats."""
    if v == "":
        return None
    return v


NullableFloat = Annotated[Optional[float], BeforeValidator(_empty_to_none)]
NullableStr = Annotated[Optional[str], BeforeValidator(_empty_to_none)]

# All routes under /api/loads require a valid API key in the X-API-Key header.
# The verify_api_key dependency runs before every endpoint in this router.
router = APIRouter(prefix="/api/loads", tags=["loads"], dependencies=[Depends(verify_api_key)])


@router.get("/search", response_model=LoadResponse)
async def search(
    # All search params are optional — omitting all returns every load in the DB.
    # These come from the voice AI after extracting carrier preferences from the call.
    # Numeric params are typed as str because the voice AI may send "" for empty values,
    # which FastAPI can't parse as float. We coerce "" → None below.
    validation_check: str = Query(...),  # Must be "VALID" — guardrail to ensure carrier is validated
    origin: Optional[str] = Query(None),  # e.g. "Denver" — where the carrier is now
    destination: Optional[str] = Query(None),  # e.g. "Chicago" — where they want to go
    equipment_type: Optional[str] = Query(None),  # e.g. "Dry Van" — what truck they have
    min_rate: Optional[str] = Query(None),  # Minimum acceptable rate in USD
    max_rate: Optional[str] = Query(None),  # Maximum acceptable rate in USD
    max_weight: Optional[str] = Query(None),  # Carrier's truck weight limit in lbs
    pickup_date: Optional[str] = Query(None),  # Earliest pickup date, e.g. "2026-02-15"
):
    """Search for available loads matching carrier preferences.

    The voice AI calls this after asking the carrier about their location,
    desired destination, and equipment type. Returns all matching loads
    so the AI can offer the best options to the carrier.
    """
    if validation_check != "VALID":
        raise HTTPException(status_code=403, detail="Carrier validation failed")

    # Coerce empty strings to None; parse numeric strings to float.
    # The voice AI sends "" when the carrier doesn't specify a value.
    loads = await search_loads(
        origin=origin or None,
        destination=destination or None,
        equipment_type=equipment_type or None,
        min_rate=float(min_rate) if min_rate else None,
        max_rate=float(max_rate) if max_rate else None,
        max_weight=float(max_weight) if max_weight else None,
        pickup_date=pickup_date or None,
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
