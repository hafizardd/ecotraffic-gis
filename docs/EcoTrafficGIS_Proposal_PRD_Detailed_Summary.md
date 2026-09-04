# EcoTraffic GIS — Detailed Proposal & PRD Summary

> **Project:** EcoTraffic GIS  
> **Team:** BANG JO  
> **Competition:** MAPID WebGIS Competition #2 — 2026, *Maps That Think! – Mass Transportation Edition*  
> **Project focus:** AI-powered WebGIS / Transport Emission Decision Support System for sustainable public-transport planning in Yogyakarta  
> **Source documents:** `Proposal_BANG JO_EcoTrafficGIS.pdf` and `BANGJO_PRD_EcotrafficGIS.pdf`

---

## 1. Executive Overview

EcoTraffic GIS is an AI-powered WebGIS designed as a **Transport Emission Decision Support System (TEDSS)** for Yogyakarta. The core idea is to combine traffic observations from CCTV, computer vision, transport and environmental spatial data, field survey results around public-transport stops, multi-criteria spatial analysis, and an LLM-based recommendation engine.

The system is intended to move the workflow from:

**raw CCTV / spatial data → vehicle detection → traffic volume → VKT → emissions → spatial analysis → AHP priority score → AI explanation & recommendation → policy-support output**

The final PRD positions the product as more than a visualization dashboard. It is intended to help stakeholders identify **which road segments/corridors should receive public-transport intervention, why they should be prioritized, and what type of intervention is appropriate**.

The PRD describes the system as integrating CCTV, transport/public-stop information, spatial layers, and Survey Activities. YOLOv8 is used for vehicle detection and classification, VKT and emission calculations are attached to road segments, AHP generates a Transport Emission Decision Score, and the AI Recommendation Engine turns analytical context into contextual recommendations using the **Avoid–Shift–Improve (ASI)** framework.

---

# 2. Problem Being Solved

## 2.1 Context

Yogyakarta is characterized by high mobility because it is both an education city and a major tourism destination. The proposal cites approximately **10.9 million tourists in 2024** and reports substantial increases in vehicle volume in tourism areas such as Malioboro during peak season.

The proposal identifies several related problems:

1. High vehicle activity contributes to urban transport emissions.
2. Public transport still faces limitations in infrastructure, route efficiency, fleet quality, and management.
3. Existing emission inventories tend to describe emission magnitude without directly turning that information into corridor-priority decisions.
4. Important supporting data are distributed across different sources:
   - road network,
   - bus stops,
   - activity/POI,
   - population,
   - CCTV,
   - field survey information,
   - and environmental information.
5. Decision makers therefore lack a single spatial platform that connects:
   - traffic conditions,
   - emissions,
   - public-transport accessibility/condition,
   - activity,
   - population,
   - and intervention priorities.

The PRD reframes the central problem as a **spatial, multi-criteria decision problem**. Because the problem differs from one road/corridor to another, a simple city-wide emission number is not enough.

---

# 3. Product Goal

The main goal is to create a WebGIS that:

- automatically inventories transport emissions using existing CCTV infrastructure;
- converts vehicle observations into traffic-volume and emission information;
- integrates traffic/emission information with spatial context;
- evaluates public-transport stop conditions using field surveys;
- identifies priority road segments/corridors through AHP;
- generates a Transport Emission Decision Score;
- explains why a corridor receives a particular priority;
- recommends appropriate transport interventions using Avoid–Shift–Improve;
- provides a dashboard and interactive map for decision makers;
- allows analytical outputs to be exported.

The intended impact is faster, more objective, transparent, and spatially targeted transport-policy planning.

---

# 4. Main Users / Personas

The PRD defines three primary personas.

## 4.1 Urban Transport Policy Maker

**Example:** Head of Urban Transport Planning at the Yogyakarta Transportation Agency.

Needs:

- identify priority corridors quickly;
- understand the reason behind a corridor's priority;
- compare corridors visually;
- obtain policy recommendations;
- export results for meetings, evaluation, and planning.

Typical questions:

- Which corridors need intervention first?
- Is the priority caused mainly by emissions, traffic volume, poor stop accessibility, activity intensity, or population?
- What transport intervention should be considered?

## 4.2 Transport & Environmental Analyst

**Example:** Transport/environment analyst at Bappeda or DLH.

Needs:

