# Negotiation Window: Dynamic Pricing Logic

The AI agent negotiates carrier rates within a **negotiation window** — a target rate (opening offer) and a cap rate (walk-away maximum). Both adjust dynamically based on market signals, mimicking how a skilled freight broker adapts under pressure.

---

## The Window

```
                             loadboard_rate
                                    |
  target_carrier_rate ---[===negotiation room===]--- cap_carrier_rate
     (first offer)                                    (max we'd pay)
```

- **target_carrier_rate**: The agent's opening offer to the carrier. Always ≤ loadboard rate.
- **cap_carrier_rate**: The absolute maximum the agent will agree to. Can exceed loadboard rate (we take a loss to cover the load).

---

## Pressure Score

Two signals feed a single **pressure score** (0.0 = cold, 1.0 = hot):

### 1. Pickup Urgency

How soon the load needs to be picked up. A load shipping today is worth paying more for — an empty truck costs the broker money.

```
urgency = max(1.0 - hours_to_pickup / 72, 0.0)
```

| Hours to pickup | Urgency |
|-----------------|---------|
| 0 (now)         | 1.0     |
| 24              | 0.67    |
| 48              | 0.33    |
| 72+             | 0.0     |

### 2. Rate Rejection Pressure

How many carriers have already rejected this load because the rate was too low. The market is signaling our price isn't competitive.

```
rejection_pressure = min(rate_rejections / 5, 1.0)
```

| "Rate too low" rejections | Pressure |
|---------------------------|----------|
| 0                         | 0.0      |
| 1                         | 0.2      |
| 3                         | 0.6      |
| 5+                        | 1.0      |

### Combined

The stronger signal wins:

```
pressure = max(urgency, rejection_pressure)
```

---

## Rate Multipliers

### Target (opening offer)

```
target_mult = 0.95 + pressure × 0.05    →  range [0.95, 1.0]
```

- Cold load (pressure=0): offer 95% of loadboard — keep 5% margin.
- Hot load (pressure=1): offer 100% of loadboard — no margin, just cover it.

### Cap (walk-away maximum)

```
cap_mult = 1.0 + min(pressure × 0.06, 0.05)    →  range [1.0, 1.05]
```

The cap ramps faster than the target (0.06 slope vs 0.05), reaching its ceiling of 1.05 before max pressure. This gives the agent negotiation room even under moderate pressure.

- Cold load (pressure=0): cap at loadboard rate — no room to lose money.
- Moderate pressure (0.33): cap at 1.02× — small buffer.
- High pressure (0.83+): cap at 1.05× — max we'll absorb.

---

## Examples (loadboard_rate = $2,800)

| Scenario                           | Pressure | Target    | Cap       |
|------------------------------------|----------|-----------|-----------|
| Pickup in 5 days, no calls         | 0.0      | $2,660    | $2,800    |
| Pickup in 2 days, no rejections    | 0.33     | $2,706    | $2,856    |
| Pickup in 5 days, 3 rate too low   | 0.6      | $2,744    | $2,901    |
| Pickup tomorrow, 4+ rate too low   | 1.0      | $2,800    | $2,940    |

---

## Data Source

Rejection stats come from a single batch aggregation query on the `call_records` collection, filtering for calls where `call_outcome = "rejected"` and `rejection_reason = "Rate too low"`, grouped by `load_id_discussed`. This adds one DB round-trip per search request regardless of result count.

---

## Implementation

All logic lives in `app/loads/service.py`:

- `_get_call_pressure(load_ids)` — batch MongoDB aggregation for rejection stats
- `_apply_pricing(load, total_calls, rate_rejections)` — computes pressure and applies multipliers
