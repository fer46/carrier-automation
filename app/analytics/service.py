from datetime import datetime, time, timezone
from typing import Optional

from app.analytics.lane_parser import CITY_COORDS, parse_lane, resolve_city
from app.analytics.models import (
    AIQualityResponse,
    CarrierLeaderboardRow,
    CarriersResponse,
    EquipmentCount,
    FunnelStage,
    GeoArc,
    GeoCity,
    GeographyResponse,
    InterruptionTimeSeriesPoint,
    LaneCount,
    MarginBucket,
    NegotiationsResponse,
    ObjectionCount,
    OperationsResponse,
    NegotiationOutcome,
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
            date_filter["$gte"] = datetime.combine(
                datetime.strptime(date_from, "%Y-%m-%d").date(), time.min
            )
        if date_to:
            date_filter["$lte"] = datetime.combine(
                datetime.strptime(date_to, "%Y-%m-%d").date(), time.max
            )
        match["ingested_at"] = date_filter
    return match


async def ingest_call_record(record: dict) -> str:
    """Upsert a call record into MongoDB. Returns 'created' or 'updated'."""
    db = get_database()
    call_id = record["system"]["call_id"]

    result = await db.call_records.update_one(
        {"system.call_id": call_id},
        {
            "$set": record,
            "$setOnInsert": {"ingested_at": datetime.now(tz=timezone.utc)},
        },
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
                                            "$load_data.loadboard_rate",
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
                                                    "$load_data.loadboard_rate",
                                                    "$transcript_extraction.negotiation.final_agreed_rate",
                                                ]
                                            },
                                            "$load_data.loadboard_rate",
                                        ]
                                    },
                                    100,
                                ]
                            },
                            None,
                        ]
                    }
                },
                "total_booked_revenue": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {
                                        "$eq": [
                                            "$transcript_extraction.outcome.call_outcome",
                                            "accepted",
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
                            "$transcript_extraction.negotiation.final_agreed_rate",
                            0,
                        ]
                    }
                },
                "total_margin_earned": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {
                                        "$eq": [
                                            "$transcript_extraction.outcome.call_outcome",
                                            "accepted",
                                        ]
                                    },
                                    {
                                        "$ne": [
                                            "$load_data.loadboard_rate",
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
                                "$subtract": [
                                    "$load_data.loadboard_rate",
                                    "$transcript_extraction.negotiation.final_agreed_rate",
                                ]
                            },
                            0,
                        ]
                    }
                },
                "avg_rate_per_mile": {
                    "$avg": {
                        "$cond": [
                            {
                                "$and": [
                                    {
                                        "$ne": [
                                            "$transcript_extraction.negotiation.final_agreed_rate",
                                            None,
                                        ]
                                    },
                                    {"$ne": ["$load_data.miles", None]},
                                    {"$gt": ["$load_data.miles", 0]},
                                ]
                            },
                            {
                                "$divide": [
                                    "$transcript_extraction.negotiation.final_agreed_rate",
                                    "$load_data.miles",
                                ]
                            },
                            None,
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
            total_booked_revenue=0.0,
            total_margin_earned=0.0,
            avg_rate_per_mile=0.0,
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
        total_booked_revenue=round(row["total_booked_revenue"] or 0.0, 2),
        total_margin_earned=round(row["total_margin_earned"] or 0.0, 2),
        avg_rate_per_mile=round(row["avg_rate_per_mile"] or 0.0, 2),
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
                        "date": "$ingested_at",
                    }
                },
                "count": {"$sum": 1},
            }
        }
    )

    # --- Pipeline 2: rejection_reasons ---
    p2: list[dict] = []
    rejection_match: dict = {
        "transcript_extraction.outcome.rejection_reason": {"$ne": None}
    }
    if date_match:
        rejection_match.update(date_match)
    p2.append({"$match": rejection_match})
    p2.append(
        {
            "$group": {
                "_id": "$transcript_extraction.outcome.rejection_reason",
                "count": {"$sum": 1},
            }
        }
    )
    p2.append({"$sort": {"count": -1}})
    p2.append({"$limit": 10})

    # --- Pipeline 3: conversion funnel ---
    p3: list[dict] = []
    funnel_match: dict = {
        "transcript_extraction.outcome.funnel_stage_reached": {"$ne": None}
    }
    if date_match:
        funnel_match.update(date_match)
    p3.append({"$match": funnel_match})
    p3.append(
        {
            "$group": {
                "_id": "$transcript_extraction.outcome.funnel_stage_reached",
                "count": {"$sum": 1},
            }
        }
    )

    r1 = await db.call_records.aggregate(p1).to_list(length=None)
    r2 = await db.call_records.aggregate(p2).to_list(length=None)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)

    calls_over_time = [
        TimeSeriesPoint(date=row["_id"], count=row["count"]) for row in r1
    ]
    rejection_reasons = [
        ReasonCount(reason=row["_id"], count=row["count"]) for row in r2
    ]

    # Build funnel with cumulative counts (each stage includes all records
    # that passed through it, i.e. records at later stages count toward
    # earlier ones).
    funnel_stages_order = [
        "call_started",
        "fmcsa_verified",
        "load_matched",
        "offer_pitched",
        "negotiation_entered",
        "deal_agreed",
        "transferred_to_sales",
    ]
    stage_counts_raw = {row["_id"]: row["count"] for row in r3}

    # Cumulative: a record that reached stage N also passed through stages 0..N-1.
    # Accumulate from bottom up.
    stage_cumulative: dict[str, int] = {}
    running = 0
    for stage in reversed(funnel_stages_order):
        running += stage_counts_raw.get(stage, 0)
        stage_cumulative[stage] = running

    first_count = stage_cumulative.get(funnel_stages_order[0], 0)
    funnel = [
        FunnelStage(
            stage=stage,
            count=stage_cumulative.get(stage, 0),
            drop_off_percent=(
                round((1 - stage_cumulative.get(stage, 0) / first_count) * 100, 1)
                if first_count > 0
                else 0.0
            ),
        )
        for stage in funnel_stages_order
    ]

    return OperationsResponse(
        calls_over_time=calls_over_time,
        rejection_reasons=rejection_reasons,
        funnel=funnel,
    )


