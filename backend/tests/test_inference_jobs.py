from datetime import datetime, timezone

from app.services.inference_jobs import InferenceJob


def test_inference_job_payload_round_trip_preserves_camera_mapping():
    job = InferenceJob(
        job_id="job-1",
        camera_id="camera-12",
        camera_database_id="2b0ea8e6-a790-44a5-aa76-8b40787c0f02",
        captured_at=datetime(2026, 8, 21, 1, 2, 3, tzinfo=timezone.utc),
        enqueued_at=datetime(2026, 8, 21, 1, 2, 4, tzinfo=timezone.utc),
        priority="high",
        sampling_interval_seconds=10,
        frame_key="inference:frame:job-1",
        frame_size_bytes=12345,
        frame_acquisition_latency_s=1.25,
        frame_capture_method="opencv",
    )

    restored = InferenceJob.from_payload(job.to_payload())

    assert restored == job
    assert restored.celery_priority == 9


def test_unknown_priority_is_normalized_for_safe_routing():
    payload = InferenceJob(
        job_id="job-1",
        camera_id="camera-12",
        camera_database_id="2b0ea8e6-a790-44a5-aa76-8b40787c0f02",
        captured_at=datetime.now(timezone.utc),
        enqueued_at=datetime.now(timezone.utc),
        priority="urgent",
        sampling_interval_seconds=None,
        frame_key="frame-key",
        frame_size_bytes=1,
        frame_acquisition_latency_s=0.1,
        frame_capture_method="ffmpeg",
    ).to_payload()

    restored = InferenceJob.from_payload(payload)

    assert restored.priority == "medium"
    assert restored.celery_priority == 5
