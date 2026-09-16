# Import CSV history into Replay

This workflow uses the checked-in `backend/data/history/emission-history.csv`.
It does not require collecting camera snapshots or running the snapshot Replay
builder. The importer reuses existing interpolation helpers from that builder;
no changes to the builder or collector are required.

## VPS deployment

First merge the CSV importer commits into the branch deployed by the VPS (`main`).
Then, from the repository on the VPS:

```bash
cd ~/apps/ecotraffic-gis
git status --short --branch
git switch main
git pull --ff-only origin main
```

If there are local modifications, preserve/review them before switching or pulling.
Create a database backup before replacing the existing derived Replay profile:

```bash
mkdir -p backups
chmod 700 backups
backup_file="backups/before-csv-$(date +%Y%m%d-%H%M%S).dump"
(umask 077; ./tools/production-compose exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_file")
test -s "$backup_file"
```

Build the backend image to include the importer. Running services do not need to
be stopped or recreated for this database-only operation:

```bash
./tools/production-compose build backend
./tools/production-compose run --rm --no-deps --entrypoint python backend \
  -m scripts.import_emission_history --dry-run
```

Expected for the checked-in file: `source_rows: 9173`, `segments: 44`,
`replay_rows: 1056`, `interpolated_hours: 196`. Only proceed after the dry run
succeeds. Import and build the profile in one transaction:

```bash
./tools/production-compose run --rm --no-deps --entrypoint python backend \
  -m scripts.import_emission_history
```

Success ends with `Committed CSV import and Replay profile.` Verify:

```bash
./tools/production-compose exec -T postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT ahp_metadata->>'source_mode' AS source, count(*)
FROM segment_emissions
WHERE ahp_metadata->>'source_mode' IN ('CSV_HISTORY', 'REPLAY')
GROUP BY 1;
SQL
```

Expect 9,173 CSV_HISTORY rows and 1,056 REPLAY rows on the first import of this
file (with no other CSV imports). Refresh the browser, select Halte & Potensi →
Replay and compare 03:00 and 07:00 WIB. Historical responses may be cached for
30 seconds. No frontend rebuild, migration or Nginx change is needed.

## Data semantics

The importer stores source facts as CSV_HISTORY, version 5, preserving the
original source mode/version and file SHA-256 in metadata. It upserts the same
segment/time/version keys on repeat runs. It atomically replaces all derived
REPLAY rows while preserving existing live and snapshot facts. A failed import
rolls back both source upserts and profile replacement.

The profile comprises 24 UTC hour buckets ending in the latest CSV hour. Each
included segment must have two or more observed hours. Interior gaps use linear
interpolation; leading/trailing gaps use the nearest observation. Filled hours
are marked in metadata. Raw counts are absent from the export and not invented.

This file covers 44 segments, with 18–21 observed hours each. SEG-0027 and
SEG-0100 have no CSV samples; no random values are generated for them. This is a
repeating historical daily profile, not newly collected live observations.
Do not run `build_replay_dataset` afterwards: that is a separate snapshot-source
workflow and can overwrite this profile.

For another file inside the container, pass `--file /app/data/history/file.csv`.
