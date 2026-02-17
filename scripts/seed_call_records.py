"""Generate and seed realistic call_records into MongoDB for the dashboard.

Usage:
    python -m scripts.seed_call_records          # seed 300 mock records
    python -m scripts.seed_call_records --clean   # delete only mock records
"""

import argparse
import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# Realistic small/mid-size carriers with power-law call frequency weights
CARRIERS = [
    # (mc_number, name, weight) — higher weight = calls more often
    (342178, "Lone Star Freight LLC", 12),
    (518423, "Midwest Cargo Express", 10),
    (290145, "Horizon Trucking Inc", 9),
    (674312, "Eagle Road Transport", 8),
    (415890, "Summit Logistics LLC", 7),
    (782034, "Crossroads Carrier Inc", 7),
    (156789, "Prairie Wind Transport", 6),
    (623401, "Gulf Coast Haulers", 6),
    (891234, "Iron Horse Freight", 5),
    (345678, "Blue Ridge Carriers", 5),
    (567012, "Cascade Trucking Co", 4),
    (234567, "Patriot Transport LLC", 4),
    (789456, "Cornerstone Freight", 3),
    (456123, "High Plains Logistics", 3),
    (912345, "Delta Express Carriers", 3),
    (678901, "Riverbend Transport", 2),
    (123890, "Sunbelt Freight Inc", 2),
    (890567, "Trailhead Trucking", 2),
    (345012, "Northern Star Hauling", 2),
    (567890, "Keystone Carriers LLC", 2),
    (210345, "Flatland Express Inc", 1),
    (432109, "Redwood Freight LLC", 1),
    (654321, "Canyon Logistics Inc", 1),
    (876543, "Pinecrest Transport", 1),
    (109876, "Great Basin Carriers", 1),
    (321098, "Tidewater Trucking Co", 1),
    (543210, "Ironclad Freight LLC", 1),
    (765432, "Stonebridge Haulers", 1),
    (987654, "Ridgeline Transport", 1),
    (198765, "Amber Wave Logistics", 1),
]
CARRIER_WEIGHTS = [c[2] for c in CARRIERS]

# Major freight corridors — (origin, destination, weight)
# Heavy lanes appear more frequently for realism
FREIGHT_CORRIDORS = [
    ("Los Angeles, CA", "Dallas, TX", 10),
    ("Chicago, IL", "Atlanta, GA", 9),
    ("Dallas, TX", "Chicago, IL", 8),
    ("Houston, TX", "Memphis, TN", 7),
    ("Atlanta, GA", "Miami, FL", 7),
    ("Los Angeles, CA", "Phoenix, AZ", 6),
    ("Chicago, IL", "Detroit, MI", 6),
    ("Dallas, TX", "Houston, TX", 6),
    ("Memphis, TN", "Nashville, TN", 5),
    ("New York, NY", "Philadelphia, PA", 5),
    ("Jacksonville, FL", "Atlanta, GA", 5),
    ("Kansas City, MO", "St. Louis, MO", 5),
    ("Indianapolis, IN", "Columbus, OH", 4),
    ("Seattle, WA", "Portland, OR", 4),
    ("Denver, CO", "Salt Lake City, UT", 4),
    ("Charlotte, NC", "Raleigh, NC", 4),
    ("San Antonio, TX", "El Paso, TX", 3),
    ("Nashville, TN", "Louisville, KY", 3),
    ("Minneapolis, MN", "Milwaukee, WI", 3),
    ("Tampa, FL", "Orlando, FL", 3),
    ("Phoenix, AZ", "Las Vegas, NV", 3),
    ("Omaha, NE", "Kansas City, MO", 3),
    ("San Francisco, CA", "Sacramento, CA", 3),
    ("Norfolk, VA", "Richmond, VA", 2),
    ("Pittsburgh, PA", "Cleveland, OH", 2),
    ("Oklahoma City, OK", "Dallas, TX", 2),
    ("Savannah, GA", "Charlotte, NC", 2),
    ("New Orleans, LA", "Houston, TX", 2),
    ("Baltimore, MD", "Newark, NJ", 2),
    ("Cincinnati, OH", "Indianapolis, IN", 2),
]
CORRIDOR_WEIGHTS = [c[2] for c in FREIGHT_CORRIDORS]

