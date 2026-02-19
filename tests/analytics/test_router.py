from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.asyncio

API_KEY = settings.API_KEY

SAMPLE_CALL_RECORD = {
    "system": {"call_id": "test-call-001", "call_duration": 245},
    "fmcsa_data": {
        "carrier_mc_number": 1234,
        "carrier_name": "TYROLER METALS INC",
        "carrier_validation_result": "VALID",
        "retrieval_date": "2026-02-13T19:45:01.867+0000",
    },
    "load_data": {
        "load_id_discussed": "LD-001",
        "alternate_loads_presented": 1,
        "loadboard_rate": 2200.00,
        "origin": "Chicago, IL",
        "destination": "Dallas, TX",
        "carrier_requested_lane": "Chicago, IL → Dallas, TX",
        "equipment_type": "Dry Van",
        "miles": 920.0,
        "pickup_datetime": "2026-02-14T08:00:00",
        "delivery_datetime": "2026-02-15T18:00:00",
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
            "call_outcome": "Success",
            "rejection_reason": None,
            "funnel_stage_reached": "transferred_to_sales",
        },
        "sentiment": {
            "call_sentiment": "positive",
            "sentiment_progression": "improving",
            "engagement_level": "high",
            "carrier_expressed_interest_future": True,
        },
        "operational": {
            "transfer_to_sales_attempted": False,
            "transfer_to_sales_completed": False,
            "transfer_reason": None,
            "loads_presented_count": 2,
        },
        "optional": {
            "negotiation_strategy_used": "anchoring_high",
            "carrier_negotiation_leverage": ["fuel_prices_mentioned"],
            "carrier_objections": ["rate_too_low"],
            "carrier_questions_asked": ["Is the rate negotiable?"],
        },
    },
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
    response = await ingest_client.post("/api/analytics/calls", json=SAMPLE_CALL_RECORD)
    assert response.status_code == 201
    data = response.json()
    assert data["call_id"] == "test-call-001"
    assert data["status"] in ("created", "updated")