# ---------------------------------------------------------------------------
# Negotiations
# ---------------------------------------------------------------------------


async def get_negotiations(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> NegotiationsResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    # --- Pipeline 1: negotiation savings ---
    p1: list[dict] = []
    rate_match: dict = {
        "transcript_extraction.negotiation.carrier_first_offer": {"$ne": None},
        "transcript_extraction.negotiation.final_agreed_rate": {"$ne": None},
    }
    if date_match:
        rate_match.update(date_match)
    p1.append({"$match": rate_match})
    p1.append(
        {
            "$group": {
                "_id": None,
                "avg_savings": {
                    "$avg": {
                        "$subtract": [
                            "$transcript_extraction.negotiation.carrier_first_offer",
                            "$transcript_extraction.negotiation.final_agreed_rate",
                        ]
                    }
                },
                "avg_savings_percent": {
                    "$avg": {
                        "$cond": [
                            {
                                "$gt": [
                                    "$transcript_extraction.negotiation.carrier_first_offer",
                                    0,
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

    # --- Pipeline 2: negotiation outcomes ---
    p2: list[dict] = []
    if date_match:
        p2.append({"$match": date_match})
    p2.append({
        "$addFields": {
            "outcome_category": {
                "$switch": {
                    "branches": [
                        {
                            "case": {"$not": [{"$eq": [
                                "$transcript_extraction.outcome.call_outcome", "accepted"
                            ]}]},
                            "then": "No Deal",
                        },
                        {
                            "case": {"$gt": [
                                {"$ifNull": [
                                    "$transcript_extraction.negotiation.negotiation_rounds", 0
                                ]},
                                0,
                            ]},
                            "then": "Negotiated & Agreed",
                        },
                    ],
                    "default": "Accepted at First Offer",
                }
            }
        }
    })
    p2.append({"$group": {"_id": "$outcome_category", "count": {"$sum": 1}}})

    # --- Pipeline 3: margin distribution ---
    p3: list[dict] = []
    margin_match: dict = {
        "load_data.loadboard_rate": {"$ne": None},
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
                                        "$load_data.loadboard_rate",
                                        "$transcript_extraction.negotiation.final_agreed_rate",
                                    ]
                                },
                                "$load_data.loadboard_rate",
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
    r2 = await db.call_records.aggregate(p2).to_list(length=None)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)
    r4 = await db.call_records.aggregate(p4).to_list(length=None)

    # Negotiation savings
    avg_savings = 0.0
    avg_savings_percent = 0.0
    avg_rounds = 0.0
    if r1:
        avg_savings = round(r1[0].get("avg_savings") or 0.0, 2)
        avg_savings_percent = round(r1[0].get("avg_savings_percent") or 0.0, 1)
        avg_rounds = round(r1[0].get("avg_rounds") or 0.0, 1)

    # Negotiation outcomes
    outcome_map = {row["_id"]: row["count"] for row in r2}
    all_categories = ["Accepted at First Offer", "Negotiated & Agreed", "No Deal"]
    negotiation_outcomes = [
        NegotiationOutcome(name=cat, count=outcome_map.get(cat, 0))
        for cat in all_categories
    ]

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
        avg_savings=avg_savings,
        avg_savings_percent=avg_savings_percent,
        avg_rounds=avg_rounds,
        negotiation_outcomes=negotiation_outcomes,
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
                        "date": "$ingested_at",
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
    tone_quality_distribution = {row["_id"]: row["count"] for row in r4 if row["_id"] is not None}

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

    # --- Pipeline 1: top objections ---
    p1: list[dict] = []
    if date_match:
        p1.append({"$match": date_match})
    p1.append({"$unwind": "$transcript_extraction.optional.carrier_objections"})
    p1.append(
        {
            "$group": {
                "_id": "$transcript_extraction.optional.carrier_objections",
                "count": {"$sum": 1},
            }
        }
    )
    p1.append({"$sort": {"count": -1}})
    p1.append({"$limit": 10})

    # --- Pipeline 2: carrier leaderboard ---
    p2: list[dict] = []
    if date_match:
        p2.append({"$match": date_match})
    p2.append(
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
    p2.append({"$sort": {"calls": -1}})
    p2.append({"$limit": 20})

    # --- Pipeline 3: top requested lanes ---
    p3: list[dict] = []
    req_lane_match: dict = {"load_data.carrier_requested_lane": {"$ne": None}}
    if date_match:
        req_lane_match.update(date_match)
    p3.append({"$match": req_lane_match})
    p3.append(
        {"$group": {"_id": "$load_data.carrier_requested_lane", "count": {"$sum": 1}}}
    )
    p3.append({"$sort": {"count": -1}})
    p3.append({"$limit": 10})

    # --- Pipeline 4: top actual lanes ---
    p4: list[dict] = []
    actual_lane_match: dict = {
        "load_data.origin": {"$ne": None},
        "load_data.destination": {"$ne": None},
    }
    if date_match:
        actual_lane_match.update(date_match)
    p4.append({"$match": actual_lane_match})
    p4.append(
        {
            "$group": {
                "_id": {
                    "$concat": [
                        "$load_data.origin",
                        " → ",
                        "$load_data.destination",
                    ]
                },
                "count": {"$sum": 1},
            }
        }
    )
    p4.append({"$sort": {"count": -1}})
    p4.append({"$limit": 10})

    # --- Pipeline 5: equipment distribution ---
    p5: list[dict] = []
    equip_match: dict = {"load_data.equipment_type": {"$ne": None}}
    if date_match:
        equip_match.update(date_match)
    p5.append({"$match": equip_match})
    p5.append(
        {"$group": {"_id": "$load_data.equipment_type", "count": {"$sum": 1}}}
    )
    p5.append({"$sort": {"count": -1}})

    r1 = await db.call_records.aggregate(p1).to_list(length=None)
    r2 = await db.call_records.aggregate(p2).to_list(length=None)
    r3 = await db.call_records.aggregate(p3).to_list(length=None)
    r4 = await db.call_records.aggregate(p4).to_list(length=None)
    r5 = await db.call_records.aggregate(p5).to_list(length=None)

    # Top objections
    top_objections = [
        ObjectionCount(objection=row["_id"], count=row["count"]) for row in r1
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
        for row in r2
    ]

    # Lane intelligence
    top_requested_lanes = [
        LaneCount(lane=row["_id"], count=row["count"]) for row in r3
    ]
    top_actual_lanes = [
        LaneCount(lane=row["_id"], count=row["count"]) for row in r4
    ]
    equipment_distribution = [
        EquipmentCount(equipment_type=row["_id"], count=row["count"]) for row in r5
    ]

    return CarriersResponse(
        top_objections=top_objections,
        carrier_leaderboard=carrier_leaderboard,
        top_requested_lanes=top_requested_lanes,
        top_actual_lanes=top_actual_lanes,
        equipment_distribution=equipment_distribution,
    )


# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------


async def get_geography(
    date_from: Optional[str] = None, date_to: Optional[str] = None
) -> GeographyResponse:
    db = get_database()
    date_match = _build_date_match(date_from, date_to)

    # --- Pipeline 1: requested lanes (free-form text) ---
    p1: list[dict] = []
    req_match: dict = {"load_data.carrier_requested_lane": {"$ne": None}}
    if date_match:
        req_match.update(date_match)
    p1.append({"$match": req_match})
    p1.append(
        {"$group": {"_id": "$load_data.carrier_requested_lane", "count": {"$sum": 1}}}
    )
    p1.append({"$sort": {"count": -1}})
    p1.append({"$limit": 20})

    # --- Pipeline 2: booked lanes (separate origin/destination fields) ---
    p2: list[dict] = []
    booked_match: dict = {
        "load_data.origin": {"$ne": None},
        "load_data.destination": {"$ne": None},
    }
    if date_match:
        booked_match.update(date_match)
    p2.append({"$match": booked_match})
    p2.append(
        {
            "$group": {
                "_id": {
                    "origin": "$load_data.origin",
                    "destination": "$load_data.destination",
                },
                "count": {"$sum": 1},
            }
        }
    )
    p2.append({"$sort": {"count": -1}})
    p2.append({"$limit": 20})

    r1 = await db.call_records.aggregate(p1).to_list(length=None)
    r2 = await db.call_records.aggregate(p2).to_list(length=None)

    arcs: list[GeoArc] = []
    city_volumes: dict[str, int] = {}

    def _add_volume(city: str, count: int) -> None:
        city_volumes[city] = city_volumes.get(city, 0) + count

    # Process requested lanes (free-form text -> parse_lane)
    for row in r1:
        parsed = parse_lane(row["_id"])
        if not parsed:
            continue
        origin, dest = parsed
        o_coords = CITY_COORDS[origin]
        d_coords = CITY_COORDS[dest]
        arcs.append(
            GeoArc(
                origin=origin,
                origin_lat=o_coords[0],
                origin_lng=o_coords[1],
                destination=dest,
                dest_lat=d_coords[0],
                dest_lng=d_coords[1],
                count=row["count"],
                arc_type="requested",
            )
        )
        _add_volume(origin, row["count"])
        _add_volume(dest, row["count"])

    # Process booked lanes (separate origin/destination)
    for row in r2:
        origin_raw = row["_id"]["origin"]
        dest_raw = row["_id"]["destination"]
        origin = resolve_city(origin_raw)
        dest = resolve_city(dest_raw)
        if not origin or not dest:
            continue
        o_coords = CITY_COORDS[origin]
        d_coords = CITY_COORDS[dest]
        arcs.append(
            GeoArc(
                origin=origin,
                origin_lat=o_coords[0],
                origin_lng=o_coords[1],
                destination=dest,
                dest_lat=d_coords[0],
                dest_lng=d_coords[1],
                count=row["count"],
                arc_type="booked",
            )
        )
        _add_volume(origin, row["count"])
        _add_volume(dest, row["count"])

    cities = [
        GeoCity(
            name=name,
            lat=CITY_COORDS[name][0],
            lng=CITY_COORDS[name][1],
            volume=vol,
        )
        for name, vol in city_volumes.items()
    ]

    return GeographyResponse(arcs=arcs, cities=cities)