# Approximate mileage for known corridors, fallback to calculation
CORRIDOR_MILES = {
    ("Los Angeles, CA", "Dallas, TX"): 1435,
    ("Chicago, IL", "Atlanta, GA"): 720,
    ("Dallas, TX", "Chicago, IL"): 920,
    ("Houston, TX", "Memphis, TN"): 580,
    ("Atlanta, GA", "Miami, FL"): 660,
    ("Los Angeles, CA", "Phoenix, AZ"): 370,
    ("Chicago, IL", "Detroit, MI"): 280,
    ("Dallas, TX", "Houston, TX"): 240,
    ("Memphis, TN", "Nashville, TN"): 210,
    ("New York, NY", "Philadelphia, PA"): 95,
    ("Jacksonville, FL", "Atlanta, GA"): 345,
    ("Kansas City, MO", "St. Louis, MO"): 250,
    ("Indianapolis, IN", "Columbus, OH"): 175,
    ("Seattle, WA", "Portland, OR"): 175,
    ("Denver, CO", "Salt Lake City, UT"): 525,
    ("Charlotte, NC", "Raleigh, NC"): 170,
    ("San Antonio, TX", "El Paso, TX"): 550,
    ("Nashville, TN", "Louisville, KY"): 175,
    ("Minneapolis, MN", "Milwaukee, WI"): 340,
    ("Tampa, FL", "Orlando, FL"): 85,
    ("Phoenix, AZ", "Las Vegas, NV"): 300,
    ("Omaha, NE", "Kansas City, MO"): 190,
    ("San Francisco, CA", "Sacramento, CA"): 90,
    ("Norfolk, VA", "Richmond, VA"): 95,
    ("Pittsburgh, PA", "Cleveland, OH"): 130,
    ("Oklahoma City, OK", "Dallas, TX"): 205,
    ("Savannah, GA", "Charlotte, NC"): 260,
    ("New Orleans, LA", "Houston, TX"): 350,
    ("Baltimore, MD", "Newark, NJ"): 190,
    ("Cincinnati, OH", "Indianapolis, IN"): 110,
}

EQUIPMENT_TYPES = ["Dry Van", "Reefer", "Flatbed", "Power Only", "Step Deck"]
EQUIPMENT_WEIGHTS = [0.45, 0.25, 0.15, 0.10, 0.05]

# Base rate per mile by equipment — reefer commands premium
RATE_PER_MILE_RANGE = {
    "Dry Van": (2.10, 3.20),
    "Reefer": (2.60, 3.90),
    "Flatbed": (2.40, 3.60),
    "Power Only": (1.80, 2.80),
    "Step Deck": (2.80, 4.20),
}

REJECTION_REASONS = [
    "Rate too low",
    "Equipment unavailable",
    "Too tight timeline",
    "Already committed",
    "Out of service area",
    "Truck breakdown",
    "Driver hours exceeded",
    "Weather concerns",
]
# "Rate too low" is #1, rest are less frequent
REJECTION_WEIGHTS = [0.30, 0.15, 0.12, 0.12, 0.10, 0.08, 0.07, 0.06]

FUNNEL_STAGES = [
    "call_started",
    "fmcsa_verified",
    "load_matched",
    "offer_pitched",
    "negotiation_entered",
    "deal_agreed",
    "transferred_to_sales",
]
# Agents are great at progressing calls — ~72% acceptance rate
# Rejected (stages 0-4) ≈ 28%, Accepted (stages 5-6) ≈ 72%
FUNNEL_STAGE_WEIGHTS = [0.02, 0.02, 0.04, 0.06, 0.14, 0.08, 0.64]

