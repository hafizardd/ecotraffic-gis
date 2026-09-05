# Segment Emission Pipeline — Detailed Implementation Plan

## 1. Overview

This plan bridges the gap between the existing pure-function segment emission library and a fully operational pipeline that processes CCTV observations, calculates road-segment-level emissions with AHP decision scores, and persists results for API consumption.

### Current State Summary

| Component | Status |
|---|---|
| Road segment + segment emission DB models | Complete |
| Migration for segment tables | Complete |
| Segment observation dataclass + validation | Complete |
| Camera-segment mapping resolver (in-memory) | Complete |
| Multi-camera aggregation service | Complete |
| Traffic calculator (volume, VKT) | Complete |
| Tier-2 emission calculator | Complete |
| 5-criterion AHP calculator | Complete |
| Spatial criteria normalizer | Complete |
| Pipeline orchestrator | Complete |
| API read endpoints | Complete |
| Segment seed data | **Missing** |
| Camera-segment mapping seed data | **Missing** |
| DB loader for camera-segment mappings | **Missing** |
| Segment emission persistence service | **Missing** |
| Inference worker → segment pipeline bridge | **Missing** |
| Periodic segment calculation task | **Missing** |
| Segment Redis latest state store | **Missing** |
| Segment WebSocket broadcast | **Missing** |
| Historical synthetic data | **Missing** |
| `data_source` field on Camera model | **Missing** |

---

## 2. Data Sources

### 2.1 Road Segment Geometry

**File:** `backend/data/road_segments_scored.geojson`

Contains 96+ Yogyakarta road segments as GeoJSON FeatureCollection. Each feature has:

| Property | Type | Description |
|---|---|---|
| `segment_id` | string | Unique ID (e.g., "SEG-0001") |
| `nama_ruas` | string | Road name |
| `chunk_no` | int | Chunk number for multi-part roads |
| `n_chunks` | int | Total chunks for this road |
| `length_km` | float | Segment length in kilometres |
| `volume_per_hour` | int | Observed vehicle volume |
| `emisi_CO2_g_per_jam` | float | CO₂ emission in g/hour |
| `decision_score` | float | Pre-computed AHP score |
| `priority_tier` | string | Priority classification |

Geometry is `LineString` in EPSG:4326 (WGS84).

### 2.2 Camera List

**File:** `backend/app/core/cctv.py`

Contains ~56 CCTV cameras with `camera_id`, `name`, `longitude`, `latitude`, `stream_url`, `referer`, `is_active`.

### 2.3 Live Cameras (PRD Requirement)

Only 2 cameras run live YOLO inference:

1. **SIMPANG JLAGRAN (PTZ)** — `atcs/ATCS_jlagran.stream/playlist.m3u8`
2. **JL. WARDHANI (SELATAN-TIMUR SMPN 5)** — `kotabaru/ANPR-Jl-Wardhani.stream/playlist.m3u8`

The remaining 54 cameras use precomputed historical data.

---

## 3. Implementation Phases

### Phase 1: Seed Data & Database Loaders

**Goal:** Populate `road_segments` and `camera_road_segments` tables so the pipeline has data to process.

#### Task 1.1 — Create Road Segment Seed Script

**File:** `backend/app/core/segment_seed.py` (new)

**Responsibilities:**
- Read `backend/data/road_segments_scored.geojson`
- For each GeoJSON feature, insert into `road_segments` table
- Use `ST_GeomFromGeoJSON()` for PostGIS geometry insertion
- Map `segment_id` → `road_segment_id` column
- Map `nama_ruas` → `name` column
- Set `length_km` from the feature properties
- Set `bus_stop_accessibility`, `activity_density`, `population` to `None` (placeholder — TODO: replace with real data)
- Set `spatial_metadata` to `{"source": "geojson_import", "priority_tier": ..., "volume_per_hour": ...}`
- Use `ON CONFLICT (road_segment_id) DO NOTHING` for idempotency
- Log inserted vs skipped counts

**SQL pattern:**
```sql
INSERT INTO road_segments (id, road_segment_id, name, geometry, length_km, spatial_metadata)
VALUES (gen_random_uuid(), :segment_id, :name, ST_GeomFromGeoJSON(:geometry), :length_km, :spatial_metadata::jsonb)
ON CONFLICT (road_segment_id) DO NOTHING
```

