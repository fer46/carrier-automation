## Project: Carrier Load Automation

AI-powered carrier load booking system with analytics dashboard. FastAPI + MongoDB (Motor async) + Pydantic + React/TypeScript.

### Architecture
- **Domain-driven structure**: Each domain gets its own folder under `app/` with `router.py`, `service.py`, `models.py`
- **Current domains**: `loads` (search & get by ID), `analytics` (call record aggregation, KPIs, geography)
- **Dashboard**: React 19 + TypeScript + Tailwind CSS 4 + Recharts + react-simple-maps, served at `/dashboard`
- **Auth**: API key via `X-API-Key` header, validated in `app/dependencies.py`
- **DB**: MongoDB via Motor async driver, lifecycle managed in `app/database.py`
- **Config**: Pydantic Settings in `app/config.py`, reads from `.env`

### Key Paths
- `app/main.py` — FastAPI app entry point (lifespan, routers, health check, SPA serving)
- `app/loads/` — Loads domain (router, service, models)
- `app/analytics/` — Analytics domain (router, service, models, lane_parser)
- `dashboard/src/` — React dashboard (App, api, types, components/)
- `data/seed_loads.json` — Sample load data
- `scripts/seed_db.py` — Seeds MongoDB with loads from JSON
- `scripts/seed_call_records.py` — Generates realistic call records for analytics
- `tests/` — Mirrors app structure, uses mocked MongoDB
- `.github/workflows/ci.yml` — CI pipeline (lint, test, dashboard build)
- `docs/` — Architecture docs and implementation plans

### Commands
- **Install deps**: `uv pip install -r requirements.txt`
- **Run locally**: `.venv/bin/uvicorn app.main:app --reload`
- **Run tests**: `.venv/bin/python -m pytest tests/ -v`
- **Lint (ruff)**: `.venv/bin/ruff check app/ tests/ scripts/`
- **Format check**: `.venv/bin/ruff format --check app/ tests/ scripts/`
- **Type check**: `.venv/bin/mypy app/`
- **Docker**: `docker-compose up --build`
- **Seed loads**: `.venv/bin/python scripts/seed_db.py`
- **Seed call records**: `.venv/bin/python -m scripts.seed_call_records`
- **Dashboard dev**: `cd dashboard && npm run dev`
- **Dashboard build**: `cd dashboard && npm install && npm run build`

### Tech Constraints
- **Python 3.13** — use `Optional[X]` from `typing` for nullable types (project convention)
- **Package manager**: Always use `uv` for installs, never raw `pip`
- **Async everywhere**: All DB operations and endpoints are async
- **Dashboard**: React 19, TypeScript 5.9, Tailwind CSS 4, Vite 7, Recharts 3

### Conventions
- Routers mount under `/api/<domain>/` prefix
- Service layer handles business logic and DB queries, routers stay thin
- Models: `<Entity>` (DB doc), `<Entity>SearchParams` (query), `<Entity>Response` (API response)
- Tests mock the DB via `unittest.mock.patch` on `get_database` in the service module
- Exclude `_id` from MongoDB query results with `{"_id": 0}`
- Dashboard components: one per tab (OperationsTab, NegotiationsTab, CarriersTab, GeographyTab)
- API client in `dashboard/src/api.ts`, types in `dashboard/src/types.ts`

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
- After ANY correction from the user: update tasks/lessons md with the pattern
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
1. **Plan First**: Write plan to tasks/todo.d* with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to tasks/todo.md
6. **Capture Lessons**: Update tasks/lessons.md after corrections
## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