async def test_ingest_call_record_requires_api_key():
    """POST without API key -> 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/analytics/calls", json=SAMPLE_CALL_RECORD)
        assert response.status_code == 422


async def test_ingest_call_record_validates_body(ingest_client):
    """POST with invalid body -> 422."""
    response = await ingest_client.post("/api/analytics/calls", json={"bad": "data"})
    assert response.status_code == 422


async def test_ingest_sets_ingested_at_on_insert():
    """ingest_call_record uses $setOnInsert to stamp ingested_at on new records."""
    mock_db = _make_mock_db(find_one_result=None)
    mock_db.call_records.update_one = AsyncMock(return_value=MagicMock(upserted_id="new"))
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            before = datetime.now(tz=UTC)
            await ac.post("/api/analytics/calls", json=SAMPLE_CALL_RECORD)
            after = datetime.now(tz=UTC)

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
    mock_db = _make_mock_db(
        aggregate_result=[
            {
                "total_calls": 10,
                "accepted": 7,
                "avg_duration": 245.5,
                "avg_rounds": 2.1,
                "avg_margin": 8.4,
                "total_margin_earned": 1400.0,
                "booked_revenue": 16940.0,
                "avg_rate_per_mile": 2.17,
                "unique_carriers": [1234, 5678, 9012, 3456, 7890],
            }
        ]
    )
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
    assert data["total_margin_earned"] == 1400.0
    assert data["booked_revenue"] == 16940.0
    assert data["avg_rate_per_mile"] == 2.17
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
            assert data["booked_revenue"] == 0.0


# --- Operations Tests ---


@pytest.fixture
async def operations_client():
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            # Pipeline 1: calls_over_time
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "2024-06-15", "count": 5},
                    {"_id": "2024-06-16", "count": 3},
                ]
            )
        elif call_count == 2:
            # Pipeline 2: rejection_reasons
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "rate_too_high", "count": 2},
                ]
            )
        elif call_count == 3:
            # Pipeline 3: conversion funnel
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "call_started", "count": 100},
                    {"_id": "fmcsa_verified", "count": 90},
                    {"_id": "load_matched", "count": 75},
                    {"_id": "offer_pitched", "count": 60},
                    {"_id": "negotiation_entered", "count": 45},
                    {"_id": "deal_agreed", "count": 30},
                    {"_id": "transferred_to_sales", "count": 20},
                ]
            )
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
    assert "outcome_distribution" not in data
    assert "avg_duration_over_time" not in data
    assert "transfer_rate" not in data
    assert len(data["calls_over_time"]) == 2
    assert len(data["rejection_reasons"]) == 1
    # Funnel assertions (cumulative: each stage includes records that reached it or later)
    # Raw: call_started=100, fmcsa_verified=90, load_matched=75, offer_pitched=60,
    #       negotiation_entered=45, deal_agreed=30, transferred_to_sales=20
    # Cumulative: 420, 320, 230, 155, 95, 50, 20
    assert len(data["funnel"]) == 7
    assert data["funnel"][0]["stage"] == "call_started"
    assert data["funnel"][0]["count"] == 420
    assert data["funnel"][0]["drop_off_percent"] == 0.0
    assert data["funnel"][-1]["stage"] == "transferred_to_sales"
    assert data["funnel"][-1]["count"] == 20
    assert data["funnel"][-1]["drop_off_percent"] == 95.2


# --- Negotiations Tests ---


@pytest.fixture
async def negotiations_analytics_client():
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {
                        "avg_savings": 150.0,
                        "avg_savings_percent": 7.5,
                        "avg_rounds": 2.1,
                    }
                ]
            )
        elif call_count == 2:
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "Accepted at First Offer", "count": 3},
                    {"_id": "Negotiated & Agreed", "count": 5},
                    {"_id": "No Deal", "count": 2},
                ]
            )
        elif call_count == 3:
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": 0, "count": 3},
                    {"_id": 5, "count": 5},
                    {"_id": 10, "count": 2},
                ]
            )
        elif call_count == 4:
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "anchoring_high", "total": 10, "accepted": 8, "avg_rounds": 2.3},
                ]
            )
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
    assert data["avg_savings"] == 150.0
    assert data["avg_savings_percent"] == 7.5
    assert "rate_progression" not in data
    assert "avg_first_offer" not in data
    outcomes = data["negotiation_outcomes"]
    assert len(outcomes) == 3
    assert outcomes[0]["name"] == "Accepted at First Offer"
    assert outcomes[0]["count"] == 3
    assert outcomes[1]["name"] == "Negotiated & Agreed"
    assert outcomes[1]["count"] == 5
    assert outcomes[2]["name"] == "No Deal"
    assert outcomes[2]["count"] == 2
    assert len(data["strategy_effectiveness"]) == 1
    assert data["strategy_effectiveness"][0]["acceptance_rate"] == 80.0


async def test_negotiations_empty_dataset():
    """All pipelines return empty results -> safe zero defaults, no crash."""
    mock_db = _make_mock_db()
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        return mock_cursor

    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            response = await ac.get("/api/analytics/negotiations")
            assert response.status_code == 200
            data = response.json()
            assert data["avg_savings"] == 0.0
            assert data["avg_savings_percent"] == 0.0
            assert data["avg_rounds"] == 0.0
            # All 3 outcome categories must still appear with count 0
            outcomes = data["negotiation_outcomes"]
            assert len(outcomes) == 3
            for o in outcomes:
                assert o["count"] == 0
            assert data["margin_distribution"] == []
            assert data["strategy_effectiveness"] == []


async def test_negotiations_null_savings_from_pipeline():
    """Pipeline returns None values for savings fields -> defaults to 0, no crash."""
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            # Savings pipeline returns None for all computed fields
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"avg_savings": None, "avg_savings_percent": None, "avg_rounds": None}
                ]
            )
        else:
            mock_cursor.to_list = AsyncMock(return_value=[])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            response = await ac.get("/api/analytics/negotiations")
            assert response.status_code == 200
            data = response.json()
            assert data["avg_savings"] == 0.0
            assert data["avg_savings_percent"] == 0.0
            assert data["avg_rounds"] == 0.0


async def test_negotiations_missing_outcome_categories():
    """Only some outcome categories returned -> all 3 present, missing ones get count=0."""
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 2:
            # Only "No Deal" comes from DB; the other two are missing
            mock_cursor.to_list = AsyncMock(return_value=[{"_id": "No Deal", "count": 5}])
        else:
            mock_cursor.to_list = AsyncMock(return_value=[])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            response = await ac.get("/api/analytics/negotiations")
            assert response.status_code == 200
            outcomes = {o["name"]: o["count"] for o in response.json()["negotiation_outcomes"]}
            assert outcomes == {
                "Accepted at First Offer": 0,
                "Negotiated & Agreed": 0,
                "No Deal": 5,
            }


async def test_negotiations_margin_bucket_labels():
    """All 6 margin bucket IDs map to correct human-readable labels."""
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 3:
            # All 6 standard bucket boundaries
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": -100, "count": 1},
                    {"_id": 0, "count": 10},
                    {"_id": 5, "count": 8},
                    {"_id": 10, "count": 6},
                    {"_id": 15, "count": 3},
                    {"_id": 20, "count": 2},
                ]
            )
        else:
            mock_cursor.to_list = AsyncMock(return_value=[])
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            response = await ac.get("/api/analytics/negotiations")
            assert response.status_code == 200
            buckets = {b["range"]: b["count"] for b in response.json()["margin_distribution"]}
            assert buckets == {
                "<0%": 1,
                "0-5%": 10,
                "5-10%": 8,
                "10-15%": 6,
                "15-20%": 3,
                "20%+": 2,
            }


# --- Carriers Tests ---


@pytest.fixture
async def carriers_client():
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            # Pipeline 1: top objections
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "rate_too_low", "count": 4},
                ]
            )
        elif call_count == 2:
            # Pipeline 2: carrier leaderboard
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": 1234, "carrier_name": "TYROLER METALS", "calls": 5, "accepted": 4},
                ]
            )
        elif call_count == 3:
            # Pipeline 3: top requested lanes
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "Chicago, IL → Dallas, TX", "count": 12},
                    {"_id": "Atlanta, GA → Miami, FL", "count": 8},
                ]
            )
        elif call_count == 4:
            # Pipeline 4: top actual lanes
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "Chicago, IL → Dallas, TX", "count": 10},
                    {"_id": "LA, CA → Phoenix, AZ", "count": 6},
                ]
            )
        elif call_count == 5:
            # Pipeline 5: equipment distribution
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "Dry Van", "count": 15},
                    {"_id": "Reefer", "count": 8},
                    {"_id": "Flatbed", "count": 3},
                ]
            )
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
    assert "sentiment_distribution" not in data
    assert "future_interest_rate" not in data
    assert "engagement_levels" not in data
    assert "top_questions" not in data
    assert len(data["top_objections"]) == 1
    assert len(data["carrier_leaderboard"]) == 1
    assert data["carrier_leaderboard"][0]["acceptance_rate"] == 80.0
    # Lane intelligence assertions
    assert len(data["top_requested_lanes"]) == 2
    assert data["top_requested_lanes"][0]["lane"] == "Chicago, IL \u2192 Dallas, TX"
    assert data["top_requested_lanes"][0]["count"] == 12
    assert len(data["top_actual_lanes"]) == 2
    assert data["top_actual_lanes"][0]["lane"] == "Chicago, IL \u2192 Dallas, TX"
    assert len(data["equipment_distribution"]) == 3
    assert data["equipment_distribution"][0]["equipment_type"] == "Dry Van"


# --- Geography Tests ---


@pytest.fixture
async def geography_client():
    call_count = 0

    def side_effect_aggregate(pipeline):
        nonlocal call_count
        call_count += 1
        mock_cursor = AsyncMock()
        if call_count == 1:
            # Pipeline 1: requested lanes (free-form text)
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": "Chicago, IL \u2192 Dallas, TX", "count": 5},
                    {"_id": "Timbuktu -> Nowhere", "count": 2},  # unparseable
                ]
            )
        elif call_count == 2:
            # Pipeline 2: booked lanes (origin/destination dicts)
            mock_cursor.to_list = AsyncMock(
                return_value=[
                    {"_id": {"origin": "Atlanta, GA", "destination": "Miami, FL"}, "count": 3},
                ]
            )
        return mock_cursor

    mock_db = _make_mock_db()
    mock_db.call_records.aggregate = MagicMock(side_effect=side_effect_aggregate)
    with patch("app.analytics.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


async def test_geography_returns_200(geography_client):
    response = await geography_client.get("/api/analytics/geography")
    assert response.status_code == 200
    data = response.json()
    # 1 requested arc (unparseable skipped) + 1 booked arc = 2 total
    assert len(data["arcs"]) == 2
    requested = [a for a in data["arcs"] if a["arc_type"] == "requested"]
    booked = [a for a in data["arcs"] if a["arc_type"] == "booked"]
    assert len(requested) == 1
    assert len(booked) == 1
    # Check requested arc coordinates
    assert requested[0]["origin"] == "Chicago, IL"
    assert requested[0]["destination"] == "Dallas, TX"
    assert requested[0]["origin_lat"] != 0
    assert requested[0]["origin_lng"] != 0
    # Check booked arc
    assert booked[0]["origin"] == "Atlanta, GA"
    assert booked[0]["destination"] == "Miami, FL"
    # Cities: Chicago, Dallas, Atlanta, Miami = 4
    assert len(data["cities"]) == 4
    city_names = {c["name"] for c in data["cities"]}
    assert "Chicago, IL" in city_names
    assert "Dallas, TX" in city_names
    assert "Atlanta, GA" in city_names
    assert "Miami, FL" in city_names