#### Task 1.2 — Create Camera-to-Segment Mapping Seed Script

**File:** `backend/app/core/segment_seed.py` (extend)

**Responsibilities:**
- For each camera in `cctv.py`, find the nearest road segment by coordinate proximity
- Algorithm: For each camera (lon, lat), compute distance to each segment's midpoint (first coordinate of LineString). Select the closest segment.
- Insert into `camera_road_segments` table with:
  - `camera_id`: reference to cameras table UUID
  - `road_segment_id`: reference to road_segments table UUID
  - `lane_or_stream_id`: `"default"` (can be refined later)
  - `is_active`: `True`
  - `valid_from`: `None` (always valid)
  - `valid_to`: `None` (no expiry)
- Use `ON CONFLICT (camera_id, road_segment_id, lane_or_stream_id, valid_from) DO NOTHING`
- Log mappings created

**SQL pattern:**
```sql
INSERT INTO camera_road_segments (id, camera_id, road_segment_id, lane_or_stream_id, is_active)
VALUES (gen_random_uuid(), :camera_db_id, :segment_db_id, 'default', true)
ON CONFLICT (camera_id, road_segment_id, lane_or_stream_id, valid_from) DO NOTHING
```

#### Task 1.3 — Create Database Loader for Active Mappings

**File:** `backend/app/services/segment_mapping.py` (extend)

**New function:**
```python
async def load_active_mappings(db: AsyncSession) -> list[CameraSegmentMapping]:
    """Load all active camera-to-segment mappings from the database."""
```

**Implementation:**
- Query `camera_road_segments` WHERE `is_active = True`
- JOIN with `cameras` to get `camera_id` (string identifier)
- JOIN with `road_segments` to get `road_segment_id` (string identifier)
- Return list of `CameraSegmentMapping` dataclass instances
- This bridges the DB data to the in-memory mapping resolver

#### Task 1.4 — Extend Main Seed Script

**File:** `backend/app/core/seed.py` (modify)

**Changes:**
- Import `seed_road_segments` and `seed_camera_segment_mappings` from `segment_seed`
- Call them after camera seeding in `main()`
- Add logging for segment seeding phase

#### Task 1.5 — Generate Synthetic Historical Data

**File:** `backend/scripts/generate_historical_segment_data.py` (new)

**Responsibilities:**
- For each of the 54 non-live cameras:
  - Determine which road segment it maps to
  - Generate 24 hours of synthetic segment emission records (one per hour)
  - Use realistic vehicle counts derived from the GeoJSON `volume_per_hour` with random variation (±20%)
  - Calculate VKT and emissions using the existing pipeline services
  - Use placeholder spatial criteria (K3-K5 = 0.5) with `spatial_criteria_status = "pending"`
  - Insert into `segment_emissions` table
- Mark all records with `calculation_version = 1`
- Use `data_source = "HISTORICAL"` metadata in `ahp_metadata`

**Vehicle count generation:**
- Base volume from GeoJSON per segment
- Distribute across 4 vehicle categories using ratios: motorcycle 60%, car 25%, bus 8%, truck 7%
- Apply random noise: `count = base_count * (0.8 + random() * 0.4)`

#### Task 1.6 — Write Seed Tests

**File:** `backend/tests/test_segment_seed.py` (new)

**Test cases:**
- Test GeoJSON file parsing (correct feature count, valid geometries)
- Test road segment insertion (correct column mapping, idempotency)
- Test camera-segment mapping (nearest-segment algorithm, correct FK references)
- Test that seed script is idempotent (run twice, no duplicates)

---

### Phase 2: Persistence Services & Worker Integration

**Goal:** Connect the inference worker to the segment pipeline so YOLO detections flow through to segment emission records.

#### Task 2.1 — Create Segment Emission Persistence Service

**File:** `backend/app/services/segment_emission_store.py` (new)

**Function:**
```python
async def persist_segment_emission(
    db: AsyncSession,
    segment_database_id: uuid.UUID,
    result: dict,
) -> SegmentEmission:
    """Persist pipeline output to the segment_emissions table."""
```

