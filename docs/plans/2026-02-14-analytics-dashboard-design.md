# Analytics Dashboard Design

**Date:** 2026-02-14
**Status:** Approved

## Overview

Full-pipeline analytics system: ingest call data via POST webhook, store in MongoDB, serve aggregated metrics via API endpoints, and render a React dashboard served by FastAPI.

## Audience

- Brokerage operations managers (call volume, outcomes, margins)
- Sales/carrier relations (sentiment, engagement, relationships)
- Executives (high-level KPIs, trends)
- Developers (AI model performance, protocol compliance, conversation quality)

## Architecture

```
Platform (webhook POST)
    -> POST /api/analytics/calls
        -> Validate with Pydantic (strict types)
        -> Upsert in MongoDB `call_records` collection
        -> Return 201

Dashboard (React SPA via Vite, served by FastAPI at /dashboard)
    -> GET /api/analytics/summary
    -> GET /api/analytics/operations
    -> GET /api/analytics/negotiations
    -> GET /api/analytics/ai-quality
    -> GET /api/analytics/carriers
    -> All support ?from=&to= date filtering
    -> Auto-polls every 30s + manual refresh
```

## Backend Structure

```
app/analytics/
    __init__.py
    models.py      - CallRecord (ingestion), response models
    router.py      - POST ingest + 5 GET aggregation endpoints
    service.py     - MongoDB aggregation pipelines

dashboard/
    src/
        components/  - KPICard, Charts, Tabs
        pages/       - Dashboard layout
    vite.config.ts
    package.json
```

## Data Model (CallRecord)

```
system:
    call_id: str (unique, indexed)
    call_startedat: datetime (indexed for time-range queries)
    call_duration: int (seconds)

fmcsa_data:
    carrier_mc_number: int
    carrier_name: str
    carrier_validation_result: str
    retrieval_date: str

load_data:
    load_id_discussed: str
    alternate_loads_presented: int

transcript_extraction:
    carrier_first_offer: Optional[float]
    broker_first_counter: Optional[float]
    carrier_second_offer: Optional[float]
    broker_second_counter: Optional[float]
    carrier_third_offer: Optional[float]
    broker_third_counter: Optional[float]
    final_agreed_rate: Optional[float]
    negotiation_rounds: Optional[int]

    outcome:
        call_outcome: str
        rejection_reason: Optional[str]

    sentiment:
        call_sentiment: Optional[str]
        sentiment_progression: Optional[str]
        engagement_level: Optional[str]
        carrier_expressed_interest_future: Optional[bool]

    performance:
        agent_followed_protocol: Optional[bool]
        protocol_violations: list[str]
        agent_tone_quality: Optional[str]

    conversation:
        ai_interruptions_count: Optional[int]
        transcription_errors_detected: Optional[bool]
        carrier_had_to_repeat_info: Optional[bool]

    operational:
        transfer_to_sales_attempted: Optional[bool]
        transfer_to_sales_completed: Optional[bool]
        transfer_reason: Optional[str]
        loads_presented_count: Optional[int]

    optional:
        negotiation_strategy_used: Optional[str]
        carrier_negotiation_leverage: list[str]
        carrier_objections: list[str]
        carrier_questions_asked: list[str]
```

Storage: nested structure as-is in MongoDB. Upsert by call_id. Indexes on system.call_id (unique) and system.call_startedat.

## API Endpoints

### POST /api/analytics/calls
Ingest one call record. Upserts by call_id. Returns 201.

### GET /api/analytics/summary
```json
{
    "total_calls": 127,
    "acceptance_rate": 73.2,
    "avg_call_duration": 245.0,
    "avg_negotiation_rounds": 2.1,
    "avg_margin_percent": 8.4,
    "ai_protocol_compliance": 94.1,
    "total_carriers": 43
}
```

### GET /api/analytics/operations
- calls_over_time: [{date, count}]
- outcome_distribution: {accepted, rejected, transferred}
- avg_duration_over_time: [{date, avg_duration}]
- rejection_reasons: [{reason, count}]
- transfer_rate: float

### GET /api/analytics/negotiations
- avg_first_offer: float
- avg_final_rate: float
- avg_rounds: float
- rate_progression: [{round, avg_rate}]
- margin_distribution: [{range, count}]
- strategy_effectiveness: [{strategy, acceptance_rate, avg_rounds, count}]

### GET /api/analytics/ai-quality
- protocol_compliance_rate: float
- common_violations: [{violation, count}]
- avg_interruptions: float
- interruptions_over_time: [{date, avg}]
- transcription_error_rate: float
- carrier_repeat_rate: float
- tone_quality_distribution: {professional, neutral, poor}

### GET /api/analytics/carriers
- sentiment_distribution: {positive, neutral, negative}
- sentiment_over_time: [{date, positive, neutral, negative}]
- engagement_levels: {high, medium, low}
- future_interest_rate: float
- top_objections: [{objection, count}]
- top_questions: [{question, count}]
- carrier_leaderboard: [{carrier_name, mc_number, calls, acceptance_rate}]

## Dashboard UI

### Layout
- Header: title, date range picker, refresh button with 30s countdown
- Hero section: 7 KPI cards with trend indicators (vs prior period)
- Tabbed navigation: Operations | Negotiation | AI Quality | Carriers

### Tech Stack
- React 18 + Vite
- Recharts (charting)
- Tailwind CSS (styling)
- Slate/blue professional theme with semantic colors

### Tab Details

**Operations:** call volume area chart, outcome donut, rejection reasons bar, duration line chart
**Negotiation:** rate progression funnel, margin histogram, strategy effectiveness table
**AI Quality:** compliance gauge, violations bar, interruptions line, quality stat cards
**Carriers:** sentiment stacked area, engagement donut, objections/questions bars, leaderboard table

### Design Principles
- Empty states with helpful messages pointing to POST endpoint
- Responsive: 2-col grid on desktop, stacked on mobile
- Color-coded KPIs: green=good, amber=watch, red=alert
- Auto-poll 30s with visible countdown + manual refresh
