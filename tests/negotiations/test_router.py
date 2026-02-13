from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.asyncio

API_KEY = settings.API_KEY

# --- Sample load data for mocking ---
# A valid, available load with a future pickup date.
AVAILABLE_LOAD = {
    "load_id": "LD-001",
    "origin": "Dallas, TX",
    "destination": "Miami, FL",
    "pickup_datetime": "2099-12-31T08:00:00",
    "delivery_datetime": "2099-12-31T18:00:00",
    "equipment_type": "Dry Van",
    "loadboard_rate": 2800,
    "status": "available",
    "notes": "Test load",
    "weight": 18000,
    "commodity_type": "Electronics",
    "num_of_pieces": 45,
    "miles": 1320,
    "dimensions": "48x40x60",
}

# A load that has already been booked.
BOOKED_LOAD = {**AVAILABLE_LOAD, "status": "booked"}

# A load with a pickup date in the past (expired).
EXPIRED_LOAD = {**AVAILABLE_LOAD, "pickup_datetime": "2020-01-01T08:00:00"}


# --- Helper to build a mock database ---

def _make_mock_db(find_one_result):
    """Create a mock MongoDB with a loads collection returning find_one_result."""
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=find_one_result)

    mock_db = MagicMock()
    mock_db.loads = mock_collection
    return mock_db


# --- Fixtures ---

@pytest.fixture
async def client():
    """HTTP client with a mocked DB where the load exists and is available."""
    mock_db = _make_mock_db(find_one_result=AVAILABLE_LOAD)
    with patch("app.negotiations.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


@pytest.fixture
async def client_no_load():
    """HTTP client with a mocked DB where the load does NOT exist."""
    mock_db = _make_mock_db(find_one_result=None)
    with patch("app.negotiations.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


@pytest.fixture
async def client_booked_load():
    """HTTP client with a mocked DB where the load is already booked."""
    mock_db = _make_mock_db(find_one_result=BOOKED_LOAD)
    with patch("app.negotiations.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


@pytest.fixture
async def client_expired_load():
    """HTTP client with a mocked DB where the load's pickup date has passed."""
    mock_db = _make_mock_db(find_one_result=EXPIRED_LOAD)
    with patch("app.negotiations.service.get_database", return_value=mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-API-Key"] = API_KEY
            yield ac


# --- Tests: Accept/Reject decisions ---

async def test_accept_offer_below_rate(client):
    """Carrier offers less than loadboard_rate → accept (we save money)."""
    response = await client.post("/api/negotiations/evaluate", json={
        "load_id": "LD-001",
        "carrier_offer": 2300,
        "negotiation_round": 1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "accept"
    assert data["loadboard_rate"] == 2800
    # margin = (2800 - 2300) / 2800 * 100 = 17.9%
    assert data["margin_percent"] == 17.9


async def test_accept_offer_equal_to_rate(client):
    """Carrier offers exactly loadboard_rate → accept (0% margin but still safe)."""
    response = await client.post("/api/negotiations/evaluate", json={
        "load_id": "LD-001",
        "carrier_offer": 2800,
        "negotiation_round": 1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "accept"
    assert data["margin_percent"] == 0.0


async def test_reject_offer_above_rate(client):
    """Carrier offers more than loadboard_rate → reject (hard limit)."""
    response = await client.post("/api/negotiations/evaluate", json={
        "load_id": "LD-001",
        "carrier_offer": 3000,
        "negotiation_round": 1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "reject"
    assert data["loadboard_rate"] == 2800
    # margin = (2800 - 3000) / 2800 * 100 = -7.1%
    assert data["margin_percent"] == -7.1


# --- Tests: Load validation ---

async def test_load_not_found(client_no_load):
    """Negotiating on a non-existent load → 404."""
    response = await client_no_load.post("/api/negotiations/evaluate", json={
        "load_id": "NONEXISTENT",
        "carrier_offer": 2000,
        "negotiation_round": 1,
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Load not found"


async def test_load_already_booked(client_booked_load):
    """Negotiating on a booked load → 400."""
    response = await client_booked_load.post("/api/negotiations/evaluate", json={
        "load_id": "LD-001",
        "carrier_offer": 2000,
        "negotiation_round": 1,
    })
    assert response.status_code == 400
    assert "not available" in response.json()["detail"]


async def test_load_expired(client_expired_load):
    """Negotiating on an expired load (pickup in the past) → 400."""
    response = await client_expired_load.post("/api/negotiations/evaluate", json={
        "load_id": "LD-001",
        "carrier_offer": 2000,
        "negotiation_round": 1,
    })
    assert response.status_code == 400
    assert "not available" in response.json()["detail"]


# --- Tests: Auth ---

async def test_requires_api_key():
    """Requests without an API key should be rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/negotiations/evaluate", json={
            "load_id": "LD-001",
            "carrier_offer": 2000,
            "negotiation_round": 1,
        })
        assert response.status_code == 422


# --- Tests: Response includes margin context ---

async def test_response_includes_margin_context(client):
    """Response should always include loadboard_rate and margin_percent."""
    response = await client.post("/api/negotiations/evaluate", json={
        "load_id": "LD-001",
        "carrier_offer": 2100,
        "negotiation_round": 2,
    })
    assert response.status_code == 200
    data = response.json()
    # Verify all fields are present
    assert "decision" in data
    assert "loadboard_rate" in data
    assert "margin_percent" in data
    assert "reasoning" in data
    # margin = (2800 - 2100) / 2800 * 100 = 25.0%
    assert data["margin_percent"] == 25.0