STRATEGIES = ["Collaborative", "Anchoring", "Conservative", "Aggressive"]
STRATEGY_WEIGHTS = [0.40, 0.25, 0.20, 0.15]

OBJECTIONS = [
    "Rate too low",
    "Need higher RPM",
    "Deadhead too far",
    "Pickup time too early",
    "Delivery window too tight",
    "No backhaul available",
    "Equipment mismatch",
    "Prefer direct shipper loads",
    "Need fuel surcharge",
]

PROTOCOL_VIOLATIONS = [
    "Skipped FMCSA verification",
    "Did not confirm equipment type",
    "Missed rate confirmation",
    "Forgot to present alternate loads",
    "Did not verify driver availability",
    "Skipped safety briefing",
    "Incomplete load details shared",
]

SENTIMENTS = ["positive", "neutral", "negative"]
ENGAGEMENT_LEVELS = ["high", "medium", "low"]
TONE_QUALITIES = ["professional", "friendly", "neutral", "rushed"]


def _get_miles(origin: str, destination: str) -> float:
    """Lookup real-ish mileage or generate a plausible one."""
    key = (origin, destination)
    if key in CORRIDOR_MILES:
        # Add small variance so not every run of the same lane is identical
        return round(CORRIDOR_MILES[key] * random.uniform(0.97, 1.03))
    # Reverse direction
    rev = (destination, origin)
    if rev in CORRIDOR_MILES:
        return round(CORRIDOR_MILES[rev] * random.uniform(0.97, 1.03))
    # Fallback: plausible interstate distance
    return round(random.uniform(180, 1600))


# ---------------------------------------------------------------------------
# Record generator
# ---------------------------------------------------------------------------


