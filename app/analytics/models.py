from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingestion models (nested, mirrors webhook JSON)
# ---------------------------------------------------------------------------

class SystemData(BaseModel):
    call_id: str
    call_startedat: datetime
    call_duration: int


class FMCSAData(BaseModel):
    carrier_mc_number: int
    carrier_name: str
    carrier_validation_result: str
    retrieval_date: str


class LoadData(BaseModel):
    load_id_discussed: str
    alternate_loads_presented: int


class Outcome(BaseModel):
    call_outcome: str
    rejection_reason: Optional[str] = None


class Sentiment(BaseModel):
    call_sentiment: Optional[str] = None
    sentiment_progression: Optional[str] = None
    engagement_level: Optional[str] = None
    carrier_expressed_interest_future: Optional[bool] = None


class Performance(BaseModel):
    agent_followed_protocol: Optional[bool] = None
    protocol_violations: list[str] = Field(default_factory=list)
    agent_tone_quality: Optional[str] = None


class Conversation(BaseModel):
    ai_interruptions_count: Optional[int] = None
    transcription_errors_detected: Optional[bool] = None
    carrier_had_to_repeat_info: Optional[bool] = None


class Operational(BaseModel):
    transfer_to_sales_attempted: Optional[bool] = None
    transfer_to_sales_completed: Optional[bool] = None
    transfer_reason: Optional[str] = None
    loads_presented_count: Optional[int] = None


class OptionalData(BaseModel):
    negotiation_strategy_used: Optional[str] = None
    carrier_negotiation_leverage: list[str] = Field(default_factory=list)
    carrier_objections: list[str] = Field(default_factory=list)
    carrier_questions_asked: list[str] = Field(default_factory=list)


class Negotiation(BaseModel):
    carrier_first_offer: Optional[float] = None
    broker_first_counter: Optional[float] = None
    carrier_second_offer: Optional[float] = None
    broker_second_counter: Optional[float] = None
    carrier_third_offer: Optional[float] = None
    broker_third_counter: Optional[float] = None
    final_agreed_rate: Optional[float] = None
    negotiation_rounds: Optional[int] = None


class TranscriptExtraction(BaseModel):
    negotiation: Negotiation = Field(default_factory=Negotiation)
    outcome: Outcome
    sentiment: Sentiment = Field(default_factory=Sentiment)
    performance: Performance = Field(default_factory=Performance)
    conversation: Conversation = Field(default_factory=Conversation)
    operational: Operational = Field(default_factory=Operational)
    optional: OptionalData = Field(default_factory=OptionalData)


class CallRecord(BaseModel):
    system: SystemData
    fmcsa_data: FMCSAData
    load_data: LoadData
    transcript_extraction: TranscriptExtraction


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    call_id: str
    status: str  # "created" or "updated"


class SummaryResponse(BaseModel):
    total_calls: int
    acceptance_rate: float
    avg_call_duration: float
    avg_negotiation_rounds: float
    avg_margin_percent: float
    ai_protocol_compliance: float
    total_carriers: int


class TimeSeriesPoint(BaseModel):
    date: str
    count: int = 0


class DurationTimeSeriesPoint(BaseModel):
    date: str
    avg_duration: float = 0.0


class ReasonCount(BaseModel):
    reason: str
    count: int


class OperationsResponse(BaseModel):
    calls_over_time: list[TimeSeriesPoint]
    outcome_distribution: dict[str, int]
    avg_duration_over_time: list[DurationTimeSeriesPoint]
    rejection_reasons: list[ReasonCount]
    transfer_rate: float


class RateProgressionPoint(BaseModel):
    round: str
    avg_rate: float


class MarginBucket(BaseModel):
    range: str
    count: int


class StrategyRow(BaseModel):
    strategy: str
    acceptance_rate: float
    avg_rounds: float
    count: int


class NegotiationsResponse(BaseModel):
    avg_first_offer: float
    avg_final_rate: float
    avg_rounds: float
    rate_progression: list[RateProgressionPoint]
    margin_distribution: list[MarginBucket]
    strategy_effectiveness: list[StrategyRow]


class ViolationCount(BaseModel):
    violation: str
    count: int


class InterruptionTimeSeriesPoint(BaseModel):
    date: str
    avg: float


class AIQualityResponse(BaseModel):
    protocol_compliance_rate: float
    common_violations: list[ViolationCount]
    avg_interruptions: float
    interruptions_over_time: list[InterruptionTimeSeriesPoint]
    transcription_error_rate: float
    carrier_repeat_rate: float
    tone_quality_distribution: dict[str, int]


class ObjectionCount(BaseModel):
    objection: str
    count: int


class QuestionCount(BaseModel):
    question: str
    count: int


class CarrierLeaderboardRow(BaseModel):
    carrier_name: str
    mc_number: int
    calls: int
    acceptance_rate: float


class CarriersResponse(BaseModel):
    sentiment_distribution: dict[str, int]
    sentiment_over_time: list[dict]
    engagement_levels: dict[str, int]
    future_interest_rate: float
    top_objections: list[ObjectionCount]
    top_questions: list[QuestionCount]
    carrier_leaderboard: list[CarrierLeaderboardRow]
