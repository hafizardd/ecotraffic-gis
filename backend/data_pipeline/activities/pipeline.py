from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from pydantic import ValidationError

from .constants import (
    DEFAULT_DATA_DIR,
    DEFAULT_INPUT,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    EXTRACTION_PROVIDER,
    EXTRACTION_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SOURCE_FILE_NAME,
    SOURCE_TYPE,
)
from .llm import LLMMetrics, LLMError, OpenRouterLLMClient, SYSTEM_PROMPT, user_prompt_for
from .schemas import RagChunk, RagDocument, SemanticExtraction, SurveyKnowledgeRecord
from .transforms import (
    deterministic_semantic,
    extract_observation_time,
    mark_duplicates,
    merge_semantic,
    normalize_title,
    normalize_whitespace,
    parse_coordinates,
    parse_created_at,
    parse_media,
    resolve_stop_entities,
    semantic_validation_warnings,
    stable_id,
)


CLEANED_FIELDS = [
    "source_file", "source_row", "source_activity_id", "observation_id",
    "title_raw", "title_normalized", "description_raw", "description_normalized",
    "geometry_coordinates_raw", "longitude", "latitude", "coordinates_valid", "coordinate_error",
    "created_at_raw", "created_at_utc", "created_at_local",
    "observed_date", "observed_time", "observed_at", "observed_time_source",
    "observed_time_confidence", "day_of_week", "time_period",
    "medias_raw", "image_urls", "video_urls", "image_count", "video_count", "media_valid", "media_error",
    "stop_id", "stop_name", "stop_name_raw", "stop_name_normalized",
    "entity_resolution_confidence", "entity_resolution_status",
    "description_hash", "duplicate_group_id", "duplicate_status",
    "total_comment", "likes", "user_name", "user_full_name", "user_profile_picture",
    "community_name", "community_picture", "community_description",
]

STRUCTURED_CSV_FIELDS = [
    "knowledge_id", "source_type", "source_activity_id", "observation_id", "stop_id", "stop_name",
    "latitude", "longitude", "coordinates_valid", "observed_at", "observed_time", "time_period",
    "duplicate_group_id", "duplicate_status", "usage", "facilities", "accessibility", "condition",
    "environment", "issues", "strengths", "weaknesses", "recommendation_tags", "evidence", "confidence",
    "description_normalized", "provenance",
]


@dataclass
class PipelineOptions:
    input_path: Path = DEFAULT_INPUT
    output_dir: Path = DEFAULT_DATA_DIR
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: str = DEFAULT_OPENROUTER_BASE_URL
    batch_size: int = 10
    limit: int | None = None
    force: bool = False
    dry_run: bool = False
    use_llm: bool = True
    timeout: float = 60.0
    max_retries: int = 3
    use_created_at_fallback: bool = False

    def __post_init__(self) -> None:
        self.input_path = Path(self.input_path).resolve()
        self.output_dir = Path(self.output_dir).resolve()
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be at least 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


@dataclass
class PipelineResult:
    inspection: dict[str, Any]
    cleaned_rows: list[dict[str, Any]] = field(default_factory=list)
    records: list[SurveyKnowledgeRecord] = field(default_factory=list)
    documents: list[RagDocument] = field(default_factory=list)
    chunks: list[RagChunk] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    quality_report: dict[str, Any] = field(default_factory=dict)
    written_files: list[Path] = field(default_factory=list)


def _json_default(value: object) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[union-attr]
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _json_dumps(value: object, *, indent: int | None = None) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=indent is None, indent=indent, default=_json_default)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _csv_text(rows: Iterable[dict[str, Any]], fields: list[str]) -> str:
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for source in rows:
        row: dict[str, Any] = {}
        for key in fields:
            value = source.get(key)
            if isinstance(value, (dict, list)):
                value = _json_dumps(value)
            elif hasattr(value, "isoformat"):
                value = value.isoformat()
            elif value is None:
                value = ""
            row[key] = value
        writer.writerow(row)
    return output.getvalue()


