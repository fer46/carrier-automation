# Carrier Load Automation

An API backend and analytics dashboard for an AI-powered voice agent that helps carriers find and book freight loads. The voice agent talks to carriers on the phone, collects their preferences (location, truck type, capacity), and uses this API to search loads — all in real time. The analytics dashboard provides operational intelligence on call outcomes, carrier performance, and lane geography.

## How It Works

```
Carrier calls in
       ↓
Voice AI extracts preferences (origin, destination, truck type, weight capacity)
       ↓
Voice AI calls  →  GET /api/loads/search  →  Returns matching loads ranked by relevance
       ↓
Voice AI confirms booking with the carrier
       ↓
Call record ingested  →  POST /api/analytics/calls  →  Powers the dashboard
```

The API acts as the **decision engine** behind the voice agent, and the dashboard provides **operational visibility** into the system's performance:

1. **Load Search** — Find available freight that matches what the carrier wants
2. **Analytics** — Aggregate call records into KPIs, negotiation metrics, carrier stats, and lane geography

## Project Structure

```
app/
├── main.py              # App entry point, startup/shutdown, health check, SPA serving
├── config.py            # Environment variables (MongoDB URL, API key)
├── database.py          # MongoDB connection management
├── dependencies.py      # API key authentication
├── loads/               # Everything related to searching loads
│   ├── router.py        #   API endpoints (search, get by ID)
│   ├── service.py       #   Business logic (filtering, relevance scoring)
│   └── models.py        #   Data shapes (Load, LoadSearchParams, LoadResponse)
└── analytics/           # Everything related to call analytics
    ├── router.py        #   API endpoints (summary, operations, negotiations, carriers, geography)
    ├── service.py       #   Aggregation logic (KPIs, funnels, lane parsing)
    ├── models.py        #   Response shapes (SummaryResponse, OperationsResponse, etc.)
    └── lane_parser.py   #   Utilities for parsing lane descriptions into origin/destination

dashboard/               # React + TypeScript analytics UI
├── src/
│   ├── App.tsx          #   Main app with tab navigation
│   ├── api.ts           #   HTTP client for analytics API
│   ├── types.ts         #   TypeScript interfaces for API responses
│   └── components/      #   Tab components (Operations, Negotiations, Carriers, Geography)
├── package.json         #   Dependencies (React 19, Recharts, react-simple-maps, Tailwind CSS 4)
└── vite.config.ts       #   Vite build configuration

tests/                   # Mirrors app/ structure, mocks the database
data/seed_loads.json     # Sample freight loads for development
scripts/
├── seed_db.py           # Populates MongoDB with sample loads
└── seed_call_records.py # Generates realistic call records for the analytics dashboard
docs/                    # Architecture docs and implementation plans
```

Each business domain (loads, analytics) lives in its own folder with the same three files: `router.py` (endpoints), `service.py` (logic), `models.py` (data shapes). Routers stay thin — they just validate input and call the service layer.

## API Endpoints

All endpoints require an `X-API-Key` header.

### Search Loads

```
GET /api/loads/search
```

Find available loads matching carrier preferences. All filters are optional — omit them all to get every available load. Requires `validation_check=VALID` as a guardrail.

| Parameter          | Type   | Description                          |
| ------------------ | ------ | ------------------------------------ |
| `validation_check` | string | Must be "VALID" (required guardrail) |
| `origin`           | string | City/state to pick up from           |
| `destination`      | string | City/state to deliver to             |
| `equipment_type`   | string | Truck type (Dry Van, Reefer, Flatbed)|
| `min_rate`         | string | Minimum pay rate ($)                 |
| `max_rate`         | string | Maximum pay rate ($)                 |
| `max_weight`       | string | Carrier's truck weight capacity (lbs)|
| `pickup_date`      | string | ISO date (e.g. `2026-02-15`)         |

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

### Analytics Endpoints

All analytics endpoints accept optional `from` and `to` query parameters for date range filtering.

