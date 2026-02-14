from typing import Optional

from app.analytics.models import (
    AIQualityResponse,
    CarrierLeaderboardRow,
    CarriersResponse,
    DurationTimeSeriesPoint,
    InterruptionTimeSeriesPoint,
    MarginBucket,
    NegotiationsResponse,
    ObjectionCount,
    OperationsResponse,
    QuestionCount,
    RateProgressionPoint,
    ReasonCount,
    StrategyRow,
    SummaryResponse,
    TimeSeriesPoint,
    ViolationCount,
)
from app.database import get_database


def _build_date_match(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> dict:
    match: dict = {}
    if date_from or date_to:
        date_filter: dict = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        match["system.call_startedat"] = date_filter
    return match


async def ingest_call_record(record: dict) -> str:
    """Upsert a call record into MongoDB. Returns 'created' or 'updated'."""
    db = get_database()
    call_id = record["system"]["call_id"]

    result = await db.call_records.update_one(
        {"system.call_id": call_id},
        {"$set": record},
        upsert=True,
    )

    return "created" if result.upserted_id else "updated"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


async def get_summary(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> SummaryResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    pipeline: list[dict] = []
    if date_match:
        pipeline.append({"$match": date_match})

    pipeline.append(
        {
            "$group": {
                "_id": None,
                "total_calls": {"$sum": 1},
                "accepted": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.outcome.call_outcome",
                                    "accepted",
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "avg_duration": {"$avg": "$system.call_duration"},
                "avg_rounds": {
                    "$avg": "$transcript_extraction.negotiation.negotiation_rounds"
                },
                "avg_margin": {
                    "$avg": {
                        "$cond": [
                            {
                                "$and": [
                                    {
                                        "$ne": [
                                            "$transcript_extraction.negotiation.carrier_first_offer",
                                            None,
                                        ]
                                    },
                                    {
                                        "$ne": [
                                            "$transcript_extraction.negotiation.final_agreed_rate",
                                            None,
                                        ]
                                    },
                                ]
                            },
                            {
                                "$multiply": [
                                    {
                                        "$divide": [
                                            {
                                                "$subtract": [
                                                    "$transcript_extraction.negotiation.carrier_first_offer",
                                                    "$transcript_extraction.negotiation.final_agreed_rate",
                                                ]
                                            },
                                            "$transcript_extraction.negotiation.carrier_first_offer",
                                        ]
                                    },
                                    100,
                                ]
                            },
                            None,
                        ]
                    }
                },
                "protocol_compliant": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.performance.agent_followed_protocol",
                                    True,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "unique_carriers": {
                    "$addToSet": "$fmcsa_data.carrier_mc_number"
                },
            }
        }
    )

    cursor = db.call_records.aggregate(pipeline)
    results = await cursor.to_list(length=1)

    if not results:
        return SummaryResponse(
            total_calls=0,
            acceptance_rate=0.0,
            avg_call_duration=0.0,
            avg_negotiation_rounds=0.0,
            avg_margin_percent=0.0,
            ai_protocol_compliance=0.0,
            total_carriers=0,
        )

    row = results[0]
    total = row["total_calls"]
    return SummaryResponse(
        total_calls=total,
        acceptance_rate=round(row["accepted"] / total * 100, 1) if total else 0.0,
        avg_call_duration=round(row["avg_duration"] or 0.0, 1),
        avg_negotiation_rounds=round(row["avg_rounds"] or 0.0, 1),
        avg_margin_percent=round(row["avg_margin"] or 0.0, 1),
        ai_protocol_compliance=(
            round(row["protocol_compliant"] / total * 100, 1) if total else 0.0
        ),
        total_carriers=len(row["unique_carriers"]),
    )


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


async def get_operations(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> OperationsResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    # --- Pipeline 1: calls_over_time + avg_duration ---
    p1: list[dict] = []
    if date_match:
        p1.append({"$match": date_match})
    p1.append(
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$system.call_startedat",
                    }
                },
                "count": {"$sum": 1},
                "avg_duration": {"$avg": "$system.call_duration"},
            }
        }
    )

    # --- Pipeline 2: outcome_distribution ---
    p2: list[dict] = []
    if date_match:
        p2.append({"$match": date_match})
    p2.append(
        {
            "$group": {
                "_id": "$transcript_extraction.outcome.call_outcome",
                "count": {"$sum": 1},
            }
        }
    )

    # --- Pipeline 3: rejection_reasons ---
    p3: list[dict] = []
    rejection_match: dict = {
        "transcript_extraction.outcome.rejection_reason": {"$ne": None}
    }
    if date_match:
        rejection_match.update(date_match)
    p3.append({"$match": rejection_match})
    p3.append(
        {
            "$group": {
                "_id": "$transcript_extraction.outcome.rejection_reason",
                "count": {"$sum": 1},
            }
        }
    )
    p3.append({"$sort": {"count": -1}})
    p3.append({"$limit": 10})

    # --- Pipeline 4: transfer_rate ---
    p4: list[dict] = []
    if date_match:
        p4.append({"$match": date_match})
    p4.append(
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "transferred": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.operational.transfer_to_sales_completed",
                                    True,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    )

    r1 = await db.call_records.aggregate(p1).to_list(length=None)
    r2 = await db.call_records.aggregate(p2).to_list(length=None)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)
    r4 = await db.call_records.aggregate(p4).to_list(length=1)

    calls_over_time = [
        TimeSeriesPoint(date=row["_id"], count=row["count"]) for row in r1
    ]
    avg_duration_over_time = [
        DurationTimeSeriesPoint(date=row["_id"], avg_duration=round(row["avg_duration"], 1))
        for row in r1
    ]
    outcome_distribution = {row["_id"]: row["count"] for row in r2}
    rejection_reasons = [
        ReasonCount(reason=row["_id"], count=row["count"]) for row in r3
    ]

    transfer_rate = 0.0
    if r4:
        total = r4[0]["total"]
        transferred = r4[0]["transferred"]
        transfer_rate = round(transferred / total * 100, 1) if total else 0.0

    return OperationsResponse(
        calls_over_time=calls_over_time,
        outcome_distribution=outcome_distribution,
        avg_duration_over_time=avg_duration_over_time,
        rejection_reasons=rejection_reasons,
        transfer_rate=transfer_rate,
    )


