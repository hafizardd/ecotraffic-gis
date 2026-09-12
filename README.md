# 🌿 EcoTraffic GIS

An AI-powered WebGIS **Transport Emission Decision Support System (TEDSS)** for Yogyakarta. It turns existing CCTV infrastructure into a corridor-level emission and mobility inventory, ranks road segments with AHP, and explains what public-transport intervention each corridor needs.

Built for the MAPID WebGIS Competition #2 (2026) — **BANG JO** — combining a **fine-tuned YOLO11n** vehicle detector, **FastAPI**, **PostGIS**, and **Next.js + React + TypeScript + MapLibre** into a single freshness-aware dashboard.

The pipeline is CCTV → vehicle detection → traffic volume → VKT → eight-pollutant emissions → spatial integration & AHP → AI recommendation → WebGIS output.

- Real-time state and analytics semantics: [Emission Analytics](docs/emission-analytics.md)
- Product requirements and scope decisions: [Proposal & PRD Summary](docs/EcoTrafficGIS_Proposal_PRD_Detailed_Summary.md)
- Bang Jo assistant design: [RAG Implementation Plan](docs/bangjo-rag-implementation-plan.md)

---

## 📸 What It Does

- Displays **56 CCTV points** on an interactive MapLibre map, color-coded by emission level
- Distinguishes **2 LIVE cameras** (online inference) from **54 HISTORICAL / REPLAY cameras** (precomputed facts) so historical data is never read as live
- Runs a **fine-tuned YOLO11n** detector over the live streams (car, motorcycle, bus, truck)
- Tracks vehicles with **ByteTrack** and counts unique flow exits per camera ROI
- Streams the annotated detection feed in-browser as MJPEG (`/tracked.mjpg`)
- Computes **VKT-based Tier-2 emissions** for eight pollutants: TSP, NOx, SO₂, HC, CO, CO₂, CH₄, N₂O
- Aggregates emission facts per **road segment** and surfaces them over WebSocket in near real time
- Produces an **AHP Transport Emission Decision Score** from five criteria: emission, vehicle volume, halte access, activity density, population
- Renders the **Activity Potential Map** as an H3 hexagonal grid from POI, population, and mobility indicators
- Answers questions through **Bang Jo**, an LLM assistant grounded in system data (with Avoid–Shift–Improve recommendations)
- Provides analytics dashboards, history, and **CSV / JSON export** with provenance preserved

---

## 🧠 Detection Model

The vehicle detector is a **YOLO11n** model **fine-tuned for 100 epochs** on the project's four-class vehicle dataset.

| Property | Value |
|---|---|
| Architecture | YOLO11n (Ultralytics) |
| Training | Fine-tuned, 100 epochs |
| Classes | `car`, `motorcycle`, `bus`, `truck` |
| Weights | `backend/yolo/best100.pt` (100-epoch); `backend/yolo/best30.pt` (earlier 30-epoch checkpoint) |
| Tracking | ByteTrack (`bytetrack.yaml`) for live flow counting |
| Runtime | PyTorch via Ultralytics, OpenCV, headless worker image |

Notes:
- Emission calculation treats `car` as a single class and uses the **gasoline-car emission factor** as the documented modeling assumption (gasoline/diesel is not inferred from video).
- The model is loaded **once per worker process**, not per frame, and shared across cameras with batched inference.
- The active weights are selected by `YOLO_MODEL_PATH`.

---

## 🏗️ Architecture

```text
CCTV streams (56)
        │   2 LIVE (YOLO11n + ByteTrack tracker process)
        │   54 HISTORICAL / REPLAY (precomputed facts)
        ▼
backend/cv          detector · ROIs · frame store · flow counter
        ▼
tracking_worker     per-camera threads → segment_traffic_observations
        ▼
segment_worker      closed-window reconciliation → segment_emissions (versioned facts)
        ▼
PostgreSQL/PostGIS  durable facts        Redis  latest state + pub/sub
        ▼
FastAPI REST + /ws/emissions  ─────────────►  Next.js dashboard (MapLibre)
```

- **`tracker`** (`Dockerfile.worker`) holds YOLO tracker state per camera and publishes track payloads + annotated MJPEG snapshots.
- **`beat`** schedules `recalculate_segment_emissions`; **`segment-worker`** runs it on the `inference` queue.
- **Redis** carries latest emission state and `emission_update` / `segment_update` / `track_update` messages.
- **PostgreSQL + PostGIS** stores cameras, road segments, mappings, observations, and versioned emission facts.

