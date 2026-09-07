# Notes

## How to Restart Database or Clear Database

1. Remove container
```bash
    docker compose down -v
```

2. Re-up postgresql container (Terminal 1)
```bash
    docker compose up postgres redis
```

3. Go to backend directory (Terminal 2)
```bash
    cd backend
```

4. Activate virtual environments (Terminal 2)
```bash
    source .venv/scripts/activate
```

5. Run backend (Terminal 2)
```bash
    uvicorn app.main:app --reload --port 8000
```

6. Create extensions in postgres (Terminal 3)
```bash
docker compose exec postgres psql -U postgres -d ecotraffic -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

7. Run migrations (Terminal 3)
```bash
cd backend
alembic upgrade head
```

8. Seed Camera (Terminal 3)
```bash
python -m app.core.seed
```

9. Import spatial source layers + backfill (idempotent — safe to re-run)
```bash
python scripts/import_pois.py
python scripts/import_population.py
python scripts/import_survey_activities.py
python scripts/backfill_spatial_context.py
```

10. Generate historical fallback (NOT idempotent — only on empty segment emissions)
```bash
python scripts/generate_historical_segment_data.py
```

## Updating After a Git Pull

Pull brings new migrations, seed data, and scripts. On an existing database you
do NOT need to reset — just upgrade and re-run the idempotent seed/imports:

```bash
git pull origin <branch>        # e.g. dev
docker compose up -d postgres redis
docker compose exec backend alembic heads          # expect a single head
docker compose exec backend alembic upgrade head   # → 9d2c6f1a4b8e
docker compose exec backend python -m app.core.seed
docker compose exec backend python scripts/import_pois.py
docker compose exec backend python scripts/import_population.py
docker compose exec backend python scripts/import_survey_activities.py
docker compose exec backend python scripts/backfill_spatial_context.py
# only if historical fallback missing/stale (appends, not idempotent):
docker compose exec backend python scripts/generate_historical_segment_data.py
docker compose up --build
```

Migration `f7a2b9c4d1e8` (applied by `alembic upgrade head`) automatically
flips the LIVE source from `kotabaru_wardhani` to `atcs_balaikota_timur` and
remaps it to `SEG-0137` — no re-seed needed for that part. If realtime
segment state looks stale, clear Redis keys matching `emission:segment:*`.

## Segment Pipeline Reset and Backfill

The seed command is idempotent and loads road geometry plus nearest camera mappings. After reseeding an empty database, run the imports + backfill above, then generate historical fallback emissions with:

```bash
python scripts/generate_historical_segment_data.py
```

To clear only segment-derived data while retaining cameras, run this against PostgreSQL:

```sql
TRUNCATE segment_emissions, segment_traffic_observations, camera_road_segments, road_segments,
       survey_stop_observations, points_of_interest, population_zones CASCADE;
```

Redis segment latest state uses keys matching `emission:segment:*`; remove those keys when testing a clean realtime state.

## How to Migrations After Modifying Tables
1. Change Model in `backend\app\models\*`
2. Generate Migrations
```bash
docker compose exec backend alembic revision --autogenerate -m "migration message"
```

3. Apply Migrations
```bash
alembic upgrade head
```
