from typing import Optional

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_201_CREATED

from app.analytics.models import (
    AIQualityResponse,
    CallRecord,
    CarriersResponse,
    GeographyResponse,
    IngestResponse,
    NegotiationsResponse,
    OperationsResponse,
    SummaryResponse,
)
from app.analytics.service import (
    get_ai_quality,
    get_carriers,
    get_geography,
    get_negotiations,
    get_operations,
    get_summary,
    ingest_call_record,
)
from app.dependencies import verify_api_key

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/calls", response_model=IngestResponse, status_code=HTTP_201_CREATED)
async def ingest(record: CallRecord):
    status = await ingest_call_record(record.model_dump())
    return IngestResponse(call_id=record.system.call_id, status=status)


@router.get("/summary", response_model=SummaryResponse)
async def summary(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_summary(date_from, date_to)


@router.get("/operations", response_model=OperationsResponse)
async def operations(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_operations(date_from, date_to)


@router.get("/negotiations", response_model=NegotiationsResponse)
async def negotiations(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_negotiations(date_from, date_to)


# DEPRECATED — AI quality metrics are no longer shown in the dashboard.
@router.get("/ai-quality", response_model=AIQualityResponse)
async def ai_quality(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_ai_quality(date_from, date_to)


@router.get("/carriers", response_model=CarriersResponse)
async def carriers(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_carriers(date_from, date_to)


@router.get("/geography", response_model=GeographyResponse)
async def geography(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_geography(date_from, date_to)