- integrate CCTV, roads, stops, POI, population, traffic volume, and emissions;
- analyze high-emission corridors;
- compare spatial layers;
- monitor recent traffic/emission data;
- explain analytical findings to non-technical stakeholders.

## 4.3 Urban Development Planner

**Example:** Junior planner at Bappeda.

Needs:

- identify areas that need low-emission transport intervention;
- connect transport priorities with activity and population;
- support cross-sector planning;
- export evidence for planning documents.

---

# 5. Solution Architecture at a Conceptual Level

The final product can be understood as seven major stages:

1. **Spatial & survey data preparation**
2. **CCTV data ingestion**
3. **Vehicle detection with YOLOv8**
4. **Traffic volume, VKT, and emission calculation**
5. **Spatial integration and AHP scoring**
6. **AI recommendation / explanation**
7. **WebGIS + dashboard + export**

Conceptually:

```text
Spatial Data + Survey Activities
          +
      CCTV Data
          |
          v
     Data Cleaning
          |
          v
   YOLOv8 Vehicle Detection
          |
          v
 Vehicle Volume by Interval
          |
          v
     VKT Calculation
          |
          v
   Emission Calculation
          |
          v
    PostGIS Integration
          |
          +--------------------+
          |                    |
          v                    v
 Activity Potential       AHP Analysis
      Map                     |
                               v
                    Transport Emission
                      Decision Score
                               |
                               v
                     AI Recommendation
                         Engine / LLM
                               |
                               v
                 ASI Recommendation +
                     Explanation
                               |
                               v
                    WebGIS / Dashboard
```

---

# 6. Data Sources

The proposal initially describes eight categories of spatial/supporting data:

| Dataset | Source | Main Purpose |
|---|---|---|
| Yogyakarta administrative boundary | GEO MAPID | Study-area boundary |
| Road network | GEO MAPID | Road/segment analysis unit |
| Bus-stop distribution | GEO MAPID / MAPID | Public-transport accessibility |
| Activity centers / POI | GEO MAPID / MAPID | Activity and trip-generation context |
| Population | GEO MAPID / BPS | Population context |
| CCTV locations | Yogyakarta Government | Traffic observation locations |
| CCTV video streams | Yogyakarta Government | Vehicle detection |
| NDVI | Sentinel-2 processing | Environmental/vegetation context in the proposal |

The final PRD keeps the core transport/spatial datasets but **removes NDVI from the decision criteria and analytical scoring**. The PRD explicitly notes that environmental condition is represented through **Survey Activities**, particularly the observed condition of public-transport stops and their surroundings.

---

# 7. CCTV Strategy — Major Final-PRD Adjustment

This is one of the most important changes between the proposal and the final implementation plan.

## Proposal concept

The proposal was written around CCTV/live-stream-based traffic observation and described the system as updating traffic/emission information periodically. The conceptual architecture therefore reads more like a broad CCTV-driven system.

## Final PRD implementation

The PRD explicitly limits online/live inference to **2 CCTV cameras out of 56**.

### Final allocation

- **56 CCTV points** are represented in the system.
- **2 cameras:** LIVE + online YOLO inference.
- **54 cameras:** HISTORICAL / PRECOMPUTED / REPLAY data.
- The 54 historical cameras are **not** processed through the same real-time inference pipeline.

The PRD explicitly requires that the system distinguish `LIVE` from `HISTORICAL` and never imply that historical data represent current conditions.

### Two live CCTV streams

1. `atcs/ATCS_jlagran.stream/playlist.m3u8`
2. `kotabaru/ANPR-Jl-Wardhani.stream/playlist.m3u8`

The PRD's camera list identifies the first as **SIMPANG JLAGRAN (PTZ)** and the second as **JL. WARDHANI (SELATAN-TIMUR SMPN 5)**.

### Live processing target

The two live cameras have:

- `inference_enabled = true`
- `data_source = LIVE`
- target processing interval: **10 seconds**
- asynchronous processing
- monitoring of processing latency / p95
- stale status when processing falls behind.

### Historical cameras

The other 54 cameras:

- are still displayed on the map;
- have camera metadata;
- may provide thumbnails/replay;
- use precomputed historical data;
- are processed/imported in batch;
- must display the observation period;
- must not be labeled as live;
- must show `HISTORICAL` or `REPLAY`.

The final PRD also requires that missing historical records be displayed as **"data tidak tersedia"**, rather than automatically converting missing values to zero.

---

