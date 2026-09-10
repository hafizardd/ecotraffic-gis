"""Actual PostgreSQL JSONB/DISTINCT/AVG and HTTP/export contracts.

Set ANALYTICS_TEST_DATABASE_URL to a disposable PostgreSQL database. Each test
owns a unique schema. Spatial columns are irrelevant to these analytics queries;
minimal road/camera tables let the suite run without installing PostGIS.
"""
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import os
import uuid

from fastapi import FastAPI
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.routes.analytics_emissions import analytics_db, router
from app.models.segment_emission import SegmentEmission
from cv.proposal_emission_factors import POLLUTANTS, VEHICLE_CATEGORIES

URL = os.getenv("ANALYTICS_TEST_DATABASE_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="ANALYTICS_TEST_DATABASE_URL is not configured")]
BASE = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def api():
    schema = "analytics_test_" + uuid.uuid4().hex
    engine = create_async_engine(URL, connect_args={"server_settings": {"search_path": schema + ",public"}})
    ids = {name: uuid.uuid4() for name in ["A", "B", "camera"]}
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text("CREATE TABLE road_segments (id UUID PRIMARY KEY, road_segment_id VARCHAR(100), name VARCHAR(255), spatial_metadata JSONB)"))
        await conn.execute(text("CREATE TABLE cameras (id UUID PRIMARY KEY, is_active BOOLEAN)"))
        await conn.execute(text("CREATE TABLE camera_road_segments (road_segment_id UUID, camera_id UUID, is_active BOOLEAN)"))
        await conn.run_sync(SegmentEmission.__table__.create)
        await conn.execute(text("INSERT INTO cameras VALUES (:id, true)"), {"id": ids["camera"]})
        for name in ["A", "B"]:
            await conn.execute(text("INSERT INTO road_segments VALUES (:id, :name, :label, CAST(:metadata AS jsonb))"),
                {"id": ids[name], "name": name, "label": f"Segment {name}", "metadata": json.dumps({"corridor_id": "C", "corridor_name": "Corridor C"})})
            await conn.execute(text("INSERT INTO camera_road_segments VALUES (:segment, :camera, true)"), {"segment": ids[name], "camera": ids["camera"]})
        for name, minute, kg, version, source in [("A", 0, 999, 1, "LIVE"), ("A", 0, 1, 2, "LIVE"),
                ("A", 1, 3, 2, "LIVE"), ("B", 0, 10, 2, "LIVE"), ("B", 2, 9999, 2, "SYNTHETIC")]:
            start = BASE + timedelta(minutes=minute)
            await conn.execute(insert(SegmentEmission).values(
                id=uuid.uuid4(), road_segment_id=ids[name], period_start=start, period_end=start + timedelta(minutes=1),
                calculated_at=start + timedelta(minutes=1, seconds=2), calculation_version=version,
                observation_duration_seconds=60, aggregation_policy="sum_independent_streams",
                source_cameras=["camera"], source_streams=["main"], source_observation_count=1,
                vehicle_count_semantics="interval_count", raw_counts={c: 1 for c in VEHICLE_CATEGORIES},
                volume_per_hour={c: 60 for c in VEHICLE_CATEGORIES}, vkt_km_h={c: 30 for c in VEHICLE_CATEGORIES},
                pollutant_totals_g_h={p: kg * 1000 for p in POLLUTANTS}, category_pollutant_breakdown_g_h={},
                raw_criteria={}, ahp_metadata={"source_mode": source, "calculation_mode": "flow_based_segment"},
            ))
    app = FastAPI()
    app.include_router(router)
    async def session():
        async with AsyncSession(engine) as db:
            yield db
    app.dependency_overrides[analytics_db] = session
    params = {"from": BASE.isoformat(), "to": (BASE + timedelta(hours=1)).isoformat()}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client, params, engine
    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await engine.dispose()


async def test_trend_averages_samples_per_segment_and_keeps_both_segments(api):
    client, params, _ = api
    response = await client.get("/api/analytics/emissions/trend", params={**params, "bucket": "1h"})
    assert response.status_code == 200, response.text
    point = response.json()["data"][0]
    for p in POLLUTANTS:
        assert point[f"{p.lower()}_kg_h"] == 12  # mean(A=1,3) + mean(B=10)
    assert point["segment_count"] == 2
    assert point["sample_count"] == 3  # excludes old version and synthetic sample
    filtered = (await client.get("/api/analytics/emissions/trend", params={**params, "bucket": "1h", "segment_id": "A"})).json()
    assert filtered["data"][0]["co2_kg_h"] == 2


