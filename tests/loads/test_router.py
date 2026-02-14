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
    response = await client.get("/api/loads/search", params={"validation_check": "VALID", "origin": "Dallas"})
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


async def test_search_loads_requires_api_key():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/loads/search")
        assert response.status_code == 422
