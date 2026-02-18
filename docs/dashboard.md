# Carrier Load Analytics Dashboard

Real-time analytics dashboard for monitoring carrier call activity, negotiation performance, and operational metrics. Built with React/TypeScript (frontend) and FastAPI/Python (backend), backed by MongoDB.

---

## Overview

The dashboard ingests carrier call records via webhook, stores them in MongoDB, and serves aggregated analytics through five API endpoints. The frontend polls these endpoints and renders KPI cards, charts, and tables across four tabs.

**Stack:** FastAPI + MongoDB (Motor async) + React + Recharts + react-simple-maps + Tailwind CSS

**Branding:** Broker Robot Logistics (BRL) -- black & white theme with vivid chart accent colors.

---

## Data Flow

```
Webhook POST → /api/analytics/calls → MongoDB (call_records collection)
                                            ↓
Dashboard GET → /api/analytics/{endpoint} → Aggregation Pipelines → JSON Response
                                                                        ↓
                                                              React Frontend
```

1. External systems POST call records to `/api/analytics/calls`
2. Records are upserted by `call_id` with a server-side `ingested_at` timestamp
3. The dashboard fetches five endpoints in parallel every 5 minutes
4. MongoDB aggregation pipelines compute metrics on the fly
5. The frontend renders the results as KPI cards, charts, and tables

---

## Authentication