def generate_call_record(call_index: int, base_date: datetime) -> dict:
    # -- Timestamp: weekday-heavy, business hours --
    for _ in range(20):  # retry until we land on a weekday (85% chance)
        days_offset = random.randint(0, 27)
        candidate = base_date + timedelta(days=days_offset)
        if candidate.weekday() < 5 or random.random() < 0.15:
            break
    hours_offset = random.choices(
        list(range(6, 21)),
        weights=[1, 3, 5, 7, 8, 8, 8, 7, 7, 6, 5, 4, 3, 2, 1],
        k=1,
    )[0]
    minutes_offset = random.randint(0, 59)
    ingested_at = base_date + timedelta(
        days=days_offset, hours=hours_offset, minutes=minutes_offset
    )

    # -- Carrier (power-law) --
    carrier = random.choices(CARRIERS, weights=CARRIER_WEIGHTS, k=1)[0]
    mc_number, carrier_name = carrier[0], carrier[1]

    # -- Lane (weighted corridors) --
    corridor = random.choices(FREIGHT_CORRIDORS, weights=CORRIDOR_WEIGHTS, k=1)[0]
    origin, destination = corridor[0], corridor[1]
    miles = _get_miles(origin, destination)

    # -- Equipment --
    equipment = random.choices(EQUIPMENT_TYPES, weights=EQUIPMENT_WEIGHTS, k=1)[0]

    # -- Rates (equipment-aware) --
    rpm_lo, rpm_hi = RATE_PER_MILE_RANGE[equipment]
    rate_per_mile = round(random.uniform(rpm_lo, rpm_hi), 2)
    loadboard_rate = round(miles * rate_per_mile, 2)

    # -- Funnel stage --
    funnel_stage = random.choices(FUNNEL_STAGES, weights=FUNNEL_STAGE_WEIGHTS, k=1)[0]
    stage_idx = FUNNEL_STAGES.index(funnel_stage)

    # Accepted = deal_agreed or transferred_to_sales
    is_accepted = stage_idx >= 5

    # -- Call duration (correlates with progression) --
    base_duration = 45 + stage_idx * 35
    call_duration = random.randint(base_duration, base_duration + 90)

    # -- Negotiation --
    negotiation: dict = {}
    final_agreed_rate = None

    if stage_idx >= 4:  # negotiation_entered or beyond
        # Carrier asks above loadboard; agent negotiates down
        carrier_first_offer = round(loadboard_rate * random.uniform(1.08, 1.25), 2)
        broker_first_counter = round(loadboard_rate * random.uniform(0.93, 1.00), 2)
        rounds = random.choices([1, 2, 3, 4], weights=[0.25, 0.40, 0.25, 0.10], k=1)[0]

        negotiation["carrier_first_offer"] = carrier_first_offer
        negotiation["broker_first_counter"] = broker_first_counter
        negotiation["negotiation_rounds"] = rounds

        if rounds >= 2:
            negotiation["carrier_second_offer"] = round(
                carrier_first_offer * random.uniform(0.92, 0.97), 2
            )
            negotiation["broker_second_counter"] = round(
                broker_first_counter * random.uniform(1.01, 1.06), 2
            )
        if rounds >= 3:
            negotiation["carrier_third_offer"] = round(
                negotiation.get("carrier_second_offer", carrier_first_offer)
                * random.uniform(0.94, 0.98),
                2,
            )
            negotiation["broker_third_counter"] = round(
                negotiation.get("broker_second_counter", broker_first_counter)
                * random.uniform(1.00, 1.04),
                2,
            )

        if is_accepted:
            # Agent closes below the loadboard rate → positive margin
            # Most deals: 5-18% below loadboard (great margins)
            discount = random.uniform(0.82, 0.95)
            final_agreed_rate = round(loadboard_rate * discount, 2)
            negotiation["final_agreed_rate"] = final_agreed_rate
    elif is_accepted:
        # Accepted at first offer — still a good deal
        discount = random.uniform(0.88, 0.97)
        final_agreed_rate = round(loadboard_rate * discount, 2)
        negotiation["final_agreed_rate"] = final_agreed_rate
        negotiation["negotiation_rounds"] = 0

    # -- Rejection reason --
    rejection_reason = None
    if not is_accepted and stage_idx >= 3:
        rejection_reason = random.choices(REJECTION_REASONS, weights=REJECTION_WEIGHTS, k=1)[0]

    # -- Strategy --
    strategy_used = None
    if stage_idx >= 4:
        strategy_used = random.choices(STRATEGIES, weights=STRATEGY_WEIGHTS, k=1)[0]

    # -- Carrier objections (0-2, less frequent since agent is good) --
    num_objections = random.choices([0, 1, 2], weights=[0.45, 0.40, 0.15], k=1)[0]
    carrier_objections = random.sample(OBJECTIONS, num_objections)

    # -- Requested lane (carrier sometimes wants a different lane) --
    # ~40% got exactly what they wanted (no separate requested lane needed),
    # ~35% requested a related lane (same origin or nearby corridor),
    # ~25% had no specific lane preference (no field set).
    carrier_requested_lane = None
    lane_roll = random.random()
    if lane_roll < 0.40:
        # Carrier got booked on their requested lane — no separate field
        pass
    elif lane_roll < 0.75:
        # Carrier requested a different but realistic lane (weighted corridors)
        # Bias toward same-origin lanes to simulate "I'm in X, what do you have?"
        same_origin_corridors = [
            (i, c)
            for i, c in enumerate(FREIGHT_CORRIDORS)
            if c[0] == origin and c[1] != destination
        ]
        if same_origin_corridors and random.random() < 0.60:
            # 60% chance: same origin, different destination
            idx, corridor_pick = random.choice(same_origin_corridors)
            carrier_requested_lane = f"{corridor_pick[0]} \u2192 {corridor_pick[1]}"
        else:
            # Pick from weighted corridors (excluding the booked lane)
            other_corridors = [
                (i, c)
                for i, c in enumerate(FREIGHT_CORRIDORS)
                if not (c[0] == origin and c[1] == destination)
            ]
            if other_corridors:
                indices, corridors = zip(*other_corridors)
                weights = [CORRIDOR_WEIGHTS[i] for i in indices]
                corridor_pick = random.choices(corridors, weights=weights, k=1)[0]
                carrier_requested_lane = f"{corridor_pick[0]} \u2192 {corridor_pick[1]}"

    # -- Pickup / delivery --
    pickup = ingested_at + timedelta(days=random.randint(1, 4))
    delivery = pickup + timedelta(hours=random.randint(10, 48))

    # -- Sentiment (accepted calls → mostly positive) --
    if is_accepted:
        sentiment = random.choices(SENTIMENTS, weights=[0.65, 0.28, 0.07], k=1)[0]
    else:
        sentiment = random.choices(SENTIMENTS, weights=[0.15, 0.40, 0.45], k=1)[0]

    # -- Performance (agent is high-quality: 91% protocol compliance) --
    followed_protocol = random.random() < 0.91
    violations = []
    if not followed_protocol:
        violations = random.sample(PROTOCOL_VIOLATIONS, random.randint(1, 2))

    # -- Conversation quality (low interruptions, few errors) --
    interruptions = random.choices([0, 1, 2, 3], weights=[0.45, 0.35, 0.15, 0.05], k=1)[0]
    transcription_errors = random.random() < 0.05
    carrier_had_to_repeat = random.random() < 0.08

    # -- Transfer to sales (consistent with funnel stage) --
    if funnel_stage == "transferred_to_sales":
        transfer_attempted = True
        transfer_completed = True
    elif funnel_stage == "deal_agreed":
        # Deal agreed but not transferred — maybe attempted but failed
        transfer_attempted = random.random() < 0.40
        transfer_completed = False
    else:
        transfer_attempted = False
        transfer_completed = False

    # -- Alternate loads --
    alternate_loads = random.choices([0, 1, 2, 3], weights=[0.35, 0.35, 0.20, 0.10], k=1)[0]

    # -- FMCSA (nearly all active) --
    fmcsa_validation = random.choices(
        ["Active", "Inactive", "Not Found"], weights=[0.93, 0.04, 0.03], k=1
    )[0]

    # -- Engagement & tone (agent is professional) --
    if is_accepted:
        engagement = random.choices(ENGAGEMENT_LEVELS, weights=[0.55, 0.35, 0.10], k=1)[0]
    else:
        engagement = random.choices(ENGAGEMENT_LEVELS, weights=[0.20, 0.45, 0.35], k=1)[0]
    tone = random.choices(TONE_QUALITIES, weights=[0.45, 0.35, 0.15, 0.05], k=1)[0]

    record = {
        "_mock": True,
        "system": {
            "call_id": str(uuid.uuid4()),
            "call_duration": call_duration,
        },
        "fmcsa_data": {
            "carrier_mc_number": mc_number,
            "carrier_name": carrier_name,
            "carrier_validation_result": fmcsa_validation,
            "retrieval_date": ingested_at.strftime("%Y-%m-%d"),
        },
        "load_data": {
            "load_id_discussed": f"LD-{random.randint(1, 50):03d}",
            "alternate_loads_presented": alternate_loads,
            "loadboard_rate": loadboard_rate,
            "origin": origin,
            "destination": destination,
            "equipment_type": equipment,
            "miles": miles,
            "pickup_datetime": pickup.isoformat(),
            "delivery_datetime": delivery.isoformat(),
        },
        "transcript_extraction": {
            "outcome": {
                "call_outcome": "accepted" if is_accepted else "rejected",
                "funnel_stage_reached": funnel_stage,
            },
            "negotiation": negotiation,
            "sentiment": {
                "call_sentiment": sentiment,
                "sentiment_progression": random.choice(["improving", "stable", "declining"]),
                "engagement_level": engagement,
                "carrier_expressed_interest_future": (
                    random.random() < 0.65 if is_accepted else random.random() < 0.25
                ),
            },
            "performance": {
                "agent_followed_protocol": followed_protocol,
                "protocol_violations": violations,
                "agent_tone_quality": tone,
            },
            "conversation": {
                "ai_interruptions_count": interruptions,
                "transcription_errors_detected": transcription_errors,
                "carrier_had_to_repeat_info": carrier_had_to_repeat,
            },
            "operational": {
                "transfer_to_sales_attempted": transfer_attempted,
                "transfer_to_sales_completed": transfer_completed,
                "transfer_reason": (
                    random.choice(
                        [
                            "High-value deal",
                            "Complex negotiation",
                            "VIP carrier",
                            "Multi-load opportunity",
                        ]
                    )
                    if transfer_attempted
                    else None
                ),
                "loads_presented_count": 1 + alternate_loads,
            },
            "optional": {
                "negotiation_strategy_used": strategy_used,
                "carrier_negotiation_leverage": (
                    random.sample(
                        [
                            "Multiple load options",
                            "Market rate data",
                            "Volume commitment",
                            "Quick payment terms",
                            "Preferred lane",
                            "Consistent freight",
                        ],
                        k=random.randint(1, 3),
                    )
                    if stage_idx >= 4
                    else []
                ),
                "carrier_objections": carrier_objections,
            },
        },
        "ingested_at": ingested_at,
    }

    if rejection_reason:
        record["transcript_extraction"]["outcome"]["rejection_reason"] = rejection_reason

    if carrier_requested_lane:
        record["load_data"]["carrier_requested_lane"] = carrier_requested_lane

    return record


