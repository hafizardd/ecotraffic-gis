"""Idempotently import population zones from populations.geojson (CRS84)."""

import json
import sys
from pathlib import Path

from geoalchemy2.elements import WKTElement

from app.core.database import get_sync_db
from app.models.spatial_sources import PopulationZone

GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "populations.geojson"
EXPECTED_ZONES = 14


def _multipolygon_wkt(geometry) -> str:
    coords = geometry.get("coordinates") or []
    polygons = []
    for poly in coords:
        rings = []
        for ring in poly:
            points = ", ".join(f"{c[0]} {c[1]}" for c in ring)
            rings.append(f"({points})")
        polygons.append("(" + ",".join(rings) + ")")
    return "MULTIPOLYGON(" + ",".join(polygons) + ")"


def import_population() -> dict:
    inserted = updated = rejected = 0
    total_population = 0
    with get_sync_db() as db:
        data = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
        features = data.get("features", [])
        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            district = (props.get("WADMKC") or "").strip()
            population = props.get("Penduduk")
            if not district or population is None or geometry.get("type") != "MultiPolygon":
                print(f"invalid population zone: {district!r}", file=sys.stderr)
                rejected += 1
                continue
            key = f"populations.geojson:{district}"
            try:
                pop_int = int(population)
            except (TypeError, ValueError):
                rejected += 1
                continue
            total_population += pop_int
            values = {
                "district_name": district,
                "population": pop_int,
                "geometry": WKTElement(_multipolygon_wkt(geometry), srid=4326),
                "source": "populations.geojson",
                "reference_year": props.get("reference_year"),
                "source_metadata": {"source_file": "populations.geojson", "properties": props},
            }
            existing = db.query(PopulationZone).filter_by(source_key=key).one_or_none()
            if existing is None:
                db.add(PopulationZone(source_key=key, **values))
                inserted += 1
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
                updated += 1
    print(f"population_zones: features={len(features)} inserted={inserted} updated={updated} rejected={rejected} total_population={total_population}")
    return {"inserted": inserted, "updated": updated, "rejected": rejected, "zones": len(features), "total_population": total_population}


if __name__ == "__main__":
    import_population()
