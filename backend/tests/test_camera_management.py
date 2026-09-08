from contextlib import contextmanager
from types import SimpleNamespace
import uuid

from app.services import camera_management


class _FakeResult:
    def __init__(self, camera):
        self.camera = camera

    def scalars(self):
        return self

    def first(self):
        return self.camera


class _FakeSession:
    def __init__(self, camera):
        self.camera = camera
        self.executed = False

    def execute(self, _statement):
        self.executed = True
        return _FakeResult(self.camera)


def _install_fake_database(monkeypatch, camera):
    session = _FakeSession(camera)

    @contextmanager
    def fake_get_sync_db():
        yield session

    monkeypatch.setattr(camera_management, "get_sync_db", fake_get_sync_db)
    return session


def test_get_active_camera_source_returns_detached_processing_data(monkeypatch):
    database_id = uuid.uuid4()
    record = SimpleNamespace(
        id=database_id,
        camera_id="camera-12",
        stream_url="https://example.test/camera-12/playlist.m3u8",
        referer="https://example.test/",
        is_active=True,
    )
    session = _install_fake_database(monkeypatch, record)

    source = camera_management.get_active_camera_source("camera-12")

    assert session.executed is True
    assert source == camera_management.CameraSource(
        id=database_id,
        camera_id="camera-12",
        stream_url="https://example.test/camera-12/playlist.m3u8",
        referer="https://example.test/",
    )


def test_get_active_camera_source_rejects_inactive_camera(monkeypatch):
    record = SimpleNamespace(
        id=uuid.uuid4(),
        camera_id="camera-12",
        stream_url="https://example.test/camera-12/playlist.m3u8",
        referer=None,
        is_active=False,
    )
    _install_fake_database(monkeypatch, record)

    assert camera_management.get_active_camera_source("camera-12") is None


def test_get_active_camera_source_returns_none_when_missing(monkeypatch):
    _install_fake_database(monkeypatch, None)

    assert camera_management.get_active_camera_source("missing") is None