# ---------------------------------------------------------------------------
# Negotiations
# ---------------------------------------------------------------------------


async def get_negotiations(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> NegotiationsResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    # --- Pipeline 1: rate averages ---
    p1: list[dict] = []
    rate_match: dict = {"transcript_extraction.negotiation.carrier_first_offer": {"$ne": None}}
    if date_match:
        rate_match.update(date_match)
    p1.append({"$match": rate_match})
    p1.append(
        {
            "$group": {
                "_id": None,
                "avg_first_offer": {
                    "$avg": "$transcript_extraction.negotiation.carrier_first_offer"
                },
                "avg_final_rate": {
                    "$avg": "$transcript_extraction.negotiation.final_agreed_rate"
                },
                "avg_rounds": {
                    "$avg": "$transcript_extraction.negotiation.negotiation_rounds"
                },
            }
        }
    )

    # --- Pipeline 2: rate progression ---
    rate_fields = [
        "carrier_first_offer",
        "broker_first_counter",
        "carrier_second_offer",
        "broker_second_counter",
        "carrier_third_offer",
        "broker_third_counter",
        "final_agreed_rate",
    ]
    p2: list[dict] = []
    if date_match:
        p2.append({"$match": date_match})
    group_stage: dict = {"_id": None}
    for field in rate_fields:
        group_stage[field] = {"$avg": f"$transcript_extraction.negotiation.{field}"}
    p2.append({"$group": group_stage})

    # --- Pipeline 3: margin distribution ---
    p3: list[dict] = []
    margin_match: dict = {
        "transcript_extraction.negotiation.carrier_first_offer": {"$ne": None},
        "transcript_extraction.negotiation.final_agreed_rate": {"$ne": None},
    }
    if date_match:
        margin_match.update(date_match)
    p3.append({"$match": margin_match})
    p3.append(
        {
            "$project": {
                "margin": {
                    "$multiply": [
                        {
                            "$divide": [
                                {
                                    "$subtract": [
                                        "$transcript_extraction.negotiation.carrier_first_offer",
                                        "$transcript_extraction.negotiation.final_agreed_rate",
                                    ]
                                },
                                "$transcript_extraction.negotiation.carrier_first_offer",
                            ]
                        },
                        100,
                    ]
                }
            }
        }
    )
    p3.append(
        {
            "$bucket": {
                "groupBy": "$margin",
                "boundaries": [-100, 0, 5, 10, 15, 20, 100],
                "default": "other",
                "output": {"count": {"$sum": 1}},
            }
        }
    )

    # --- Pipeline 4: strategy effectiveness ---
    p4: list[dict] = []
    strategy_match: dict = {
        "transcript_extraction.optional.negotiation_strategy_used": {"$ne": None}
    }
    if date_match:
        strategy_match.update(date_match)
    p4.append({"$match": strategy_match})
    p4.append(
        {
            "$group": {
                "_id": "$transcript_extraction.optional.negotiation_strategy_used",
                "total": {"$sum": 1},
                "accepted": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.outcome.call_outcome",
                                    "accepted",
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "avg_rounds": {
                    "$avg": "$transcript_extraction.negotiation.negotiation_rounds"
                },
            }
        }
    )

    r1 = await db.call_records.aggregate(p1).to_list(length=1)
    r2 = await db.call_records.aggregate(p2).to_list(length=1)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)
    r4 = await db.call_records.aggregate(p4).to_list(length=None)

    # Rate averages
    avg_first_offer = 0.0
    avg_final_rate = 0.0
    avg_rounds = 0.0
    if r1:
        avg_first_offer = round(r1[0].get("avg_first_offer") or 0.0, 2)
        avg_final_rate = round(r1[0].get("avg_final_rate") or 0.0, 2)
        avg_rounds = round(r1[0].get("avg_rounds") or 0.0, 1)

    # Rate progression
    rate_progression: list[RateProgressionPoint] = []
    if r2:
        row = r2[0]
        for field in rate_fields:
            val = row.get(field)
            if val is not None:
                label = field.replace("_", " ").title()
                rate_progression.append(
                    RateProgressionPoint(round=label, avg_rate=round(val, 2))
                )

    # Margin distribution
    bucket_labels = {-100: "<0%", 0: "0-5%", 5: "5-10%", 10: "10-15%", 15: "15-20%", 20: "20%+"}
    margin_distribution = [
        MarginBucket(range=bucket_labels.get(row["_id"], str(row["_id"])), count=row["count"])
        for row in r3
    ]

    # Strategy effectiveness
    strategy_effectiveness = [
        StrategyRow(
            strategy=row["_id"],
            acceptance_rate=round(row["accepted"] / row["total"] * 100, 1) if row["total"] else 0.0,
            avg_rounds=round(row["avg_rounds"] or 0.0, 1),
            count=row["total"],
        )
        for row in r4
    ]

    return NegotiationsResponse(
        avg_first_offer=avg_first_offer,
        avg_final_rate=avg_final_rate,
        avg_rounds=avg_rounds,
        rate_progression=rate_progression,
        margin_distribution=margin_distribution,
        strategy_effectiveness=strategy_effectiveness,
    )


