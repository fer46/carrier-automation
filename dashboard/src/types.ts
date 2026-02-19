/**
 * types.ts -- Shared TypeScript interfaces for the Carrier Load Analytics dashboard.
 *
 * Every interface here mirrors a JSON response shape returned by the FastAPI
 * backend under /api/analytics/*.  When the backend Pydantic models change,
 * these types must be updated in lockstep so the compiler catches mismatches.
 *
 * The file is organised by analytics domain:
 *   1. Summary  (top-level KPI hero cards)
 *   2. Operations  (call volume, outcomes, durations, rejections)
 *   3. Negotiations  (rate progression, margins, strategy effectiveness)
 *   4. Carriers  (sentiment, engagement, objections, leaderboard)
 */

// ---------------------------------------------------------------------------
// 1. Summary -- /api/analytics/summary
//    High-level KPIs displayed in the hero card row at the top of the dashboard.
// ---------------------------------------------------------------------------

export interface SummaryData {
  /** Total number of carrier calls recorded in the selected date range. */
  total_calls: number;
  /** Percentage of calls that resulted in load acceptance (0-100). */
  acceptance_rate: number;
  /** Average call duration in seconds; the UI converts to "Xm Ys" format. */
  avg_call_duration: number;
  /** Average number of back-and-forth negotiation rounds per call. */
  avg_negotiation_rounds: number;
  /** Average gross margin as a percentage (0-100), computed against simulated shipper_rate. */
  avg_margin_percent: number;
  /** Total gross margin across all accepted loads (shipper_rate - final_agreed_rate). */
  total_margin_earned: number;
  /** Total booked revenue: sum of shipper_rate for accepted loads. */
  booked_revenue: number;
  /** Average rate per mile across accepted loads with mileage data. */
  avg_rate_per_mile: number;
  /** Count of distinct carriers contacted. */
  total_carriers: number;
}

// ---------------------------------------------------------------------------
// 2. Operations -- /api/analytics/operations
//    Charts: call volume over time, rejection bar, conversion funnel.
// ---------------------------------------------------------------------------

/** A single date-bucketed count used for the call-volume area chart. */
export interface TimeSeriesPoint {
  date: string;   // ISO date string, e.g. "2025-01-15"
  count: number;
}

/** A labelled count for a specific rejection reason (horizontal bar chart). */
export interface ReasonCount {
  reason: string;
  count: number;
}

/** A single stage in the conversion funnel with cumulative count and drop-off. */
export interface FunnelStage {
  stage: string;
  count: number;
  drop_off_percent: number;
}

/** Aggregated operational metrics for the Operations tab. */
export interface OperationsData {
  /** Daily call counts for the area chart. */
  calls_over_time: TimeSeriesPoint[];
  /** Top rejection reasons and their counts for the horizontal bar chart. */
  rejection_reasons: ReasonCount[];
  /** Conversion funnel from call_started through transferred_to_sales. */
  funnel: FunnelStage[];
}

// ---------------------------------------------------------------------------
// 3. Negotiations -- /api/analytics/negotiations
//    Charts: negotiation outcomes donut, margin bar, strategy effectiveness table.
// ---------------------------------------------------------------------------

/** A single outcome category for the negotiation outcomes donut chart. */
export interface NegotiationOutcome {
  name: string;   // "Accepted at First Offer", "Negotiated & Agreed", or "No Deal"
  count: number;
}

/** A histogram bucket for profit margin distribution (e.g. "5-10%"). */
export interface MarginBucket {
  range: string; // human-readable range label
  count: number; // number of calls that fell in this bucket
}

/** One row in the strategy effectiveness comparison table. */
export interface StrategyRow {
  strategy: string;        // name of the negotiation strategy
  acceptance_rate: number; // percentage (0-100)
  avg_rounds: number;      // average negotiation rounds for this strategy
  count: number;           // total calls that used this strategy
}

/** Aggregated negotiation metrics for the Negotiations tab. */
export interface NegotiationsData {
  avg_savings: number;          // average per-deal savings (carrier_first_offer - final_agreed_rate)
  avg_savings_percent: number;  // average savings as percentage of carrier's first offer (0-100)
  avg_rounds: number;           // average negotiation rounds across all calls
  /** Breakdown of call outcomes: first-offer acceptance, negotiated deals, no deals. */
  negotiation_outcomes: NegotiationOutcome[];
  /** Distribution of profit margins across completed negotiations. */
  margin_distribution: MarginBucket[];
  /** Comparison of different negotiation strategies. */
  strategy_effectiveness: StrategyRow[];
}

// ---------------------------------------------------------------------------
// 4. Carriers -- /api/analytics/carriers
//    Charts: sentiment area, engagement pie, objections/questions bars, leaderboard table.
// ---------------------------------------------------------------------------

/** A labelled count for a specific carrier objection. */
export interface ObjectionCount {
  objection: string;
  count: number;
}

/** One row in the carrier leaderboard ranking table. */
export interface CarrierLeaderboardRow {
  carrier_name: string;    // display name
  mc_number: number;       // FMCSA Motor Carrier number (unique identifier)
  calls: number;           // total calls with this carrier
  acceptance_rate: number; // percentage of calls that ended in acceptance (0-100)
}

/** A lane with its occurrence count (used for requested and actual lane rankings). */
export interface LaneCount {
  lane: string;
  count: number;
}

/** An equipment type with its occurrence count. */
export interface EquipmentCount {
  equipment_type: string;
  count: number;
}

/** Aggregated carrier-focused metrics for the Carriers tab. */
export interface CarriersData {
  /** Most common objections raised by carriers, sorted by count descending. */
  top_objections: ObjectionCount[];
  /** Top carriers ranked by acceptance rate (used in the leaderboard table). */
  carrier_leaderboard: CarrierLeaderboardRow[];
  /** Top lanes requested by carriers. */
  top_requested_lanes: LaneCount[];
  /** Top actual lanes (origin → destination). */
  top_actual_lanes: LaneCount[];
  /** Equipment type distribution across calls. */
  equipment_distribution: EquipmentCount[];
}

// ---------------------------------------------------------------------------
// 5. Geography -- /api/analytics/geography
//    Arc map showing requested vs booked lanes across US cities.
// ---------------------------------------------------------------------------

export interface GeoCity {
  name: string;
  lat: number;
  lng: number;
  volume: number;
}

export interface GeoArc {
  origin: string;
  origin_lat: number;
  origin_lng: number;
  destination: string;
  dest_lat: number;
  dest_lng: number;
  count: number;
  arc_type: 'requested' | 'booked';
}

export interface GeographyData {
  arcs: GeoArc[];
  cities: GeoCity[];
}
