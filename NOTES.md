# Notes

## How to Restart Database or Clear Database

Everything runs in Docker — do not start a local venv/uvicorn while using these
commands, or `docker compose exec backend` will talk to a different process.

1. Remove container
```bash
docker compose down -v
```

2. Re-up postgres, redis, and backend (Terminal 1)
```bash
docker compose up -d postgres redis backend
```

3. Create extensions in postgres (Terminal 2)
```bash
docker compose exec postgres psql -U postgres -d ecotraffic -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

4. Run migrations (Terminal 2)
```bash
docker compose exec backend alembic upgrade head
```

5. Seed Camera (Terminal 2)
```bash
docker compose exec backend python -m app.core.seed
```

6. Import spatial source layers + backfill (idempotent — safe to re-run)
```bash
docker compose exec backend python -m scripts.import_pois
docker compose exec backend python -m scripts.import_population
docker compose exec backend python -m scripts.import_survey_activities
docker compose exec backend python -m scripts.import_survey_ahp_scores
docker compose exec backend python -m scripts.import_activity_grid --verify
docker compose exec backend python -m scripts.score_bus_stops
docker compose exec backend python -m scripts.backfill_spatial_context
```

`import_survey_ahp_scores` needs `survey_stop_observations` from
`import_survey_activities`, so keep it after that line.

7. Generate historical fallback (NOT idempotent — only on empty segment emissions)
```bash
docker compose exec backend python -m scripts.generate_historical_segment_data
```

8. Optional data scripts
```bash
docker compose exec backend python -m scripts.seed_snapshot_schedule             # M4 snapshot sampler schedule
docker compose exec backend python -m scripts.build_replay_dataset               # REPLAY profile (needs snapshot facts)
docker compose exec backend python -m scripts.report_spatial_coverage            # coverage report (after build_replay_dataset)
docker compose exec backend python -m scripts.backfill_segment_name_embeddings   # Bang Jo RAG — needs OPENROUTER_API_KEY
```

## Updating After a Git Pull

Pull brings new migrations, seed data, and scripts. On an existing database you
do NOT need to reset — just upgrade and re-run the idempotent seed/imports:

```bash
git pull origin <branch>        # e.g. dev
docker compose up -d postgres redis backend
docker compose exec backend alembic heads          # expect a single head
docker compose exec backend alembic upgrade head   # → 9d2c6f1a4b8e
docker compose exec backend python -m app.core.seed
docker compose exec backend python -m scripts.import_pois
docker compose exec backend python -m scripts.import_population
docker compose exec backend python -m scripts.import_survey_activities
docker compose exec backend python -m scripts.import_survey_ahp_scores
docker compose exec backend python -m scripts.import_activity_grid --verify
docker compose exec backend python -m scripts.score_bus_stops
docker compose exec backend python -m scripts.backfill_spatial_context
# only if historical fallback missing/stale (appends, not idempotent):
docker compose exec backend python -m scripts.generate_historical_segment_data
docker compose up --build
```

Migration `f7a2b9c4d1e8` (applied by `alembic upgrade head`) automatically
flips the LIVE source from `kotabaru_wardhani` to `atcs_balaikota_timur` and
remaps it to `SEG-0137` — no re-seed needed for that part. If realtime
segment state looks stale, clear Redis keys matching `emission:segment:*`.

## Segment Pipeline Reset and Backfill

The seed command is idempotent and loads road geometry plus nearest camera mappings. After reseeding an empty database, run the imports + backfill above (keep `import_survey_ahp_scores` after `import_survey_activities`), then generate historical fallback emissions with:

```bash
docker compose exec backend python -m scripts.generate_historical_segment_data
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
docker compose exec backend alembic upgrade head
```
