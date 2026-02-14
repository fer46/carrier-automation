from datetime import datetime, timezone
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
        "negotiation": {
            "carrier_first_offer": 1900.00,
            "broker_first_counter": 2100.00,
            "carrier_second_offer": 2000.00,
            "broker_second_counter": None,
            "carrier_third_offer": None,
            "broker_third_counter": None,
            "final_agreed_rate": 2000.00,
            "negotiation_rounds": 2,
        },
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
    """POST a valid call record -> 201 with call_id and status."""
    response = await ingest_client.post(
        "/api/analytics/calls", json=SAMPLE_CALL_RECORD
    )
    assert response.status_code == 201
    data = response.json()
    assert data["call_id"] == "test-call-001"
    assert data["status"] in ("created", "updated")


async def test_ingest_call_record_requires_api_key():
    """POST without API key -> 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/analytics/calls", json=SAMPLE_CALL_RECORD
        )
        assert response.status_code == 422


async def test_ingest_call_record_validates_body(ingest_client):
    """POST with invalid body -> 422."""
    response = await ingest_client.post(
        "/api/analytics/calls", json={"bad": "data"}
    )
    assert response.status_code == 422


async def test_ingest_sets_ingested_at_on_insert():
    """ingest_call_record uses $setOnInsert to stamp ingested_at on new records."""
    mock_db = _make_mock_db(find_one_result=None)
    mock_db.call_records.update_one = AsyncMock(
        return_value=MagicMock(upserted_id="new")
    )
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            before = datetime.now(tz=timezone.utc)
            await ac.post("/api/analytics/calls", json=SAMPLE_CALL_RECORD)
            after = datetime.now(tz=timezone.utc)

    # Verify update_one was called with $setOnInsert containing ingested_at
    call_args = mock_db.call_records.update_one.call_args
    update_doc = call_args[0][1]  # second positional arg is the update document
    assert "$setOnInsert" in update_doc
    ts = update_doc["$setOnInsert"]["ingested_at"]
    assert isinstance(ts, datetime)
    assert before <= ts <= after


async def test_summary_date_filter_uses_ingested_at():
    """Date-filtered summary queries must filter on ingested_at, not system.call_startedat."""
    mock_db = _make_mock_db(aggregate_result=[])
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            await ac.get("/api/analytics/summary?from=2026-01-01&to=2026-12-31")

    # Inspect the pipeline passed to aggregate
    pipeline = mock_db.call_records.aggregate.call_args[0][0]
    match_stage = pipeline[0]
    assert "$match" in match_stage
    assert "ingested_at" in match_stage["$match"]
    assert "system.call_startedat" not in match_stage["$match"]


# --- Summary Tests ---


@pytest.fixture
async def summary_client():
    mock_db = _make_mock_db(aggregate_result=[{
        "total_calls": 10,
        "accepted": 7,
        "avg_duration": 245.5,
        "avg_rounds": 2.1,
        "avg_margin": 8.4,
        "protocol_compliant": 9,
        "unique_carriers": [1234, 5678, 9012, 3456, 7890],
    }])
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_summary_returns_200(summary_client):
    response = await summary_client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_calls"] == 10
    assert data["acceptance_rate"] == 70.0
    assert data["avg_call_duration"] == 245.5
    assert data["ai_protocol_compliance"] == 90.0
    assert data["total_carriers"] == 5


async def test_summary_empty_db():
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


# --- Operations Tests ---


@pytest.fixture
async def operations_client():
    call_count = 0
    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "2024-06-15", "count": 5, "avg_duration": 200.0},
                {"_id": "2024-06-16", "count": 3, "avg_duration": 300.0},
            ])
        elif call_count == 2:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "accepted", "count": 7},
                {"_id": "rejected", "count": 2},
                {"_id": "transferred_to_sales", "count": 1},
            ])
        elif call_count == 3:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "rate_too_high", "count": 2},
            ])
        elif call_count == 4:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": None, "total": 10, "transferred": 1},
            ])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_operations_returns_200(operations_client):
    response = await operations_client.get("/api/analytics/operations")
    assert response.status_code == 200
    data = response.json()
    assert len(data["calls_over_time"]) == 2
    assert "accepted" in data["outcome_distribution"]
    assert len(data["rejection_reasons"]) == 1
    assert data["transfer_rate"] == 10.0


# --- Negotiations Tests ---


@pytest.fixture
async def negotiations_analytics_client():
    call_count = 0
    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            mock_cursor.to_list = AsyncMock(return_value=[{
                "avg_first_offer": 1900.0,
                "avg_final_rate": 2000.0,
                "avg_rounds": 2.1,
            }])
        elif call_count == 2:
            mock_cursor.to_list = AsyncMock(return_value=[{
                "_id": None,
                "carrier_first_offer": 1900.0,
                "broker_first_counter": 2100.0,
                "carrier_second_offer": 2000.0,
                "broker_second_counter": None,
                "carrier_third_offer": None,
                "broker_third_counter": None,
                "final_agreed_rate": 2000.0,
            }])
        elif call_count == 3:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": 0, "count": 3},
                {"_id": 5, "count": 5},
                {"_id": 10, "count": 2},
            ])
        elif call_count == 4:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "anchoring_high", "total": 10, "accepted": 8, "avg_rounds": 2.3},
            ])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_negotiations_returns_200(negotiations_analytics_client):
    response = await negotiations_analytics_client.get("/api/analytics/negotiations")
    assert response.status_code == 200
    data = response.json()
    assert data["avg_first_offer"] == 1900.0
    assert data["avg_final_rate"] == 2000.0
    assert len(data["strategy_effectiveness"]) == 1
    assert data["strategy_effectiveness"][0]["acceptance_rate"] == 80.0


# --- AI Quality Tests ---


@pytest.fixture
async def ai_quality_client():
    call_count = 0
    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            mock_cursor.to_list = AsyncMock(return_value=[{
                "total": 10,
                "compliant": 9,
                "avg_interruptions": 1.2,
                "transcription_errors": 1,
                "carrier_repeats": 2,
            }])
        elif call_count == 2:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "skipped_greeting", "count": 3},
            ])
        elif call_count == 3:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "2024-06-15", "avg": 1.5},
            ])
        elif call_count == 4:
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
    response = await ai_quality_client.get("/api/analytics/ai-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["protocol_compliance_rate"] == 90.0
    assert len(data["common_violations"]) == 1
    assert data["avg_interruptions"] == 1.2
    assert data["transcription_error_rate"] == 10.0
    assert data["carrier_repeat_rate"] == 20.0


# --- Carriers Tests ---


@pytest.fixture
async def carriers_client():
    call_count = 0
    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "positive", "count": 6},
                {"_id": "neutral", "count": 3},
                {"_id": "negative", "count": 1},
            ])
        elif call_count == 2:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "2024-06-15", "positive": 3, "neutral": 1, "negative": 0},
            ])
        elif call_count == 3:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "high", "count": 5},
                {"_id": "medium", "count": 3},
            ])
        elif call_count == 4:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": None, "total": 10, "interested": 7},
            ])
        elif call_count == 5:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "rate_too_low", "count": 4},
            ])
        elif call_count == 6:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": "Is the rate negotiable?", "count": 3},
            ])
        elif call_count == 7:
            mock_cursor.to_list = AsyncMock(return_value=[
                {"_id": 1234, "carrier_name": "TYROLER METALS", "calls": 5, "accepted": 4},
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
    response = await carriers_client.get("/api/analytics/carriers")
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment_distribution"]["positive"] == 6
    assert data["future_interest_rate"] == 70.0
    assert len(data["top_objections"]) == 1
    assert len(data["carrier_leaderboard"]) == 1
    assert data["carrier_leaderboard"][0]["acceptance_rate"] == 80.0
