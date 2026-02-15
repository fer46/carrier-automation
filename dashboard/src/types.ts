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
 *   4. AI Quality  (protocol compliance, interruptions, tone)
 *   5. Carriers  (sentiment, engagement, objections, leaderboard)
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
  /** Average profit margin as a percentage (0-100). */
  avg_margin_percent: number;
  /** Total revenue from booked (accepted) loads. */
  total_booked_revenue: number;
  /** Total margin earned across all accepted loads (loadboard_rate - final_agreed_rate). */
  total_margin_earned: number;
  /** Average rate per mile across accepted loads with mileage data. */
  avg_rate_per_mile: number;
  /** Count of distinct carriers contacted. */
  total_carriers: number;
}

// ---------------------------------------------------------------------------
// 2. Operations -- /api/analytics/operations
//    Charts: call volume over time, outcome pie, rejection bar, duration line.
// ---------------------------------------------------------------------------

/** A single date-bucketed count used for the call-volume area chart. */
export interface TimeSeriesPoint {
  date: string;   // ISO date string, e.g. "2025-01-15"
  count: number;
}

/** A single date-bucketed average duration used for the duration line chart. */
export interface DurationTimeSeriesPoint {
  date: string;         // ISO date string
  avg_duration: number; // seconds
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
  /** Outcome label -> count mapping for the donut/pie chart (e.g. "accepted": 42). */
  outcome_distribution: Record<string, number>;
  /** Daily average call duration for the line chart. */
  avg_duration_over_time: DurationTimeSeriesPoint[];
  /** Top rejection reasons and their counts for the horizontal bar chart. */
  rejection_reasons: ReasonCount[];
  /** Percentage of calls transferred to a human agent. */
  transfer_rate: number;
  /** Conversion funnel from call_started through transferred_to_sales. */
  funnel: FunnelStage[];
}

// ---------------------------------------------------------------------------
// 3. Negotiations -- /api/analytics/negotiations
//    Charts: rate progression line, margin bar, strategy effectiveness table.
// ---------------------------------------------------------------------------

/** Average carrier rate at a specific negotiation round/stage (e.g. "Round 1"). */
export interface RateProgressionPoint {
  round: string;    // label like "Initial Offer", "Round 1", "Final"
  avg_rate: number; // dollar amount
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
  avg_first_offer: number;  // average initial carrier rate offer ($)
  avg_final_rate: number;   // average accepted/final rate ($)
  avg_rounds: number;       // average negotiation rounds across all calls
  /** How the average rate changes through negotiation rounds. */
  rate_progression: RateProgressionPoint[];
  /** Distribution of profit margins across completed negotiations. */
  margin_distribution: MarginBucket[];
  /** Comparison of different negotiation strategies. */
  strategy_effectiveness: StrategyRow[];
}

// ---------------------------------------------------------------------------
// 5. Carriers -- /api/analytics/carriers
//    Charts: sentiment area, engagement pie, objections/questions bars, leaderboard table.
// ---------------------------------------------------------------------------

/** A labelled count for a specific carrier objection. */
export interface ObjectionCount {
  objection: string;
  count: number;
}

/** A labelled count for a specific carrier question. */
export interface QuestionCount {
  question: string;
  count: number;
}

/** One row in the carrier leaderboard ranking table. */
export interface CarrierLeaderboardRow {
  carrier_name: string;    // display name
  mc_number: number;       // FMCSA Motor Carrier number (unique identifier)
  calls: number;           // total calls with this carrier
  acceptance_rate: number; // percentage of calls that ended in acceptance (0-100)
}

/** A date-bucketed breakdown of carrier sentiment (stacked area chart). */
export interface SentimentTimePoint {
  date: string;
  positive: number; // count of positive-sentiment calls
  neutral: number;
  negative: number;
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
  /** Sentiment label -> count mapping for overall distribution. */
  sentiment_distribution: Record<string, number>;
  /** Daily sentiment breakdown for the stacked area chart. */
  sentiment_over_time: SentimentTimePoint[];
  /** Engagement level label -> count (e.g. "high": 30, "medium": 45). */
  engagement_levels: Record<string, number>;
  /** Percentage of carriers who expressed interest in future loads (0-100). */
  future_interest_rate: number;
  /** Most common objections raised by carriers, sorted by count descending. */
  top_objections: ObjectionCount[];
  /** Most common questions asked by carriers, sorted by count descending. */
  top_questions: QuestionCount[];
  /** Top carriers ranked by acceptance rate (used in the leaderboard table). */
  carrier_leaderboard: CarrierLeaderboardRow[];
  /** Top lanes requested by carriers. */
  top_requested_lanes: LaneCount[];
  /** Top actual lanes (origin → destination). */
  top_actual_lanes: LaneCount[];
  /** Equipment type distribution across calls. */
  equipment_distribution: EquipmentCount[];
}
