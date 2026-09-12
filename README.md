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
│   │   ├── services/
│   │   │   ├── emission_calculator.py  # CO₂ math logic
│   │   │   └── stream_reader.py        # HLS frame fetcher
│   │   ├── workers/
│   │   │   └── inference_worker.py   # Celery tasks: fetch → YOLO → store
│   │   └── main.py                   # FastAPI app entry point
│   ├── cv/
│   │   ├── detector.py               # YOLOv8 wrapper
│   │   └── emission_factors.py       # Vehicle type → g CO₂/min constants
│   ├── migrations/                   # Alembic migration files
│   │   └── versions/
│   ├── tests/
│   │   ├── test_emission_calculator.py
│   │   └── test_detector.py
│   ├── alembic.ini
│   ├── requirements.txt              # ← this file
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/
│   │   │   │   ├── MapView.jsx         # Main Leaflet map
│   │   │   │   └── CameraMarker.jsx    # Color-coded dot per CCTV
│   │   │   ├── Panel/
│   │   │   │   ├── SidePanel.jsx       # Opens on marker click
│   │   │   │   ├── VideoFeed.jsx       # HLS.js player
│   │   │   │   └── EmissionStats.jsx   # Per-camera stats
│   │   │   └── Dashboard/
│   │   │       ├── GlobalCounter.jsx   # Total CO₂ across all cameras
│   │   │       └── EmissionChart.jsx   # Recharts time-series
│   │   ├── hooks/
│   │   │   ├── useSocket.js            # Socket.IO connection
│   │   │   └── useCameras.js           # Fetch camera list from API
│   │   ├── services/
│   │   │   └── api.js                  # Axios base config
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml              # Runs Postgres, Redis, backend, frontend
├── .env.example                    # Template — commit this
├── .env                            # Real secrets — NEVER commit
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
#### 1. Setup the Docker

```bash
git clone https://github.com/YOUR_USERNAME/ecotraffic-gis.git
cd ecotraffic-gis

# Global .env
cp .env.example .env       # fill in your values

# Backend .env
cd backend                  # go to backend dir
cp .env.example .env        # fill in your values
cp .env.example .env.local  # fill in your values
cd ..                       # back to root dir

# Frontend .env
cd frontend                 # go to frontend dir
cp .env.example .env        # fill in your values
cp .env.example .env.local  # fill in your values
cd ..                       # back to root dir

docker compose up --build   # make sure it's in root directory
```

### Segment Pipeline

After migrations, seed cameras, road segments, and nearest-segment mappings with `python -m app.core.seed`. Then import the spatial source layers and backfill segments with `python scripts/import_pois.py`, `python scripts/import_population.py`, `python scripts/import_survey_activities.py`, `python scripts/import_activity_grid.py --verify`, `python scripts/score_bus_stops.py`, and `python scripts/backfill_spatial_context.py`. Generate the 24-hour synthetic fallback dataset with `python scripts/generate_historical_segment_data.py`.

Segment endpoints are `GET /api/segments/geojson`, `GET /api/emissions/map`, and `GET /api/emissions/{road_segment_id}`. Camera responses include `data_source`; filter live or historical cameras with `GET /api/cameras?data_source=LIVE` or `HISTORICAL`. The `/ws/emissions` socket forwards camera messages and `segment_update` messages.

#### Precomputed REPLAY dataset (54 non-LIVE cameras)

The 54 non-LIVE cameras stay visible on the map with metadata but are **not**
sampled; they ship precomputed `REPLAY` facts. The real-data collection is done:
`app.workers.snapshot_worker` is **deprecated** (removed from
`celery_app.include`, `task_routes`, and `beat_schedule`) and the cameras are
labeled `data_source = REPLAY`.

Build or refresh the hourly dataset from the accumulated `SNAPSHOT_REAL` facts:

