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

## Segment Pipeline Reset and Backfill

The seed command is idempotent and loads road geometry plus nearest camera mappings. After reseeding an empty database, generate historical fallback emissions with:

```bash
python scripts/generate_historical_segment_data.py
```

To clear only segment-derived data while retaining cameras, run this against PostgreSQL:

```sql
TRUNCATE segment_emissions, segment_traffic_observations, camera_road_segments, road_segments CASCADE;
```

Redis segment latest state uses keys matching `emission:segment:*`; remove those keys when testing a clean realtime state.

## How to Migrations After Modifying Tables
1. Change Model in `backend\app\models\*`
2. Generate Migrations
```bash
docker compose exec app alembic revision --autogenerate -m "migration message"
```

3. Apply Migrations
```bash
alembic upgrade head
```
