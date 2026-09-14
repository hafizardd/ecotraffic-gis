import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from app.observability.http import MetricsMiddleware
from app.observability.logging import JsonFormatter, request_id
from app.observability import browser


def value(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {}) or 0


def test_routes_bounded_request_ids_generated():
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)
    @app.get('/items/{item_id}')
    async def item(item_id: str):
        return {'ok': True}
    client = TestClient(app)
    labels = {'method': 'GET', 'route': '/items/{item_id}', 'status': '200'}
    before = value('eco_http_requests_total', labels)
    response = client.get('/items/private-id?token=secret', headers={'X-Request-ID': 'untrusted'})
    assert len(response.headers['x-request-id']) == 32
    assert value('eco_http_requests_total', labels) == before + 1
    client.get('/unknown/private-id')
    assert value('eco_http_requests_total', {'method': 'GET', 'route': 'unmatched', 'status': '404'}) >= 1
    assert value('eco_http_inflight') == 0


@pytest.mark.asyncio
async def test_stream_forwarded_before_completion_and_cancel_cleanup():
    sent, first, release = [], asyncio.Event(), asyncio.Event()
    async def app(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'multipart/x-mixed-replace')]})
        await send({'type': 'http.response.body', 'body': b'frame', 'more_body': True})
        await release.wait()
    async def send(message):
        sent.append(message)
        if message['type'] == 'http.response.body':
            first.set()
    async def receive():
        return {'type': 'http.request'}
    before = value('eco_http_duration_seconds_count', {'method': 'GET', 'route': 'unmatched'})
    task = asyncio.create_task(MetricsMiddleware(app)({'type': 'http', 'path': '/stream', 'method': 'GET'}, receive, send))
    await asyncio.wait_for(first.wait(), 1)
    assert sent[-1]['body'] == b'frame' and not task.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert value('eco_http_inflight') == 0
    assert value('eco_http_duration_seconds_count', {'method': 'GET', 'route': 'unmatched'}) == before


def test_json_log_preserves_extras_redacts_credentials():
    record = logging.makeLogRecord({'msg': 'request_failed', 'levelname': 'ERROR', 'camera_id': 'camera-1', 'nested': {'token': 'secret'}})
    token = request_id.set('abc')
    try:
        data = json.loads(JsonFormatter().format(record))
    finally:
        request_id.reset(token)
    assert data['request_id'] == 'abc'
    assert data['camera_id'] == 'camera-1'
    assert data['nested']['token'] == '[REDACTED]'


def test_browser_validation_limits_metrics(monkeypatch):
    monkeypatch.setenv('BROWSER_TELEMETRY_ENABLED', 'true')
    monkeypatch.setenv('CORS_ORIGINS', 'https://eco.example')
    monkeypatch.setattr(browser, '_tokens', 60)
    monkeypatch.setattr(browser, '_updated', time.monotonic())
    app = FastAPI()
    app.include_router(browser.router)
    client = TestClient(app)
    headers = {'Origin': 'https://eco.example'}
    event = {'name': 'fetch_body', 'route': 'cameras', 'outcome': 'ok', 'duration_ms': 250}
    labels = {'name': 'fetch_body', 'route': 'cameras', 'outcome': 'ok'}
    before = value('eco_browser_events_total', labels)
    assert client.post('/api/telemetry', json={'events': [event]}, headers=headers).status_code == 204
    assert value('eco_browser_events_total', labels) == before + 1
    assert client.post('/api/telemetry', json={'events': [event]}).status_code == 403
    assert client.post('/api/telemetry', json={'events': [{**event, 'route': '/secret-user-id'}]}, headers=headers).status_code == 422
    assert client.post('/api/telemetry', json={'events': [event] * 21}, headers=headers).status_code == 422
    assert client.post('/api/telemetry', content='x' * 8193, headers=headers).status_code == 413
    monkeypatch.setattr(browser, '_tokens', 0)
    assert client.post('/api/telemetry', json={'events': [event]}, headers=headers).status_code == 429


def test_prefork_metrics_visible_in_parent(tmp_path):
    env = {**os.environ, 'PROMETHEUS_MULTIPROC_DIR': str(tmp_path)}
    child = "from app.observability.celery import before, after; from types import SimpleNamespace; before(task_id='example'); after(task_id='example', task=SimpleNamespace(name='test.task'), state='SUCCESS')"
    subprocess.run([sys.executable, '-c', child], env=env, check=True)
    result = subprocess.check_output([sys.executable, '-c', 'from app.observability.metrics import registry; from prometheus_client import generate_latest; print(generate_latest(registry()).decode())'], env=env, text=True)
    assert 'eco_worker_tasks_total{state="SUCCESS",task="test.task"} 1.0' in result
    assert 'eco_worker_tasks_active 0.0' in result


@pytest.mark.asyncio
async def test_mjpeg_error_and_cleanup(monkeypatch):
    from app.api.routes import cameras
    class DB:
        async def execute(self, query):
            return SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(is_active=True))
    class Redis:
        calls, closed = 0, False
        def get(self, key):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError('unavailable')
            return b'jpeg'
        def close(self):
            self.closed = True
    redis = Redis()
    monkeypatch.setattr(cameras.redis.Redis, 'from_url', lambda *a, **k: redis)
    async def no_sleep(_):
        pass
    monkeypatch.setattr(cameras.asyncio, 'sleep', no_sleep)
    before = value('eco_video_errors_total', {'kind': 'mjpeg', 'reason': 'redis'})
    response = await cameras.get_tracked_stream('camera-1', DB())
    frame = await anext(response.body_iterator)
    assert b'jpeg' in frame
    assert value('eco_video_errors_total', {'kind': 'mjpeg', 'reason': 'redis'}) == before + 1
    await response.body_iterator.aclose()
    assert redis.closed and value('eco_video_active', {'kind': 'mjpeg'}) == 0


def test_database_query_metrics_success_and_failure():
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    from app.observability.database import instrument_engine
    engine = create_engine('sqlite://')
    instrument_engine(engine, 'unit')
    labels = {'database': 'unit'}
    count = value('eco_db_query_seconds_count', labels)
    errors = value('eco_db_errors_total', labels)
    with engine.connect() as conn:
        assert conn.execute(text('select 1')).scalar() == 1
        with pytest.raises(OperationalError):
            conn.execute(text('select * from missing_table'))
    engine.dispose()
    assert value('eco_db_query_seconds_count', labels) == count + 2
    assert value('eco_db_errors_total', labels) == errors + 1