---

## 🗂️ Project Structure

```
ecotraffic-gis/
│
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── cameras.py            # CCTV locations, live proxy, tracked.mjpg
│   │   │   ├── emissions.py          # Live emission data
│   │   │   ├── analytics_emissions.py# Trend/history/top-corridors/composition/export
│   │   │   ├── segment_emissions.py  # Segment GeoJSON + per-segment facts
│   │   │   ├── spatial_layers.py     # Spatial layer endpoints
│   │   │   ├── activity_grid.py      # H3 activity-potential grid
│   │   │   ├── bangjo.py             # Bang Jo LLM assistant (/api/chat)
│   │   │   └── websocket.py          # /ws/emissions + Redis subscriber
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic settings from .env
│   │   │   ├── database.py           # SQLAlchemy async + sync engines
│   │   │   ├── cctv.py               # 56-camera source list
│   │   │   └── seed.py / segment_seed.py
│   │   ├── models/                   # Cameras, segments, observations, emissions, embeddings
│   │   ├── schemas/                  # Pydantic request/response models
│   │   ├── services/                 # Emission math, aggregation, mapping, AHP, Bang Jo RAG
│   │   ├── workers/
│   │   │   ├── celery_app.py
│   │   │   ├── tracking_worker.py            # YOLO11n + ByteTrack (2 LIVE cameras)
│   │   │   ├── segment_calculation_worker.py # Windowed segment reconciliation
│   │   │   └── snapshot_worker.py            # Deprecated historical sampler
│   │   └── main.py                   # FastAPI app entry point
│   ├── cv/
│   │   ├── detector.py               # YOLO11n wrapper (single + batched, ROI)
│   │   ├── track_emission.py         # FlowCounter / occupancy
│   │   ├── emission_factors.py       # Snapshot multi-pollutant factors
│   │   ├── proposal_emission_factors.py  # Tier-2 g/km factors (segment pipeline)
│   │   ├── rois.py · capture.py · frame_store.py · stream_loop.py · spot_check.py
│   ├── yolo/
│   │   ├── best100.pt                # Fine-tuned YOLO11n, 100 epochs
│   │   └── best30.pt                 # Earlier 30-epoch checkpoint
│   ├── migrations/versions/          # Alembic migrations
│   ├── scripts/                      # Seed/import/backfill/replay/report scripts
│   ├── tests/                        # pytest suite
│   ├── alembic.ini
│   ├── requirements.txt              # API + shared deps
│   ├── requirements.cv.txt           # Worker deps (Ultralytics, PyTorch, OpenCV)
│   ├── Dockerfile                    # API image
│   ├── Dockerfile.worker             # CV worker image
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/                      # Next.js App Router (layout.tsx, page.tsx, globals.css)
│   │   ├── components/
│   │   │   ├── Map/                  # MapView (MapLibre), legend, control deck, hour slider
│   │   │   ├── Panel/                # SidePanel, VideoFeed (MJPEG), segment/activity/bus-stop panels
│   │   │   ├── Dashboard/            # Shell, sidebar, header, global counter
│   │   │   ├── Analytics/            # Filters, charts, history table, export, bulk delete
│   │   │   ├── Chatbot/              # Bang Jo panel, composer, message, quick questions
│   │   │   ├── Pages/                # EmisiTren, Kendaraan, Riwayat, Pengaturan
│   │   │   └── ui/ · charts/
│   │   ├── context/ · hooks/ · services/api.ts · utils/ · constants/ · types.ts
│   ├── tests/                        # node --test unit tests
│   ├── package.json
│   ├── next.config.ts · tsconfig.json · postcss.config.mjs
│   └── .env.example
│
├── docs/                             # PRD summary, analytics spec, Bang Jo plans
├── docker-compose.yml                # postgres, redis, backend, beat, tracker, segment-worker, frontend
├── .env.example                      # Template — commit this
├── .env                              # Real secrets — NEVER commit
├── NOTES.md                          # DB reset, migrations, post-pull steps
└── README.md                         # ← this file
```

---

## 🚀 Quick Start (Development)

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ with PostGIS extension
- Docker + Docker Compose (recommended — handles DB, Redis, and workers)

### Option A — Docker (recommended for team)