**Implementation:**
- Map pipeline result dict fields to `SegmentEmission` model columns:
  - `result["period_start"]` → `period_start`
  - `result["period_end"]` → `period_end`
  - `result["calculated_at"]` → `calculated_at`
  - `result["observation_duration_seconds"]` → `observation_duration_seconds`
  - `result["provenance"]["aggregation_policy"]` → `aggregation_policy`
  - `result["provenance"]["source_cameras"]` → `source_cameras`
  - `result["provenance"]["source_streams"]` → `source_streams`
  - `result["raw_counts"]` → `raw_counts`
  - `result["volume_per_hour"]` → `volume_per_hour`
  - `result["vkt_km_h"]` → `vkt_km_h`
  - `result["emissions"]["totals_g_h"]` → `pollutant_totals_g_h`
  - `result["emissions"]["by_category"]` → `category_pollutant_breakdown_g_h`
  - `result["raw_criteria"]` → `raw_criteria`
  - `result.get("normalized_criteria")` → `normalized_criteria`
  - `result.get("decision_score")` → `decision_score`
  - `result.get("priority")` → `priority`
  - `result["spatial_criteria_status"]` → `spatial_criteria_status`
  - Build `ahp_metadata` from `result.get("ahp_weights")`, `result.get("ahp_consistency")`
- Set `source_observation_count` from provenance
- Set `calculation_version = 1` (default)
- Handle upsert: check if a record exists for `(road_segment_id, period_start, calculation_version)`. If exists, update. If not, insert.
- `db.flush()` and return the persisted record

#### Task 2.2 — Extend Observation Persistence Service

**File:** `backend/app/services/segment_observation_store.py` (modify)

**New function:**
```python
async def persist_observation(
    db: AsyncSession,
    observation: SegmentTrafficObservation,
    segment_database_id: uuid.UUID,
    camera_database_id: uuid.UUID,
) -> SegmentTrafficObservationRecord:
    """Persist a validated observation to the database."""
```

**Implementation:**
- Call existing `observation_row()` to build the row dict
- Create `SegmentTrafficObservationRecord` model instance from the dict
- `db.add()` + `db.flush()`
- Return the persisted record

#### Task 2.3 — Bridge Inference Worker to Segment Pipeline

**File:** `backend/app/workers/inference_worker.py` (modify)

**Changes to `process_inference_job`:**

After the existing YOLO detection and camera-level emission aggregation, add segment pipeline integration:

1. **Load active mappings** (cached per worker process, refreshed periodically):
   ```python
   mappings = load_active_mappings_cached()
   ```

2. **Resolve camera → segment mapping:**
   ```python
   try:
       mapping = resolve_camera_mapping(mappings, camera_id=job.camera_id, captured_at=job.captured_at)
   except MappingResolutionError:
       metadata["segment_pipeline_status"] = "no_mapping"
       return result
   ```

3. **Create SegmentTrafficObservation from YOLO counts:**
   ```python
   observation = SegmentTrafficObservation(
       camera_id=job.camera_id,
       road_segment_id=mapping.road_segment_id,
       lane_or_stream_id=mapping.lane_or_stream_id,
       captured_at=job.captured_at,
       observation_duration_seconds=settings.EMISSION_AGGREGATION_WINDOW_SECONDS,
       raw_detected_count=vehicle_counts,
       vehicle_count_semantics=VehicleCountSemantics.SNAPSHOT_OCCUPANCY,
   )
   ```

4. **Persist observation** (using a synchronous session, since the Celery worker is sync):
   ```python
   db = sync_session_factory()
   try:
       segment_db_id = get_segment_database_id(db, mapping.road_segment_id)
       camera_db_id = job.camera_database_id
       persist_observation_sync(db, observation, segment_db_id, camera_db_id)
       db.commit()
   finally:
       db.close()
   ```

5. **Aggregate recent observations for the segment:**
   ```python
   recent_observations = get_recent_observations(db, segment_db_id, window_seconds=settings.EMISSION_AGGREGATION_WINDOW_SECONDS)
   ```

