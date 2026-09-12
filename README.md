# 🌿 EcoTraffic GIS

A real-time WebGIS platform that monitors vehicle-based carbon emissions across a city using live CCTV feeds and computer vision.

The segment pipeline adds PostGIS road segments, camera-to-segment mappings, Tier-2 emissions, AHP priority scoring, historical fallback data, Redis latest state, and live segment updates.

Built for the AI Innovation Competition — combining **YOLO vehicle detection**, **FastAPI**, **PostGIS**, and **Next.js + React + TypeScript + MapLibre** into a single freshness-aware dashboard targeting urban traffic corridors in Yogyakarta.

The current scalable scheduler, bounded inference pipeline, aggregation
semantics, configuration, and synthetic load-test results are documented in
[Scalable CCTV Processing Pipeline](docs/scalable-cctv-pipeline.md).

---

## 📸 What It Does

- Displays a live map with colored dots for each CCTV camera (green → amber → red by emission level)
- Streams live video from each camera in-browser via HLS.js
- Runs YOLOv8 to detect and classify vehicles (car, motorcycle, truck, bus)
- Calculates CO₂ emission estimates per camera in real time using IPCC/EMEP emission factors
- Shows city-wide total emission statistics with time-series charts
- Exports emission logs as CSV for offline analysis

---

## 🗂️ Project Structure

```
ecotraffic-gis/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── cameras.py        # CCTV location endpoints
│   │   │       ├── emissions.py      # Emission data endpoints
│   │   │       └── websocket.py      # Live push to frontend
│   │   ├── core/
│   │   │   ├── config.py             # App settings from .env
│   │   │   └── database.py           # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── camera.py             # CCTV location DB model (PostGIS geometry)
│   │   │   └── emission.py           # Emission log DB model
│   │   ├── schemas/
│   │   │   ├── camera.py             # Pydantic request/response schemas
│   │   │   └── emission.py
│   │   ├── services/                   # aggregation, analytics, spatial, CCTV
│   │   ├── workers/
│   │   │   ├── tracking_worker.py      # continuous live-camera tracking
│   │   │   └── segment_calculation_worker.py
│   │   └── main.py                   # FastAPI app entry point
│   ├── cv/
│   │   ├── detector.py               # YOLOv8 wrapper
│   │   └── emission_factors.py       # Vehicle type → g CO₂/min constants
│   ├── migrations/                   # Alembic migration files
│   │   └── versions/
│   ├── data/                         # spatial and replay source data
│   ├── yolo/                         # mounted YOLO model weights
│   ├── tests/
│   ├── alembic.ini
│   ├── requirements.txt              # ← this file
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/
│   │   │   │   ├── MapView.tsx         # Main MapLibre map
│   │   │   │   └── MapLegend.tsx       # Map legend and layers
│   │   │   ├── Panel/
│   │   │   │   ├── SidePanel.tsx       # Camera and segment details
│   │   │   │   ├── VideoFeed.tsx       # HLS.js player
│   │   │   │   └── EmissionStats.tsx   # Per-camera stats
│   │   │   └── Dashboard/
│   │   │       ├── GlobalCounter.tsx   # Total CO₂ across all cameras
│   │   │       └── EmissionChart.tsx   # Recharts time-series
│   │   ├── hooks/
│   │   │   ├── useEmissions.ts         # WebSocket connection
│   │   │   └── useCameras.ts           # Fetch camera list from API
│   │   ├── services/
│   │   │   └── api.ts                  # Fetch API client
│   │   └── app/                        # Next.js app shell and routes
│   ├── package.json
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml              # Postgres, Redis, API, workers, frontend
├── .env.example                    # optional root Compose template
├── .gitignore
└── README.md                       # ← this file
```

---

## 🚀 Quick Start (Development)

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ with PostGIS extension
- Docker + Docker Compose (recommended — handles DB and Redis automatically)

### Option A — Docker (recommended for team)
#### 1. Setup Docker and environment files

```bash
git clone https://github.com/YOUR_USERNAME/ecotraffic-gis.git
cd ecotraffic-gis

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit both files before starting. For local Docker networking, backend URLs must
use the Compose service names `postgres` and `redis`; browser-facing frontend
URLs must use `localhost`:

```env
# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/ecotraffic
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:password@postgres:5432/ecotraffic
REDIS_URL=redis://redis:6379/0
YOLO_MODEL_PATH=yolo/best100.pt

