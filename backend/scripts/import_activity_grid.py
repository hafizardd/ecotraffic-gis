"""Idempotently import the offline AHP activity-potential hex grid.

Imports ``data/activity_grid.geojson`` verbatim (keyed by ``hex_id``); the AHP
score is NOT recomputed here so a routine re-import can never silently change
the classification. Use ``--verify`` to check the stored score against the
three normalized inputs and the versioned hex weights.
"""

import argparse
import json
import sys
from pathlib import Path

from geoalchemy2.elements import WKTElement

from app.core.database import get_sync_db
from app.models.activity_grid import ActivityGridHex

GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "activity_grid.geojson"
AHP_WEIGHT_VERSION = "hex-ahp-v1"
SOURCE = "Skoring_Grid_Potensi_Timbulan_Kemacetan.xlsx"
# From the 'AHP Bobot' Saaty matrix (CR = 0.0096).
HEX_AHP_WEIGHTS = {"volume": 0.5390, "poi": 0.2973, "penduduk": 0.1638}
EPSILON = 0.01
POI_CATEGORIES = {
    "Pariwisata": "poi_pariwisata", "Pendidikan": "poi_pendidikan", "Perdagangan": "poi_perdagangan",
    "Peribadatan": "poi_peribadatan", "Perkantoran": "poi_perkantoran", "Transportasi": "poi_transportasi",
    "Kesehatan": "poi_kesehatan", "Kuliner": "poi_kuliner",
}


def _polygon_wkt(geometry) -> str:
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        rings = ", ".join("(" + ", ".join(f"{c[0]} {c[1]}" for c in ring) + ")" for ring in coords)
        return "POLYGON(" + rings + ")"
    polygons = []
    for poly in coords:
        holes = ", ".join("(" + ", ".join(f"{c[0]} {c[1]}" for c in ring) + ")" for ring in poly)
        polygons.append("(" + holes + ")")
    return "MULTIPOLYGON(" + ", ".join(polygons) + ")"


def _verify(props: dict) -> float:
    expected = (
        HEX_AHP_WEIGHTS["volume"] * float(props["norm_volume"])
        + HEX_AHP_WEIGHTS["poi"] * float(props["norm_poi"])
        + HEX_AHP_WEIGHTS["penduduk"] * float(props["norm_penduduk"])
    )
    stored = float(props["skor_total_ahp"])
    if abs(expected - stored) > EPSILON:
        raise ValueError(f"hex_id={props['hex_id']} score drift: stored={stored} recomputed={expected}")
    return expected


def import_activity_grid(verify: bool = False) -> dict:
    inserted = updated = rejected = 0
    with get_sync_db() as db:
        data = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
        features = data.get("features", [])
        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            try:
                hex_id = int(props["hex_id"])
            except (KeyError, TypeError, ValueError):
                rejected += 1
                continue
            if verify:
                try:
                    _verify(props)
                except (KeyError, TypeError, ValueError) as error:
                    print(f"verify failed: {error}", file=sys.stderr)
                    raise
            values = {
                "geometry": WKTElement(_polygon_wkt(geometry), srid=4326),
                "luas_km2": float(props["luas_km2"]),
                "poi_total": int(props["poi_total"]),
                "poi_breakdown": {category: int(props.get(key, 0) or 0) for category, key in POI_CATEGORIES.items()},
                "penduduk": int(props["penduduk"]),
                "volume_mean": float(props["volume_mean"]),
                "norm_volume": float(props["norm_volume"]),
                "norm_poi": float(props["norm_poi"]),
                "norm_penduduk": float(props["norm_penduduk"]),
                "skor_total_ahp": float(props["skor_total_ahp"]),
                "ranking": int(props["ranking"]),
                "klasifikasi_potensi": str(props["klasifikasi_potensi"]),
                "ahp_weight_version": AHP_WEIGHT_VERSION,
                "source": SOURCE,
            }
            existing = db.query(ActivityGridHex).filter_by(hex_id=hex_id).one_or_none()
            if existing is None:
                db.add(ActivityGridHex(hex_id=hex_id, **values))
                inserted += 1
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
                updated += 1
    print(f"activity_grid_hexes: features={len(features)} inserted={inserted} updated={updated} rejected={rejected} verify={verify}")
    return {"inserted": inserted, "updated": updated, "rejected": rejected, "features": len(features)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="recompute skor_total_ahp from normalized inputs and fail on drift")
    import_activity_grid(verify=parser.parse_args().verify)