All endpoints require an `X-API-Key` header. The key is configured via the `API_KEY` environment variable (backend) and `VITE_API_KEY` (frontend).

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analytics/calls` | Ingest a call record |
| GET | `/api/analytics/summary` | Hero KPI metrics |
| GET | `/api/analytics/operations` | Call volume, funnel, rejection reasons |
| GET | `/api/analytics/negotiations` | Negotiation savings, outcomes, margins |
| GET | `/api/analytics/carriers` | Objections, lanes, equipment, leaderboard |
| GET | `/api/analytics/geography` | Requested vs booked lane arcs, city volumes |

All GET endpoints accept optional `from` and `to` query parameters (ISO date strings, e.g. `?from=2026-01-01&to=2026-01-31`). Dates filter on the `ingested_at` field (server timestamp when the record was first created).

---

## Dashboard Layout

### Header

- **Branding** on the left (BRL logo + "Broker Robot Logistics" title)
- **Time range selector**: 1D / 7D / 30D buttons that control the date filter
- **Refresh button**: triggers an immediate data fetch

### Hero KPI Row

Eight cards displayed in a responsive grid (2 cols mobile, 3 tablet, 4 desktop):

| Card | Description | Format |
|------|-------------|--------|
| Total Calls | Count of calls in the date range | Integer |
| Avg Call Duration | Average call length | Duration (Xm Ys) |
| Acceptance Rate | % of calls resulting in acceptance | Percentage |
| Margin Earned | Sum of `(loadboard_rate - final_agreed_rate)` for accepted calls | Dollar |
| Avg Margin % | Average margin as a percentage | Percentage |
| Rate/Mile | Average `final_agreed_rate / miles` | Dollar |
| Unique Carriers | Count of distinct MC numbers | Integer |

When no data exists, an onboarding banner is shown instead.

### Tabs

Four tabs below the hero row: **Operations**, **Negotiations**, **Carriers**, **Geography**.

---

## Operations Tab

Provides a bird's-eye view of call activity.

### Conversion Funnel

Full-width horizontal bar chart showing how calls progress through the pipeline:

1. **Call Started** -- initial contact
2. **FMCSA Verified** -- carrier passed validation
3. **Load Matched** -- a matching load was found
4. **Offer Pitched** -- rate was presented to carrier
5. **Negotiation Entered** -- back-and-forth began
6. **Deal Agreed** -- both parties accepted terms
7. **Transferred to Sales** -- handoff to human agent

Counts are **cumulative**: a record that reached "Deal Agreed" also counts toward all earlier stages. Drop-off percentage is calculated relative to the first stage.

The final stage bar is colored green; all others are blue.

### Call Volume Over Time

Area chart showing daily call counts over the selected date range.

### Rejection Reasons

Horizontal bar chart ranking the top 10 rejection reasons by frequency.

---

## Negotiations Tab

Analyzes rate negotiation patterns and margin performance.

### Summary Stats

Three headline cards:

- **Avg Savings / Deal** -- average dollar amount saved per negotiation (carrier's first offer minus final agreed rate), computed per-deal to avoid sample bias.
- **Avg Savings %** -- average savings as a percentage of the carrier's first offer, normalized across load sizes.
- **Avg Rounds** -- average number of back-and-forth exchanges per call.

### Negotiation Outcomes

Donut chart breaking down all calls into three categories:

- **Accepted at First Offer** -- carrier accepted without negotiation rounds (green).
- **Negotiated & Agreed** -- carrier accepted after one or more negotiation rounds (blue).
- **No Deal** -- call ended in rejection or transfer to sales (red).

Each slice shows a percentage label.

### Margin Distribution

Histogram showing how many deals fall into each margin bucket: `<0%`, `0-5%`, `5-10%`, `10-15%`, `15-20%`, `20%+`.

**Margin formula:**

```
margin_percent = ((loadboard_rate - final_agreed_rate) / loadboard_rate) * 100
```

- `loadboard_rate`: the broker's posted rate (what the load is worth)
- `final_agreed_rate`: the rate the carrier accepted
- A positive margin means the carrier accepted below the posted rate

---

## Carriers Tab

Shows carrier behavior patterns and market intelligence.

### Lane Intelligence

Three-column section showing:

- **Top Requested Lanes**: lanes carriers asked about (`carrier_requested_lane` field), ranked by frequency. Includes all calls regardless of outcome (both booked and unbooked).
- **Top Actual Lanes**: lanes that were actually discussed, formatted as "Origin -> Destination", ranked by frequency.
- **Equipment Types**: donut chart showing equipment type distribution (Dry Van, Reefer, Flatbed, etc.)

Comparing requested vs. actual lanes reveals mismatches between carrier preferences and available loads.

### Top Carrier Objections

Horizontal bar chart ranking the most common objections raised by carriers (e.g. "Rate too low").

### Carrier Leaderboard

Table of top 20 carriers ranked by call volume, showing:
- Carrier name and MC number
- Total calls
- Acceptance rate with a visual progress bar

---

## Geography Tab

Interactive US map visualizing the geographic distribution of requested vs booked freight lanes.

### Arc Map

Full-width map of the continental US (Albers USA projection via `react-simple-maps`) with two arc layers:

- **Requested Lanes** (gray dashed arcs) -- lanes carriers asked about, parsed from the free-form `carrier_requested_lane` field.
- **Booked Lanes** (green solid arcs) -- lanes where loads were actually discussed, built from `origin` + `destination` fields.

Arc thickness scales with lane frequency. When the same lane appears in both requested and booked sets, the arcs curve at different heights to avoid overlap.

**City markers** (blue circles) are sized proportionally to total load volume (sum of inbound + outbound across both requested and booked). The top 5 cities by volume display name labels. Hovering over a city shows a tooltip with its name and volume count.

### Summary Cards

Four-column row of metric cards:

| Card | Description |
|------|-------------|
| Requested Lanes | Count of distinct requested lane pairs |
| Booked Lanes | Count of distinct booked lane pairs |
| Active Cities | Count of unique cities appearing in any lane |
| Overlapping Lanes | Count of lanes that appear in both requested and booked sets |

### Collapsible Panels

Three collapsible disclosure panels in a row:

- **Top Requested Lanes** -- ranked list (up to 8) with gray progress bars
- **Top Booked Lanes** -- ranked list (up to 8) with green progress bars
- **Top Hubs** -- ranked list (up to 8) of cities by total volume

---

## Webhook Payload

The POST `/api/analytics/calls` endpoint accepts this structure:

```json
{
  "system": {
    "call_id": "unique-call-id",
    "call_duration": 245
  },
  "fmcsa_data": {
    "carrier_mc_number": 1234567,
    "carrier_name": "CARRIER NAME",
    "carrier_validation_result": "VALID",
    "retrieval_date": "2026-02-13T19:45:01.867+0000"
  },
  "load_data": {
    "load_id_discussed": "LD-001",
    "alternate_loads_presented": 1,
    "loadboard_rate": 2200.00,
    "origin": "Chicago, IL",
    "destination": "Dallas, TX",
    "carrier_requested_lane": "Chicago, IL -> Dallas, TX",
    "equipment_type": "Dry Van",
    "miles": 920.0,
    "pickup_datetime": "2026-02-14T08:00:00",
    "delivery_datetime": "2026-02-15T18:00:00"
  },
  "transcript_extraction": {
    "negotiation": {
      "carrier_first_offer": 1900.00,
      "broker_first_counter": 2100.00,
      "carrier_second_offer": 2000.00,
      "broker_second_counter": null,
      "carrier_third_offer": null,
      "broker_third_counter": null,
      "final_agreed_rate": 2000.00,
      "negotiation_rounds": 2
    },
    "outcome": {
      "call_outcome": "Success",
      "rejection_reason": null,
      "funnel_stage_reached": "transferred_to_sales"
    },
    "sentiment": {
      "call_sentiment": "positive",
      "sentiment_progression": "improving",
      "engagement_level": "high",
      "carrier_expressed_interest_future": true
    },
    "performance": {
      "agent_followed_protocol": true,
      "protocol_violations": [],
      "agent_tone_quality": "professional"
    },
    "conversation": {
      "ai_interruptions_count": 1,
      "transcription_errors_detected": false,
      "carrier_had_to_repeat_info": false
    },
    "operational": {
      "transfer_to_sales_attempted": false,
      "transfer_to_sales_completed": false,
      "transfer_reason": null,
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
```

All fields inside `load_data` (except `load_id_discussed` and `alternate_loads_presented`) and `outcome.funnel_stage_reached` are optional -- they default to `null` if omitted. Empty strings are automatically coerced to `null`.

Records are upserted by `call_id`: posting the same `call_id` twice updates the existing record while preserving the original `ingested_at` timestamp.

---

## Auto-Refresh

The dashboard polls all five analytics endpoints every **5 minutes**. Changing the time range triggers an immediate fetch. A manual refresh button is available in the header.

All five endpoints are fetched in parallel to minimize load time.

---

## Empty States

Every chart gracefully handles missing data with contextual messages rather than rendering broken visuals:

- No call data at all: onboarding banner with API instructions
- No funnel data: "No funnel data yet"
- No rejections: "No rejections recorded"
- No lane data: "No lane data yet" / "No lane data available for the selected period"
- No equipment data: "No equipment data yet"
- No objections: "No objections recorded"
- Generic: "No data available"

---

## Key Metrics & Formulas

| Metric | Formula | Notes |
|--------|---------|-------|
| Acceptance Rate | `(accepted_calls / total_calls) * 100` | Percentage |
| Avg Savings | `AVG(carrier_first_offer - final_agreed_rate)` | Per-deal, requires both rates non-null |
| Avg Savings % | `AVG((carrier_first_offer - final_agreed_rate) / carrier_first_offer * 100)` | Per-deal percentage |
| Margin % | `((loadboard_rate - final_agreed_rate) / loadboard_rate) * 100` | Per-call, then averaged |
| Margin Earned | `SUM(loadboard_rate - final_agreed_rate)` where accepted + both rates exist | Dollar total |
| Rate/Mile | `AVG(final_agreed_rate / miles)` where miles > 0 | Dollar per mile |
| Funnel Drop-off | `(1 - stage_count / first_stage_count) * 100` | Per stage |
