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