| Endpoint                       | Method | Description                                          |
| ------------------------------ | ------ | ---------------------------------------------------- |
| `POST /api/analytics/calls`   | POST   | Ingest a call record from the voice AI               |
| `GET /api/analytics/summary`  | GET    | High-level KPIs (total calls, bookings, revenue)     |
| `GET /api/analytics/operations` | GET  | Operations metrics and lane volume data              |
| `GET /api/analytics/negotiations` | GET | Negotiation outcomes (booked, declined, pending)   |
| `GET /api/analytics/carriers`  | GET   | Carrier performance metrics and rankings             |
| `GET /api/analytics/geography` | GET   | Geographic arc data for requested vs booked lanes    |

## Dashboard

The analytics dashboard is served at `/dashboard` from the FastAPI app. It visualizes call record data across four tabs:

- **Operations** — Lane volumes, call distribution, operational KPIs
- **Negotiations** — Outcome donut charts, savings metrics, conversion funnels
- **Carriers** — Carrier performance rankings and activity metrics
- **Geography** — Arc map showing requested vs booked lanes on a US map

Built with React 19, TypeScript, Tailwind CSS 4, Recharts, and react-simple-maps.

## Quick Start

### Prerequisites

- Python 3.13
- [uv](https://github.com/astral-sh/uv) (package manager)
- MongoDB (local or Atlas)
- Node.js 20+ (for dashboard development)

### Run Locally

```bash
# 1. Install Python dependencies
uv pip install -r requirements.txt

# 2. Configure environment — edit .env with your MongoDB URL and API key
#    MONGODB_URL="mongodb://localhost:27017"
#    DATABASE_NAME=carrier_load_automation
#    API_KEY="your-secret-key"

# 3. Seed the database with sample loads
.venv/bin/python scripts/seed_db.py

# 4. (Optional) Seed call records for the analytics dashboard
.venv/bin/python -m scripts.seed_call_records

# 5. Build the dashboard
cd dashboard && npm install && npm run build && cd ..

# 6. Start the server
.venv/bin/uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Check `http://localhost:8000/health` to verify it's running. The dashboard is at `http://localhost:8000/dashboard`.

### Run with Docker

```bash
docker-compose up --build
```

This starts both the API (port 8000) and a MongoDB instance (port 27017) with persistent storage. The Dockerfile builds the dashboard automatically.

### Run Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

Tests mock the database entirely — no MongoDB needed.

## Tech Stack

| Component    | Technology                         | Why                                         |
| ------------ | ---------------------------------- | ------------------------------------------- |
| Framework    | FastAPI                            | Async, auto-generated docs, type validation |
| Database     | MongoDB (Motor async)              | Flexible schema for varied load data        |
| Validation   | Pydantic                           | Type-safe request/response models           |
| Auth         | API key header                     | Simple, sufficient for service-to-service   |
| Server       | Uvicorn                            | High-performance ASGI server                |
| Tests        | pytest + httpx                     | Async test support with mocked DB           |
| Container    | Docker + docker-compose            | Consistent environments                     |
| Dashboard    | React 19 + TypeScript + Tailwind 4 | Modern UI with type safety                  |
| Charts       | Recharts + react-simple-maps       | Data visualization and geographic arcs      |
| Build        | Vite                               | Fast frontend build tooling                 |

## Key Design Decisions

**Why relevance scoring instead of exact matching?**
Carriers give fuzzy descriptions ("I'm near Denver" not "Denver, CO"). Partial matching with scoring lets us return useful results even with imprecise input.

**Why async everywhere?**
Every request hits MongoDB. Async I/O means the server can handle many concurrent requests without blocking — important when multiple voice agents are calling simultaneously.

**Why domain folders instead of flat files?**
As new domains are added (bookings, pricing), each gets its own isolated folder. No single file grows too large, and teams can work on different domains independently.

**Why serve the dashboard from FastAPI?**
Single deployment: one Docker container serves both the API and the dashboard UI. The dashboard is built into static files by Vite and served at `/dashboard` using FastAPI's static file mounting.

## Adding a New Domain

1. Create `app/<domain>/` with `router.py`, `service.py`, `models.py`
2. Register the router in `app/main.py`
3. Add tests in `tests/<domain>/`
4. Follow the existing patterns — thin routers, logic in services, Pydantic models for everything