6. **Run segment emission pipeline:**
   ```python
   segment_result = calculate_segment_emission(
       recent_observations,
       period_start=...,
       period_end=...,
       road_length_km=segment_length_km,
       spatial_criteria={"K3": 0.5, "K4": 0.5, "K5": 0.5},  # TODO: replace with real data
   )
   ```

7. **Persist segment emission:**
   ```python
   persist_segment_emission(db, segment_db_id, segment_result)
   db.commit()
   ```

8. **Update metadata:**
   ```python
   metadata["segment_pipeline_status"] = "completed"
   metadata["segment_id"] = mapping.road_segment_id
   ```

**Caching strategy for mappings:**
- Store mappings in a module-level variable with timestamp
- Refresh if older than a configured TTL (default 5 minutes)
- Thread-safe (worker uses threads pool)

#### Task 2.4 — Add `data_source` Field to Camera Model

**File:** `backend/app/models/camera.py` (modify)

**Changes:**
- Add column: `data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="HISTORICAL")`
- Valid values: `"LIVE"`, `"HISTORICAL"`, `"REPLAY"`

#### Task 2.5 — Create Migration for `data_source`

**File:** `backend/migrations/versions/<new>_add_camera_data_source.py` (new)

**Migration:**
```python
def upgrade():
    op.add_column("cameras", sa.Column("data_source", sa.String(20), nullable=False, server_default="HISTORICAL"))
    # Set the 2 live cameras
    op.execute("UPDATE cameras SET data_source = 'LIVE' WHERE camera_id IN (<live_camera_ids>)")

def downgrade():
    op.drop_column("cameras", "data_source")
```

**Note:** The exact `camera_id` values for the 2 live cameras need to be verified against `cctv.py`. The PRD specifies:
- `atcs/ATCS_jlagran.stream/playlist.m3u8`
- `kotabaru/ANPR-Jl-Wardhani.stream/playlist.m3u8`

These may need to be added to `cctv.py` if not already present, or matched by partial URL.

#### Task 2.6 — Write Persistence Tests

**File:** `backend/tests/test_segment_emission_store.py` (new)

**Test cases:**
- Test round-trip: create pipeline result dict → persist → read back → verify all fields
- Test upsert: persist same period twice → verify only one record (updated)
- Test that `normalized_criteria` and `decision_score` can be `None` (spatial pending)
- Test that all JSONB columns serialize/deserialize correctly

---

### Phase 3: Scheduling, State Store & API Enhancements

**Goal:** Add periodic segment calculation, real-time state caching, and GeoJSON API endpoint.

#### Task 3.1 — Create Periodic Segment Calculation Task

**File:** `backend/app/workers/segment_calculation_worker.py` (new)

**Responsibilities:**
- Define a Celery Beat periodic task that runs periodically (default every 5 minutes)
- Query all road segments that have at least one active camera mapping
- For each segment:
  - Load recent observations from `segment_traffic_observations` table
  - If observations exist, run `calculate_segment_emission()`
  - Persist result to `segment_emissions` table
  - Update Redis latest state
  - Publish WebSocket update
- Log calculation results

**Task definition:**
```python
@celery_app.task(name="app.workers.segment_calculation_worker.recalculate_segment_emissions")
def recalculate_segment_emissions():
    """Periodic task to recalculate segment emissions for all active segments."""
```

**Celery Beat schedule (in `celery_app.py` or `docker-compose.yml`):**
```python
beat_schedule = {
    "recalculate-segment-emissions": {
        "task": "app.workers.segment_calculation_worker.recalculate_segment_emissions",
        "schedule": crontab(minute="*/5"),
    },
}
```

#### Task 3.2 — Create Segment Redis Latest State Store

**File:** `backend/app/services/segment_latest_state.py` (new)

**Class:**
```python
class SegmentLatestStateStore:
    def __init__(self, redis_client, ttl_seconds=3600):
        ...

    def save(self, segment_id: str, state: dict) -> dict:
        """Store latest emission state for a segment. Returns the stored payload."""
        ...

    def load(self, segment_id: str) -> dict | None:
        """Load latest emission state for a segment."""
        ...

    def load_all(self) -> dict[str, dict]:
        """Load latest states for all segments."""
        ...
```

