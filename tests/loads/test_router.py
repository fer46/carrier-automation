from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_search_loads_returns_200(client):
    response = await client.get("/api/loads/search", params={"validation_check": "VALID"})
    assert response.status_code == 200
    data = response.json()
    assert "loads" in data
    assert "total" in data


async def test_search_loads_filters_by_origin(client):
    params = {"validation_check": "VALID", "origin": "Dallas"}
    response = await client.get("/api/loads/search", params=params)
    assert response.status_code == 200
    data = response.json()
    for load in data["loads"]:
        assert "Dallas" in load["origin"]


async def test_get_load_by_id_returns_load(client):
    response = await client.get("/api/loads/LD-001")
    assert response.status_code == 200
    data = response.json()
    assert data["load_id"] == "LD-001"


async def test_get_load_not_found(client):
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_collection.find_one = AsyncMock(return_value=None)

    mock_db = MagicMock()
    mock_db.loads = mock_collection

    with patch("app.loads.service.get_database", return_value=mock_db):
        response = await client.get("/api/loads/NONEXISTENT")
        assert response.status_code == 404


async def test_search_loads_includes_pricing_cold_load(client):
    """Cold load (far future pickup, no call history) → base rates."""
    response = await client.get("/api/loads/search", params={"validation_check": "VALID"})
    assert response.status_code == 200
    data = response.json()
    for load in data["loads"]:
        assert "target_carrier_rate" in load
        assert "cap_carrier_rate" in load
        # Cold load: pressure=0 → target=0.95×, cap=1.0×
        expected_target = round(load["loadboard_rate"] * 0.95, 2)
        expected_cap = round(load["loadboard_rate"] * 1.0, 2)
        assert load["target_carrier_rate"] == expected_target
        assert load["cap_carrier_rate"] == expected_cap


async def test_get_load_by_id_includes_pricing_cold_load(client):
    """Cold load via get_by_id → base rates."""
    response = await client.get("/api/loads/LD-001")
    assert response.status_code == 200
    data = response.json()
    # Cold load: loadboard_rate=2800 → target=2660.0, cap=2800.0
    assert data["target_carrier_rate"] == 2660.0
    assert data["cap_carrier_rate"] == 2800.0


async def test_dynamic_pricing_with_rate_rejections(api_key, sample_loads):
    """Rate rejections increase target and cap via pressure."""
    from tests.conftest import _make_mock_db

    call_pressure = [
        {"_id": "LD-001", "total_calls": 5, "rate_rejections": 3},
    ]
    mock_db = _make_mock_db(sample_loads, sample_loads[0], call_pressure)

    with patch("app.loads.service.get_database", return_value=mock_db):
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = api_key
            response = await ac.get("/api/loads/LD-001")
            data = response.json()
            # 3 rejections → rejection_pressure=0.6, pickup far → urgency=0
            # pressure=0.6 → target=0.95+0.03=0.98×, cap=1.0+min(0.036,0.05)=1.036×
            assert data["target_carrier_rate"] == round(2800 * 0.98, 2)
            assert data["cap_carrier_rate"] == round(2800 * 1.036, 2)


async def test_delivery_date_only_includes_same_day_loads(api_key, sample_loads):
    """Date-only delivery filter should include loads delivering on that date.

    The voice AI sends "2027-06-17" (no time component). The DB stores
    "2027-06-17T14:00:00". Without the fix, the $lte comparison would
    exclude these loads because "T14:00:00" sorts after end-of-string.
    """
    from tests.conftest import _make_mock_db

    mock_db = _make_mock_db(sample_loads, sample_loads[0])

    with patch("app.loads.service.get_database", return_value=mock_db):
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = api_key
            response = await ac.get(
                "/api/loads/search",
                params={
                    "validation_check": "VALID",
                    "delivery_datetime": "2027-06-17",
                },
            )
            assert response.status_code == 200
            # The mock DB always returns sample_loads, but verify the query
            # was built correctly by checking that the delivery filter includes
            # the T23:59:59 suffix
            call_args = mock_db.loads.find.call_args
            query = call_args[0][0]
            assert query["delivery_datetime"] == {"$lte": "2027-06-17T23:59:59"}


async def test_search_loads_requires_api_key():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loads/search")
        assert response.status_code == 422