```bash
git clone https://github.com/YOUR_USERNAME/ecotraffic-gis.git
cd ecotraffic-gis

# Global .env
cp .env.example .env            # fill in your values

# Backend .env
cd backend
cp .env.example .env            # fill in your values
cp .env.example .env.local      # fill in your values
cd ..

# Frontend .env
cd frontend
cp .env.example .env            # fill in your values
cp .env.example .env.local      # fill in your values
cd ..

docker compose up --build       # run from the repo root
```

Services started: `postgres`, `redis`, `backend`, `beat`, `tracker`, `segment-worker`, `frontend`.

- Backend API: http://localhost:8080
- Frontend: http://localhost:3000
- API docs: http://localhost:8080/docs

#### Configure the live tracking cameras

`tracker` runs YOLO11n + ByteTrack over the cameras listed in `TRACK_CAMS`
(default `atcs_jlagran,atcs_balaikota_timur`). Detection cadence and thresholds
are set in `backend/.env` (`TRACK_FPS`, `CONFIDENCE_THRESHOLD`, `YOLO_IMAGE_SIZE`,
`YOLO_MODEL_PATH`). `segment-worker` concurrency and queue are defined in
`docker-compose.yml`.

### Segment Pipeline

After migrations, seed cameras, road segments, and nearest-segment mappings with
`python -m app.core.seed`. Then import the spatial source layers and backfill
segments with `python -m scripts.import_pois`, `python -m scripts.import_population`,
`python -m scripts.import_survey_activities`, `python -m scripts.import_survey_ahp_scores`,
`python -m scripts.import_activity_grid --verify`, `python -m scripts.score_bus_stops`,
and `python -m scripts.backfill_spatial_context`. Generate the 24-hour synthetic
fallback dataset with `python -m scripts.generate_historical_segment_data`.

Segment endpoints are `GET /api/segments/geojson`, `GET /api/emissions/map`, and
`GET /api/emissions/{road_segment_id}`. Camera responses include `data_source`;
filter live or historical cameras with `GET /api/cameras?data_source=LIVE` or
`HISTORICAL`. The `/ws/emissions` socket forwards camera messages and
`segment_update` messages.

#### Precomputed REPLAY dataset (54 non-LIVE cameras)

The 54 non-LIVE cameras stay visible on the map with metadata but are **not**
sampled; they ship precomputed `REPLAY` facts. The real-data collection is done:
`app.workers.snapshot_worker` is **deprecated** (removed from
`celery_app.include`, `task_routes`, and `beat_schedule`) and the cameras are
labeled `data_source = REPLAY`.

Build or refresh the static hourly profile from the durable snapshot
(`snapshot_occupancy`, version 2) facts the non-LIVE cameras already produced:

```bash
docker compose exec backend python -m scripts.build_replay_dataset
docker compose exec backend python -m scripts.report_spatial_coverage
```

The builder is anchored to the latest collected hour, so the completed collection
stays addressable on any calendar day. Each segment with real samples gets one
`REPLAY` row per UTC hour. Gap hours are interpolated (linear between real hours;
forward/backward fill at the day edges) and flagged with
`calculation_metadata.is_interpolated`; segments with no real sample at all are
skipped, never fabricated. Only `SYNTHETIC` stays excluded from analytics and
exports — `REPLAY` is included and readable through the analytics and
activity-grid APIs. Segments without their own camera keep a clearly labeled
estimate borrowed from the nearest observed segment (`data_status = estimated`).

`scripts/generate_historical_segment_data.py` remains a **deprecated** dev seed
for an empty database.

### Seed the Data

```bash
# From the repo root
docker compose exec backend alembic upgrade head        # migrate data + add extension
docker compose exec backend python -m app.core.seed     # seed cameras + road segments + mappings (idempotent)

# Verify there is a single migration head; then apply it
docker compose exec backend alembic heads               # expect a single head
docker compose exec backend alembic upgrade head        # → 9d2c6f1a4b8e

# All seed/import scripts below are idempotent — safe to re-run on existing data
docker compose exec backend python -m app.core.seed
docker compose exec backend python -m scripts.import_pois
docker compose exec backend python -m scripts.import_population
docker compose exec backend python -m scripts.import_survey_activities
docker compose exec backend python -m scripts.import_survey_ahp_scores
docker compose exec backend python -m scripts.import_activity_grid --verify
docker compose exec backend python -m scripts.score_bus_stops
docker compose exec backend python -m scripts.backfill_spatial_context

# (RUN ONCE) Only if historical fallback is missing or stale — appends, NOT idempotent:
docker compose exec backend python -m scripts.generate_historical_segment_data

# Optional data scripts (only when the data layer needs them)
docker compose exec backend python -m scripts.seed_snapshot_schedule            # M4 snapshot sampler schedule
docker compose exec backend python -m scripts.build_replay_dataset              # REPLAY profile (needs snapshot facts)
docker compose exec backend python -m scripts.report_spatial_coverage           # coverage report (after build_replay_dataset)
docker compose exec backend python -m scripts.backfill_segment_name_embeddings  # Bang Jo RAG — needs OPENROUTER_API_KEY

# Restart docker
docker compose down
docker compose up -d --build
```