# ---------------------------------------------------------------------------
# AI Quality
# ---------------------------------------------------------------------------


async def get_ai_quality(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> AIQualityResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    # --- Pipeline 1: main stats ---
    p1: list[dict] = []
    if date_match:
        p1.append({"$match": date_match})
    p1.append(
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "compliant": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.performance.agent_followed_protocol",
                                    True,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "avg_interruptions": {
                    "$avg": "$transcript_extraction.conversation.ai_interruptions_count"
                },
                "transcription_errors": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.conversation.transcription_errors_detected",
                                    True,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "carrier_repeats": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.conversation.carrier_had_to_repeat_info",
                                    True,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    )

    # --- Pipeline 2: common violations ---
    p2: list[dict] = []
    if date_match:
        p2.append({"$match": date_match})
    p2.append({"$unwind": "$transcript_extraction.performance.protocol_violations"})
    p2.append(
        {
            "$group": {
                "_id": "$transcript_extraction.performance.protocol_violations",
                "count": {"$sum": 1},
            }
        }
    )
    p2.append({"$sort": {"count": -1}})
    p2.append({"$limit": 10})

    # --- Pipeline 3: interruptions over time ---
    p3: list[dict] = []
    if date_match:
        p3.append({"$match": date_match})
    p3.append(
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$system.call_startedat",
                    }
                },
                "avg": {
                    "$avg": "$transcript_extraction.conversation.ai_interruptions_count"
                },
            }
        }
    )

    # --- Pipeline 4: tone distribution ---
    p4: list[dict] = []
    if date_match:
        p4.append({"$match": date_match})
    p4.append(
        {
            "$group": {
                "_id": "$transcript_extraction.performance.agent_tone_quality",
                "count": {"$sum": 1},
            }
        }
    )

    r1 = await db.call_records.aggregate(p1).to_list(length=1)
    r2 = await db.call_records.aggregate(p2).to_list(length=None)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)
    r4 = await db.call_records.aggregate(p4).to_list(length=None)

    # Main stats
    compliance_rate = 0.0
    avg_interruptions = 0.0
    transcription_error_rate = 0.0
    carrier_repeat_rate = 0.0
    if r1:
        row = r1[0]
        total = row["total"]
        if total:
            compliance_rate = round(row["compliant"] / total * 100, 1)
            transcription_error_rate = round(
                row["transcription_errors"] / total * 100, 1
            )
            carrier_repeat_rate = round(row["carrier_repeats"] / total * 100, 1)
        avg_interruptions = round(row["avg_interruptions"] or 0.0, 1)

    # Common violations
    common_violations = [
        ViolationCount(violation=row["_id"], count=row["count"]) for row in r2
    ]

    # Interruptions over time
    interruptions_over_time = [
        InterruptionTimeSeriesPoint(date=row["_id"], avg=round(row["avg"], 1))
        for row in r3
    ]

    # Tone distribution
    tone_quality_distribution = {row["_id"]: row["count"] for row in r4}

    return AIQualityResponse(
        protocol_compliance_rate=compliance_rate,
        common_violations=common_violations,
        avg_interruptions=avg_interruptions,
        interruptions_over_time=interruptions_over_time,
        transcription_error_rate=transcription_error_rate,
        carrier_repeat_rate=carrier_repeat_rate,
        tone_quality_distribution=tone_quality_distribution,
    )