# frontend/.env
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WS_URL=ws://localhost:8080
```

Use `--env-file backend/.env` with Compose commands. The model files are
mounted from `backend/yolo/` into the backend and tracker containers.

### Segment Pipeline

After migrations, seed cameras, road segments, and nearest-segment mappings with `python -m app.core.seed`. Then import the spatial source layers and backfill segments with `python -m scripts.import_pois`, `python -m scripts.import_population`, `python -m scripts.import_survey_activities`, `python -m scripts.import_survey_ahp_scores`, `python -m scripts.import_activity_grid --verify`, `python -m scripts.score_bus_stops`, and `python -m scripts.backfill_spatial_context`. Generate the 24-hour synthetic fallback dataset with `python -m scripts.generate_historical_segment_data`.

Segment endpoints are `GET /api/segments/geojson`, `GET /api/emissions/map`, and `GET /api/emissions/{road_segment_id}`. Camera responses include `data_source`; filter live or historical cameras with `GET /api/cameras?data_source=LIVE` or `HISTORICAL`. The `/ws/emissions` socket forwards camera messages and `segment_update` messages.

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

#### 2. Seed the Data
```bash
# Open new terminal and go to root dir
docker compose exec backend alembic upgrade head        # migrate data + add extension
docker compose exec backend python -m app.core.seed     # seed cameras + road segments + mappings (idempotent)
# Verify there is a single migration head; then apply it
docker compose --env-file backend/.env run --rm backend alembic heads
docker compose --env-file backend/.env run --rm backend alembic upgrade head

# All seed/import scripts below are idempotent — safe to re-run on existing data
docker compose exec backend python -m app.core.seed
docker compose exec backend python -m scripts.import_pois
docker compose exec backend python -m scripts.import_population
docker compose exec backend python -m scripts.import_survey_activities
docker compose exec backend python -m scripts.import_survey_ahp_scores
docker compose exec backend python -m scripts.import_activity_grid --verify
docker compose exec backend python -m scripts.score_bus_stops
docker compose exec backend python -m scripts.backfill_spatial_context

# (RUN ONCE) Only if historical fallback is missing or stale — this appends and is NOT idempotent:
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
- If historical fallback is missing or stale, run the generator separately only
  after confirming the target segment table is empty or intentionally being backfilled.

Compose includes PostgreSQL and Redis healthchecks. Backend and worker services
wait for both dependencies to become healthy, and long-running services use
`restart: unless-stopped`.

#### 4. Configure the Worker
The current Compose workers are:

- `beat`: Celery scheduler
- `tracker`: continuous ByteTrack/YOLO worker for configured live cameras
- `segment-worker`: Celery worker for the `inference` queue

Adjust tracker settings such as `TRACK_CAMS`, `TRACK_FPS`, `YOLO_DEVICE`, and
`YOLO_IMAGE_SIZE` in `backend/.env`. Adjust segment-worker concurrency in the
`segment-worker` command in `docker-compose.yml`.

- Backend API: http://localhost:8080
- Frontend: http://localhost:3000
- API docs: http://localhost:8080/docs

### Option B — Manual Setup (Not Tested Yet)

Docker is the supported development path. If running manually, use the same
database and Redis settings from `backend/.env`; the worker entrypoints are
`python -m app.workers.tracking_worker`, Celery beat, and the `inference` queue
worker shown in `docker-compose.yml`.

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/ecotraffic-gis.git
cd ecotraffic-gis
```

**2. Set up backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in your DB and config values
alembic upgrade head            # run DB migrations
uvicorn app.main:app --reload
```

**3. Start the workers (separate terminals)**
```bash
cd backend
source venv/bin/activate
python -m app.workers.tracking_worker
celery -A app.workers.celery_app worker -Q inference --loglevel=info --concurrency=1
celery -A app.workers.celery_app beat --loglevel=info
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

## 🧰 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Vehicle detection | YOLOv8 (Ultralytics) | Best accuracy/speed tradeoff, pre-trained on vehicles |
| CV runtime | Python 3.10 + OpenCV | Standard, headless-friendly for server deployment |
| Backend API | FastAPI | Async, fast, Python-native for ML integration |
| Real-time push | WebSocket (FastAPI native) | Low-latency updates to browser |
| Task queue | Celery + Redis | Background stream processing without blocking API |
| Database | PostgreSQL + PostGIS | Native geospatial queries for CCTV coordinates |
| ORM | SQLAlchemy + GeoAlchemy2 | Geospatial model support |
| Map library | MapLibre + react-map-gl | Vector map rendering and interactive segment/camera layers |
| Video streaming | HLS.js | Plays `.m3u8` CCTV streams natively in browser |
| Charts | Recharts | React-native, clean time-series visualizations |
| Frontend framework | Next.js + React + TypeScript | Application routing and typed component-based UI |
| Styling | Global CSS and component styles | Dashboard visual system |

---

## ⚙️ Environment Variables

For Docker, keep runtime configuration in `backend/.env` and browser-facing
configuration in `frontend/.env`. Never commit either file.

Backend database URLs use Docker service names:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/ecotraffic
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:password@postgres:5432/ecotraffic
REDIS_URL=redis://redis:6379/0
```

Frontend `NEXT_PUBLIC_*` values are read by the browser, so local development
uses `localhost:8080`; a deployed frontend must use the public API hostname.

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

## 🗺️ Emission Model (Example)

Vehicle CO₂ factors used (derived from IPCC/EMEP emission factor databases):

| Vehicle class | Emission factor |
|---|---|
| Motorcycle | ~40 g CO₂/min |
| Car (gasoline) | ~120 g CO₂/min |
| Bus / large truck | ~300–400 g CO₂/min |

Total emission per camera per minute = Σ (vehicle count × factor). These are static baseline factors; speed estimation would refine them further.