Notes:
- `import_survey_ahp_scores` matches rows by `source_id`, so it must run **after**
  `import_survey_activities`; rows it cannot match keep their keyword scores.
- If realtime segment state looks stale, clear Redis keys matching `emission:segment:*`.
- Re-running `generate_historical_segment_data.py` blindly duplicates rows; only run it on an empty
  segment emissions table (see `NOTES.md` for the truncate command).

### Option B — Manual Setup (Not Tested Yet)

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/ecotraffic-gis.git
cd ecotraffic-gis
```

**2. Set up backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your DB and config values
alembic upgrade head            # run DB migrations
uvicorn app.main:app --reload
```

**3. Start the CV tracker (separate terminal)**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.cv.txt
python -m app.workers.tracking_worker
```

**4. Set up frontend**
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000

---

## 🔌 API Reference

| Method & path | Purpose |
|---|---|
| `GET /health` | Health check used by Docker/monitoring |
| `GET /api/cameras` | Camera GeoJSON; filter with `?data_source=LIVE\|HISTORICAL` |
| `GET /api/cameras/{id}/tracked.mjpg` | Annotated MJPEG detection stream |
| `GET /api/emissions/map` | Emission values for the map layer |
| `GET /api/emissions/{road_segment_id}` | Latest per-camera/segment emission data |
| `GET /api/segments/geojson` | Road-segment GeoJSON layer |
| `GET /api/analytics/emissions/options` | Segment/corridor filter options |
| `GET /api/analytics/emissions/latest` | Current eight-pollutant segment rates |
| `GET /api/analytics/emissions/trend` | Database-bucketed rates |
| `GET /api/analytics/emissions/top-corridors` | Corridors ranked by a pollutant |
| `GET /api/analytics/emissions/composition` | Eight-pollutant distribution |
| `GET /api/analytics/emissions/history` | Paginated analytical facts |
| `GET /api/analytics/emissions/export?format=csv\|json` | Filtered facts export |
| `GET /api/analytics/emissions/historical-cameras` | Latest non-LIVE fact per camera |
| `GET /api/spatial/activity-grid` | H3 activity-potential scores |
| `GET /api/spatial/activity-grid/{hex_id}` | Hex detail (+ `.../hourly`) |
| `POST /api/chat` | Bang Jo assistant (grounded in system context) |
| `WS /ws/emissions` | Live `emission_update` / `segment_update` push |

Ranges are limited to 31 days, export to 100,000 facts, and history to 200 rows
per page. Invalid ranges return 4xx; database failures return 503. See
[docs/emission-analytics.md](docs/emission-analytics.md) for the full contract.

---

## 🧰 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Vehicle detection | Fine-tuned YOLO11n (Ultralytics) | Lightweight, accurate on the project's 4 vehicle classes |
| Tracking | ByteTrack (`bytetrack.yaml`) | Stable IDs for unique flow counting per ROI |
| CV runtime | Python 3.10 + OpenCV + PyTorch | Headless-friendly server inference |
| Backend API | FastAPI + Uvicorn | Async, Python-native ML integration |
| Real-time push | Native FastAPI WebSocket | Low-latency updates without extra transport libs |
| Task queue | Celery + Celery Beat + Redis | Windowed segment reconciliation off the request path |
| Database | PostgreSQL + PostGIS | Geospatial cameras/segments and versioned facts |
| ORM | SQLAlchemy + GeoAlchemy2 + Alembic | Geospatial models and migrations |
| Spatial indexing | H3 | Dynamic hex aggregation for the activity grid |
| Map | MapLibre GL + react-map-gl | Vector map rendering for camera/segment/hex layers |
| Video | Annotated MJPEG (`/tracked.mjpg`) | Detection overlay served straight from the tracker |
| Charts | Recharts | Time-series and composition visualizations |
| Frontend | Next.js 16 + React 19 + TypeScript | App Router and typed component UI |
| Styling | Tailwind CSS v4 | Design tokens and utility styling |
| Assistant | Groq / OpenRouter (OpenAI-compatible) | Bang Jo LLM answers + entity embeddings |

---

## ⚙️ Environment Variables

Use `backend/.env.example`, `frontend/.env.example`, and the root `.env.example`
as templates. Never commit `.env` files.

Key backend settings:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` / `DATABASE_URL_SYNC` | Async + sync PostgreSQL DSNs |
| `REDIS_URL` | Celery broker/backend and latest-state store |
| `YOLO_MODEL_PATH` | Active YOLO11n weights (default `.env.example` → `yolo/yolo11n.pt`) |
| `TRACK_CAMS` | LIVE cameras handled by the tracker |
| `TRACK_FPS`, `CONFIDENCE_THRESHOLD`, `YOLO_IMAGE_SIZE` | Detection cadence and thresholds |
| `SEGMENT_OBSERVATION_WINDOW_SECONDS` | Flow/segment reconciliation window (default 60s) |
| `SNAPSHOT_*` | Historical sampler cadence and batching |
| `GROQ_API_KEY`, `OPENROUTER_API_KEY` | Bang Jo LLM + embeddings |

