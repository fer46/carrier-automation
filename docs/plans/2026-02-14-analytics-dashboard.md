# Analytics Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-pipeline analytics system that ingests call data via POST, stores in MongoDB, serves aggregated metrics via API, and renders a React dashboard served by FastAPI.

**Architecture:** New `app/analytics/` domain following existing patterns (models.py, service.py, router.py). React + Vite + Tailwind + Recharts frontend in `dashboard/` directory, built to static files and served by FastAPI at `/dashboard`. All aggregations computed server-side via MongoDB pipelines.

**Tech Stack:** FastAPI, MongoDB (Motor async), Pydantic, React 18, Vite, Tailwind CSS, Recharts

---

## Task 1: Backend — Pydantic Models

**Files:**
- Create: `app/analytics/__init__.py`
- Create: `app/analytics/models.py`

**Step 1: Create the analytics module**

```bash
mkdir -p app/analytics
touch app/analytics/__init__.py
```

**Step 2: Write all Pydantic models**

Create `app/analytics/models.py` with these models:

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Ingestion Models (nested, mirrors webhook JSON) ---

class SystemData(BaseModel):
    call_id: str
    call_startedat: datetime
    call_duration: int

class FMCSAData(BaseModel):
    carrier_mc_number: int
    carrier_name: str
    carrier_validation_result: str
    retrieval_date: str

class LoadData(BaseModel):
    load_id_discussed: str
    alternate_loads_presented: int

class Outcome(BaseModel):
    call_outcome: str
    rejection_reason: Optional[str] = None

class Sentiment(BaseModel):
    call_sentiment: Optional[str] = None
    sentiment_progression: Optional[str] = None
    engagement_level: Optional[str] = None
    carrier_expressed_interest_future: Optional[bool] = None

class Performance(BaseModel):
    agent_followed_protocol: Optional[bool] = None
    protocol_violations: list[str] = Field(default_factory=list)
    agent_tone_quality: Optional[str] = None

class Conversation(BaseModel):
    ai_interruptions_count: Optional[int] = None
    transcription_errors_detected: Optional[bool] = None
    carrier_had_to_repeat_info: Optional[bool] = None

class Operational(BaseModel):
    transfer_to_sales_attempted: Optional[bool] = None
    transfer_to_sales_completed: Optional[bool] = None
    transfer_reason: Optional[str] = None
    loads_presented_count: Optional[int] = None

class OptionalData(BaseModel):
    negotiation_strategy_used: Optional[str] = None
    carrier_negotiation_leverage: list[str] = Field(default_factory=list)
    carrier_objections: list[str] = Field(default_factory=list)
    carrier_questions_asked: list[str] = Field(default_factory=list)

class TranscriptExtraction(BaseModel):
    carrier_first_offer: Optional[float] = None
    broker_first_counter: Optional[float] = None
    carrier_second_offer: Optional[float] = None
    broker_second_counter: Optional[float] = None
    carrier_third_offer: Optional[float] = None
    broker_third_counter: Optional[float] = None
    final_agreed_rate: Optional[float] = None
    negotiation_rounds: Optional[int] = None
    outcome: Outcome
    sentiment: Sentiment = Field(default_factory=Sentiment)
    performance: Performance = Field(default_factory=Performance)
    conversation: Conversation = Field(default_factory=Conversation)
    operational: Operational = Field(default_factory=Operational)
    optional: OptionalData = Field(default_factory=OptionalData)

class CallRecord(BaseModel):
    system: SystemData
    fmcsa_data: FMCSAData
    load_data: LoadData
    transcript_extraction: TranscriptExtraction


# --- Response Models ---

class IngestResponse(BaseModel):
    call_id: str
    status: str  # "created" or "updated"

class SummaryResponse(BaseModel):
    total_calls: int
    acceptance_rate: float
    avg_call_duration: float
    avg_negotiation_rounds: float
    avg_margin_percent: float
    ai_protocol_compliance: float
    total_carriers: int

class TimeSeriesPoint(BaseModel):
    date: str
    count: int = 0

class DurationTimeSeriesPoint(BaseModel):
    date: str
    avg_duration: float = 0.0

class ReasonCount(BaseModel):
    reason: str
    count: int

class OperationsResponse(BaseModel):
    calls_over_time: list[TimeSeriesPoint]
    outcome_distribution: dict[str, int]
    avg_duration_over_time: list[DurationTimeSeriesPoint]
    rejection_reasons: list[ReasonCount]
    transfer_rate: float

class RateProgressionPoint(BaseModel):
    round: str
    avg_rate: float

class MarginBucket(BaseModel):
    range: str
    count: int

class StrategyRow(BaseModel):
    strategy: str
    acceptance_rate: float
    avg_rounds: float
    count: int

class NegotiationsResponse(BaseModel):
    avg_first_offer: float
    avg_final_rate: float
    avg_rounds: float
    rate_progression: list[RateProgressionPoint]
    margin_distribution: list[MarginBucket]
    strategy_effectiveness: list[StrategyRow]

class ViolationCount(BaseModel):
    violation: str
    count: int

class InterruptionTimeSeriesPoint(BaseModel):
    date: str
    avg: float

class AIQualityResponse(BaseModel):
    protocol_compliance_rate: float
    common_violations: list[ViolationCount]
    avg_interruptions: float
    interruptions_over_time: list[InterruptionTimeSeriesPoint]
    transcription_error_rate: float
    carrier_repeat_rate: float
    tone_quality_distribution: dict[str, int]

class ObjectionCount(BaseModel):
    objection: str
    count: int

class QuestionCount(BaseModel):
    question: str
    count: int

class CarrierLeaderboardRow(BaseModel):
    carrier_name: str
    mc_number: int
    calls: int
    acceptance_rate: float

class CarriersResponse(BaseModel):
    sentiment_distribution: dict[str, int]
    sentiment_over_time: list[dict]
    engagement_levels: dict[str, int]
    future_interest_rate: float
    top_objections: list[ObjectionCount]
    top_questions: list[QuestionCount]
    carrier_leaderboard: list[CarrierLeaderboardRow]
```

**Step 3: Commit**

```bash
git add app/analytics/__init__.py app/analytics/models.py
git commit -m "feat(analytics): add Pydantic models for call record ingestion and response"
```

---

## Task 2: Backend — Service Layer (Ingest)

**Files:**
- Create: `app/analytics/service.py`
- Create: `tests/analytics/__init__.py`
- Create: `tests/analytics/test_router.py`

**Step 1: Write the failing test for ingest**

Create `tests/analytics/__init__.py` (empty) and `tests/analytics/test_router.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.asyncio

API_KEY = settings.API_KEY

SAMPLE_CALL_RECORD = {
    "system": {
        "call_id": "test-call-001",
        "call_startedat": "2024-06-15T10:30:00Z",
        "call_duration": 245
    },
    "fmcsa_data": {
        "carrier_mc_number": 1234,
        "carrier_name": "TYROLER METALS INC",
        "carrier_validation_result": "VALID",
        "retrieval_date": "2026-02-13T19:45:01.867+0000"
    },
    "load_data": {
        "load_id_discussed": "LD-001",
        "alternate_loads_presented": 1
    },
    "transcript_extraction": {
        "carrier_first_offer": 1900.00,
        "broker_first_counter": 2100.00,
        "carrier_second_offer": 2000.00,
        "broker_second_counter": None,
        "carrier_third_offer": None,
        "broker_third_counter": None,
        "final_agreed_rate": 2000.00,
        "negotiation_rounds": 2,
        "outcome": {
            "call_outcome": "accepted",
            "rejection_reason": None
        },
        "sentiment": {
            "call_sentiment": "positive",
            "sentiment_progression": "improving",
            "engagement_level": "high",
            "carrier_expressed_interest_future": True
        },
        "performance": {
            "agent_followed_protocol": True,
            "protocol_violations": [],
            "agent_tone_quality": "professional"
        },
        "conversation": {
            "ai_interruptions_count": 1,
            "transcription_errors_detected": False,
            "carrier_had_to_repeat_info": False
        },
        "operational": {
            "transfer_to_sales_attempted": False,
            "transfer_to_sales_completed": False,
            "transfer_reason": None,
            "loads_presented_count": 2
        },
        "optional": {
            "negotiation_strategy_used": "anchoring_high",
            "carrier_negotiation_leverage": ["fuel_prices_mentioned"],
            "carrier_objections": ["rate_too_low"],
            "carrier_questions_asked": ["Is the rate negotiable?"]
        }
    }
}


