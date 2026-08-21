from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.services.emission_aggregation import (
    EmissionObservation,
    EmissionWindowAggregator,
    LateEmissionObservation,
)
from cv.emission_factors import calculate_emission


BASE_TIME = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def _observation(
    *,
    camera_id: str = "camera-1",
    captured_at: datetime = BASE_TIME,
    car: int = 0,
    motorcycle: int = 0,
    bus: int = 0,
    truck: int = 0,
) -> EmissionObservation:
    return EmissionObservation(
        camera_id=camera_id,
        camera_database_id=f"database-{camera_id}",
        job_id=f"job-{camera_id}-{captured_at.timestamp()}",
        captured_at=captured_at,
        vehicle_counts={
            "car": car,
            "motorcycle": motorcycle,
            "bus": bus,
            "truck": truck,
        },
        frame_acquisition_latency_s=1,
        queue_wait_s=2,
        inference_latency_s=3,
        cycle_duration_s=4,
    )


def test_repeated_snapshots_are_averaged_instead_of_summed():
    aggregator = EmissionWindowAggregator(window_seconds=60)

    aggregator.add(_observation(car=5, motorcycle=2))
    update = aggregator.add(
        _observation(
            captured_at=BASE_TIME + timedelta(seconds=20),
            car=5,
            motorcycle=2,
        )
    )

    assert update.current.sample_count == 2
    assert update.current.mean_vehicle_counts == {
        "car": 5,
        "motorcycle": 2,
        "bus": 0,
        "truck": 0,
    }
    assert update.current.emission["total_co_g_per_min"] == calculate_emission(
        {"car": 5, "motorcycle": 2}
    )["total_co_g_per_min"]


def test_aggregate_rate_is_recalculated_from_mean_snapshot_counts():
    aggregator = EmissionWindowAggregator(window_seconds=60)
    aggregator.add(_observation(car=2, bus=1))

    update = aggregator.add(
        _observation(
            captured_at=BASE_TIME + timedelta(seconds=30),
            car=8,
            bus=3,
        )
    )

    assert update.current.mean_vehicle_counts["car"] == 5
    assert update.current.mean_vehicle_counts["bus"] == 2
    expected = calculate_emission({"car": 5, "bus": 2})
    assert update.current.emission["total_nox_g_per_min"] == expected[
        "total_nox_g_per_min"
    ]
    assert update.current.emission["total_pm_kg_per_hr"] == expected[
        "total_pm_kg_per_hr"
    ]


def test_new_camera_window_finalizes_only_that_cameras_previous_window():
    aggregator = EmissionWindowAggregator(window_seconds=60)
    aggregator.add(_observation(camera_id="camera-a", car=2))
    aggregator.add(
        _observation(
            camera_id="camera-b",
            captured_at=BASE_TIME + timedelta(seconds=10),
            truck=4,
        )
    )

    update = aggregator.add(
        _observation(
            camera_id="camera-a",
            captured_at=BASE_TIME + timedelta(seconds=61),
            car=6,
        )
    )

    assert [item.camera_id for item in update.completed] == ["camera-a"]
    assert update.completed[0].period_start == BASE_TIME
    assert update.completed[0].period_end == BASE_TIME + timedelta(seconds=60)
    assert update.current.period_start == BASE_TIME + timedelta(seconds=60)
    assert aggregator.preview("camera-b").sample_count == 1

    camera_b_update = aggregator.add(
        _observation(
            camera_id="camera-b",
            captured_at=BASE_TIME + timedelta(seconds=40),
            truck=2,
        )
    )
    assert camera_b_update.current.sample_count == 2


def test_explicit_watermark_flushes_expired_windows_and_rejects_late_data():
    aggregator = EmissionWindowAggregator(window_seconds=60)
    aggregator.add(_observation(car=3))

    completed = aggregator.flush_expired(BASE_TIME + timedelta(seconds=60))

    assert len(completed) == 1
    assert completed[0].sample_count == 1
    with pytest.raises(LateEmissionObservation, match="already finalized"):
        aggregator.add(
            _observation(captured_at=BASE_TIME + timedelta(seconds=30), car=9)
        )


def test_concurrent_observations_update_one_window_safely():
    aggregator = EmissionWindowAggregator(window_seconds=60)
    observations = [
        _observation(
            captured_at=BASE_TIME + timedelta(milliseconds=index),
            car=index % 5,
        )
        for index in range(100)
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(aggregator.add, observations))

    preview = aggregator.preview("camera-1")
    assert preview.sample_count == 100
    assert preview.mean_vehicle_counts["car"] == 2


def test_normalized_payload_documents_snapshot_mean_semantics():
    aggregator = EmissionWindowAggregator(window_seconds=60)
    aggregate = aggregator.add(_observation(car=3)).current

    payload = aggregate.to_payload()

    assert payload["period_start"] == BASE_TIME.isoformat()
    assert payload["period_end"] == (BASE_TIME + timedelta(seconds=60)).isoformat()
    assert payload["aggregation_method"] == "arithmetic_mean_of_snapshot_counts"
    assert payload["vehicle_count_semantics"] == "mean_observed_snapshot_count"
    assert payload["vehicle_count"]["car"] == 3
    assert set(payload["emission"]) == {
        "total_co_g_per_min",
        "total_co_kg_per_hr",
        "total_nox_g_per_min",
        "total_nox_kg_per_hr",
        "total_pm_g_per_min",
        "total_pm_kg_per_hr",
        "total_nmvoc_g_per_min",
        "total_nmvoc_kg_per_hr",
    }
    assert payload["mean_queue_wait_s"] == 2
    assert payload["mean_inference_latency_s"] == 3


def test_flush_all_finalizes_partial_windows_deterministically():
    aggregator = EmissionWindowAggregator(window_seconds=60)
    aggregator.add(_observation(camera_id="camera-b", truck=2))
    aggregator.add(_observation(camera_id="camera-a", car=1))

    completed = aggregator.flush_all()

    assert [item.camera_id for item in completed] == ["camera-a", "camera-b"]
    assert aggregator.preview("camera-a") is None
    assert aggregator.preview("camera-b") is None


def test_observation_requires_aware_timestamp_and_valid_counts():
    with pytest.raises(ValueError, match="timezone-aware"):
        _observation(captured_at=datetime(2026, 8, 21, 12, 0))
    with pytest.raises(ValueError, match="finite and non-negative"):
        _observation(car=-1)
