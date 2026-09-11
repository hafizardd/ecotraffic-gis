# Activities standardization pipeline

This package turns `backend/data/output/activities.csv` into traceable, validated
activity observations and deterministic RAG documents. It does not write embeddings,
calculate recommendation scores, or invent spatial relationships.

## Data flow

```text
data/output/activities.csv
  -> data/raw/activities_raw.csv                 immutable byte-for-byte copy
  -> data/cleaned/activities_cleaned.csv         factual normalization + entity resolution
  -> data/processed/activities_structured.*      Pydantic-validated observation records
  -> data/knowledge/activities_knowledge.jsonl   validated knowledge records
  -> data/knowledge/activities_documents.jsonl   citation-ready documents
  -> data/knowledge/activities_chunks.jsonl      semantic sections + filter metadata
  -> data/reports/*                              quality and manual-QA outputs
```

`created_at` is retained as upload/creation time. A time found in the description is
stored independently. If the description supplies a time but no date, `observed_time`
is populated while `observed_at` remains null. The optional
`--use-created-at-fallback` flag is explicit and labels that fallback with low confidence.

## Commands

Run these from `backend/`:

```bash
python -m data_pipeline.activities inspect
python -m data_pipeline.activities clean
python -m data_pipeline.activities extract --limit 10
python -m data_pipeline.activities validate
python -m data_pipeline.activities build-knowledge
python -m data_pipeline.activities build-rag
python -m data_pipeline.activities all
```

All source-processing commands accept `--input`, `--output`, `--model`,
`--batch-size`, `--limit`, `--force`, `--dry-run`, `--timeout`, and
`--max-retries`. A dry run makes no network calls and writes no files. For an explicit
deterministic-only build (for example, before credentials are configured), pass
`--no-llm`; this is never selected silently.

## OpenRouter

OpenRouter is the only semantic-extraction gateway. Defaults:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_SITE_URL=
OPENROUTER_APP_NAME=EcoTraffic GIS
```

The client first requests JSON Schema output, then falls back to JSON-object output
on an explicit provider/model unsupported-format response. It never changes model or
provider. Only HTTP 408, 429, 500, 502, 503 and transport timeouts are retried, with
bounded exponential backoff. HTTP 401, 402, and 403 fail immediately. Cache keys include
description, model, schema version, prompt version, and extraction version.

Every populated semantic field must be supported by an evidence entry whose key is the field's
exact dotted schema path. Before validation, unsupported LLM-only fields are reset to their schema
defaults and confidence entries without evidence are removed. This normalization never fabricates
evidence, does not modify issues (which carry their own required evidence), and runs before merging
with evidence-backed deterministic extraction.

## Database integration

`scripts/import_survey_activities.py` prefers the cleaned CSV and falls back to the
legacy source only when the cleaned layer is absent. Invalid-coordinate observations
remain in file outputs but cannot enter the existing PostGIS model because its geometry
column is non-null. The importer no longer labels `created_at` as `observed_at`.