# ---------------------------------------------------------------------------
# Carriers
# ---------------------------------------------------------------------------


async def get_carriers(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> CarriersResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    # --- Pipeline 1: sentiment distribution ---
    p1: list[dict] = []
    if date_match:
        p1.append({"$match": date_match})
    p1.append(
        {
            "$group": {
                "_id": "$transcript_extraction.sentiment.call_sentiment",
                "count": {"$sum": 1},
            }
        }
    )

    # --- Pipeline 2: sentiment over time ---
    p2: list[dict] = []
    if date_match:
        p2.append({"$match": date_match})
    p2.append(
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$system.call_startedat",
                    }
                },
                "positive": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.sentiment.call_sentiment",
                                    "positive",
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "neutral": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.sentiment.call_sentiment",
                                    "neutral",
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "negative": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.sentiment.call_sentiment",
                                    "negative",
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    )

    # --- Pipeline 3: engagement levels ---
    p3: list[dict] = []
    if date_match:
        p3.append({"$match": date_match})
    p3.append(
        {
            "$group": {
                "_id": "$transcript_extraction.sentiment.engagement_level",
                "count": {"$sum": 1},
            }
        }
    )

    # --- Pipeline 4: future interest rate ---
    p4: list[dict] = []
    if date_match:
        p4.append({"$match": date_match})
    p4.append(
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "interested": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.sentiment.carrier_expressed_interest_future",
                                    True,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    )

    # --- Pipeline 5: top objections ---
    p5: list[dict] = []
    if date_match:
        p5.append({"$match": date_match})
    p5.append({"$unwind": "$transcript_extraction.optional.carrier_objections"})
    p5.append(
        {
            "$group": {
                "_id": "$transcript_extraction.optional.carrier_objections",
                "count": {"$sum": 1},
            }
        }
    )
    p5.append({"$sort": {"count": -1}})
    p5.append({"$limit": 10})

    # --- Pipeline 6: top questions ---
    p6: list[dict] = []
    if date_match:
        p6.append({"$match": date_match})
    p6.append({"$unwind": "$transcript_extraction.optional.carrier_questions_asked"})
    p6.append(
        {
            "$group": {
                "_id": "$transcript_extraction.optional.carrier_questions_asked",
                "count": {"$sum": 1},
            }
        }
    )
    p6.append({"$sort": {"count": -1}})
    p6.append({"$limit": 10})

    # --- Pipeline 7: carrier leaderboard ---
    p7: list[dict] = []
    if date_match:
        p7.append({"$match": date_match})
    p7.append(
        {
            "$group": {
                "_id": "$fmcsa_data.carrier_mc_number",
                "carrier_name": {"$first": "$fmcsa_data.carrier_name"},
                "calls": {"$sum": 1},
                "accepted": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": [
                                    "$transcript_extraction.outcome.call_outcome",
                                    "accepted",
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    )
    p7.append({"$sort": {"calls": -1}})
    p7.append({"$limit": 20})

    r1 = await db.call_records.aggregate(p1).to_list(length=None)
    r2 = await db.call_records.aggregate(p2).to_list(length=None)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)
    r4 = await db.call_records.aggregate(p4).to_list(length=1)
    r5 = await db.call_records.aggregate(p5).to_list(length=None)
    r6 = await db.call_records.aggregate(p6).to_list(length=None)
    r7 = await db.call_records.aggregate(p7).to_list(length=None)

    # Sentiment distribution
    sentiment_distribution = {row["_id"]: row["count"] for row in r1}

    # Sentiment over time
    sentiment_over_time = [
        {
            "date": row["_id"],
            "positive": row["positive"],
            "neutral": row["neutral"],
            "negative": row["negative"],
        }
        for row in r2
    ]

    # Engagement levels
    engagement_levels = {row["_id"]: row["count"] for row in r3}

    # Future interest rate
    future_interest_rate = 0.0
    if r4:
        total = r4[0]["total"]
        interested = r4[0]["interested"]
        future_interest_rate = round(interested / total * 100, 1) if total else 0.0

    # Top objections
    top_objections = [
        ObjectionCount(objection=row["_id"], count=row["count"]) for row in r5
    ]

    # Top questions
    top_questions = [
        QuestionCount(question=row["_id"], count=row["count"]) for row in r6
    ]

    # Carrier leaderboard
    carrier_leaderboard = [
        CarrierLeaderboardRow(
            carrier_name=row["carrier_name"],
            mc_number=row["_id"],
            calls=row["calls"],
            acceptance_rate=(
                round(row["accepted"] / row["calls"] * 100, 1) if row["calls"] else 0.0
            ),
        )
        for row in r7
    ]

    return CarriersResponse(
        sentiment_distribution=sentiment_distribution,
        sentiment_over_time=sentiment_over_time,
        engagement_levels=engagement_levels,
        future_interest_rate=future_interest_rate,
        top_objections=top_objections,
        top_questions=top_questions,
        carrier_leaderboard=carrier_leaderboard,
    )