**State payload:**
```python
{
    "segment_id": "SEG-0001",
    "decision_score": 49.05,
    "priority": "Sedang",
    "total_emission_g_h": 2166489.5,
    "volume_per_hour": 1273,
    "pollutant_totals": {...},
    "calculated_at": "2026-09-04T10:00:00Z",
    "spatial_criteria_status": "pending",
}
```

**Redis key pattern:** `emission:segment:{segment_id}`

#### Task 3.3 — Extend WebSocket for Segment Updates

**File:** `backend/app/api/routes/websocket.py` (modify)

**Changes:**
- After segment calculation, publish to channel `emissions:segment:{segment_id}`
- In the WebSocket handler, subscribe to both `emissions:{camera_id}` and `emissions:segment:*` patterns
- Forward segment updates to connected clients with type indicator:
  ```python
  {"type": "segment_update", "segment_id": "...", "data": {...}}
  ```

#### Task 3.4 — Add Segment GeoJSON Endpoint

**File:** `backend/app/api/routes/segment_emissions.py` (modify)

**New endpoint:**
```python
@router.get("/api/segments/geojson")
async def get_segments_geojson(db: AsyncSession = Depends(get_db)):
    """Return all road segments as GeoJSON FeatureCollection with emission data."""
```

**Implementation:**
- Query all `RoadSegment` records
- For each segment, find the latest `SegmentEmission` record
- Build GeoJSON FeatureCollection:
  - `geometry`: from `RoadSegment.geometry` (using `ST_AsGeoJSON`)
  - `properties`: segment_id, name, length_km + emission data (decision_score, priority, pollutant_totals, volume_per_hour)
- Return as GeoJSON response

#### Task 3.5 — Update Camera Endpoints with `data_source`

**File:** `backend/app/api/routes/cameras.py` (modify)

**Changes:**
- Include `data_source` field in camera GeoJSON properties
- Add filtering: `?data_source=LIVE` to return only live cameras
- Add filtering: `?data_source=HISTORICAL` to return only historical cameras

#### Task 3.6 — Write Scheduling & State Tests

**File:** `backend/tests/test_segment_calculation_worker.py` (new)

**Test cases:**
- Test periodic task queries correct segments
- Test that segment emissions are calculated and persisted
- Test Redis state store save/load/load_all
- Test that task handles missing observations gracefully

---

### Phase 4: Integration Testing & Documentation

**Goal:** Verify the complete pipeline works end-to-end and document the system.

#### Task 4.1 — End-to-End Pipeline Test

**Manual testing procedure:**
1. Run `alembic upgrade head`
2. Run `python -m app.core.seed` (seeds cameras + segments + mappings)
3. Run `python scripts/generate_historical_segment_data.py` (generates historical data)
4. Start backend: `uvicorn app.main:app --reload`
5. Start Celery worker: `celery -A app.workers.inference_worker worker --loglevel=info`
6. Start Celery Beat: `celery -A app.workers.inference_worker beat --loglevel=info`
7. Verify `GET /api/segments/geojson` returns segments with geometry
8. Verify `GET /api/emissions/map` returns segments with emission data
9. Verify `GET /api/emissions/SEG-0001` returns detailed segment emission
10. Trigger live camera inference and verify new segment emission records appear

#### Task 4.2 — Verify GeoJSON Import

- Confirm all segments loaded with correct geometry
- Confirm `length_km` values match GeoJSON
- Confirm camera-segment mappings are reasonable (cameras near their assigned segments)

#### Task 4.3 — Verify Historical Data

- Confirm 54 non-live cameras have 24 hours of synthetic emission records
- Confirm emission values are realistic (based on GeoJSON volume data)
- Confirm `spatial_criteria_status = "pending"` for all historical records

#### Task 4.4 — Run Full Test Suite

```bash
cd backend
pytest -v
```

Ensure all existing + new tests pass.

#### Task 4.5 — Update Documentation

**Files to update:**
- `README.md`: Document segment pipeline, new API endpoints, seed process
- `NOTES.md`: Add segment pipeline reset/clear instructions

---

## 4. API Endpoints Summary

