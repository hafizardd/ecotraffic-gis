from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - requirements include python-dotenv
    load_dotenv = None

from .constants import DEFAULT_DATA_DIR, DEFAULT_INPUT, DEFAULT_OPENROUTER_BASE_URL, DEFAULT_OPENROUTER_MODEL
from .pipeline import ActivitiesPipeline, PipelineOptions


COMMANDS = ("inspect", "clean", "extract", "validate", "build-knowledge", "build-rag", "all")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standardize activities.csv and build validated RAG artifacts")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="source activities CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR, help="data output root")
    parser.add_argument("--model", default=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL))
    parser.add_argument("--base-url", default=os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL))
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--force", action="store_true", help="ignore semantic extraction cache")
    parser.add_argument("--dry-run", action="store_true", help="run locally without network or filesystem writes")
    parser.add_argument("--no-llm", action="store_true", help="explicitly build deterministic-only records")
    parser.add_argument(
        "--use-created-at-fallback",
        action="store_true",
        help="label created_at as a low-confidence observation-time fallback when description time is absent",
    )
    return parser


def _load_environment() -> None:
    if load_dotenv is None:
        return
    backend_dir = Path(__file__).resolve().parents[2]
    load_dotenv(backend_dir.parent / ".env", override=False)
    load_dotenv(backend_dir / ".env", override=False)


def _options(args: argparse.Namespace) -> PipelineOptions:
    return PipelineOptions(
        input_path=args.input,
        output_dir=args.output,
        model=args.model,
        base_url=args.base_url,
        batch_size=args.batch_size,
        limit=args.limit,
        force=args.force,
        dry_run=args.dry_run,
        use_llm=not args.no_llm,
        timeout=args.timeout,
        max_retries=args.max_retries,
        use_created_at_fallback=args.use_created_at_fallback,
    )


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    _load_environment()
    args = build_parser().parse_args(argv)
    pipeline = ActivitiesPipeline(_options(args))

    if args.command == "inspect":
        _print(pipeline.inspect())
        return 0

    if args.command in {"validate", "build-knowledge", "build-rag"}:
        source = pipeline.paths["knowledge"] if args.command == "build-rag" else pipeline.paths["structured_jsonl"]
        if args.command == "build-rag" and not source.exists():
            source = pipeline.paths["structured_jsonl"]
        records = pipeline.load_records(source)
        if args.command == "validate":
            failures = pipeline.validate_records(records)
            _print({
                "valid": not failures,
                "record_count": len(records),
                "validation_failures": failures,
                "source": str(source),
            })
            return 1 if failures else 0
        elif args.command == "build-knowledge":
            written = [] if args.dry_run else [str(pipeline.write_knowledge(records))]
            _print({"record_count": len(records), "dry_run": args.dry_run, "written_files": written})
        else:
            documents, chunks = pipeline.build_rag(records)
            written = [] if args.dry_run else [str(path) for path in pipeline.write_rag(documents, chunks)]
            _print({"document_count": len(documents), "chunk_count": len(chunks), "dry_run": args.dry_run, "written_files": written})
        return 0

    rows = pipeline.read_source()
    inspection = pipeline.inspect(rows)
    cleaned = pipeline.clean(rows)
    if args.command == "clean":
        written = []
        if not args.dry_run:
            written = [str(pipeline.preserve_raw()), str(pipeline.write_cleaned(cleaned))]
        _print({"inspection": inspection, "cleaned_records": len(cleaned), "dry_run": args.dry_run, "written_files": written})
        return 0

    if args.command == "extract":
        records, errors, _ = pipeline.extract(cleaned)
        written = []
        if not args.dry_run:
            written = [str(pipeline.preserve_raw()), str(pipeline.write_cleaned(cleaned))]
            written.extend(str(path) for path in pipeline.write_structured(records, errors))
        _print({
            "record_count": len(records), "error_count": len(errors), "llm": pipeline.metrics.to_dict(),
            "dry_run": args.dry_run, "written_files": written,
        })
        return 0

    result = pipeline.run_all()
    cache = pipeline._load_cache()  # safe plan information; values are never displayed
    cached_records = sum(pipeline._cache_key(str(row["description_normalized"])) in cache for row in result.cleaned_rows)
    _print({
        "inspection": result.inspection,
        "quality": result.quality_report,
        "rag": {"documents": len(result.documents), "chunks": len(result.chunks)},
        "configuration": {
            "provider": "openrouter",
            "base_url": pipeline.options.base_url,
            "model": pipeline.options.model,
            "api_key_configured": bool(os.getenv("OPENROUTER_API_KEY")),
            "batch_size": pipeline.options.batch_size,
            "records_to_process": len(result.cleaned_rows),
            "cached_records": cached_records,
            "new_llm_calls": 0 if args.dry_run or args.no_llm else max(0, len(result.cleaned_rows) - cached_records),
            "dry_run": args.dry_run,
            "llm_enabled": not args.no_llm,
        },
        "written_files": [str(path) for path in result.written_files],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