def _make_mock_db(find_one_result=None, aggregate_result=None):
    """Create a mock MongoDB with a call_records collection."""
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=find_one_result)
    mock_collection.update_one = AsyncMock()

    if aggregate_result is not None:
        mock_agg_cursor = AsyncMock()
        mock_agg_cursor.to_list = AsyncMock(return_value=aggregate_result)
        mock_collection.aggregate = MagicMock(return_value=mock_agg_cursor)

    mock_db = MagicMock()
    mock_db.call_records = mock_collection
    return mock_db


# --- Ingest Tests ---

@pytest.fixture
async def ingest_client():
    """HTTP client for ingest endpoint (new record)."""
    mock_db = _make_mock_db(find_one_result=None)
    mock_db.call_records.update_one.return_value = MagicMock(upserted_id="new")
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_ingest_call_record_returns_201(ingest_client):
    """POST a valid call record → 201 with call_id and status."""
    response = await ingest_client.post(
        "/api/analytics/calls", json=SAMPLE_CALL_RECORD
    )
    assert response.status_code == 201
    data = response.json()
    assert data["call_id"] == "test-call-001"
    assert data["status"] in ("created", "updated")


async def test_ingest_call_record_requires_api_key():
    """POST without API key → 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/analytics/calls", json=SAMPLE_CALL_RECORD
        )
        assert response.status_code == 422


async def test_ingest_call_record_validates_body(ingest_client):
    """POST with invalid body → 422."""
    response = await ingest_client.post(
        "/api/analytics/calls", json={"bad": "data"}
    )
    assert response.status_code == 422
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
```

Expected: FAIL (module not found / no router registered)

**Step 3: Write the service ingest function**

Create `app/analytics/service.py`:

```python
from typing import Optional

from app.analytics.models import (
    AIQualityResponse,
    CarrierLeaderboardRow,
    CarriersResponse,
    DurationTimeSeriesPoint,
    InterruptionTimeSeriesPoint,
    MarginBucket,
    NegotiationsResponse,
    ObjectionCount,
    OperationsResponse,
    QuestionCount,
    RateProgressionPoint,
    ReasonCount,
    StrategyRow,
    SummaryResponse,
    TimeSeriesPoint,
    ViolationCount,
)
from app.database import get_database


async def ingest_call_record(record: dict) -> str:
    """Upsert a call record into MongoDB. Returns 'created' or 'updated'."""
    db = get_database()
    call_id = record["system"]["call_id"]

    result = await db.call_records.update_one(
        {"system.call_id": call_id},
        {"$set": record},
        upsert=True,
    )

    return "created" if result.upserted_id else "updated"
```

**Step 4: Write the router**

Create `app/analytics/router.py`:

```python
from typing import Optional

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_201_CREATED

from app.analytics.models import (
    AIQualityResponse,
    CallRecord,
    CarriersResponse,
    IngestResponse,
    NegotiationsResponse,
    OperationsResponse,
    SummaryResponse,
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
```

**Step 5: Register router in main.py**

Add to `app/main.py`:

```python
from app.analytics.router import router as analytics_router
# ...
app.include_router(analytics_router)
```

**Step 6: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
```

Expected: 3 PASS

**Step 7: Commit**

```bash
git add app/analytics/ tests/analytics/ app/main.py
git commit -m "feat(analytics): add call record ingestion endpoint with upsert"
```

---

## Task 3: Backend — Summary Aggregation

**Files:**
- Modify: `app/analytics/service.py`
- Modify: `app/analytics/router.py`
- Modify: `tests/analytics/test_router.py`

**Step 1: Write failing tests for summary**

Append to `tests/analytics/test_router.py`:

```python
# --- Summary Tests ---

@pytest.fixture
async def summary_client():
    """HTTP client for summary endpoint with mock aggregation data."""
    mock_db = _make_mock_db(aggregate_result=[{
        "total_calls": 10,
        "accepted": 7,
        "avg_duration": 245.5,
        "avg_rounds": 2.1,
        "avg_margin": 8.4,
        "protocol_compliant": 9,
        "unique_carriers": 5,
    }])
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_summary_returns_200(summary_client):
    """GET summary → 200 with all KPI fields."""
    response = await summary_client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_calls"] == 10
    assert data["acceptance_rate"] == 70.0
    assert data["avg_call_duration"] == 245.5
    assert data["ai_protocol_compliance"] == 90.0
    assert data["total_carriers"] == 5


async def test_summary_empty_db():
    """GET summary with no data → 200 with zeros."""
    mock_db = _make_mock_db(aggregate_result=[])
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            response = await ac.get("/api/analytics/summary")
            assert response.status_code == 200
            data = response.json()
            assert data["total_calls"] == 0
            assert data["acceptance_rate"] == 0.0
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py::test_summary_returns_200 -v
```

**Step 3: Implement get_summary in service.py**

Add to `app/analytics/service.py`:

```python
async def get_summary(date_from: Optional[str] = None, date_to: Optional[str] = None) -> SummaryResponse:
    """Compute top-level KPIs via MongoDB aggregation."""
    db = get_database()
    match_stage = _build_date_match(date_from, date_to)

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": None,
                "total_calls": {"$sum": 1},
                "accepted": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$transcript_extraction.outcome.call_outcome", "accepted"]},
                            1, 0,
                        ]
                    }
                },
                "avg_duration": {"$avg": "$system.call_duration"},
                "avg_rounds": {"$avg": "$transcript_extraction.negotiation_rounds"},
                "avg_margin": {
                    "$avg": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$transcript_extraction.final_agreed_rate", None]},
                                {"$ne": ["$transcript_extraction.carrier_first_offer", None]},
                            ]},
                            {
                                "$multiply": [
                                    {
                                        "$divide": [
                                            {"$subtract": [
                                                "$transcript_extraction.carrier_first_offer",
                                                "$transcript_extraction.final_agreed_rate",
                                            ]},
                                            "$transcript_extraction.carrier_first_offer",
                                        ]
                                    },
                                    100,
                                ]
                            },
                            None,
                        ]
                    }
                },
                "protocol_compliant": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$transcript_extraction.performance.agent_followed_protocol", True]},
                            1, 0,
                        ]
                    }
                },
                "unique_carriers": {"$addToSet": "$fmcsa_data.carrier_mc_number"},
            }
        },
    ]

    cursor = db.call_records.aggregate(pipeline)
    results = await cursor.to_list(length=1)

    if not results:
        return SummaryResponse(
            total_calls=0, acceptance_rate=0.0, avg_call_duration=0.0,
            avg_negotiation_rounds=0.0, avg_margin_percent=0.0,
            ai_protocol_compliance=0.0, total_carriers=0,
        )

    r = results[0]
    total = r["total_calls"]
    return SummaryResponse(
        total_calls=total,
        acceptance_rate=round((r["accepted"] / total) * 100, 1) if total > 0 else 0.0,
        avg_call_duration=round(r["avg_duration"] or 0.0, 1),
        avg_negotiation_rounds=round(r["avg_rounds"] or 0.0, 1),
        avg_margin_percent=round(r["avg_margin"] or 0.0, 1),
        ai_protocol_compliance=round((r["protocol_compliant"] / total) * 100, 1) if total > 0 else 0.0,
        total_carriers=len(r["unique_carriers"]),
    )


def _build_date_match(date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """Build a $match stage for date filtering on system.call_startedat."""
    match: dict = {}
    if date_from or date_to:
        date_filter: dict = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        match["system.call_startedat"] = date_filter
    return match
```

**Step 4: Add summary endpoint to router.py**

Add to `app/analytics/router.py`:

```python
from app.analytics.service import ingest_call_record, get_summary

@router.get("/summary", response_model=SummaryResponse)
async def summary(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_summary(date_from, date_to)
```

**Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
```

Expected: 5 PASS

**Step 6: Commit**

```bash
git add app/analytics/service.py app/analytics/router.py tests/analytics/test_router.py
git commit -m "feat(analytics): add summary KPI aggregation endpoint"
```

---

## Task 4: Backend — Operations Aggregation

**Files:**
- Modify: `app/analytics/service.py`
- Modify: `app/analytics/router.py`
- Modify: `tests/analytics/test_router.py`

**Step 1: Write failing test**

Add to test file:

```python
@pytest.fixture
async def operations_client():
    """HTTP client for operations endpoint."""
    agg_results = [
        {"_id": "2024-06-15", "count": 5, "avg_duration": 200.0},
        {"_id": "2024-06-16", "count": 3, "avg_duration": 300.0},
    ]
    mock_db = _make_mock_db()

    # Operations uses multiple aggregation calls, so mock returns different results per call
    call_count = 0
    original_aggregate = mock_db.call_records.aggregate

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:  # calls_over_time + avg_duration
            mock_cursor.to_list = AsyncMock(return_value=agg_results)
        elif call_count == 2:  # outcome_distribution
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "accepted", "count": 7},
                {"_id": "rejected", "count": 2},
                {"_id": "transferred_to_sales", "count": 1},
            ])
        elif call_count == 3:  # rejection_reasons
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "rate_too_high", "count": 2},
            ])
        elif call_count == 4:  # transfer_rate
            mock_cursor.to_list = AsyncMock(return_value=[
                {"total": 10, "transferred": 1},
            ])
        return mock_cursor

    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)

    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_operations_returns_200(operations_client):
    """GET operations → 200 with all expected fields."""
    response = await operations_client.get("/api/analytics/operations")
    assert response.status_code == 200
    data = response.json()
    assert "calls_over_time" in data
    assert "outcome_distribution" in data
    assert "rejection_reasons" in data
    assert "transfer_rate" in data
```

**Step 2: Implement get_operations in service.py**

```python
async def get_operations(date_from: Optional[str] = None, date_to: Optional[str] = None) -> OperationsResponse:
    """Compute operations metrics via MongoDB aggregation."""
    db = get_database()
    match_stage = _build_date_match(date_from, date_to)

    # 1. Calls over time + avg duration by day
    time_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$system.call_startedat"}},
            "count": {"$sum": 1},
            "avg_duration": {"$avg": "$system.call_duration"},
        }},
        {"$sort": {"_id": 1}},
    ]
    time_cursor = db.call_records.aggregate(time_pipeline)
    time_results = await time_cursor.to_list(length=1000)

    calls_over_time = [TimeSeriesPoint(date=r["_id"], count=r["count"]) for r in time_results]
    avg_duration_over_time = [
        DurationTimeSeriesPoint(date=r["_id"], avg_duration=round(r["avg_duration"], 1))
        for r in time_results
    ]

    # 2. Outcome distribution
    outcome_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$transcript_extraction.outcome.call_outcome", "count": {"$sum": 1}}},
    ]
    outcome_cursor = db.call_records.aggregate(outcome_pipeline)
    outcome_results = await outcome_cursor.to_list(length=100)
    outcome_distribution = {r["_id"]: r["count"] for r in outcome_results if r["_id"]}

    # 3. Rejection reasons
    rejection_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.outcome.rejection_reason": {"$ne": None}}},
        {"$group": {"_id": "$transcript_extraction.outcome.rejection_reason", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    rejection_cursor = db.call_records.aggregate(rejection_pipeline)
    rejection_results = await rejection_cursor.to_list(length=10)
    rejection_reasons = [ReasonCount(reason=r["_id"], count=r["count"]) for r in rejection_results]

    # 4. Transfer rate
    transfer_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "transferred": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.operational.transfer_to_sales_completed", True]},
                    1, 0,
                ]}
            },
        }},
    ]
    transfer_cursor = db.call_records.aggregate(transfer_pipeline)
    transfer_results = await transfer_cursor.to_list(length=1)
    transfer_rate = 0.0
    if transfer_results and transfer_results[0]["total"] > 0:
        transfer_rate = round(
            (transfer_results[0]["transferred"] / transfer_results[0]["total"]) * 100, 1
        )

    return OperationsResponse(
        calls_over_time=calls_over_time,
        outcome_distribution=outcome_distribution,
        avg_duration_over_time=avg_duration_over_time,
        rejection_reasons=rejection_reasons,
        transfer_rate=transfer_rate,
    )
```

**Step 3: Add endpoint to router.py**

```python
from app.analytics.service import ingest_call_record, get_summary, get_operations

@router.get("/operations", response_model=OperationsResponse)
async def operations(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_operations(date_from, date_to)
```

**Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
```

**Step 5: Commit**

```bash
git add app/analytics/service.py app/analytics/router.py tests/analytics/test_router.py
git commit -m "feat(analytics): add operations metrics aggregation endpoint"
```

---

## Task 5: Backend — Negotiations Aggregation

**Files:**
- Modify: `app/analytics/service.py`
- Modify: `app/analytics/router.py`
- Modify: `tests/analytics/test_router.py`

**Step 1: Write failing test**

```python
@pytest.fixture
async def negotiations_client():
    """HTTP client for negotiations endpoint."""
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:  # rate averages
            mock_cursor.to_list = AsyncMock(return_value=[{
                "avg_first_offer": 1900.0,
                "avg_final_rate": 2000.0,
                "avg_rounds": 2.1,
            }])
        elif call_count == 2:  # rate progression
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "carrier_first_offer", "avg_rate": 1900.0},
                {"_id": "final_agreed_rate", "avg_rate": 2000.0},
            ])
        elif call_count == 3:  # margin distribution
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "5-10%", "count": 5},
            ])
        elif call_count == 4:  # strategy effectiveness
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "anchoring_high", "acceptance_rate": 80.0, "avg_rounds": 2.3, "count": 10},
            ])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)

    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_negotiations_returns_200(negotiations_client):
    """GET negotiations → 200 with all expected fields."""
    response = await negotiations_client.get("/api/analytics/negotiations")
    assert response.status_code == 200
    data = response.json()
    assert "avg_first_offer" in data
    assert "avg_final_rate" in data
    assert "margin_distribution" in data
    assert "strategy_effectiveness" in data
```

**Step 2: Implement get_negotiations in service.py**

```python
async def get_negotiations(date_from: Optional[str] = None, date_to: Optional[str] = None) -> NegotiationsResponse:
    """Compute negotiation performance metrics."""
    db = get_database()
    match_stage = _build_date_match(date_from, date_to)

    # 1. Rate averages
    avg_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.carrier_first_offer": {"$ne": None}}},
        {"$group": {
            "_id": None,
            "avg_first_offer": {"$avg": "$transcript_extraction.carrier_first_offer"},
            "avg_final_rate": {"$avg": "$transcript_extraction.final_agreed_rate"},
            "avg_rounds": {"$avg": "$transcript_extraction.negotiation_rounds"},
        }},
    ]
    avg_cursor = db.call_records.aggregate(avg_pipeline)
    avg_results = await avg_cursor.to_list(length=1)

    avg_first = 0.0
    avg_final = 0.0
    avg_rounds = 0.0
    if avg_results:
        avg_first = round(avg_results[0].get("avg_first_offer") or 0.0, 2)
        avg_final = round(avg_results[0].get("avg_final_rate") or 0.0, 2)
        avg_rounds = round(avg_results[0].get("avg_rounds") or 0.0, 1)

    # 2. Rate progression (avg at each negotiation stage)
    rate_fields = [
        ("carrier_first_offer", "Carrier 1st Offer"),
        ("broker_first_counter", "Broker 1st Counter"),
        ("carrier_second_offer", "Carrier 2nd Offer"),
        ("broker_second_counter", "Broker 2nd Counter"),
        ("carrier_third_offer", "Carrier 3rd Offer"),
        ("broker_third_counter", "Broker 3rd Counter"),
        ("final_agreed_rate", "Final Rate"),
    ]
    rate_progression_group = {}
    for field, _ in rate_fields:
        rate_progression_group[field] = {
            "$avg": {
                "$cond": [
                    {"$ne": [f"$transcript_extraction.{field}", None]},
                    f"$transcript_extraction.{field}",
                    None,
                ]
            }
        }
    rate_progression_group["_id"] = None

    rp_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.carrier_first_offer": {"$ne": None}}},
        {"$group": rate_progression_group},
    ]
    rp_cursor = db.call_records.aggregate(rp_pipeline)
    rp_results = await rp_cursor.to_list(length=1)

    rate_progression = []
    if rp_results:
        for field, label in rate_fields:
            val = rp_results[0].get(field)
            if val is not None:
                rate_progression.append(RateProgressionPoint(round=label, avg_rate=round(val, 2)))

    # 3. Margin distribution (buckets)
    margin_pipeline = [
        {"$match": {
            **match_stage,
            "transcript_extraction.carrier_first_offer": {"$ne": None},
            "transcript_extraction.final_agreed_rate": {"$ne": None},
        }},
        {"$project": {
            "margin": {
                "$multiply": [
                    {"$divide": [
                        {"$subtract": [
                            "$transcript_extraction.carrier_first_offer",
                            "$transcript_extraction.final_agreed_rate",
                        ]},
                        "$transcript_extraction.carrier_first_offer",
                    ]},
                    100,
                ]
            }
        }},
        {"$bucket": {
            "groupBy": "$margin",
            "boundaries": [-100, 0, 5, 10, 15, 20, 100],
            "default": "other",
            "output": {"count": {"$sum": 1}},
        }},
    ]
    margin_cursor = db.call_records.aggregate(margin_pipeline)
    margin_results = await margin_cursor.to_list(length=100)

    bucket_labels = {-100: "<0%", 0: "0-5%", 5: "5-10%", 10: "10-15%", 15: "15-20%", 20: "20%+", "other": "other"}
    margin_distribution = [
        MarginBucket(range=bucket_labels.get(r["_id"], str(r["_id"])), count=r["count"])
        for r in margin_results
    ]

    # 4. Strategy effectiveness
    strategy_pipeline = [
        {"$match": {
            **match_stage,
            "transcript_extraction.optional.negotiation_strategy_used": {"$ne": None},
        }},
        {"$group": {
            "_id": "$transcript_extraction.optional.negotiation_strategy_used",
            "total": {"$sum": 1},
            "accepted": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.outcome.call_outcome", "accepted"]},
                    1, 0,
                ]}
            },
            "avg_rounds": {"$avg": "$transcript_extraction.negotiation_rounds"},
        }},
        {"$sort": {"total": -1}},
    ]
    strat_cursor = db.call_records.aggregate(strategy_pipeline)
    strat_results = await strat_cursor.to_list(length=100)

    strategy_effectiveness = [
        StrategyRow(
            strategy=r["_id"],
            acceptance_rate=round((r["accepted"] / r["total"]) * 100, 1) if r["total"] > 0 else 0.0,
            avg_rounds=round(r["avg_rounds"] or 0, 1),
            count=r["total"],
        )
        for r in strat_results
    ]

    return NegotiationsResponse(
        avg_first_offer=avg_first,
        avg_final_rate=avg_final,
        avg_rounds=avg_rounds,
        rate_progression=rate_progression,
        margin_distribution=margin_distribution,
        strategy_effectiveness=strategy_effectiveness,
    )
```

**Step 3: Add endpoint**

```python
@router.get("/negotiations", response_model=NegotiationsResponse)
async def negotiations(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_negotiations(date_from, date_to)
```

**Step 4: Run tests, commit**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
git add app/analytics/ tests/analytics/
git commit -m "feat(analytics): add negotiations metrics aggregation endpoint"
```

---

## Task 6: Backend — AI Quality Aggregation

**Files:**
- Modify: `app/analytics/service.py`
- Modify: `app/analytics/router.py`
- Modify: `tests/analytics/test_router.py`

**Step 1: Write failing test**

```python
@pytest.fixture
async def ai_quality_client():
    """HTTP client for AI quality endpoint."""
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:  # main stats
            mock_cursor.to_list = AsyncMock(return_value=[{
                "total": 10,
                "compliant": 9,
                "avg_interruptions": 1.2,
                "transcription_errors": 1,
                "carrier_repeats": 2,
            }])
        elif call_count == 2:  # violations
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "skipped_greeting", "count": 3},
            ])
        elif call_count == 3:  # interruptions over time
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "2024-06-15", "avg": 1.5},
            ])
        elif call_count == 4:  # tone distribution
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "professional", "count": 8},
                {"_id": "neutral", "count": 2},
            ])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)

    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_ai_quality_returns_200(ai_quality_client):
    """GET ai-quality → 200 with all expected fields."""
    response = await ai_quality_client.get("/api/analytics/ai-quality")
    assert response.status_code == 200
    data = response.json()
    assert "protocol_compliance_rate" in data
    assert "common_violations" in data
    assert "avg_interruptions" in data
    assert "tone_quality_distribution" in data
    assert data["protocol_compliance_rate"] == 90.0
```

**Step 2: Implement get_ai_quality in service.py**

```python
async def get_ai_quality(date_from: Optional[str] = None, date_to: Optional[str] = None) -> AIQualityResponse:
    """Compute AI/model quality metrics."""
    db = get_database()
    match_stage = _build_date_match(date_from, date_to)

    # 1. Main stats
    main_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "compliant": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.performance.agent_followed_protocol", True]},
                    1, 0,
                ]}
            },
            "avg_interruptions": {"$avg": "$transcript_extraction.conversation.ai_interruptions_count"},
            "transcription_errors": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.conversation.transcription_errors_detected", True]},
                    1, 0,
                ]}
            },
            "carrier_repeats": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.conversation.carrier_had_to_repeat_info", True]},
                    1, 0,
                ]}
            },
        }},
    ]
    main_cursor = db.call_records.aggregate(main_pipeline)
    main_results = await main_cursor.to_list(length=1)

    if not main_results:
        return AIQualityResponse(
            protocol_compliance_rate=0.0, common_violations=[], avg_interruptions=0.0,
            interruptions_over_time=[], transcription_error_rate=0.0,
            carrier_repeat_rate=0.0, tone_quality_distribution={},
        )

    r = main_results[0]
    total = r["total"]

    # 2. Common violations (unwind array, count each)
    violation_pipeline = [
        {"$match": match_stage},
        {"$unwind": "$transcript_extraction.performance.protocol_violations"},
        {"$group": {"_id": "$transcript_extraction.performance.protocol_violations", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    viol_cursor = db.call_records.aggregate(violation_pipeline)
    viol_results = await viol_cursor.to_list(length=10)
    common_violations = [ViolationCount(violation=v["_id"], count=v["count"]) for v in viol_results]

    # 3. Interruptions over time
    int_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$system.call_startedat"}},
            "avg": {"$avg": "$transcript_extraction.conversation.ai_interruptions_count"},
        }},
        {"$sort": {"_id": 1}},
    ]
    int_cursor = db.call_records.aggregate(int_pipeline)
    int_results = await int_cursor.to_list(length=1000)
    interruptions_over_time = [
        InterruptionTimeSeriesPoint(date=i["_id"], avg=round(i["avg"] or 0, 2))
        for i in int_results
    ]

    # 4. Tone quality distribution
    tone_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.performance.agent_tone_quality": {"$ne": None}}},
        {"$group": {"_id": "$transcript_extraction.performance.agent_tone_quality", "count": {"$sum": 1}}},
    ]
    tone_cursor = db.call_records.aggregate(tone_pipeline)
    tone_results = await tone_cursor.to_list(length=100)
    tone_distribution = {t["_id"]: t["count"] for t in tone_results}

    return AIQualityResponse(
        protocol_compliance_rate=round((r["compliant"] / total) * 100, 1) if total > 0 else 0.0,
        common_violations=common_violations,
        avg_interruptions=round(r["avg_interruptions"] or 0.0, 2),
        interruptions_over_time=interruptions_over_time,
        transcription_error_rate=round((r["transcription_errors"] / total) * 100, 1) if total > 0 else 0.0,
        carrier_repeat_rate=round((r["carrier_repeats"] / total) * 100, 1) if total > 0 else 0.0,
        tone_quality_distribution=tone_distribution,
    )
```

**Step 3: Add endpoint**

```python
@router.get("/ai-quality", response_model=AIQualityResponse)
async def ai_quality(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_ai_quality(date_from, date_to)
```

**Step 4: Run tests, commit**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
git add app/analytics/ tests/analytics/
git commit -m "feat(analytics): add AI quality metrics aggregation endpoint"
```

---

## Task 7: Backend — Carriers Aggregation

**Files:**
- Modify: `app/analytics/service.py`
- Modify: `app/analytics/router.py`
- Modify: `tests/analytics/test_router.py`

**Step 1: Write failing test**

```python
@pytest.fixture
async def carriers_client():
    """HTTP client for carriers endpoint."""
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:  # sentiment distribution
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "positive", "count": 6},
                {"_id": "neutral", "count": 3},
                {"_id": "negative", "count": 1},
            ])
        elif call_count == 2:  # sentiment over time
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "2024-06-15", "positive": 3, "neutral": 1, "negative": 0},
            ])
        elif call_count == 3:  # engagement levels
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "high", "count": 5},
                {"_id": "medium", "count": 3},
            ])
        elif call_count == 4:  # future interest
            mock_cursor.to_list = AsyncMock(return_value=[
                {"total": 10, "interested": 7},
            ])
        elif call_count == 5:  # objections
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "rate_too_low", "count": 4},
            ])
        elif call_count == 6:  # questions
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "Is the rate negotiable?", "count": 3},
            ])
        elif call_count == 7:  # leaderboard
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": 1234, "carrier_name": "TYROLER METALS", "calls": 5,
                 "accepted": 4, "total": 5},
            ])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)

    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_carriers_returns_200(carriers_client):
    """GET carriers → 200 with all expected fields."""
    response = await carriers_client.get("/api/analytics/carriers")
    assert response.status_code == 200
    data = response.json()
    assert "sentiment_distribution" in data
    assert "carrier_leaderboard" in data
    assert "top_objections" in data
    assert data["future_interest_rate"] == 70.0
```

**Step 2: Implement get_carriers in service.py**

```python
async def get_carriers(date_from: Optional[str] = None, date_to: Optional[str] = None) -> CarriersResponse:
    """Compute carrier intelligence metrics."""
    db = get_database()
    match_stage = _build_date_match(date_from, date_to)

    # 1. Sentiment distribution
    sent_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.sentiment.call_sentiment": {"$ne": None}}},
        {"$group": {"_id": "$transcript_extraction.sentiment.call_sentiment", "count": {"$sum": 1}}},
    ]
    sent_cursor = db.call_records.aggregate(sent_pipeline)
    sent_results = await sent_cursor.to_list(length=100)
    sentiment_distribution = {s["_id"]: s["count"] for s in sent_results}

    # 2. Sentiment over time
    sot_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.sentiment.call_sentiment": {"$ne": None}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$system.call_startedat"}},
            "positive": {"$sum": {"$cond": [{"$eq": ["$transcript_extraction.sentiment.call_sentiment", "positive"]}, 1, 0]}},
            "neutral": {"$sum": {"$cond": [{"$eq": ["$transcript_extraction.sentiment.call_sentiment", "neutral"]}, 1, 0]}},
            "negative": {"$sum": {"$cond": [{"$eq": ["$transcript_extraction.sentiment.call_sentiment", "negative"]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    sot_cursor = db.call_records.aggregate(sot_pipeline)
    sot_results = await sot_cursor.to_list(length=1000)
    sentiment_over_time = [
        {"date": r["_id"], "positive": r["positive"], "neutral": r["neutral"], "negative": r["negative"]}
        for r in sot_results
    ]

    # 3. Engagement levels
    eng_pipeline = [
        {"$match": {**match_stage, "transcript_extraction.sentiment.engagement_level": {"$ne": None}}},
        {"$group": {"_id": "$transcript_extraction.sentiment.engagement_level", "count": {"$sum": 1}}},
    ]
    eng_cursor = db.call_records.aggregate(eng_pipeline)
    eng_results = await eng_cursor.to_list(length=100)
    engagement_levels = {e["_id"]: e["count"] for e in eng_results}

    # 4. Future interest rate
    fi_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "interested": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.sentiment.carrier_expressed_interest_future", True]},
                    1, 0,
                ]}
            },
        }},
    ]
    fi_cursor = db.call_records.aggregate(fi_pipeline)
    fi_results = await fi_cursor.to_list(length=1)
    future_interest_rate = 0.0
    if fi_results and fi_results[0]["total"] > 0:
        future_interest_rate = round((fi_results[0]["interested"] / fi_results[0]["total"]) * 100, 1)

    # 5. Top objections (unwind array)
    obj_pipeline = [
        {"$match": match_stage},
        {"$unwind": "$transcript_extraction.optional.carrier_objections"},
        {"$group": {"_id": "$transcript_extraction.optional.carrier_objections", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    obj_cursor = db.call_records.aggregate(obj_pipeline)
    obj_results = await obj_cursor.to_list(length=10)
    top_objections = [ObjectionCount(objection=o["_id"], count=o["count"]) for o in obj_results]

    # 6. Top questions (unwind array)
    q_pipeline = [
        {"$match": match_stage},
        {"$unwind": "$transcript_extraction.optional.carrier_questions_asked"},
        {"$group": {"_id": "$transcript_extraction.optional.carrier_questions_asked", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    q_cursor = db.call_records.aggregate(q_pipeline)
    q_results = await q_cursor.to_list(length=10)
    top_questions = [QuestionCount(question=q["_id"], count=q["count"]) for q in q_results]

    # 7. Carrier leaderboard
    lb_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$fmcsa_data.carrier_mc_number",
            "carrier_name": {"$first": "$fmcsa_data.carrier_name"},
            "calls": {"$sum": 1},
            "accepted": {
                "$sum": {"$cond": [
                    {"$eq": ["$transcript_extraction.outcome.call_outcome", "accepted"]},
                    1, 0,
                ]}
            },
        }},
        {"$sort": {"calls": -1}},
        {"$limit": 20},
    ]
    lb_cursor = db.call_records.aggregate(lb_pipeline)
    lb_results = await lb_cursor.to_list(length=20)
    carrier_leaderboard = [
        CarrierLeaderboardRow(
            carrier_name=c["carrier_name"],
            mc_number=c["_id"],
            calls=c["calls"],
            acceptance_rate=round((c["accepted"] / c["calls"]) * 100, 1) if c["calls"] > 0 else 0.0,
        )
        for c in lb_results
    ]

    return CarriersResponse(
        sentiment_distribution=sentiment_distribution,
        sentiment_over_time=sentiment_over_time,
        engagement_levels=engagement_levels,
        future_interest_rate=future_interest_rate,
        top_objections=top_objections,
        top_questions=top_questions,
        carrier_leaderboard=carrier_leaderboard,
    )
```

**Step 3: Add endpoint**

```python
@router.get("/carriers", response_model=CarriersResponse)
async def carriers(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    return await get_carriers(date_from, date_to)
```

**Step 4: Run tests, commit**

```bash
.venv/bin/python -m pytest tests/analytics/test_router.py -v
git add app/analytics/ tests/analytics/
git commit -m "feat(analytics): add carriers intelligence metrics aggregation endpoint"
```

---

## Task 8: Backend — Final Router & Run All Tests

**Step 1: Verify final router.py has all imports and endpoints**

Final `app/analytics/router.py` should import and register all 6 endpoints:
- POST `/calls` → ingest
- GET `/summary` → summary KPIs
- GET `/operations` → operations metrics
- GET `/negotiations` → negotiation metrics
- GET `/ai-quality` → AI quality metrics
- GET `/carriers` → carrier intelligence

**Step 2: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests pass (existing loads + negotiations + new analytics tests).

**Step 3: Commit if any final adjustments**

```bash
git add -A
git commit -m "feat(analytics): complete backend with all aggregation endpoints"
```

---

## Task 9: Frontend — Scaffold React + Vite + Tailwind + Recharts

**Files:**
- Create: `dashboard/` directory with Vite React project

**Step 1: Initialize Vite project**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC
npm create vite@latest dashboard -- --template react-ts
cd dashboard
npm install
```

**Step 2: Install Tailwind CSS**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC/dashboard
npm install -D tailwindcss @tailwindcss/vite
```

Add Tailwind to `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

Replace `dashboard/src/index.css` with:

```css
@import "tailwindcss";
```

**Step 3: Install Recharts**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC/dashboard
npm install recharts
```

**Step 4: Verify it builds**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC/dashboard
npm run build
```

**Step 5: Commit**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC
git add dashboard/
git commit -m "feat(dashboard): scaffold React + Vite + Tailwind + Recharts"
```

---

## Task 10: Frontend — API Client & TypeScript Types

**Files:**
- Create: `dashboard/src/api.ts`
- Create: `dashboard/src/types.ts`

**Step 1: Create TypeScript types matching backend response models**

`dashboard/src/types.ts`:

```typescript
export interface SummaryData {
  total_calls: number;
  acceptance_rate: number;
  avg_call_duration: number;
  avg_negotiation_rounds: number;
  avg_margin_percent: number;
  ai_protocol_compliance: number;
  total_carriers: number;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
}

export interface DurationTimeSeriesPoint {
  date: string;
  avg_duration: number;
}

export interface ReasonCount {
  reason: string;
  count: number;
}

export interface OperationsData {
  calls_over_time: TimeSeriesPoint[];
  outcome_distribution: Record<string, number>;
  avg_duration_over_time: DurationTimeSeriesPoint[];
  rejection_reasons: ReasonCount[];
  transfer_rate: number;
}

export interface RateProgressionPoint {
  round: string;
  avg_rate: number;
}

export interface MarginBucket {
  range: string;
  count: number;
}

export interface StrategyRow {
  strategy: string;
  acceptance_rate: number;
  avg_rounds: number;
  count: number;
}

export interface NegotiationsData {
  avg_first_offer: number;
  avg_final_rate: number;
  avg_rounds: number;
  rate_progression: RateProgressionPoint[];
  margin_distribution: MarginBucket[];
  strategy_effectiveness: StrategyRow[];
}

export interface ViolationCount {
  violation: string;
  count: number;
}

export interface InterruptionPoint {
  date: string;
  avg: number;
}

export interface AIQualityData {
  protocol_compliance_rate: number;
  common_violations: ViolationCount[];
  avg_interruptions: number;
  interruptions_over_time: InterruptionPoint[];
  transcription_error_rate: number;
  carrier_repeat_rate: number;
  tone_quality_distribution: Record<string, number>;
}

export interface ObjectionCount {
  objection: string;
  count: number;
}

export interface QuestionCount {
  question: string;
  count: number;
}

export interface CarrierLeaderboardRow {
  carrier_name: string;
  mc_number: number;
  calls: number;
  acceptance_rate: number;
}

export interface SentimentTimePoint {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface CarriersData {
  sentiment_distribution: Record<string, number>;
  sentiment_over_time: SentimentTimePoint[];
  engagement_levels: Record<string, number>;
  future_interest_rate: number;
  top_objections: ObjectionCount[];
  top_questions: QuestionCount[];
  carrier_leaderboard: CarrierLeaderboardRow[];
}
```

**Step 2: Create API client**

`dashboard/src/api.ts`:

```typescript
import type {
  SummaryData,
  OperationsData,
  NegotiationsData,
  AIQualityData,
  CarriersData,
} from './types';

const API_KEY = import.meta.env.VITE_API_KEY || '';
const BASE = '/api/analytics';

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), {
    headers: { 'X-API-Key': API_KEY },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getSummary: (from?: string, to?: string) =>
    fetchAPI<SummaryData>(`${BASE}/summary`, { from: from || '', to: to || '' }),
  getOperations: (from?: string, to?: string) =>
    fetchAPI<OperationsData>(`${BASE}/operations`, { from: from || '', to: to || '' }),
  getNegotiations: (from?: string, to?: string) =>
    fetchAPI<NegotiationsData>(`${BASE}/negotiations`, { from: from || '', to: to || '' }),
  getAIQuality: (from?: string, to?: string) =>
    fetchAPI<AIQualityData>(`${BASE}/ai-quality`, { from: from || '', to: to || '' }),
  getCarriers: (from?: string, to?: string) =>
    fetchAPI<CarriersData>(`${BASE}/carriers`, { from: from || '', to: to || '' }),
};
```

**Step 3: Commit**

```bash
git add dashboard/src/types.ts dashboard/src/api.ts
git commit -m "feat(dashboard): add TypeScript types and API client"
```

---

## Task 11: Frontend — Dashboard Layout + KPI Hero

**Files:**
- Create: `dashboard/src/components/KPICard.tsx`
- Create: `dashboard/src/components/Header.tsx`
- Modify: `dashboard/src/App.tsx`

**Step 1: Build KPICard component**

`dashboard/src/components/KPICard.tsx`:

```tsx
interface KPICardProps {
  label: string;
  value: string | number;
  format?: 'number' | 'percent' | 'duration';
  color?: 'green' | 'amber' | 'blue' | 'slate';
}

const colorMap = {
  green: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  amber: 'bg-amber-50 border-amber-200 text-amber-700',
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  slate: 'bg-slate-50 border-slate-200 text-slate-700',
};

function formatValue(value: string | number, format?: string): string {
  if (typeof value === 'string') return value;
  if (format === 'percent') return `${value.toFixed(1)}%`;
  if (format === 'duration') {
    const mins = Math.floor(value / 60);
    const secs = Math.round(value % 60);
    return `${mins}m ${secs}s`;
  }
  if (Number.isInteger(value)) return value.toLocaleString();
  return value.toFixed(1);
}

export default function KPICard({ label, value, format, color = 'slate' }: KPICardProps) {
  return (
    <div className={`rounded-xl border p-5 ${colorMap[color]}`}>
      <p className="text-sm font-medium opacity-70 mb-1">{label}</p>
      <p className="text-3xl font-bold tracking-tight">{formatValue(value, format)}</p>
    </div>
  );
}
```

**Step 2: Build Header component**

`dashboard/src/components/Header.tsx`:

```tsx
import { useState, useEffect } from 'react';

interface HeaderProps {
  dateFrom: string;
  dateTo: string;
  onDateChange: (from: string, to: string) => void;
  onRefresh: () => void;
  countdown: number;
}

export default function Header({ dateFrom, dateTo, onDateChange, onRefresh, countdown }: HeaderProps) {
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">CL</span>
        </div>
        <h1 className="text-xl font-bold text-slate-800">Carrier Load Analytics</h1>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <label className="text-slate-500">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => onDateChange(e.target.value, dateTo)}
            className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          />
          <label className="text-slate-500">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => onDateChange(dateFrom, e.target.value)}
            className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          />
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 bg-blue-600 text-white px-3 py-1.5 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Refresh
          <span className="text-blue-200 text-xs">({countdown}s)</span>
        </button>
      </div>
    </header>
  );
}
```

**Step 3: Build main App with KPI hero and tab structure**

Replace `dashboard/src/App.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import KPICard from './components/KPICard';
import OperationsTab from './components/OperationsTab';
import NegotiationsTab from './components/NegotiationsTab';
import AIQualityTab from './components/AIQualityTab';
import CarriersTab from './components/CarriersTab';
import { api } from './api';
import type { SummaryData, OperationsData, NegotiationsData, AIQualityData, CarriersData } from './types';

const TABS = ['Operations', 'Negotiations', 'AI Quality', 'Carriers'] as const;
type Tab = typeof TABS[number];

const POLL_INTERVAL = 30;

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('Operations');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [countdown, setCountdown] = useState(POLL_INTERVAL);

  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [operations, setOperations] = useState<OperationsData | null>(null);
  const [negotiations, setNegotiations] = useState<NegotiationsData | null>(null);
  const [aiQuality, setAIQuality] = useState<AIQualityData | null>(null);
  const [carriers, setCarriers] = useState<CarriersData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const from = dateFrom || undefined;
      const to = dateTo || undefined;
      const [s, o, n, a, c] = await Promise.all([
        api.getSummary(from, to),
        api.getOperations(from, to),
        api.getNegotiations(from, to),
        api.getAIQuality(from, to),
        api.getCarriers(from, to),
      ]);
      setSummary(s);
      setOperations(o);
      setNegotiations(n);
      setAIQuality(a);
      setCarriers(c);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  // Initial fetch + auto-poll
  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      fetchAll();
      setCountdown(POLL_INTERVAL);
    }, POLL_INTERVAL * 1000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : POLL_INTERVAL));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleRefresh = () => {
    setCountdown(POLL_INTERVAL);
    fetchAll();
  };

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
  };

  const isEmpty = summary && summary.total_calls === 0;

  return (
    <div className="min-h-screen bg-slate-100">
      <Header
        dateFrom={dateFrom}
        dateTo={dateTo}
        onDateChange={handleDateChange}
        onRefresh={handleRefresh}
        countdown={countdown}
      />

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* KPI Hero Section */}
        {isEmpty ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center mb-6">
            <p className="text-slate-400 text-lg mb-2">No call data yet</p>
            <p className="text-slate-500 text-sm">
              POST call records to <code className="bg-slate-100 px-2 py-0.5 rounded text-blue-600">/api/analytics/calls</code> to see metrics here.
            </p>
          </div>
        ) : summary ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
            <KPICard label="Total Calls" value={summary.total_calls} color="blue" />
            <KPICard label="Acceptance Rate" value={summary.acceptance_rate} format="percent" color="green" />
            <KPICard label="Avg Margin" value={summary.avg_margin_percent} format="percent" color="green" />
            <KPICard label="Protocol Compliance" value={summary.ai_protocol_compliance} format="percent" color="amber" />
            <KPICard label="Avg Duration" value={summary.avg_call_duration} format="duration" color="slate" />
            <KPICard label="Avg Negotiation Rounds" value={summary.avg_negotiation_rounds} color="slate" />
            <KPICard label="Unique Carriers" value={summary.total_carriers} color="blue" />
          </div>
        ) : null}

        {/* Tab Navigation */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="border-b border-slate-200">
            <nav className="flex">
              {TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-3 text-sm font-medium transition-colors ${
                    activeTab === tab
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {loading && !summary ? (
              <p className="text-slate-400 text-center py-12">Loading...</p>
            ) : (
              <>
                {activeTab === 'Operations' && <OperationsTab data={operations} />}
                {activeTab === 'Negotiations' && <NegotiationsTab data={negotiations} />}
                {activeTab === 'AI Quality' && <AIQualityTab data={aiQuality} />}
                {activeTab === 'Carriers' && <CarriersTab data={carriers} />}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add dashboard/src/
git commit -m "feat(dashboard): add layout, KPI hero cards, and tab structure"
```

---

## Task 12: Frontend — Operations Tab

**Files:**
- Create: `dashboard/src/components/OperationsTab.tsx`
- Create: `dashboard/src/components/EmptyState.tsx`

**Step 1: Create EmptyState helper**

`dashboard/src/components/EmptyState.tsx`:

```tsx
export default function EmptyState({ message }: { message?: string }) {
  return (
    <div className="text-center py-12 text-slate-400">
      <p>{message || 'No data available'}</p>
    </div>
  );
}
```

**Step 2: Create OperationsTab**

`dashboard/src/components/OperationsTab.tsx`:

```tsx
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, LineChart, Line, Legend,
} from 'recharts';
import type { OperationsData } from '../types';
import EmptyState from './EmptyState';

const COLORS = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6'];

interface Props {
  data: OperationsData | null;
}

export default function OperationsTab({ data }: Props) {
  if (!data) return <EmptyState />;

  const outcomeData = Object.entries(data.outcome_distribution).map(([name, value]) => ({
    name, value,
  }));
  const total = outcomeData.reduce((s, d) => s + d.value, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Call Volume Over Time */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Call Volume Over Time</h3>
        {data.calls_over_time.length === 0 ? <EmptyState /> : (
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={data.calls_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <Tooltip />
              <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Outcome Distribution */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Outcome Distribution</h3>
        {outcomeData.length === 0 ? <EmptyState /> : (
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={outcomeData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                   dataKey="value" nameKey="name" label={({ name, value }) => `${name} ${((value/total)*100).toFixed(0)}%`}>
                {outcomeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Rejection Reasons */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Rejection Reasons</h3>
        {data.rejection_reasons.length === 0 ? <EmptyState message="No rejections recorded" /> : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.rejection_reasons} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis type="category" dataKey="reason" tick={{ fontSize: 12 }} stroke="#94a3b8" width={140} />
              <Tooltip />
              <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Avg Duration Over Time */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Avg Call Duration Over Time</h3>
        {data.avg_duration_over_time.length === 0 ? <EmptyState /> : (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.avg_duration_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <Tooltip formatter={(v: number) => `${(v / 60).toFixed(1)} min`} />
              <Line type="monotone" dataKey="avg_duration" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add dashboard/src/components/
git commit -m "feat(dashboard): add Operations tab with charts"
```

---

## Task 13: Frontend — Negotiations Tab

**Files:**
- Create: `dashboard/src/components/NegotiationsTab.tsx`

```tsx
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import type { NegotiationsData } from '../types';
import EmptyState from './EmptyState';

const COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6'];

interface Props {
  data: NegotiationsData | null;
}

export default function NegotiationsTab({ data }: Props) {
  if (!data) return <EmptyState />;

  return (
    <div className="space-y-6">
      {/* Summary stats row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg First Offer</p>
          <p className="text-2xl font-bold text-slate-800">${data.avg_first_offer.toLocaleString()}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Final Rate</p>
          <p className="text-2xl font-bold text-emerald-600">${data.avg_final_rate.toLocaleString()}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Rounds</p>
          <p className="text-2xl font-bold text-slate-800">{data.avg_rounds}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rate Progression */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Rate Progression (Avg per Stage)</h3>
          {data.rate_progression.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={data.rate_progression}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="round" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
                <Line type="monotone" dataKey="avg_rate" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Margin Distribution */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Margin Distribution</h3>
          {data.margin_distribution.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.margin_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="range" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.margin_distribution.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Strategy Effectiveness Table */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Strategy Effectiveness</h3>
        {data.strategy_effectiveness.length === 0 ? <EmptyState message="No strategy data" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="pb-2 font-medium">Strategy</th>
                  <th className="pb-2 font-medium">Accept Rate</th>
                  <th className="pb-2 font-medium">Avg Rounds</th>
                  <th className="pb-2 font-medium">Count</th>
                </tr>
              </thead>
              <tbody>
                {data.strategy_effectiveness.map((row) => (
                  <tr key={row.strategy} className="border-b border-slate-100">
                    <td className="py-2 font-medium text-slate-700">{row.strategy}</td>
                    <td className="py-2">
                      <span className={row.acceptance_rate >= 70 ? 'text-emerald-600' : row.acceptance_rate >= 50 ? 'text-amber-600' : 'text-red-500'}>
                        {row.acceptance_rate}%
                      </span>
                    </td>
                    <td className="py-2 text-slate-600">{row.avg_rounds}</td>
                    <td className="py-2 text-slate-600">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Commit:**

```bash
git add dashboard/src/components/NegotiationsTab.tsx
git commit -m "feat(dashboard): add Negotiations tab with rate progression and strategy table"
```

---

## Task 14: Frontend — AI Quality Tab

**Files:**
- Create: `dashboard/src/components/AIQualityTab.tsx`

```tsx
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts';
import type { AIQualityData } from '../types';
import EmptyState from './EmptyState';

const COLORS = ['#10b981', '#94a3b8', '#ef4444'];

interface Props {
  data: AIQualityData | null;
}

export default function AIQualityTab({ data }: Props) {
  if (!data) return <EmptyState />;

  const toneData = Object.entries(data.tone_quality_distribution).map(([name, value]) => ({
    name, value,
  }));

  return (
    <div className="space-y-6">
      {/* Stat cards row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Protocol Compliance</p>
          <p className={`text-3xl font-bold ${data.protocol_compliance_rate >= 90 ? 'text-emerald-600' : 'text-amber-600'}`}>
            {data.protocol_compliance_rate}%
          </p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Interruptions</p>
          <p className="text-3xl font-bold text-slate-800">{data.avg_interruptions}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Transcription Errors</p>
          <p className={`text-3xl font-bold ${data.transcription_error_rate <= 5 ? 'text-emerald-600' : 'text-red-500'}`}>
            {data.transcription_error_rate}%
          </p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Carrier Repeat Rate</p>
          <p className={`text-3xl font-bold ${data.carrier_repeat_rate <= 10 ? 'text-emerald-600' : 'text-amber-600'}`}>
            {data.carrier_repeat_rate}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Common Violations */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Common Protocol Violations</h3>
          {data.common_violations.length === 0 ? <EmptyState message="No violations recorded" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.common_violations} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis type="category" dataKey="violation" tick={{ fontSize: 12 }} stroke="#94a3b8" width={150} />
                <Tooltip />
                <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Interruptions Over Time */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Interruptions Over Time</h3>
          {data.interruptions_over_time.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={data.interruptions_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                <Line type="monotone" dataKey="avg" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Tone Quality Distribution */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Tone Quality Distribution</h3>
          {toneData.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={toneData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                     dataKey="value" nameKey="name"
                     label={({ name, value }) => `${name} (${value})`}>
                  {toneData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Commit:**

```bash
git add dashboard/src/components/AIQualityTab.tsx
git commit -m "feat(dashboard): add AI Quality tab with compliance, violations, and tone charts"
```

---

## Task 15: Frontend — Carriers Tab

**Files:**
- Create: `dashboard/src/components/CarriersTab.tsx`

```tsx
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend,
} from 'recharts';
import type { CarriersData } from '../types';
import EmptyState from './EmptyState';

const SENT_COLORS = { positive: '#10b981', neutral: '#94a3b8', negative: '#ef4444' };
const ENG_COLORS = ['#3b82f6', '#f59e0b', '#94a3b8'];

interface Props {
  data: CarriersData | null;
}

export default function CarriersTab({ data }: Props) {
  if (!data) return <EmptyState />;

  const engData = Object.entries(data.engagement_levels).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Over Time */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Sentiment Over Time</h3>
          {data.sentiment_over_time.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={data.sentiment_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="positive" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.6} />
                <Area type="monotone" dataKey="neutral" stackId="1" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.6} />
                <Area type="monotone" dataKey="negative" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Engagement Levels */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Engagement Levels</h3>
          {engData.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={engData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                     dataKey="value" nameKey="name"
                     label={({ name, value }) => `${name} (${value})`}>
                  {engData.map((_, i) => <Cell key={i} fill={ENG_COLORS[i % ENG_COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top Objections */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Top Carrier Objections</h3>
          {data.top_objections.length === 0 ? <EmptyState message="No objections recorded" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.top_objections} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis type="category" dataKey="objection" tick={{ fontSize: 12 }} stroke="#94a3b8" width={150} />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top Questions */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Top Carrier Questions</h3>
          {data.top_questions.length === 0 ? <EmptyState message="No questions recorded" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.top_questions} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis type="category" dataKey="question" tick={{ fontSize: 11 }} stroke="#94a3b8" width={180} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Future Interest + Leaderboard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-slate-50 rounded-lg p-4 text-center flex flex-col items-center justify-center">
          <p className="text-sm text-slate-500 mb-2">Future Interest Rate</p>
          <p className="text-4xl font-bold text-blue-600">{data.future_interest_rate}%</p>
          <p className="text-xs text-slate-400 mt-1">Carriers expressing future interest</p>
        </div>

        <div className="bg-slate-50 rounded-lg p-4 lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Carrier Leaderboard</h3>
          {data.carrier_leaderboard.length === 0 ? <EmptyState /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    <th className="pb-2 font-medium">Carrier</th>
                    <th className="pb-2 font-medium">MC#</th>
                    <th className="pb-2 font-medium">Calls</th>
                    <th className="pb-2 font-medium">Accept Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {data.carrier_leaderboard.map((row) => (
                    <tr key={row.mc_number} className="border-b border-slate-100">
                      <td className="py-2 font-medium text-slate-700">{row.carrier_name}</td>
                      <td className="py-2 text-slate-500">{row.mc_number}</td>
                      <td className="py-2 text-slate-600">{row.calls}</td>
                      <td className="py-2">
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-slate-200 rounded-full h-2">
                            <div
                              className="bg-emerald-500 h-2 rounded-full"
                              style={{ width: `${Math.min(row.acceptance_rate, 100)}%` }}
                            />
                          </div>
                          <span className="text-slate-600">{row.acceptance_rate}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Commit:**

```bash
git add dashboard/src/components/CarriersTab.tsx
git commit -m "feat(dashboard): add Carriers tab with sentiment, engagement, and leaderboard"
```

---

## Task 16: Integration — FastAPI Serves Dashboard + CORS

**Files:**
- Modify: `app/main.py`

**Step 1: Add static file serving and CORS to main.py**

Update `app/main.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import connect_db, disconnect_db
from app.loads.router import router as loads_router
from app.negotiations.router import router as negotiations_router
from app.analytics.router import router as analytics_router

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="Carrier Load Automation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(loads_router)
app.include_router(negotiations_router)
app.include_router(analytics_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve dashboard SPA — must be after API routes
if DASHBOARD_DIR.exists():
    app.mount("/dashboard/assets", StaticFiles(directory=DASHBOARD_DIR / "assets"), name="dashboard-assets")

    @app.get("/dashboard/{full_path:path}")
    async def serve_dashboard(full_path: str = ""):
        return FileResponse(DASHBOARD_DIR / "index.html")

    @app.get("/dashboard")
    async def dashboard_root():
        return FileResponse(DASHBOARD_DIR / "index.html")
```

**Step 2: Update vite.config.ts base path**

```typescript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/dashboard/',
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

**Step 3: Build dashboard**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC/dashboard
npm run build
```

**Step 4: Run full test suite**

```bash
cd /Users/fernandoaliagaestella/HappyRobot-TC
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests pass (loads + negotiations + analytics).

**Step 5: Commit**

```bash
git add app/main.py dashboard/vite.config.ts dashboard/dist/
git commit -m "feat: integrate dashboard with FastAPI static file serving + CORS"
```

---

## Task 17: Final Verification

**Step 1: Run the full application**

```bash
.venv/bin/uvicorn app.main:app --reload
```

**Step 2: POST a test call record**

```bash
curl -X POST http://localhost:8000/api/analytics/calls \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "system": {"call_id": "test-001", "call_startedat": "2024-06-15T10:30:00Z", "call_duration": 245},
    "fmcsa_data": {"carrier_mc_number": 1234, "carrier_name": "TYROLER METALS INC", "carrier_validation_result": "VALID", "retrieval_date": "2026-02-13T19:45:01.867+0000"},
    "load_data": {"load_id_discussed": "LD-001", "alternate_loads_presented": 1},
    "transcript_extraction": {
      "carrier_first_offer": 1900.00, "broker_first_counter": 2100.00,
      "carrier_second_offer": 2000.00, "final_agreed_rate": 2000.00,
      "negotiation_rounds": 2,
      "outcome": {"call_outcome": "accepted", "rejection_reason": null},
      "sentiment": {"call_sentiment": "positive", "engagement_level": "high", "carrier_expressed_interest_future": true},
      "performance": {"agent_followed_protocol": true, "protocol_violations": [], "agent_tone_quality": "professional"},
      "conversation": {"ai_interruptions_count": 1, "transcription_errors_detected": false, "carrier_had_to_repeat_info": false},
      "operational": {"transfer_to_sales_attempted": false, "transfer_to_sales_completed": false, "loads_presented_count": 2},
      "optional": {"negotiation_strategy_used": "anchoring_high", "carrier_negotiation_leverage": ["fuel_prices_mentioned"], "carrier_objections": ["rate_too_low"], "carrier_questions_asked": ["Is the rate negotiable?"]}
    }
  }'
```

**Step 3: Verify API endpoints return data**

```bash
curl http://localhost:8000/api/analytics/summary -H "X-API-Key: YOUR_API_KEY"
```

**Step 4: Open dashboard at http://localhost:8000/dashboard**

Verify:
- KPI cards show data from the ingested record
- All 4 tabs render charts
- Auto-refresh countdown is visible
- Empty states show correctly for missing data

**Step 5: Run full test suite one final time**

```bash
.venv/bin/python -m pytest tests/ -v
```

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: analytics dashboard complete — ingest, aggregation, and React UI"
```