# 8. Vehicle Classification — Major Proposal-to-PRD Adjustment

## Proposal

The proposal's emission-factor table distinguishes **five vehicle categories**:

1. Motorcycle / Motor
2. Gasoline car / Mobil Bensin
3. Diesel car / Mobil Solar
4. Bus
5. Truck

The proposal's Tier-2 emission-factor table provides separate emission factors for gasoline and diesel cars.

## Final PRD

The final PRD simplifies the vehicle classification used by the application to four operational classes:

1. **Motorcycle**
2. **Car**
3. **Bus**
4. **Truck**

The PRD explicitly requires YOLOv8 to detect and count these four classes.

### Important implementation decision

The final product **does not distinguish gasoline cars and diesel cars in the detected vehicle class**.

Instead:

> **Car is treated as one category in the application, and the emission calculation uses the gasoline-car emission factor for that car category.**

This is an implementation simplification and should be treated as a documented assumption in the system so users understand why a single `car` class is mapped to one emission-factor profile.

This distinction is important because the proposal's five-category emission table and the PRD's four-category detection model are not identical.

---

# 9. Emission Calculation

The proposal and PRD use the same basic analytical concept:

## 9.1 Vehicle Kilometres Travelled

For vehicle category `j` on road segment `i`:

**VKT = vehicle volume × road-segment length**

More specifically, the proposal defines:

- `Qji` = vehicle volume for category `j` on road segment `i`, in vehicles/hour;
- `li` = length of road segment `i`, in km;
- `VKTj,line` = Vehicle Kilometres Travelled.

## 9.2 Emission calculation

Emission is derived from:

**Emission = VKT × Emission Factor × correction factor**

The proposal assumes emission-control efficiency `C = 0%` because vehicle-specific emission-control effectiveness is unavailable and outside the scope.

Therefore the correction factor does not reduce the estimated emission.

## 9.3 Pollutants

The system stores/calculates eight pollutants:

1. TSP
2. NOx
3. SO₂
4. HC
5. CO
6. CO₂
7. CH₄
8. N₂O

The PRD requires emission-factor information to be **configurable and versioned**, so calculated results can be traced to the emission-factor version used.

---

# 10. NDVI Adjustment — Major Analytical Change

## Proposal

NDVI was an explicit component of the proposal.

It was:

- included as a spatial dataset;
- described as vegetation-density analysis;
- included as **K6** in the AHP;
- used alongside emissions, traffic, accessibility, activity, and population.

The proposal therefore had six AHP criteria:

1. Transport Emission
2. Vehicle Volume
3. Stop Accessibility
4. Activity Density
5. Population
6. Vegetation Density / NDVI

The proposal's AHP table assigned approximately:

| Criterion | Proposal Weight |
|---|---:|
| K1 Emission | 34% |
| K2 Vehicle Volume | 34% |
| K3 Stop Access | 17% |
| K4 Activity Density | 9% |
| K5 Population | 5% |
| K6 NDVI | 3% |

The proposal reported a **Consistency Ratio (CR) of 0.07**, below the stated 0.10 threshold.

## Final PRD

NDVI is **removed from the AHP decision criteria**.

The final PRD uses only five criteria:

1. **Transport Emission**
2. **Vehicle Volume**
3. **Stop/Halte Access**
4. **Activity Density**
5. **Population**

The final PRD explicitly states that NDVI is not used because environmental condition is represented through **Survey Activities**.

### Consequence

NDVI should not be treated as:

- an AHP criterion;
- a component of the final Transport Emission Decision Score;
- an evidence factor for the five-criterion priority calculation.

The environmental context instead comes from field observations around transport stops, especially:

- cleanliness;
- physical condition;
- comfort;
- surrounding environmental condition;
- pedestrian accessibility;
- facilities.

---

# 11. Final AHP Decision Model

The final PRD's priority model is:

| Criterion | Meaning |
|---|---|
| **K1 — Transport Emission** | Estimated emissions associated with a road segment |
| **K2 — Vehicle Volume** | Traffic volume detected from CCTV / historical data |
| **K3 — Halte Access** | Accessibility and quality of nearby public-transport stops |
| **K4 — Activity Density** | Intensity of activity represented by POI and related spatial indicators |
| **K5 — Population** | Population context around the road/corridor |

The AHP process consists of:

