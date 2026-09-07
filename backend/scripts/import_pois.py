"""Idempotently import POI features from poi.geojson (CRS84)."""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from geoalchemy2.elements import WKTElement

from app.core.database import get_sync_db
from app.models.spatial_sources import PointOfInterest

GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "poi.geojson"


def _source_key(feature) -> str:
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    if len(coords) >= 2:
        lat = coords[1] if geometry.get("type") == "Point" else None
    identity = "|".join(str(props.get(k)) for k in ("NAMA", "TIPE_1", "TIPE_2", "TIPE_3", "KATEGORI"))
    seed = f"{identity}|{json.dumps(coords[:2], separators=(',', ':'))}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def _lonlat(coords) -> tuple[float, float] | None:
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


def import_pois() -> dict:
    inserted = updated = rejected = 0
    categories = Counter()
    with get_sync_db() as db:
        data = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
        features = data.get("features", [])
        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Point":
                rejected += 1
                continue
            coords = _lonlat(geometry.get("coordinates"))
            if coords is None:
                rejected += 1
                continue
            lon, lat = coords
            key = _source_key(feature)
            category = props.get("KATEGORI")
            if category:
                categories[category] += 1
            values = {
                "name": props.get("NAMA"),
                "category": category,
                "type_1": props.get("TIPE_1"),
                "type_2": props.get("TIPE_2"),
                "type_3": props.get("TIPE_3"),
                "address": props.get("ALAMAT"),
                "geometry": WKTElement(f"POINT({lon} {lat})", srid=4326),
                "source": "poi.geojson",
                "source_metadata": {"source_file": "poi.geojson", "properties": props},
            }
            existing = db.query(PointOfInterest).filter_by(source_key=key).one_or_none()
            if existing is None:
                db.add(PointOfInterest(source_key=key, **values))
                inserted += 1
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
                updated += 1
    print(f"points_of_interest: features={len(features)} inserted={inserted} updated={updated} rejected={rejected}")
    print("category_distribution:", json.dumps(dict(categories), ensure_ascii=False))
    return {"inserted": inserted, "updated": updated, "rejected": rejected, "features": len(features), "category_distribution": dict(categories)}


if __name__ == "__main__":
    import_pois()