After implementation, the following endpoints will be available:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/segments/geojson` | GeoJSON FeatureCollection of all road segments with emission data |
| `GET` | `/api/emissions/map` | Lightweight map items (segment_id, decision_score, priority, total_emission) |
| `GET` | `/api/emissions/{road_segment_id}` | Detailed segment emission with AHP scores, provenance, breakdown |
| `GET` | `/api/cameras` | Camera list (now includes `data_source` field) |
| `GET` | `/api/cameras?data_source=LIVE` | Only the live cameras |
| `WS` | `/ws/emissions` | Real-time push for both camera and segment updates |

---

## 5. Database Schema Additions

### 5.1 `cameras` table — new column

```sql
ALTER TABLE cameras ADD COLUMN data_source VARCHAR(20) NOT NULL DEFAULT 'HISTORICAL';
```

### 5.2 Data flow

```
YOLO Detection (worker)
    ↓
SegmentTrafficObservation (in-memory)
    ↓
segment_traffic_observations (DB) ← raw observation persisted
    ↓
aggregate_segment_observations() ← aggregates recent observations
    ↓
calculate_segment_emission() ← runs full pipeline (VKT, Tier-2, AHP)
    ↓
segment_emissions (DB) ← result persisted
    ↓
Redis latest state (emission:segment:{id}) ← for fast reads
    ↓
WebSocket broadcast → Frontend
```

---

## 6. Configuration Additions

New settings to add to `backend/app/core/config.py`:

```python
# Segment pipeline
SEGMENT_CALCULATION_PERIOD_MINUTES: int = 5
SEGMENT_OBSERVATION_WINDOW_SECONDS: int = 60
SEGMENT_MAPPING_CACHE_TTL_SECONDS: int = 300
SEGMENT_LATEST_STATE_TTL_SECONDS: int = 3600

# Spatial criteria placeholders (TODO: replace with real data)
DEFAULT_SPATIAL_CRITERIA_K3: float = 0.5
DEFAULT_SPATIAL_CRITERIA_K4: float = 0.5
DEFAULT_SPATIAL_CRITERIA_K5: float = 0.5
```

---

## 7. Known Limitations & TODOs

| Item | Status | Notes |
|---|---|---|
| Spatial criteria K3-K5 | Placeholder (0.5) | TODO: Replace with real bus stop, POI, population data |
| Vehicle count semantics | `snapshot_occupancy` | Current YOLO provides single-frame counts, not interval counts |
| Speed estimation | Not implemented | PRD marks this as out-of-scope |
| NDVI | Not used | Removed from final PRD AHP model |
| Gasoline/diesel car distinction | Not implemented | PRD uses single "car" class with gasoline emission factor |
| Historical data import | Synthetic | TODO: Replace with real precomputed data when available |

---

## 8. File Creation Summary

### New Files
| File | Purpose |
|---|---|
| `backend/app/core/segment_seed.py` | Seed road segments + camera-segment mappings from GeoJSON |
| `backend/app/services/segment_emission_store.py` | Persist pipeline output to `segment_emissions` table |
| `backend/app/workers/segment_calculation_worker.py` | Periodic Celery task for segment recalculation |
| `backend/app/services/segment_latest_state.py` | Redis latest state store for segments |
| `backend/scripts/generate_historical_segment_data.py` | Generate synthetic historical emission data |
| `backend/tests/test_segment_seed.py` | Tests for seed scripts |
| `backend/tests/test_segment_emission_store.py` | Tests for persistence service |
| `backend/tests/test_segment_calculation_worker.py` | Tests for periodic task |

### Modified Files
| File | Changes |
|---|---|
| `backend/app/core/seed.py` | Add segment seeding calls |
| `backend/app/services/segment_mapping.py` | Add `load_active_mappings()` DB loader |
| `backend/app/workers/inference_worker.py` | Add segment pipeline bridge after YOLO detection |
| `backend/app/models/camera.py` | Add `data_source` column |
| `backend/app/api/routes/segment_emissions.py` | Add `/api/segments/geojson` endpoint |
| `backend/app/api/routes/cameras.py` | Add `data_source` to responses + filtering |
| `backend/migrations/versions/` | New migration for `data_source` column |