```bash
docker compose exec backend python -m scripts.build_replay_dataset --only-missing
docker compose exec backend python -m scripts.report_spatial_coverage
```

Each segment with real samples gets one `REPLAY` row per UTC hour. Gap hours are
interpolated (linear between real hours; forward/backward fill at the day edges)
and flagged with `calculation_metadata.is_interpolated`; segments with no real
sample at all are skipped, never fabricated. Only `SYNTHETIC` stays excluded
from analytics and exports — `REPLAY` is included and readable through the
analytics and activity-grid APIs.

`scripts/generate_historical_segment_data.py` remains a **deprecated** dev seed
for an empty database.

#### 2. Seed the Data
```bash
# Open new terminal and go to root dir
docker compose exec backend alembic upgrade head        # migrate data + add extension
docker compose exec backend python -m app.core.seed     # seed cameras + road segments + mappings (idempotent)

# Import spatial source layers (idempotent — safe to re-run)
docker compose exec backend python -m scripts.import_pois                # points_of_interest  (data/poi.geojson)
docker compose exec backend python -m scripts.import_population          # population_zones     (data/populations.geojson)
docker compose exec backend python -m scripts.import_survey_activities   # survey_stop_observations (data/output/activities.csv)
docker compose exec backend python -m scripts.import_activity_grid --verify  # activity_grid_hexes (data/activity_grid.geojson)
docker compose exec backend python -m scripts.score_bus_stops            # bus stop accessibility + intervention class
docker compose exec backend python -m scripts.backfill_spatial_context   # segment spatial_metadata + population

# Generate 24h synthetic historical fallback (NOT idempotent — skip if data already exists)
docker compose exec backend python -m scripts.generate_historical_segment_data

# Restart docker
Ctrl + C
docker compose up
```

#### 3. Update an Existing Checkout (git pull)

When pulling new code that added migrations, seed data, or scripts, bring a
database that already has cameras/segments up to date without resetting it:

```bash
git pull origin <branch>                       # e.g. dev
docker compose up -d postgres redis

# Verify there is a single migration head; then apply it
docker compose exec backend alembic heads      # expect a single head
docker compose exec backend alembic upgrade head   # → 9d2c6f1a4b8e (adds survey/poi/population layers;
                                                  #   also flips LIVE to atcs_balaikota_timur / SEG-0137)

# All seed/import scripts below are idempotent — safe to re-run on existing data
docker compose exec backend python -m app.core.seed
docker compose exec backend python scripts/import_pois.py
docker compose exec backend python scripts/import_population.py
docker compose exec backend python scripts/import_survey_activities.py
docker compose exec backend python scripts/import_activity_grid.py --verify
docker compose exec backend python scripts/score_bus_stops.py
docker compose exec backend python scripts/backfill_spatial_context.py

# Only if historical fallback is missing or stale — this appends and is NOT idempotent:
docker compose exec backend python scripts/generate_historical_segment_data.py

docker compose up --build
```

Notes:
- If realtime segment state looks stale, clear Redis keys matching `emission:segment:*`.
- Re-running `generate_historical_segment_data.py` blindly duplicates rows; only run it on an empty
  segment emissions table (see `NOTES.md` for the truncate command).

#### 4. Configure the Worker
1. Open `docker-compose.yml` in root dir
2. See for this line of code
`celery -A app.workers.inference_worker worker --loglevel=info --pool=threads --concurrency=16`
3. Change the concurrency (can 2, 4, 8, etc)

- Backend API: http://localhost:8080
- Frontend: http://localhost:3000
- API docs: http://localhost:8080/docs

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
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in your DB and config values
alembic upgrade head            # run DB migrations
uvicorn app.main:app --reload
```

**3. Start the Celery worker (separate terminal)**
```bash
cd backend
source venv/bin/activate
celery -A app.workers.inference_worker worker --loglevel=info
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

Copy `.env.example` to `.env` and `.env.local` if any and fill in your values. Never commit `.env`.

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