1. Pairwise comparison matrix.
2. Saaty scale.
3. Priority-weight calculation.
4. Consistency Index (CI).
5. Consistency Ratio (CR).
6. Normalized criterion scores for each road segment.
7. Final Transport Emission Decision Score.

The PRD requires the system to store the pairwise-comparison matrix and make the final score traceable back to the five criteria.

### Important documentation note

The final PRD acceptance criteria still contains the text:

> "Bobot 34/34/17/9/5/3 tersedia."

This appears to retain the **old six-criterion weight list** even though the same PRD explicitly states that the AHP now uses **five criteria**.

Therefore, for implementation, the intended conceptual model is clearly the **five-criterion model**, but the exact final five-criterion numerical weights should be explicitly revalidated/recomputed rather than blindly using `34/34/17/9/5/3`.

This is a PRD consistency issue worth resolving before production.

---

# 12. Survey Activities

Survey Activities are used to provide ground truth/context for public-transport conditions.

## Survey locations

The survey focuses on public-transport stops in Yogyakarta, especially stops associated with road segments that:

- have high vehicle volume;
- have high emissions;
- are connected to CCTV/road-network analysis;
- are relevant to priority corridors.

## Survey objects

The survey examines:

### Stop facilities

- shelter;
- seating;
- information board;
- supporting facilities;
- completeness and physical condition.

### Accessibility

- sidewalks;
- pedestrian access;
- crossing;
- access route to the stop.

### Environmental condition

- cleanliness;
- comfort;
- physical condition;
- surrounding environment.

### User activity

- number of users;
- observation time;
- activity conditions;
- photos;
- GPS coordinates.

## Role in analysis

Survey data are not merely documentation.

They contribute to the **composite stop-accessibility score**, which combines:

- proximity/buffer analysis;
- facility condition;
- pedestrian accessibility;
- environmental condition;
- user activity.

This produces a more meaningful K3 accessibility criterion than distance alone.

Survey evidence can also support AI recommendations, especially recommendations in the **Improve** category, such as improving stop facilities when traffic/emissions are high but public-transport infrastructure is weak.

---

# 13. Spatial Analysis

The final PRD uses several spatial-analysis operations.

## 13.1 Spatial Join

Connects:

- road segments;
- CCTV;
- stops;
- POI;
- population.

The goal is for each road segment to have a consolidated analytical attribute set.

## 13.2 VKT & Emission Overlay

Connects:

- detected traffic volume;
- road length;
- VKT;
- emission factors;
- emission estimates.

Output: emissions per road segment.

## 13.3 Hexagonal Grid Density Analysis

POI, population, and mobility indicators are aggregated into consistent hexagonal cells.

Output:

**Activity Potential Map**

The map highlights areas with high activity/trip-generation potential.

## 13.4 Buffer / Proximity Analysis

Calculates road-segment proximity/accessibility to nearby stops.

## 13.5 Composite Stop Accessibility Scoring

Combines proximity with Survey Activities so accessibility is not represented only by distance.

## 13.6 AHP-Based Multi-Criteria Scoring

The final PRD applies AHP to the five criteria:

- emission;
- vehicle volume;
- stop access;
- activity density;
- population.

Output:

**Transport Emission Decision Score**

---

# 14. Main Maps

## 14.1 Activity Potential Map

Uses hexagonal grids to show areas with high potential activity and mobility.

Inputs include:

- POI;
- population;
- mobility/traffic indicators.

Each hexagon has:

- Activity Potential Score;
- classification;
- underlying indicators;
- period/freshness information.

The map is contextual rather than an emission map.

## 14.2 Transport Emission Decision Map

Uses road segments as the primary visualization unit.

It shows:

- emission intensity;
- traffic-related information;
- decision score;
- priority level.

Road segments can be selected to inspect analytical details.

The PRD emphasizes traceability: map values should be connected to:

- `camera_id`;
- `data_source`;
- `observed_at`;
- `processed_at`;
- `model_version`.

---

# 15. AI Recommendation Engine

The AI layer is not intended to replace the analytical system.

Instead, it consumes analytical context produced by the system.

## Inputs

The AI can receive:

- corridor characteristics;
- emission information;
- vehicle volume;
- stop accessibility;
- activity context;
- population;
- AHP Decision Score;
- analytical evidence;
- Survey Activities evidence.

The final PRD emphasizes that the AI context should come from **actual system data**.

## AI responsibilities

The LLM should:

1. summarize the condition of a corridor;
2. identify the main factors contributing to its priority;
3. explain the Decision Score;
4. propose interventions;
5. classify recommendations using ASI;
6. provide evidence/reasons;
7. avoid inventing unavailable analytical values.

---

# 16. Avoid–Shift–Improve Framework

Recommendations are organized using:

### Avoid

Reduce the need for unnecessary/private vehicle travel.

Examples can include interventions that reduce dependency on private vehicle trips or improve land-use/transport interaction.

### Shift

Move trips from private vehicles to more sustainable modes.

Examples:

- public-transport strengthening;
- feeder services;
- improved access to public transport;
- better pedestrian connections.

### Improve

Improve the efficiency/quality of transport systems.

Examples:

- stop/facility improvement;
- pedestrian-access improvement;
- public-transport service improvement;
- other corridor-specific infrastructure/service interventions.

The PRD explicitly requires recommendations to be **corridor-specific**, not generic text.

---

# 17. Explainable AI

A key product principle is that the AI should answer:

> **Why was this corridor prioritized, and why was this intervention recommended?**

The system should expose evidence such as:

- high emissions;
- high traffic volume;
- poor stop access;
- high activity density;
- population;
- field-survey findings.

The evidence should be traceable back to analytical data.

The AI therefore acts as a **Spatial AI Assistant**, not merely a chatbot that generates generic transport-policy text.

---

# 18. AI Chatbot

The PRD includes a separate AI Chatbot interface.

The chatbot should answer questions about:

- current/recent traffic conditions;
- estimated emissions;
- traffic volume;
- road segments;
- corridor priority;
- AHP Decision Score;
- stop accessibility;
- factors affecting a corridor;
- AI recommendations;
- Avoid–Shift–Improve classification.

The chatbot must use actual system context.

Important safeguards:

- it must not invent unavailable values;
- its answers should be traceable to system data/analysis;
- AI failure must not crash the WebGIS;
- chatbot activity must not interfere with CCTV monitoring or core analysis.

---

# 19. Traffic & Emission Dashboard

The final dashboard should include:

## Monitoring status

- Live now: **2/56**
- Historical available: **54/56**
- Offline/stale count;
- last update time.

## Traffic

- total volume;
- volume by vehicle class;
- time trends;
- road/corridor filtering;
- highest-volume segments.

## Emission

- total estimated emissions;
- emissions by pollutant;
- emission trends;
- highest-emission segments.

## Decision support

- highest Decision Score corridors;
- corridor ranking;
- AHP summary;
- priority levels;
- recommended interventions.

## Data freshness

The dashboard must make it obvious whether a number comes from:

- LIVE;
- HISTORICAL;
- REPLAY.

This is critical to avoid users interpreting historical data as real-time information.

---

# 20. Product Features & Acceptance Requirements

## 20.1 CCTV & Vehicle Detection

The final PRD requires:

- exactly 56 camera points displayed;
- camera IDs;
- road/location names;
- coordinates;
- stream URL;
- source status;
- timestamps;
- LIVE/HISTORICAL labels;
- HLS playback where applicable;
- offline/stale handling;
- historical fallback with source/period label;
- exactly two cameras with online inference;
- 54 historical cameras not scheduled for online inference;
- bounding boxes;
- confidence scores;
- relevant vehicle-class counting;
- model not reloaded for every frame.

Final vehicle classes:

- motorcycle;
- car;
- truck;
- bus.

## 20.2 Traffic & Emission Analysis

The system must:

- aggregate counts by interval;
- aggregate by vehicle type;
- connect counts to road segments;
- support multi-camera aggregation;
- calculate VKT;
- use versioned/configurable emission factors;
- calculate eight pollutants;
- distinguish live and historical coverage.

The "Live now" summary must represent only the **2 live cameras**, not all 56.

## 20.3 Decision Map

Must:

- display emission values spatially;
- allow road-segment selection;
- allow pollutant selection;
- maintain consistent spatial references;
- show freshness;
- preserve traceability to source/model/timestamps.

## 20.4 AHP

Must:

- use five final criteria;
- store pairwise comparison matrix;
- calculate priority weights;
- use Saaty scale;
- calculate CI and CR;
- flag CR > 0.1;
- calculate normalized road-segment criterion scores;
- make the result traceable to the five criteria.

## 20.5 Activity Potential Map

Must:

