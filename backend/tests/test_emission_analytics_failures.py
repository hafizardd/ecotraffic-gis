"""Failure and publication contracts independent of external services."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.routes import analytics_emissions
from app.workers import segment_calculation_worker as worker


def test_database_outage_returns_503(monkeypatch):
    class Unavailable:
        async def execute(self, statement):
            raise OperationalError("SELECT", {}, Exception("database unavailable"))
    async def unavailable_db():
        yield Unavailable()
    monkeypatch.setattr(analytics_emissions, "get_db", unavailable_db)
    app = FastAPI()
    app.include_router(analytics_emissions.router)
    response = TestClient(app).get("/api/analytics/emissions/trend")
    assert response.status_code == 503
    assert response.json()["detail"] == "Emission analytics database unavailable"


def test_segment_publish_contains_eight_backend_rates_and_legacy_data(monkeypatch):
    rates = {p: 1.0 for p in ["tsp", "co", "nox", "so2", "hc", "co2", "ch4", "n2o"]}
    payload = {"segment_id": "A", "observed_at": "2026-09-10T00:00:00Z", "processed_at": "2026-09-10T00:00:01Z", "emissions_kg_h": rates}
    monkeypatch.setattr(worker, "serialize_model", lambda *_: dict(payload))
    published = []
    monkeypatch.setattr(worker, "redis_client", SimpleNamespace(publish=lambda *args: published.append(args)))
    store = SimpleNamespace(save=lambda segment, state: state)
    emission = SimpleNamespace(pollutant_totals_g_h={"CO2": 1000},
        calculated_at=datetime.now(timezone.utc), vehicle_count_semantics="interval_count")
    segment = SimpleNamespace(road_segment_id="A", spatial_metadata={})
    worker._publish(segment, emission, store)
    import json
    channel, encoded = published[0]
    message = json.loads(encoded)
    assert channel == "emissions:segment:A"
    assert message["type"] == "segment_update"
    assert message["emissions_kg_h"] == message["data"]["emissions_kg_h"] == rates
    def fail(*args): raise ConnectionError("redis down")
    monkeypatch.setattr(worker, "redis_client", SimpleNamespace(publish=fail))
    # Publishing failure is contained after the durable fact has been committed.
    worker._publish(segment, emission, store)
