# 🌿 EcoTraffic GIS

A real-time WebGIS platform that monitors vehicle-based carbon emissions across a city using live CCTV feeds and computer vision.

Built for the AI Innovation Competition — combining **YOLOv8 vehicle detection**, **FastAPI**, **PostGIS**, and **React + Leaflet.js** into a single live dashboard targeting urban traffic corridors in Yogyakarta.

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

```bash
git clone https://github.com/YOUR_USERNAME/ecotraffic-gis.git
cd ecotraffic-gis
cp .env.example .env       # fill in your values
docker compose up --build
```

- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### Option B — Manual Setup

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
cp .env.example .env.local     # set VITE_API_URL etc.
npm run dev
```

Open http://localhost:5173

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
| Map library | Leaflet.js + React-Leaflet | Lightweight, free tile layers (OpenStreetMap) |
| Video streaming | HLS.js | Plays `.m3u8` CCTV streams natively in browser |
| Charts | Recharts | React-native, clean time-series visualizations |
| Frontend framework | React 18 + Vite | Fast dev server, component-based |
| Styling | Tailwind CSS | Utility-first, rapid UI building |

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env`.

```
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/ecotraffic

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# App
SECRET_KEY=changeme
DEBUG=true

# YOLO
YOLO_MODEL_PATH=yolov8n.pt
CONFIDENCE_THRESHOLD=0.4
```

---

## 👥 Team & Collaboration

| Role | Responsible for |
|---|---|
| ML / CV Engineer | `backend/cv/` — YOLOv8 pipeline, emission factor model |
| Backend Engineer | `backend/app/` — API routes, WebSocket, DB models |
| Frontend Engineer | `frontend/` — Map, UI components, charts |

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