- use consistent hexagons;
- aggregate POI;
- aggregate population;
- connect mobility indicators;
- normalize indicators;
- calculate Activity Potential Score;
- classify cells;
- show legend;
- show details when selected;
- provide freshness information.

## 20.6 AI Recommendation

Must:

- send actual analytical context to the LLM;
- receive corridor characteristics;
- receive Decision Score;
- identify score drivers;
- produce corridor-specific recommendations;
- return structured output;
- survive LLM failure without breaking the map/dashboard;
- allow recommendations to be saved.

## 20.7 Explainable ASI Recommendation

Must:

- classify recommendations as Avoid / Shift / Improve;
- explain the classification;
- show influential factors;
- use emission, volume, stop, activity, and population evidence;
- connect evidence to analytical data;
- avoid generic recommendations.

## 20.8 Export

Exports should preserve:

- source mode;
- observation period;
- processing timestamp;
- units;
- VKT/emission assumptions;
- model version;
- selected period;
- road segment/area.

The system should support exporting:

- vehicle volume;
- estimated emissions;
- Decision Score;
- road-segment analytical results.

## 20.9 Chatbot

The chatbot must:

- answer system-data questions;
- explain analytical results;
- explain priority;
- explain recommendations;
- use actual context;
- avoid hallucinating system values;
- remain operational independently from the core WebGIS.

---

# 21. Technology Stack

The PRD specifies the following stack.

## Frontend

- Next.js
- React 19
- GeoMapID Maps
- Recharts
- TailwindCSS
- HLS.js for CCTV playback

## Backend

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic
- WebSockets

## Computer Vision

- YOLOv8 / YOLOv8n
- Ultralytics
- OpenCV
- PyTorch
- torchvision

## Async Processing

- Celery
- Celery Beat
- Redis

## Database

- PostgreSQL
- PostGIS
- SQLAlchemy
- GeoAlchemy2
- Alembic

## AI

The PRD allows external LLM services such as:

- Google Gemini API;
- OpenRouter;
- GROQ.

The final architecture also describes an **AI Router** and RAG-style use of system data/context so that AI answers are grounded in the system's own analytical information.

## Deployment

- Rumahweb VPS L
- Ubuntu Server 24.04 LTS
- Docker
- Docker Compose
- Nginx / reverse proxy
- HTTPS / TLS
- PostgreSQL/PostGIS
- Redis

---

# 22. Final Deployment Configuration

The PRD's deployment baseline is:

- **2 vCPU**
- **4 GB RAM**
- **80 GB SSD**
- Ubuntu Server 24.04 LTS
- Docker Compose
- frontend + backend + worker + database + Redis + scheduler + reverse proxy.

The intended live workload is deliberately limited:

- YOLOv8n;
- only 2 live cameras;
- approximately 10-second sampling target;
- low worker concurrency.

The 54 historical camera datasets are precomputed and imported before the demo.

This architecture is primarily a **competition/demo-ready resource-constrained design**, rather than a claim that all 56 CCTV streams can be processed continuously in real time.

---

# 23. User Flow

The final user journey is:

1. Open EcoTraffic GIS.
2. See the dashboard and map.
3. Inspect CCTV/data-source status.
4. Review traffic and emission information.
5. Explore Activity Potential Map.
6. Explore Transport Emission Decision Map.
7. Select a road segment/corridor.
8. View:
   - emissions;
   - vehicle volume;
   - stop accessibility;
   - activity;
   - population.
9. View Transport Emission Decision Score.
10. Understand the priority level.
11. Request AI analysis/recommendation.
12. Review:
   - cause/factors;
   - evidence;
   - ASI recommendation;
   - explanation.
13. Export results for planning/decision support.

---

# 24. Development Timeline

The PRD defines an eight-week development plan:

| Week | Focus | Expected Output |
|---|---|---|
| M1 | Project Definition | Final problem, goals, users, indicators |
| M2 | Data Collection | Road, stop, CCTV, POI, population datasets |
| M3 | Survey & AI Planning | Stop survey + AI/CV design |
| M4 | Data Processing | Vehicle detection, volume, VKT, emissions |
| M5 | Development | Maps, layers, dashboard |
| M6 | AI Integration | Recommendation engine |
| M7 | Testing & Refinement | Validation and UI/system refinement |
| M8 | Deployment | Final system, documentation, demo |

---

# 25. Major Risks & Mitigations

## VPS / resource limitations

**Risk:** inference overload, latency, out-of-memory.