class ActivitiesPipeline:
    def __init__(
        self,
        options: PipelineOptions | None = None,
        *,
        llm_client: OpenRouterLLMClient | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        self.options = options or PipelineOptions()
        self.environ = environ if environ is not None else os.environ
        self._llm_client = llm_client
        self.metrics = LLMMetrics(model=self.options.model)
        self._processed_at = datetime.now(timezone.utc)

    @property
    def paths(self) -> dict[str, Path]:
        root = self.options.output_dir
        return {
            "raw": root / "raw" / "activities_raw.csv",
            "cleaned": root / "cleaned" / "activities_cleaned.csv",
            "structured_csv": root / "processed" / "activities_structured.csv",
            "structured_jsonl": root / "processed" / "activities_structured.jsonl",
            "errors": root / "processed" / "extraction_errors.jsonl",
            "cache": root / "processed" / ".activities_extraction_cache.json",
            "knowledge": root / "knowledge" / "activities_knowledge.jsonl",
            "documents": root / "knowledge" / "activities_documents.jsonl",
            "chunks": root / "knowledge" / "activities_chunks.jsonl",
            "quality_json": root / "reports" / "activities_quality_report.json",
            "quality_csv": root / "reports" / "activities_quality_report.csv",
            "manual_qa": root / "reports" / "activities_manual_qa.jsonl",
        }

    def read_source(self) -> list[dict[str, str]]:
        if not self.options.input_path.exists():
            raise FileNotFoundError(f"activities CSV not found: {self.options.input_path}")
        with self.options.input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if self.options.limit is not None:
            rows = rows[: self.options.limit]
        return rows

    def inspect(self, rows: list[dict[str, str]] | None = None) -> dict[str, Any]:
        rows = rows if rows is not None else self.read_source()
        columns = list(rows[0]) if rows else []
        exact_keys = [tuple(row.get(column, "") for column in columns) for row in rows]
        ids = [(row.get("id") or "").strip() for row in rows]
        descriptions = [normalize_whitespace(row.get("description")).casefold() for row in rows]
        coordinate_validity = [parse_coordinates(row.get("geometry.coordinates"))[2] for row in rows]
        timestamp_validity = [parse_created_at(row.get("created_at"))[0] is not None for row in rows]
        media = [parse_media(row.get("medias")) for row in rows]
        time_mentions = [extract_observation_time(row.get("description"))["observed_time"] is not None for row in rows]

        def duplicate_excess(values: list[object], *, ignore_empty: bool = False) -> int:
            counts: dict[object, int] = {}
            for value in values:
                if ignore_empty and not value:
                    continue
                counts[value] = counts.get(value, 0) + 1
            return sum(count - 1 for count in counts.values() if count > 1)

        inferred_types: dict[str, list[str]] = {}
        json_columns = {"geometry.coordinates", "medias", "likes", "user_profile_picture"}
        for column in columns:
            types: set[str] = set()
            for row in rows:
                value = row.get(column)
                if value is None or not value.strip():
                    types.add("null")
                elif column in json_columns:
                    try:
                        types.add(type(json.loads(value)).__name__)
                    except json.JSONDecodeError:
                        types.add("invalid_json")
                elif column in {"total_comment"} and value.isdigit():
                    types.add("integer_string")
                else:
                    types.add("string")
            inferred_types[column] = sorted(types)

        description_lengths = [len(normalize_whitespace(row.get("description")).split()) for row in rows]
        return {
            "source_file": str(self.options.input_path),
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": columns,
            "data_types": inferred_types,
            "null_counts": {column: sum(not (row.get(column) or "").strip() for row in rows) for column in columns},
            "duplicate_count": duplicate_excess(exact_keys),
            "duplicate_source_id_count": duplicate_excess(ids, ignore_empty=True),
            "content_duplicate_count": duplicate_excess(descriptions, ignore_empty=True),
            "unique_id_count": len({value for value in ids if value}),
            "coordinate_validity": {"valid": sum(coordinate_validity), "invalid": len(rows) - sum(coordinate_validity)},
            "timestamp_validity": {"valid": sum(timestamp_validity), "invalid": len(rows) - sum(timestamp_validity)},
            "description_completeness": {
                "present": sum(bool(normalize_whitespace(row.get("description"))) for row in rows),
                "missing": sum(not bool(normalize_whitespace(row.get("description"))) for row in rows),
                "word_count_min": min(description_lengths, default=0),
                "word_count_max": max(description_lengths, default=0),
                "word_count_average": round(mean(description_lengths), 2) if description_lengths else 0,
                "explicit_time_mentions": sum(time_mentions),
            },
            "media_format": {
                "valid_json_arrays": sum(bool(item["media_valid"]) for item in media),
                "invalid": sum(not bool(item["media_valid"]) for item in media),
                "image_count": sum(int(item["image_count"]) for item in media),
                "video_count": sum(int(item["video_count"]) for item in media),
            },
        }

    def clean(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        for source_row, row in enumerate(rows, start=2):
            source_id = normalize_whitespace(row.get("id"))
            description_raw = row.get("description") or ""
            description_normalized = normalize_whitespace(description_raw)
            if not source_id:
                source_id = stable_id("missing_source", source_row, description_normalized)
            observation_id = stable_id("obs", SOURCE_TYPE, source_id, description_normalized)
            longitude, latitude, coordinates_valid, coordinate_error = parse_coordinates(row.get("geometry.coordinates"))
            created_utc, created_local, timestamp_error = parse_created_at(row.get("created_at"))
            temporal = extract_observation_time(
                description_raw,
                created_at_local=created_local,
                use_created_at_fallback=self.options.use_created_at_fallback,
            )
            media = parse_media(row.get("medias"))
            record: dict[str, Any] = {
                "source_file": SOURCE_FILE_NAME,
                "source_row": source_row,
                "source_activity_id": source_id,
                "observation_id": observation_id,
                "title_raw": row.get("title") or "",
                "title_normalized": normalize_title(row.get("title")),
                "description_raw": description_raw,
                "description_normalized": description_normalized,
                "geometry_coordinates_raw": row.get("geometry.coordinates") or "",
                "longitude": longitude,
                "latitude": latitude,
                "coordinates_valid": coordinates_valid,
                "coordinate_error": coordinate_error,
                "created_at_raw": row.get("created_at") or "",
                "created_at_utc": created_utc,
                "created_at_local": created_local,
                "timestamp_error": timestamp_error,
                "medias_raw": row.get("medias") or "",
                **temporal,
                **media,
                "total_comment": _safe_int(row.get("total_comment")),
                "likes": _safe_json(row.get("likes"), default=row.get("likes") or ""),
                "user_name": row.get("user_name") or "",
                "user_full_name": row.get("user_full_name") or "",
                "user_profile_picture": _safe_json(row.get("user_profile_picture"), default=row.get("user_profile_picture") or ""),
                "community_name": row.get("community_name") or "",
                "community_picture": row.get("community_picture") or "",
                "community_description": row.get("community_description") or "",
            }
            cleaned.append(record)
        mark_duplicates(cleaned)
        resolve_stop_entities(cleaned)
        return cleaned

    def _client(self) -> OpenRouterLLMClient:
        if self._llm_client is not None:
            return self._llm_client
        api_key = self.environ.get("OPENROUTER_API_KEY", "")
        self._llm_client = OpenRouterLLMClient(
            api_key=api_key,
            base_url=self.options.base_url,
            model=self.options.model,
            max_retries=self.options.max_retries,
            site_url=self.environ.get("OPENROUTER_SITE_URL"),
            app_name=self.environ.get("OPENROUTER_APP_NAME"),
        )
        return self._llm_client

    def _load_cache(self) -> dict[str, Any]:
        path = self.paths["cache"]
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _cache_key(self, description: str) -> str:
        return hashlib.sha256("\x1f".join([
            description, SCHEMA_VERSION, PROMPT_VERSION, EXTRACTION_VERSION, self.options.model,
        ]).encode("utf-8")).hexdigest()

    def extract(self, cleaned_rows: list[dict[str, Any]]) -> tuple[list[SurveyKnowledgeRecord], list[dict[str, Any]], dict[str, Any]]:
        cache = self._load_cache() if not self.options.force else {}
        cache_changed = False
        errors: list[dict[str, Any]] = []
        records: list[SurveyKnowledgeRecord] = []
        client = None
        if self.options.use_llm and not self.options.dry_run:
            client = self._client()

        for batch_start in range(0, len(cleaned_rows), self.options.batch_size):
            batch = cleaned_rows[batch_start : batch_start + self.options.batch_size]
            for row in batch:
                deterministic = deterministic_semantic(str(row["description_normalized"]))
                semantic = deterministic
                status = "deterministic_only"
                request_id = None
                cache_key = self._cache_key(str(row["description_normalized"]))
                cached = cache.get(cache_key)
                if client is not None and cached is not None:
                    try:
                        semantic = merge_semantic(deterministic, SemanticExtraction.model_validate(cached["semantic"]))
                        status = "cache_hit"
                        request_id = cached.get("request_id")
                        client.metrics.cache_hits += 1
                    except (KeyError, ValidationError, TypeError):
                        cached = None
                if client is not None and cached is None:
                    try:
                        payload = client.extract_structured(
                            system_prompt=SYSTEM_PROMPT,
                            user_prompt=user_prompt_for(str(row["description_normalized"])),
                            response_schema=SemanticExtraction.model_json_schema(),
                            model=self.options.model,
                            temperature=0.0,
                            timeout=self.options.timeout,
                        )
                        enrichment = SemanticExtraction.model_validate(payload)
                        warnings = semantic_validation_warnings(enrichment)
                        if warnings:
                            raise ValueError("; ".join(warnings))
                        semantic = merge_semantic(deterministic, enrichment)
                        status = "llm_validated"
                        request_id = client.last_request_id
                        cache[cache_key] = {
                            "semantic": enrichment.model_dump(mode="json"),
                            "request_id": request_id,
                            "model": self.options.model,
                            "schema_version": SCHEMA_VERSION,
                            "prompt_version": PROMPT_VERSION,
                            "extraction_version": EXTRACTION_VERSION,
                        }
                        cache_changed = True
                    except (LLMError, ValidationError, ValueError) as exc:
                        if isinstance(exc, (ValidationError, ValueError)):
                            client.metrics.validation_failures += 1
                        errors.append({
                            "source_activity_id": row["source_activity_id"],
                            "observation_id": row["observation_id"],
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "provider": EXTRACTION_PROVIDER,
                            "model": self.options.model,
                            "processed_at": self._processed_at.isoformat(),
                        })

                record = self._knowledge_record(row, semantic, status=status, request_id=request_id)
                record_warnings = semantic_validation_warnings(semantic)
                if record_warnings:
                    errors.append({
                        "source_activity_id": row["source_activity_id"],
                        "observation_id": row["observation_id"],
                        "error_type": "SemanticConsistencyWarning",
                        "error": "; ".join(record_warnings),
                        "provider": EXTRACTION_PROVIDER,
                        "model": self.options.model,
                        "processed_at": self._processed_at.isoformat(),
                    })
                records.append(record)

        if client is not None:
            self.metrics = client.metrics
        if cache_changed and not self.options.dry_run:
            _atomic_write_text(self.paths["cache"], _json_dumps(cache, indent=2) + "\n")
        return records, errors, cache

    def _knowledge_record(
        self,
        row: dict[str, Any],
        semantic: SemanticExtraction,
        *,
        status: str,
        request_id: str | None,
    ) -> SurveyKnowledgeRecord:
        social_metadata = {
            "total_comment": row.get("total_comment"),
            "likes": row.get("likes"),
            "user_name": row.get("user_name"),
            "user_full_name": row.get("user_full_name"),
            "user_profile_picture": row.get("user_profile_picture"),
            "community_name": row.get("community_name"),
            "community_picture": row.get("community_picture"),
            "community_description": row.get("community_description"),
        }
        return SurveyKnowledgeRecord(
            knowledge_id=stable_id("knowledge", SOURCE_TYPE, row["observation_id"], EXTRACTION_VERSION),
            source_activity_id=str(row["source_activity_id"]),
            observation_id=str(row["observation_id"]),
            stop_id=row.get("stop_id"),
            stop_name=row.get("stop_name"),
            stop_name_raw=row.get("stop_name_raw"),
            stop_name_normalized=row.get("stop_name_normalized"),
            entity_resolution_confidence=float(row["entity_resolution_confidence"]),
            entity_resolution_status=str(row["entity_resolution_status"]),
            latitude=row.get("latitude"),
            longitude=row.get("longitude"),
            coordinates_valid=bool(row["coordinates_valid"]),
            created_at_utc=row.get("created_at_utc"),
            created_at_local=row.get("created_at_local"),
            observed_date=row.get("observed_date"),
            observed_time=row.get("observed_time"),
            observed_at=row.get("observed_at"),
            observed_time_source=row.get("observed_time_source"),
            observed_time_confidence=float(row["observed_time_confidence"]),
            day_of_week=row.get("day_of_week"),
            time_period=row.get("time_period"),
            title_raw=str(row["title_raw"]),
            title_normalized=str(row["title_normalized"]),
            description_raw=str(row["description_raw"]),
            description_normalized=str(row["description_normalized"]),
            image_urls=list(row["image_urls"]),
            video_urls=list(row["video_urls"]),
            image_count=int(row["image_count"]),
            video_count=int(row["video_count"]),
            media_valid=bool(row["media_valid"]),
            duplicate_group_id=row.get("duplicate_group_id"),
            duplicate_status=str(row["duplicate_status"]),
            social_metadata=social_metadata,
            **semantic.model_dump(mode="python"),
            provenance={
                "source_file": SOURCE_FILE_NAME,
                "source_row": int(row["source_row"]),
                "processed_at": self._processed_at,
                "extraction_provider": EXTRACTION_PROVIDER,
                "extraction_model": self.options.model,
                "extraction_version": EXTRACTION_VERSION,
                "prompt_version": PROMPT_VERSION,
                "request_id": request_id,
                "extraction_status": status,
            },
        )

    def build_rag(self, records: list[SurveyKnowledgeRecord]) -> tuple[list[RagDocument], list[RagChunk]]:
        documents: list[RagDocument] = []
        chunks: list[RagChunk] = []
        for record in records:
            sections = _rag_sections(record)
            metadata = _rag_metadata(record)
            document = RagDocument(
                document_id=stable_id("doc", record.knowledge_id),
                knowledge_id=record.knowledge_id,
                text="\n\n".join(text for _, text in sections),
                metadata=metadata,
            )
            documents.append(document)
            for chunk_type, text in sections:
                chunks.append(RagChunk(
                    chunk_id=stable_id("chunk", record.knowledge_id, chunk_type),
                    knowledge_id=record.knowledge_id,
                    chunk_type=chunk_type,
                    text=text,
                    metadata={**metadata, "chunk_type": chunk_type},
                ))
        return documents, chunks

    def quality_report(
        self,
        inspection: dict[str, Any],
        cleaned: list[dict[str, Any]],
        records: list[SurveyKnowledgeRecord],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        def coverage(predicate: Any) -> dict[str, Any]:
            count = sum(1 for record in records if predicate(record))
            return {"count": count, "percent": round(100 * count / len(records), 2) if records else 0.0}

        record_confidences = [mean(record.confidence.values()) if record.confidence else 0.0 for record in records]
        report = {
            "generated_at": self._processed_at.isoformat(),
            "source": inspection,
            "total_records": len(records),
            "duplicate_records": sum(row.get("duplicate_status") != "unique" for row in cleaned),
            "invalid_coordinates": sum(not bool(row.get("coordinates_valid")) for row in cleaned),
            "missing_descriptions": sum(not bool(row.get("description_normalized")) for row in cleaned),
            "missing_observed_time": sum(row.get("observed_time") is None for row in cleaned),
            "missing_observed_at": sum(row.get("observed_at") is None for row in cleaned),
            "missing_stop_name": sum(not bool(row.get("stop_name")) for row in cleaned),
            "unresolved_stop_entities": sum(str(row.get("entity_resolution_status", "")).startswith("unresolved") for row in cleaned),
            "low_confidence_records": sum(score < 0.6 for score in record_confidences),
            "validation_failures": sum(error["error_type"] in {"ValidationError", "ValueError", "SemanticConsistencyWarning"} for error in errors),
            "field_coverage": {
                "usage": coverage(lambda item: any(value not in (None, "unknown") for value in item.usage.model_dump().values())),
                "facility": coverage(lambda item: any(value is not None for value in item.facilities.model_dump().values())),
                "accessibility": coverage(lambda item: any(value not in (None, "unknown", []) for value in item.accessibility.model_dump().values())),
                "condition": coverage(lambda item: any(value not in (None, "unknown") for value in item.condition.model_dump().values())),
                "environment": coverage(lambda item: any(bool(value) for value in item.environment.model_dump().values())),
                "issue": coverage(lambda item: bool(item.issues)),
            },
            "entity_resolution": _entity_resolution_summary(cleaned),
            "llm": self.metrics.to_dict(),
        }
        return report

    def manual_qa(self, records: list[SurveyKnowledgeRecord]) -> list[dict[str, Any]]:
        if not records:
            return []
        target = min(len(records), max(10, round(len(records) * 0.1)))
        ranked = sorted(records, key=lambda item: mean(item.confidence.values()) if item.confidence else 0.0)
        indexes = {round(index * (len(ranked) - 1) / max(target - 1, 1)) for index in range(target)}
        selected = [ranked[index] for index in sorted(indexes)]
        selected_ids = {item.observation_id for item in selected}
        for item in ranked:
            if len(selected) >= target:
                break
            if item.observation_id not in selected_ids:
                selected.append(item)
                selected_ids.add(item.observation_id)
        return [{
            "source_activity_id": item.source_activity_id,
            "observation_id": item.observation_id,
            "stop_name": item.stop_name,
            "description_raw": item.description_raw,
            "structured_extraction": {
                "usage": item.usage.model_dump(mode="json"),
                "facilities": item.facilities.model_dump(mode="json"),
                "accessibility": item.accessibility.model_dump(mode="json"),
                "condition": item.condition.model_dump(mode="json"),
                "environment": item.environment.model_dump(mode="json"),
                "issues": [issue.model_dump(mode="json") for issue in item.issues],
                "recommendation_tags": item.recommendation_tags,
                "evidence": item.evidence,
                "confidence": item.confidence,
            },
            "qa_status": "pending_manual_review",
        } for item in selected]

    def preserve_raw(self) -> Path:
        destination = self.paths["raw"]
        if destination.exists():
            if _sha256_file(destination) != _sha256_file(self.options.input_path):
                raise RuntimeError(
                    f"immutable raw copy differs from input and will not be overwritten: {destination}"
                )
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.options.input_path.open("rb") as source, destination.open("xb") as target:
            shutil.copyfileobj(source, target)
        return destination

    def write_cleaned(self, cleaned: list[dict[str, Any]]) -> Path:
        _atomic_write_text(self.paths["cleaned"], _csv_text(cleaned, CLEANED_FIELDS))
        return self.paths["cleaned"]

    def write_structured(self, records: list[SurveyKnowledgeRecord], errors: list[dict[str, Any]]) -> list[Path]:
        payloads = [record.model_dump(mode="json") for record in records]
        _atomic_write_text(self.paths["structured_jsonl"], _jsonl_text(payloads))
        _atomic_write_text(self.paths["structured_csv"], _csv_text(payloads, STRUCTURED_CSV_FIELDS))
        _atomic_write_text(self.paths["errors"], _jsonl_text(errors))
        return [self.paths["structured_csv"], self.paths["structured_jsonl"], self.paths["errors"]]

    def write_knowledge(self, records: list[SurveyKnowledgeRecord]) -> Path:
        _atomic_write_text(self.paths["knowledge"], _jsonl_text(record.model_dump(mode="json") for record in records))
        return self.paths["knowledge"]

    def write_rag(self, documents: list[RagDocument], chunks: list[RagChunk]) -> list[Path]:
        _atomic_write_text(self.paths["documents"], _jsonl_text(item.model_dump(mode="json") for item in documents))
        _atomic_write_text(self.paths["chunks"], _jsonl_text(item.model_dump(mode="json") for item in chunks))
        return [self.paths["documents"], self.paths["chunks"]]

    def write_reports(self, report: dict[str, Any], qa: list[dict[str, Any]]) -> list[Path]:
        _atomic_write_text(self.paths["quality_json"], _json_dumps(report, indent=2) + "\n")
        summary_rows = _flatten_report_for_csv(report)
        _atomic_write_text(self.paths["quality_csv"], _csv_text(summary_rows, ["metric", "value"]))
        _atomic_write_text(self.paths["manual_qa"], _jsonl_text(qa))
        return [self.paths["quality_json"], self.paths["quality_csv"], self.paths["manual_qa"]]

    def run_all(self) -> PipelineResult:
        rows = self.read_source()
        inspection = self.inspect(rows)
        cleaned = self.clean(rows)
        records, errors, _ = self.extract(cleaned)
        documents, chunks = self.build_rag(records)
        report = self.quality_report(inspection, cleaned, records, errors)
        result = PipelineResult(
            inspection=inspection,
            cleaned_rows=cleaned,
            records=records,
            documents=documents,
            chunks=chunks,
            errors=errors,
            quality_report=report,
        )
        if self.options.dry_run:
            return result
        result.written_files.append(self.preserve_raw())
        result.written_files.append(self.write_cleaned(cleaned))
        result.written_files.extend(self.write_structured(records, errors))
        result.written_files.append(self.write_knowledge(records))
        result.written_files.extend(self.write_rag(documents, chunks))
        result.written_files.extend(self.write_reports(report, self.manual_qa(records)))
        if self.paths["cache"].exists():
            result.written_files.append(self.paths["cache"])
        return result

    def load_records(self, path: Path) -> list[SurveyKnowledgeRecord]:
        records: list[SurveyKnowledgeRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line.strip():
                    try:
                        records.append(SurveyKnowledgeRecord.model_validate_json(line))
                    except ValidationError as exc:
                        raise ValueError(f"invalid structured record at {path}:{line_number}: {exc}") from exc
        return records

    def validate_records(self, records: list[SurveyKnowledgeRecord]) -> list[dict[str, str]]:
        failures: list[dict[str, str]] = []
        for record in records:
            semantic = SemanticExtraction.model_validate({
                "usage": record.usage,
                "facilities": record.facilities,
                "accessibility": record.accessibility,
                "condition": record.condition,
                "environment": record.environment,
                "issues": record.issues,
                "strengths": record.strengths,
                "weaknesses": record.weaknesses,
                "recommendation_tags": record.recommendation_tags,
                "evidence": record.evidence,
                "confidence": record.confidence,
            })
            for warning in semantic_validation_warnings(semantic):
                failures.append({"observation_id": record.observation_id, "error": warning})
        return failures


def _safe_int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _safe_json(value: str | None, *, default: object) -> object:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonl_text(rows: Iterable[object]) -> str:
    return "".join(_json_dumps(row) + "\n" for row in rows)


def _meaningful_values(model: Any) -> list[str]:
    values = []
    for key, value in model.model_dump(mode="python").items():
        if value not in (None, "unknown", [], {}):
            values.append(f"{key}: {str(value).lower() if isinstance(value, bool) else value}")
    return values


def _rag_sections(record: SurveyKnowledgeRecord) -> list[tuple[str, str]]:
    observed = record.observed_at.isoformat() if record.observed_at else (
        f"waktu {record.observed_time.isoformat(timespec='minutes')}; tanggal tidak disebutkan"
        if record.observed_time else "tidak disebutkan"
    )
    overview = (
        f"Halte/lokasi: {record.stop_name or record.title_normalized}\n"
        f"Lokasi: latitude {record.latitude}, longitude {record.longitude}\n"
        f"Waktu observasi: {observed}\n"
        f"Sumber: Survey Activity ID {record.source_activity_id}; Observation ID {record.observation_id}"
    )
    sections: list[tuple[str, str]] = [("overview", overview)]
    mappings = [
        ("usage", "Aktivitas penumpang", record.usage),
        ("facilities", "Fasilitas", record.facilities),
        ("accessibility", "Aksesibilitas", record.accessibility),
        ("condition", "Kondisi", record.condition),
        ("environment", "Lingkungan sekitar", record.environment),
    ]
    for chunk_type, label, model in mappings:
        values = _meaningful_values(model)
        if values:
            sections.append((chunk_type, f"{label}:\n" + "\n".join(f"- {value}" for value in values)))
    if record.issues:
        issue_lines = [f"{item.category}/{item.issue} (severity: {item.severity}); bukti: {item.evidence}" for item in record.issues]
        sections.append(("issues", "Masalah:\n" + "\n".join(f"- {line}" for line in issue_lines)))
    evidence_lines = []
    if record.strengths:
        evidence_lines.append("Kelebihan: " + "; ".join(record.strengths))
    if record.weaknesses:
        evidence_lines.append("Kekurangan: " + "; ".join(record.weaknesses))
    if record.recommendation_tags:
        evidence_lines.append("Tag bukti rekomendasi: " + ", ".join(record.recommendation_tags))
    if evidence_lines:
        sections.append(("recommendation_evidence", "\n".join(evidence_lines)))
    return sections


def _rag_metadata(record: SurveyKnowledgeRecord) -> dict[str, object]:
    return {
        "knowledge_id": record.knowledge_id,
        "source_type": record.source_type,
        "source_activity_id": record.source_activity_id,
        "observation_id": record.observation_id,
        "stop_id": record.stop_id,
        "stop_name": record.stop_name,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "observed_at": record.observed_at.isoformat() if record.observed_at else None,
        "observed_time": record.observed_time.isoformat(timespec="minutes") if record.observed_time else None,
        "time_period": record.time_period,
        "passenger_level": record.usage.passenger_level,
        "maintenance": record.condition.maintenance,
        "cleanliness": record.condition.cleanliness,
        "wheelchair_access": record.accessibility.wheelchair_access,
        "nearby_place_categories": record.environment.nearby_place_categories,
        "recommendation_tags": record.recommendation_tags,
        "extraction_version": record.provenance.extraction_version,
    }


def _entity_resolution_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for row in rows:
        status = str(row.get("entity_resolution_status"))
        summary[status] = summary.get(status, 0) + 1
    summary["unique_stop_ids"] = len({row.get("stop_id") for row in rows if row.get("stop_id")})
    return summary


def _flatten_report_for_csv(report: dict[str, Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def walk(prefix: str, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                walk(f"{prefix}.{key}" if prefix else key, nested)
        elif isinstance(value, list):
            rows.append({"metric": prefix, "value": _json_dumps(value)})
        else:
            rows.append({"metric": prefix, "value": value})

    walk("", report)
    return rows
