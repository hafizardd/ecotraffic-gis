"""Segment observation writes from the tracking worker (LIVE/track cameras)."""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.segment_mapping import CameraSegmentMapping
from app.workers import tracking_worker


CAPTURED_AT = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)
MAPPING = CameraSegmentMapping("atcs_jlagran", "SEG-0022", "main")
OCCUPANCY = {"car": 2, "motorcycle": 5, "bus": 0, "truck": 1}


class FakeSession:
    def __init__(self, segment_id, fail=False):
        self.segment_id = segment_id
        self.fail = fail
        self.added = []
        self.executed = 0

    def execute(self, *args, **kwargs):
        self.executed += 1
        return SimpleNamespace(scalar_one=lambda: SimpleNamespace(id=self.segment_id))

    def add(self, row):
        self.added.append(row)

    def flush(self):
        if self.fail:
            raise RuntimeError("db down")


@contextmanager
def fake_db(session):
    yield session


def _patch(monkeypatch, session):
    monkeypatch.setattr(tracking_worker, "_load_segment_mappings_cached", lambda: [MAPPING])
    monkeypatch.setattr(tracking_worker, "get_sync_db", lambda: fake_db(session))


def test_persist_writes_flow_observation_with_measured_duration(monkeypatch):
    segment_id = uuid.uuid4()
    session = FakeSession(segment_id)
    _patch(monkeypatch, session)

    status = tracking_worker._persist_segment_flow(
        "atcs_jlagran", str(uuid.uuid4()), OCCUPANCY, CAPTURED_AT, 60.5
    )

    assert status == "observation_stored"
    assert len(session.added) == 1
    row = session.added[0]
    assert row.camera_identifier == "atcs_jlagran"
    assert row.lane_or_stream_id == "main"
    assert row.road_segment_id == segment_id
    assert row.vehicle_count_semantics == "interval_count"
    assert row.observation_duration_seconds == 60.5
    assert row.raw_detected_count == {"car": 2.0, "motorcycle": 5.0, "bus": 0.0, "truck": 1.0}


def test_persist_zero_flow_still_writes(monkeypatch):
    session = FakeSession(uuid.uuid4())
    _patch(monkeypatch, session)

    status = tracking_worker._persist_segment_flow(
        "atcs_jlagran", str(uuid.uuid4()),
        {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}, CAPTURED_AT, 60,
    )

    assert status == "observation_stored"
    assert len(session.added) == 1


def test_persist_without_mapping_skips_db(monkeypatch):
    monkeypatch.setattr(tracking_worker, "_load_segment_mappings_cached", lambda: [])
    called = []
    monkeypatch.setattr(tracking_worker, "get_sync_db", lambda: called.append(True) or fake_db(FakeSession(uuid.uuid4())))

    status = tracking_worker._persist_segment_flow(
        "unknown_cam", str(uuid.uuid4()), OCCUPANCY, CAPTURED_AT, 60
    )

    assert status == "no_mapping"
    assert called == []


def test_persist_db_failure_returns_failed(monkeypatch):
    session = FakeSession(uuid.uuid4(), fail=True)
    _patch(monkeypatch, session)

    status = tracking_worker._persist_segment_flow(
        "atcs_jlagran", str(uuid.uuid4()), OCCUPANCY, CAPTURED_AT, 60
    )

    assert status == "failed"