**Mitigation:**

- benchmark two cameras;
- start with concurrency 1;
- increase only if safe;
- monitor queue and p95;
- maintain utilization target around 80–85%;
- scale VPS if necessary.

## Accidental scheduling of all 56 cameras

**Risk:** historical cameras are processed as live.

**Mitigation:**

- explicitly mark live camera IDs;
- schedule only those two;
- test scheduler behavior.

## Queue backlog

**Risk:** live updates become delayed.

**Mitigation:**

- per-camera locks;
- task expiry;
- low prefetch;
- queue-length monitoring;
- p95 processing monitoring.

## Wrong YOLO model

**Risk:** RAM/latency changes or implementation diverges from PRD.

**Mitigation:**

- verify `yolov8n.pt`;
- record model version;
- checksum/path verification;
- post-deployment smoke tests.

## CCTV stream failure

**Risk:** missing detections/video.

**Mitigation:**

- retry;
- active/inactive status;
- stale/offline state;
- snapshot/historical fallback;
- clear source labeling.

## Detection accuracy degradation

Potential causes:

- night;
- rain/fog;
- occlusion;
- low-quality video;
- camera shake.

Mitigation:

- confidence threshold;
- manual sample validation;
- data-quality indicators.

## Historical data misunderstood as live

This is a particularly important product risk.

Mitigation:

- `LIVE`, `HISTORICAL`, `REPLAY` badges;
- observation period;
- `observed_at`;
- `processed_at`;
- source information;
- clear explanation that only 2/56 cameras are live.

---

# 26. Out-of-Scope Items

The final PRD explicitly excludes:

- direct traffic control;
- full-FPS real-time processing for all 56 cameras;
- 24/7 raw-video storage;
- representing historical data as current conditions;
- automatic road-geometry changes;
- operating public transport;
- installing new CCTV/sensors;
- training a foundation AI/LLM from scratch;
- long-term traffic prediction;
- automatic execution of AI recommendations;
- special government-system integrations requiring restricted access;
- vehicle-speed calculation;
- guaranteed 100% detection accuracy;
- 24/7 full-FPS processing of all cameras;
- replacing spatial analysis with real-time data alone;
- what-if simulation;
- native mobile application.

---

# 27. Proposal vs Final PRD — Detailed Change Log

This section should be treated as the **source of truth for implementation differences**.

| Area | Proposal | Final PRD | Implementation Meaning |
|---|---|---|---|
| Vehicle classes | 5: motorcycle, gasoline car, diesel car, bus, truck | 4: motorcycle, car, bus, truck | Gasoline/diesel distinction is removed from the application class model |
| Car emission factor | Separate gasoline and diesel factors in proposal table | One `car` category | **Car uses gasoline-car emission factor**, per final implementation decision |
| AHP criteria | 6 criteria including NDVI | 5 criteria | NDVI removed from final AHP |
| NDVI | Dataset + vegetation-density analysis + AHP K6 | Not used in final decision score | Environmental context is represented through Survey Activities |
| AHP weights | 34%, 34%, 17%, 9%, 5%, 3% for six criteria | Five-criterion model | Revalidate/recompute the final five-criterion weights; do not blindly retain six weights |
| CCTV | Broad CCTV/live-stream concept | 56 cameras, only 2 live | Explicit resource-aware architecture |
| Live inference | Conceptually broad | Exactly 2 cameras | Only two cameras use online YOLO inference |
| Other cameras | CCTV source | 54 historical/precomputed | Batch/replay, not real-time inference |
| Live update | Proposal describes hourly update | 2 live cameras target ~10-second processing | Live dashboard uses latest records from the two live cameras |
| Historical update | General periodic/near-real-time framing | Batch/precomputed with freshness labels | Historical data must never be presented as current |
| Missing data | Less explicit | Must show "data tidak tersedia" | Do not substitute zero for missing records |
| AI | LLM recommendation | LLM + actual analytical context + explainability + ASI | AI is grounded in system data and corridor characteristics |
| Survey | Field validation | Integrated into stop-accessibility scoring | Survey has direct analytical value, not just documentation |

---

# 28. The Three Most Important Final Decisions

## Decision 1 — Vehicle model

**Application-level vehicle taxonomy:**

```text
motorcycle
car
bus
truck
```

Do **not** create separate gasoline/diesel car classes in the YOLO output.

For emission calculation:

