from typing import Optional

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_201_CREATED

from app.analytics.models import (
    CallRecord,
    IngestResponse,
)
from app.analytics.service import ingest_call_record
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