async def test_top_composition_and_corridor_filter_agree(api):
    client, params, _ = api
    top = await client.get("/api/analytics/emissions/top-corridors", params={**params, "corridor_id": "C"})
    assert top.status_code == 200, top.text
    row = top.json()["data"][0]
    assert row["emission_kg_h"] == 12
    assert row["sample_count"] == 3
    assert set(row["segment_ids"]) == {"A", "B"}
    assert row["pollutant"] == "co2"
    composition = (await client.get("/api/analytics/emissions/composition", params=params)).json()
    assert len(composition["data"]) == 8
    assert all(p["kg_h"] == 12 for p in composition["data"])


async def test_latest_has_eight_pollutants_and_actual_freshness(api):
    client, params, _ = api
    response = await client.get("/api/analytics/emissions/latest", params=params)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["segments"]) == 2
    assert data["summary"]["emissions_kg_h"]["co2"] == 13
    for row in data["segments"]:
        assert set(row["emissions_kg_h"]) == {p.lower() for p in POLLUTANTS}
        assert row["freshness_seconds"] >= 0
        assert row["processed_at"] and row["observed_at"]
        assert row["calculation_version"] == 2


async def test_history_pagination_and_exports_use_identical_facts(api):
    client, params, _ = api
    response = await client.get("/api/analytics/emissions/history", params={**params, "page_size": 1})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 3
    assert len(response.json()["data"]) == 1
    exported = await client.get("/api/analytics/emissions/export", params={**params, "format": "json"})
    assert exported.status_code == 200, exported.text
    records = exported.json()["data"]
    assert len(records) == 3
    assert records[0] == response.json()["data"][0] or records[0]["id"] == response.json()["data"][0]["id"]
    csv_response = await client.get("/api/analytics/emissions/export", params={**params, "format": "csv"})
    assert csv_response.status_code == 200, csv_response.text
    rows = list(csv.DictReader(io.StringIO(csv_response.text.lstrip("\ufeff"))))
    assert len(rows) == 3
    assert float(rows[0]["co2_kg_h"]) == records[0]["emissions_kg_h"]["co2"]
    assert float(rows[0]["car_vehicles_h"]) == records[0]["volume_per_hour"]["car"]


async def test_vehicle_analytics_are_aggregated_server_side(api):
    client, params, _ = api
    response = await client.get("/api/analytics/emissions/vehicles", params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body["totals"]) == {"car", "motorcycle", "bus", "truck"}
    assert body["totals"]["car"] == 120  # mean(A=60) + mean(B=60), synthetic excluded
    assert body["composition"][0]["share"] == 0.25
    assert [row["key"] for row in body["composition"]] == ["car", "motorcycle", "bus", "truck"]
    assert len(body["ranking"]) == 2
    assert body["ranking"][0]["total_veh_h"] == 240  # four categories x 60 per segment
    assert body["vkt"]["car"] == 60
    assert body["series"][0]["car_veh_h"] == 120


async def test_empty_ranges_and_invalid_inputs(api):
    client, params, _ = api
    for extra, expected in [({"from": params["to"], "to": params["from"]}, 422), ({"from": "bad-date"}, 422),
            ({"from": "2026-09-10T00:00:00"}, 422), ({"segment_id": "missing"}, 404),
            ({"corridor_id": "missing"}, 404), ({"bucket": "invalid"}, 422)]:
        response = await client.get("/api/analytics/emissions/trend", params={**params, **extra})
        assert response.status_code == expected, response.text
    empty = {"from": (BASE + timedelta(days=1)).isoformat(), "to": (BASE + timedelta(days=2)).isoformat()}
    assert (await client.get("/api/analytics/emissions/history", params=empty)).json()["total"] == 0
    assert (await client.get("/api/analytics/emissions/trend", params=empty)).json()["data"] == []
    assert (await client.get("/api/analytics/emissions/composition", params=empty)).json()["sample_count"] == 0