# ---------------------------------------------------------------------------
# Seed / Clean
# ---------------------------------------------------------------------------

NUM_RECORDS = 150


async def clean():
    """Delete only mock records (where _mock == True)."""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    result = await db.call_records.delete_many({"_mock": True})
    print(
        f"Deleted {result.deleted_count} mock call records "
        f"from '{settings.DATABASE_NAME}.call_records'"
    )
    client.close()


async def seed():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    # Remove previous mock data only (preserve real records)
    deleted = await db.call_records.delete_many({"_mock": True})
    if deleted.deleted_count:
        print(f"Removed {deleted.deleted_count} previous mock records")

    # Base date: 30 days ago; records end 2 days before today (no today/yesterday)
    base_date = datetime.now(tz=UTC) - timedelta(days=30)

    records = [generate_call_record(i, base_date) for i in range(1, NUM_RECORDS + 1)]

    result = await db.call_records.insert_many(records)
    print(
        f"Seeded {len(result.inserted_ids)} mock call records into "
        f"'{settings.DATABASE_NAME}.call_records'"
    )

    # Summary
    accepted = sum(
        1 for r in records if r["transcript_extraction"]["outcome"]["call_outcome"] == "accepted"
    )
    with_negotiation = sum(
        1
        for r in records
        if r["transcript_extraction"]["negotiation"].get("final_agreed_rate")
        and r["transcript_extraction"]["negotiation"].get("negotiation_rounds", 0) > 0
    )
    margins = []
    for r in records:
        lb = r["load_data"]["loadboard_rate"]
        fa = r["transcript_extraction"]["negotiation"].get("final_agreed_rate")
        if lb and fa:
            margins.append((lb - fa) / lb * 100)

    print(f"  Accepted: {accepted}/{len(records)} ({accepted / len(records) * 100:.1f}%)")
    print(f"  Negotiated deals: {with_negotiation}")
    if margins:
        print(f"  Avg margin: {sum(margins) / len(margins):.1f}%")
    print(f"  Date range: {base_date.date()} to {(base_date + timedelta(days=27)).date()}")
    print(f"  Unique carriers: {len(set(r['fmcsa_data']['carrier_mc_number'] for r in records))}")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed or clean mock call records")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete only mock records (_mock: true) instead of seeding",
    )
    args = parser.parse_args()

    if args.clean:
        asyncio.run(clean())
    else:
        asyncio.run(seed())
