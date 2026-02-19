# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Carrier Load Automation

AI-powered carrier load booking system with analytics dashboard. A voice AI agent talks to carriers on the phone, uses this API to search freight loads in real time, and the dashboard provides operational visibility into call outcomes, carrier performance, and lane geography.

FastAPI + MongoDB (Motor async) + Pydantic + React/TypeScript.

### Architecture
- **Domain-driven structure**: Each domain gets its own folder under `app/` with `router.py`, `service.py`, `models.py`
- **Current domains**: `loads` (search & get by ID, dynamic pricing), `analytics` (call record aggregation, KPIs, geography)
- **Dashboard**: React 19 + TypeScript + Tailwind CSS 4 + Recharts + react-simple-maps, served at `/dashboard`
- **Auth**: API key via `X-API-Key` header, timing-safe comparison (`hmac.compare_digest`) in `app/dependencies.py`
- **DB**: MongoDB via Motor async driver, lifecycle managed in `app/database.py` (module-level global client, `get_database()` raises `RuntimeError` if called before `connect_db()`)
- **Config**: Pydantic Settings in `app/config.py`, reads from `.env` (includes `CORS_ORIGINS` as comma-separated string, `DOCS_ENABLED`)

### Key Paths
- `app/main.py` — FastAPI app entry point (lifespan, routers, health check, SPA serving)
- `app/loads/` — Loads domain (router, service, models)
- `app/analytics/` — Analytics domain (router, service, models, lane_parser)
- `dashboard/src/` — React dashboard (App, api, types, components/)
- `data/seed_loads.json` — Sample load data
- `scripts/seed_db.py` — Seeds MongoDB with loads from JSON
- `scripts/seed_call_records.py` — Generates 150 realistic call records (`_mock: True` tagged, `--clean` removes only mock data)
- `tests/` — Mirrors app structure, uses mocked MongoDB
- `.github/workflows/ci.yml` — CI pipeline (lint, test, dashboard build — all 3 jobs run in parallel)
- `docs/` — Architecture docs and implementation plans

### Commands
- **Install deps**: `uv pip install -r requirements.txt`
- **Run locally**: `.venv/bin/uvicorn app.main:app --reload`
- **Run all tests**: `.venv/bin/python -m pytest tests/ -v`
- **Run single test file**: `.venv/bin/python -m pytest tests/loads/test_router.py -v`
- **Run single test**: `.venv/bin/python -m pytest tests/loads/test_router.py::test_search_loads_returns_200 -v`
- **Lint (ruff)**: `.venv/bin/ruff check app/ tests/ scripts/`
- **Format check**: `.venv/bin/ruff format --check app/ tests/ scripts/`
- **Type check**: `.venv/bin/mypy app/`
- **Docker**: `docker-compose up --build`
- **Seed loads**: `.venv/bin/python scripts/seed_db.py`
- **Seed call records**: `.venv/bin/python -m scripts.seed_call_records`
- **Dashboard dev**: `cd dashboard && npm run dev`
- **Dashboard build**: `cd dashboard && npm install && npm run build`
- **Dashboard lint**: `cd dashboard && npm run lint`

### Tech Constraints
- **Python 3.13** — use `Optional[X]` from `typing` for nullable types (explicit project convention; ruff `UP045` is ignored in `pyproject.toml`)
- **Ruff line-length**: 99 characters (not the default 88)
- **Package manager**: Always use `uv` for installs, never raw `pip`
- **Async everywhere**: All DB operations and endpoints are async
- **pytest asyncio_mode = "auto"**: All `async def test_*` functions are automatically async tests — no `@pytest.mark.asyncio` decorator needed
- **Dashboard**: React 19, TypeScript 5.9, Tailwind CSS 4, Vite 7, Recharts 3

### Conventions
- Routers mount under `/api/<domain>/` prefix
- Service layer handles business logic and DB queries, routers stay thin
- Models: `<Entity>` (DB doc), `<Entity>SearchParams` (query), `<Entity>Response` (API response)
- Exclude `_id` from MongoDB query results with `{"_id": 0}`
- Dashboard components: one per tab (OperationsTab, NegotiationsTab, CarriersTab, GeographyTab)
- API client in `dashboard/src/api.ts` (generic `fetchAPI<T>` wrapper, uses `window.location.origin` as base), types in `dashboard/src/types.ts` (manually kept in sync with Pydantic models)

### Testing Patterns
- **Mock patch path**: Always patch `app.<domain>.service.get_database`, NOT `app.database.get_database`. Patching the wrong path silently does nothing.
- **Client**: `httpx.AsyncClient` with `ASGITransport(app=app)`, no real server. API key set via `ac.headers["X-API-Key"]`.
- **Multi-pipeline mocking**: Analytics service fires sequential `aggregate()` calls (named `p1`, `p2`, `p3`...). Tests use a `call_count` closure with `side_effect` — the order must match pipeline execution order in the service. If you add or reorder pipelines, update test fixtures.
- **`_make_mock_db` helpers**: `tests/conftest.py` has one for loads; analytics tests define their own local versions per file (same name, different signature).

### Non-obvious Domain Logic
- **`validation_check=VALID` guardrail**: Load search requires this query param (FMCSA carrier validation). Any other value → 403.
- **Dynamic pricing**: `target_carrier_rate` and `cap_carrier_rate` are computed on every search/get call, never stored. Pressure = `max(urgency, rejection_pressure)`.
- **Cross-domain query**: `loads/service.py` queries the `call_records` collection directly for rejection pressure calculation.
- **Relevance scoring**: origin 40% + destination 40% + rate-per-mile 20%. Exact city match (state stripped) → full weight; substring → half.
- **`_WebhookModel` base class** (analytics `models.py`): Auto-coerces `""` to `None`, wraps bare strings into `[value]` for list fields, and coerces `""`/`null` to `[]` for list fields. Handles messy webhook payloads.
- **`call_outcome` values**: `"Success"` (capital S) for accepted calls in analytics. Be aware of this exact string when writing queries or tests.
- **Analytics funnel is cumulative**: A record at stage `transferred_to_sales` counts for all 6 earlier stages too.
- **SPA conditional mount**: Dashboard routes only register if `dashboard/dist/` exists at startup. Running uvicorn without `npm run build` → `/dashboard` returns 404.
- **`VITE_API_KEY` env var**: Must be set in `dashboard/.env` for the dev server to authenticate API calls.
- **Simulated shipper rate**: `shipper_rate = loadboard_rate * 1.10` is computed on the fly in the summary aggregation pipeline (`SHIPPER_RATE_MARKUP` constant in `analytics/service.py`). Used for hero KPI margin calculations (Gross Margin, Avg Margin %, Booked Revenue). The negotiations tab margin distribution uses the raw `loadboard_rate` instead — different purpose (AI negotiation performance vs. brokerage margin).
- **Numeric params as strings**: Load search params (`min_rate`, `max_rate`, `max_weight`) arrive as `Optional[str]` because the voice AI sends `""` for empty values, parsed to float in the router.

---

## Workflow Orchestration
### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity
### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
### 3. Self-Improvement Loop
- After ANY correction from the user: update tasks/lessons.md with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project
### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness
### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it
### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how
## Task Management
1. **Plan First**: Write plan to tasks/todo.md with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to tasks/todo.md
6. **Capture Lessons**: Update tasks/lessons.md after corrections
## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
