from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.fixture
def api_key():
    return settings.API_KEY


@pytest.fixture
def sample_loads():
    return [
        {
            "load_id": "LD-001",
            "origin": "Dallas, TX",
            "destination": "Miami, FL",
            "pickup_datetime": "2027-06-15T08:00:00",
            "delivery_datetime": "2027-06-17T14:00:00",
            "equipment_type": "Dry Van",
            "loadboard_rate": 2800,
            "status": "available",
            "notes": "Fragile electronics, secure stacking required",
            "weight": 18000,
            "commodity_type": "Electronics",
            "num_of_pieces": 45,
            "miles": 1320,
            "dimensions": "48x40x60",
        }
    ]


def _make_mock_db(loads_data, find_one_result, call_pressure_results=None):
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=loads_data)

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_collection.find_one = AsyncMock(return_value=find_one_result)

    mock_agg_cursor = AsyncMock()
    mock_agg_cursor.to_list = AsyncMock(return_value=call_pressure_results or [])
    mock_call_records = MagicMock()
    mock_call_records.aggregate = MagicMock(return_value=mock_agg_cursor)

    mock_db = MagicMock()
    mock_db.loads = mock_collection
    mock_db.call_records = mock_call_records
    return mock_db


@pytest.fixture
async def client(api_key, sample_loads):
    mock_db = _make_mock_db(sample_loads, sample_loads[0])

    with patch("app.loads.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = api_key
            yield ac
