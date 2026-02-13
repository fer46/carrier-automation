# Carrier Load Automation

An API backend for an AI-powered voice agent that helps carriers find and book freight loads. The voice agent talks to carriers on the phone, collects their preferences (location, truck type, capacity), and uses this API to search loads and negotiate rates — all in real time.

## How It Works

```
Carrier calls in
       ↓
Voice AI extracts preferences (origin, destination, truck type, weight capacity)
       ↓
Voice AI calls  →  GET /api/loads/search  →  Returns matching loads ranked by relevance
       ↓
Carrier picks a load and proposes a rate
       ↓
Voice AI calls  →  POST /api/negotiations/evaluate  →  Accept or reject decision
       ↓
Voice AI confirms booking with the carrier
```

The API acts as the **decision engine** behind the voice agent. It handles two things:

1. **Load Search** — Find available freight that matches what the carrier wants
2. **Negotiation Guardrails** — Decide if a carrier's proposed rate is acceptable (never exceed our budget)

## Project Structure

```
app/
├── main.py              # App entry point, startup/shutdown, health check
├── config.py            # Environment variables (MongoDB URL, API key)
├── database.py          # MongoDB connection management
├── dependencies.py      # API key authentication
├── loads/               # Everything related to searching loads
│   ├── router.py        #   API endpoints (search, get by ID)
│   ├── service.py       #   Business logic (filtering, relevance scoring)
│   └── models.py        #   Data shapes (Load, LoadSearchParams, LoadResponse)
└── negotiations/        # Everything related to evaluating offers
    ├── router.py        #   API endpoint (evaluate offer)
    ├── service.py       #   Business logic (accept/reject decision)
    └── models.py        #   Data shapes (NegotiationRequest, NegotiationResponse)

tests/                   # Mirrors app/ structure, mocks the database
data/seed_loads.json     # 25 sample freight loads for development
scripts/seed_db.py       # Populates MongoDB with sample data
```

Each business domain (loads, negotiations) lives in its own folder with the same three files: `router.py` (endpoints), `service.py` (logic), `models.py` (data shapes). Routers stay thin — they just validate input and call the service layer.

## API Endpoints

All endpoints require an `X-API-Key` header.

### Search Loads

```
GET /api/loads/search
```

Find available loads matching carrier preferences. All filters are optional — omit them all to get every available load.

| Parameter        | Type   | Description                          |
| ---------------- | ------ | ------------------------------------ |
| `origin`         | string | City/state to pick up from           |
| `destination`    | string | City/state to deliver to             |
| `equipment_type` | string | Truck type (Dry Van, Reefer, Flatbed)|
| `min_rate`       | float  | Minimum pay rate ($)                 |
| `max_rate`       | float  | Maximum pay rate ($)                 |
| `max_weight`     | float  | Carrier's truck weight capacity (lbs)|
| `pickup_date`    | string | ISO date (e.g. `2026-02-15`)         |

**What happens behind the scenes:**
- Filters out loads that are already booked or have expired pickup dates
- Text filters (origin, destination, equipment) use case-insensitive partial matching
- Results are ranked by a **relevance score** (city match = 80%, rate per mile = 20%)
- Returns up to 100 loads, best matches first

### Get Load by ID

```
GET /api/loads/{load_id}
```

Fetch a single load's full details. Returns 404 if the load doesn't exist.

### Evaluate Negotiation

```
POST /api/negotiations/evaluate
```

The carrier proposes a rate; the API decides whether to accept or reject.

```json
{
  "load_id": "LD-005",
  "carrier_offer": 1900.00,
  "negotiation_round": 1
}
```

**The rule is simple:** if the carrier's offer is at or below our loadboard rate, accept. If it's above, reject. The response includes the margin percentage so the voice agent knows how much room it has.

```json
{
  "decision": "accept",
  "loadboard_rate": 2100.00,
  "margin_percent": 9.5,
  "reasoning": "Carrier offer $1,900.00 is within our rate $2,100.00 (9.5% margin). Safe to book."
}
```

The API also validates that the load exists, is still available, and hasn't expired before evaluating.

## Quick Start

### Prerequisites

- Python 3.13
- [uv](https://github.com/astral-sh/uv) (package manager)
- MongoDB (local or Atlas)

### Run Locally

```bash
# 1. Install dependencies
uv pip install -r requirements.txt

# 2. Configure environment — edit .env with your MongoDB URL and API key
#    MONGODB_URL="mongodb://localhost:27017"
#    DATABASE_NAME=carrier_load_automation
#    API_KEY="your-secret-key"

# 3. Seed the database with sample loads
.venv/bin/python scripts/seed_db.py

# 4. Start the server
.venv/bin/uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Check `http://localhost:8000/health` to verify it's running.

### Run with Docker

```bash
docker-compose up --build
```

This starts both the API (port 8000) and a MongoDB instance (port 27017) with persistent storage.

### Run Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

Tests mock the database entirely — no MongoDB needed.

## Tech Stack

| Component    | Technology                | Why                                         |
| ------------ | ------------------------- | ------------------------------------------- |
| Framework    | FastAPI                   | Async, auto-generated docs, type validation |
| Database     | MongoDB (Motor async)     | Flexible schema for varied load data        |
| Validation   | Pydantic                  | Type-safe request/response models           |
| Auth         | API key header            | Simple, sufficient for service-to-service   |
| Server       | Uvicorn                   | High-performance ASGI server                |
| Tests        | pytest + httpx            | Async test support with mocked DB           |
| Container    | Docker + docker-compose   | Consistent environments                     |

## Key Design Decisions

**Why relevance scoring instead of exact matching?**
Carriers give fuzzy descriptions ("I'm near Denver" not "Denver, CO"). Partial matching with scoring lets us return useful results even with imprecise input.

**Why is the negotiation logic so simple (offer <= rate)?**
This API is a safety guardrail, not a negotiation strategy engine. The voice AI handles the actual negotiation tactics. The API's job is to enforce one hard rule: never book above our loadboard rate.

**Why async everywhere?**
Every request hits MongoDB. Async I/O means the server can handle many concurrent requests without blocking — important when multiple voice agents are calling simultaneously.

**Why domain folders instead of flat files?**
As new domains are added (bookings, analytics, dashboard), each gets its own isolated folder. No single file grows too large, and teams can work on different domains independently.

## Adding a New Domain

1. Create `app/<domain>/` with `router.py`, `service.py`, `models.py`
2. Register the router in `app/main.py`
3. Add tests in `tests/<domain>/`
4. Follow the existing patterns — thin routers, logic in services, Pydantic models for everything