Frontend (`frontend/.env.example`): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`,
`NEXT_PUBLIC_GEOMAPID_API_KEY`.

---

## 🧪 Testing

```bash
# Backend (from backend/)
pytest

# Frontend (from frontend/)
npm test        # node --test unit tests
npm run lint    # eslint
npm run build   # production build / type check
```

---

## 👥 Team & Collaboration

| No. | Name | Role in Team | Github Username |
|---:|---|---|---|
| 1 | Mohammad Radyt Fahrasya | Project Leader, Emission Analyst, Transport & Environmental Domain Expert |@fahrasyaa|
| 2 | Muhammad Hafiz Ardiansyah | Technical Lead, Frontend Engineer, Computer Vision/ML Engineer, AI/LLM Engineer |@hafizardd|
| 3 | Rayhan Firdaus Ardian | Backend Engineer, AI/LLM Engineer, DevOps/Infrastructure Engineer |@HappyRehund|
| 4 | Fahmi Shampoerna | UI/UX Designer, Frontend Engineer |@shampoerna|
| 5 | Reginald Maghfirot Rammadhani Guzherra | Emission Analyst, Transport & Environmental Domain Expert ||

### Branch Naming Convention

| Prefix | Use for |
|---|---|
| `feat/` | New features (e.g. `feat/emission-chart`) |
| `fix/` | Bug fixes |
| `ml/` | Model experiments and CV changes |
| `docs/` | Documentation updates |
| `chore/` | Setup, config, dependencies |

**Always open a Pull Request — no direct commits to `main`.**

Recommended flow:
1. Branch off `dev` for your work
2. Open PR → `dev` when done
3. `dev` → `main` only for stable, demo-ready releases

---

## 🗺️ Emission Model

Segment-level emissions use the proposal's **Tier-2 VKT model** in
`cv/proposal_emission_factors.py`:

```text
vehicles/hour   = interval count × 3600 / observed seconds
VKT km/hour     = vehicles/hour × segment length km
emission g/hour = VKT km/hour × Tier-2 factor g/km
emission kg/hour = emission g/hour / 1000
```

Eight pollutants are calculated per vehicle class (`car`, `motorcycle`, `bus`,
`truck`): **TSP, NOx, SO₂, HC, CO, CO₂, CH₄, N₂O**.

| Modeling rule | Value |
|---|---|
| `car` factor | Gasoline-car baseline (diesel not inferred from video) |
| Emission-control efficiency | `C = 0%` (no vehicle-specific control data) |
| Factors | Versioned and copied into each fact's calculation metadata |
| Road length | Required for VKT; stored on the road segment |
| Camera rule | 56 represented — 2 `LIVE`, 54 `HISTORICAL` / `REPLAY` |

The legacy snapshot calculator in `cv/emission_factors.py` remains for the live
per-camera view. Historical/REPLAY rows are always labeled by `source_mode`,
`observed_at`, and `processed_at`, and gap-filled hours carry
`is_interpolated` so an estimate is never presented as an observation.
