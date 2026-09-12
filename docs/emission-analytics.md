# Emission Analytics

Emission analytics uses `segment_traffic_observations` as its durable input and
`segment_emissions` as its analytical fact table. Redis keeps the current
segment state, and WebSocket messages deliver that state to the dashboard. The
REST analytics endpoints read PostgreSQL so trend, history, and export use the
same versioned facts.

## Calculation path

Historical segment analytics uses tracked vehicle flow. `FlowCounter` counts a
ByteTrack identity once when it leaves the configured ROI. Counts are collected
over the measured capture duration and stored with
`vehicle_count_semantics=interval_count`.

For each vehicle category (`motorcycle`, `car`, `bus`, and `truck`), the segment
pipeline calculates:

```text
vehicles/hour = interval count * 3600 / observed seconds
VKT km/hour   = vehicles/hour * segment length km
emission g/hour = VKT km/hour * Tier-2 factor g/km
emission kg/hour = emission g/hour / 1000
```

The pipeline produces separate rates for TSP, CO, NOx, SO2, HC, CO2, CH4, and
N2O. Camera occupancy remains available for the existing live camera view. If
an old segment observation only contains snapshot occupancy, its analytical
fact is labeled `live_occupancy_estimate` and `estimated`; it is never presented
as observed flow.

The segment observation window defaults to 60 seconds and is configured by
`SEGMENT_OBSERVATION_WINDOW_SECONDS`. The Celery schedule and flow measurement
use the same setting. A 10-second default was not adopted because it would
multiply inference-adjacent database writes and WebSocket/Redis traffic by six;
deployments can lower the setting after measuring GPU throughput, capture
continuity, database write capacity, and dashboard update load.

## Rate aggregation

Samples for one segment are averaged inside each time bucket. Rates for
independent segments are then added for the same pollutant. The service never
sums repeated kg/hour samples over time and never combines different pollutants
into an unlabeled total.

Default time buckets are:

| Selected range | Bucket |
| --- | --- |
| up to 1 hour | 1 minute |
| up to 3 hours | 5 minutes |
| up to 12 hours | 15 minutes |
| up to 24 hours | 1 hour |

Recalculations are versioned. For an identical segment and period, queries use
the highest calculation version and newest processing time. Rows marked
`SYNTHETIC` or `REPLAY` are excluded from live analytical results and exports.

## API and realtime contract

The router at `/api/analytics/emissions` exposes:

- `GET /options` for segment and corridor filters.
- `GET /latest` for the current eight-pollutant segment rates.
- `GET /trend` for database-bucketed rates.
- `GET /top-corridors` for a selected pollutant, ranked by average rate.
- `GET /composition` for the eight-pollutant distribution.
- `GET /history` for paginated analytical facts.
- `GET /export?format=csv|json` for the same filtered facts used by history.

The time range is limited to 31 days, export to 100,000 facts, and history to
200 rows per page. Invalid ranges and missing segment/corridor filters return
explicit 4xx responses. Database failures return 503. Export includes units in
the column names or metadata and protects CSV cells that spreadsheet programs
could otherwise interpret as formulas.

Every `segment_update` includes the eight kg/hour values, category vehicle
volume, category VKT, `observed_at`, `processed_at`, freshness, provenance,
calculation mode, and calculation version. Redis updates use an atomic timestamp
comparison so late workers cannot replace newer state. The frontend applies the
same ordering check before updating its segment map.

## Data provenance and current assumptions

Emission factors come from `cv/proposal_emission_factors.py`; the factor set and
road/control assumptions are copied into each fact's calculation metadata.
Road segment length is required for VKT. A corridor is read from
`RoadSegment.spatial_metadata.corridor_id` and `corridor_name`; when those fields
are absent, the segment ID and name form a one-segment corridor. This fallback
keeps existing road-segment records queryable without adding a parallel history
schema.

`observed_at` represents when the source interval ended, while `processed_at`
records calculation time. The dashboard labels a value stale after the larger
of `DATA_AGING_THRESHOLD_SECONDS` and three observation windows. A Redis outage
does not roll back PostgreSQL facts: reconciliation can republish their latest
state later.