```text
car → gasoline-car emission factor
```

This should be documented as an explicit modeling assumption.

---

## Decision 2 — AHP model

The final decision model uses exactly five criteria:

```text
1. Transport Emission
2. Vehicle Volume
3. Halte Access
4. Activity Density
5. Population
```

NDVI is removed from the final AHP.

---

## Decision 3 — CCTV execution model

The production/demo system contains 56 CCTV points but only two are genuinely live:

```text
LIVE
├── ATCS Jlagran
└── ANPR Jl Wardhani

HISTORICAL / PRECOMPUTED
└── remaining 54 cameras
```

Only the two live cameras run the online inference pipeline.

The other 54 cameras are visualization/data-history sources and should be clearly labeled as such.

---

# 29. Practical Data Model Implications

The final PRD implies several important database fields.

## CCTV

```text
camera_id
name
longitude
latitude
stream_url
data_source
inference_enabled
active
observed_at
processed_at
```

`data_source` should distinguish:

```text
LIVE
HISTORICAL
REPLAY
```

## Vehicle detection

```text
camera_id
road_segment_id
vehicle_type
count
confidence
observed_at
processed_at
model_version
```

`vehicle_type`:

```text
motorcycle
car
bus
truck
```

## Emission

```text
road_segment_id
pollutant
vkt
emission_value
emission_factor_version
observed_at
processed_at
```

## AHP

```text
road_segment_id
emission_score
vehicle_volume_score
halte_access_score
activity_score
population_score
decision_score
priority_level
ahp_version
```

## AI recommendation

```text
road_segment_id
decision_score
asi_category
recommendation
reason
evidence
model/provider
created_at
```

---

# 30. Important Interpretation Rules for the Final Product

The following rules should be reflected in both code and UI:

1. **56 cameras does not mean 56 live cameras.**
2. **Only 2/56 cameras contribute to the live monitoring state.**
3. Historical data must always show its observation period.
4. Missing historical data is not equivalent to zero traffic.
5. `Car` is one detection class; gasoline/diesel is not inferred from the camera.
6. `Car` emission estimation uses the gasoline-car emission factor under the final modeling assumption.
7. NDVI is not an AHP criterion in the final system.
8. Survey Activities provide environmental/public-transport condition context.
9. AI recommendations must be based on analytical context from the system.
10. AI must not invent analytical values.
11. AHP results must be traceable to the five final criteria.
12. Exported results must preserve source/freshness/model assumptions.

---

# 31. Overall Product Narrative

The strongest way to understand EcoTraffic GIS is:

> **EcoTraffic GIS identifies where transport-related emissions and mobility pressure are high, checks whether public transport is capable of absorbing/replacing some of that demand, ranks corridors objectively, and explains what intervention should be considered.**

It combines three layers of intelligence:

### Layer 1 — Observation

**CCTV + YOLOv8**

"What is happening on the road?"

### Layer 2 — Spatial decision analysis

**VKT + emissions + stops + activity + population + AHP**

"Which corridors are most urgent, and why?"

### Layer 3 — Policy intelligence

**LLM + ASI + evidence**

"What should be done, and what evidence supports the recommendation?"

This is what makes the product a **decision-support system rather than only a traffic/emission dashboard**.

---

# 32. Final Source-of-Truth Summary

For implementation, the **PRD should supersede the proposal wherever they differ**.

The final implementation should therefore use:

- **4 vehicle classes**, not 5;
- **one Car class**, not gasoline/diesel car classes;
- **gasoline-car emission factor for Car**, as the stated final modeling assumption;
- **5 AHP criteria**, not 6;
- **no NDVI in the AHP / Decision Score**;
- **56 CCTV locations represented**;
- **2 live cameras**;
- **54 historical/precomputed cameras**;
- **10-second target processing for the two live cameras**;
- explicit LIVE/HISTORICAL/REPLAY labeling;
- Survey Activities as part of stop-accessibility/environmental context;
- VKT + 8-pollutant emission calculations;
- Transport Emission Decision Map;
- Activity Potential Map;
- AHP Decision Score;
- AI Recommendation Engine;
- ASI classification;
- explainable evidence;
- AI chatbot;
- export functionality;
- resource-conscious Docker/VPS deployment.

The proposal remains valuable as the **original conceptual and methodological foundation**, while the PRD is the more concrete **engineering and product specification** that narrows the scope for a realistic competition/demo implementation.
