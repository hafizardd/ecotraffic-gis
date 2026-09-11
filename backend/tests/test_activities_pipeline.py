import hashlib
from pathlib import Path

from data_pipeline.activities.llm import LLMMetrics
from data_pipeline.activities.pipeline import ActivitiesPipeline, PipelineOptions


DATASET = Path(__file__).resolve().parents[1] / "data" / "output" / "activities.csv"


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_deterministic_pipeline_builds_valid_citation_ready_rag_without_user_metadata(tmp_path):
    pipeline = ActivitiesPipeline(PipelineOptions(
        input_path=DATASET, output_dir=tmp_path, limit=2, dry_run=True, use_llm=False,
    ))
    result = pipeline.run_all()
    assert len(result.records) == 2
    assert len(result.documents) == 2
    assert result.documents[0].metadata["source_activity_id"] == result.records[0].source_activity_id
    assert result.records[0].observation_id in result.documents[0].text
    assert "user_name" not in result.documents[0].metadata
    assert "user_full_name" not in result.documents[0].text
    assert all(chunk.knowledge_id in {record.knowledge_id for record in result.records} for chunk in result.chunks)


def test_pipeline_is_idempotent_and_raw_copy_is_immutable(tmp_path):
    options = PipelineOptions(input_path=DATASET, output_dir=tmp_path, limit=2, use_llm=False)
    first = ActivitiesPipeline(options).run_all()
    raw = tmp_path / "raw" / "activities_raw.csv"
    first_raw_hash = _hash(raw)
    first_ids = [record.knowledge_id for record in first.records]

    second = ActivitiesPipeline(options).run_all()
    assert _hash(raw) == first_raw_hash == _hash(DATASET)
    assert [record.knowledge_id for record in second.records] == first_ids
    assert len({record.knowledge_id for record in second.records}) == 2


def test_dry_run_never_writes_or_calls_openrouter(tmp_path):
    class ExplodingClient:
        def extract_structured(self, **kwargs):
            raise AssertionError("dry-run must not call OpenRouter")

    pipeline = ActivitiesPipeline(
        PipelineOptions(input_path=DATASET, output_dir=tmp_path, limit=1, dry_run=True),
        llm_client=ExplodingClient(),  # type: ignore[arg-type]
    )
    result = pipeline.run_all()
    assert result.records
    assert result.written_files == []
    assert list(tmp_path.iterdir()) == []


def test_pipeline_normalizes_missing_evidence_without_marking_successful_llm_call_failed(tmp_path):
    class NormalizableClient:
        def __init__(self):
            self.metrics = LLMMetrics(model="test/model")
            self.last_request_id = "request-normalized"

        def extract_structured(self, **kwargs):
            self.metrics.number_of_calls += 1
            self.metrics.successful_calls += 1
            return {
                "environment": {
                    "nearby_place_categories": ["school"],
                    "landmark_categories": ["government"],
                },
                "facilities": {"has_wifi": True},
                "confidence": {"facilities.has_wifi": 0.9},
            }

    pipeline = ActivitiesPipeline(
        PipelineOptions(input_path=DATASET, output_dir=tmp_path, limit=1),
        llm_client=NormalizableClient(),  # type: ignore[arg-type]
    )

    result = pipeline.run_all()

    assert pipeline.metrics.number_of_calls == 1
    assert pipeline.metrics.successful_calls == 1
    assert pipeline.metrics.failed_calls == 0
    assert pipeline.metrics.validation_failures == 0
    assert result.records[0].provenance.extraction_status == "llm_validated"
    assert result.records[0].environment.landmark_categories == []
    assert not [error for error in result.errors if error["error_type"] in {"ValueError", "ValidationError"}]


def test_manual_qa_contains_ten_real_records(tmp_path):
    pipeline = ActivitiesPipeline(PipelineOptions(input_path=DATASET, output_dir=tmp_path, use_llm=False, dry_run=True))
    result = pipeline.run_all()
    qa = pipeline.manual_qa(result.records)
    assert len(qa) >= 10
    assert all(item["description_raw"] for item in qa)
    assert all(item["source_activity_id"] for item in qa)


def test_validate_records_checks_evidence_and_consistency(tmp_path):
    pipeline = ActivitiesPipeline(PipelineOptions(input_path=DATASET, output_dir=tmp_path, limit=1, dry_run=True, use_llm=False))
    result = pipeline.run_all()
    assert pipeline.validate_records(result.records) == []
    result.records[0].usage.passenger_level = "very_high"
    result.records[0].evidence.pop("usage.passenger_level", None)
    assert pipeline.validate_records(result.records)
