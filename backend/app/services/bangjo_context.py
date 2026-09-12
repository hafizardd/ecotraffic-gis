"""Assemble the real, evidence-grounded context object Bang Jo narrates.

Every field is a real query. Missing pieces stay ``None``/empty - nothing is
fabricated - matching the existing ``_empty_result()``/``"status": "pending"``
convention.
"""

from datetime import datetime, timedelta, timezone
from collections import Counter

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_grid import ActivityGridHex
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.models.spatial_sources import SurveyStopObservation
from app.services.emission_analytics import source_mode_expression
from app.services.hex_activity_scoring import hour_scores, profile_hour
from app.services.segment_estimate import OBSERVED, build_display_fact, build_display_facts
from app.services.spatial_integration import K4_BUFFER_M
from cv.proposal_emission_factors import POLLUTANTS

_geog = Geography(srid=4326)
HIGH_POTENTIAL = ("Sangat Tinggi", "Tinggi")
WEAK_CLASSES = ("Rendah", "Sangat Rendah")
DOMINANT_POI_LIMIT = 5
REPLAY_WINDOW_HOURS = 24
OVERVIEW_TOP_LIMIT = 10
OVERVIEW_BOTTOM_LIMIT = 5
OVERVIEW_INTERVENTION_LIMIT = 20
BUS_STOP_RANKING_LIMIT = 5
INTERVENTION_LABELS = {
    "add_new_stop": "tambah halte baru",
    "improve_existing_stop": "perbaiki halte yang ada",
    "increase_frequency": "tambah frekuensi layanan",
}


def _hourly_point(emission: SegmentEmission) -> dict:
    """One precomputed REPLAY hour, interpolation flags included."""
    metadata = emission.ahp_metadata or {}
    calc_meta = metadata.get("calculation_metadata") or {}
    totals = emission.pollutant_totals_g_h or {}
    return {
        "hour": emission.period_start.isoformat(),
        "emissions_kg_h": {
            pollutant.lower(): (totals[pollutant] / 1000 if totals.get(pollutant) is not None else None)
            for pollutant in POLLUTANTS
        },
        "volume_per_hour": emission.volume_per_hour,
        "is_interpolated": bool(calc_meta.get("is_interpolated")),
        "interpolation_method": calc_meta.get("interpolation_method"),
    }


async def _profile_anchor(db: AsyncSession) -> datetime | None:
    """Newest static-profile bucket, or the newest real sample as fallback.

    The precomputed REPLAY profile is a completed collection, so its window must
    be anchored to the data, not to wall-clock ``now()``; otherwise the profile
    ages out of any rolling 24h read.
    """
    anchor = (await db.execute(
        select(func.max(SegmentEmission.period_start)).where(
            SegmentEmission.ahp_metadata["source_mode"].astext == "REPLAY")
    )).scalar_one_or_none()
    if anchor is not None:
        return anchor
    return (await db.execute(
        select(func.max(SegmentEmission.period_start)).where(source_mode_expression().notin_(["SYNTHETIC"]))
    )).scalar_one_or_none()


async def build_context(db: AsyncSession, road_segment_id: str) -> dict | None:
    segment = (
        await db.execute(select(RoadSegment).where(RoadSegment.road_segment_id == road_segment_id))
    ).scalar_one_or_none()
    if segment is None:
        return None
    display = await build_display_fact(db, road_segment_id)
    emission = display.emission if display else None

    segment_geom = select(RoadSegment.geometry).where(RoadSegment.road_segment_id == road_segment_id).scalar_subquery()
    hexes = (
        await db.execute(select(ActivityGridHex).where(func.ST_Intersects(ActivityGridHex.geometry, segment_geom)))
    ).scalars().all()

    stop_rows = (
        await db.execute(
            select(
                SurveyStopObservation,
                func.ST_Distance(cast(segment_geom, _geog), cast(SurveyStopObservation.geometry, _geog)).label("distance_m"),
            )
            .where(func.ST_DWithin(cast(segment_geom, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M))
        )
    ).all()

    dominant = {}
    for hex_cell in hexes:
        for category, count in (hex_cell.poi_breakdown or {}).items():
            dominant[category] = dominant.get(category, 0) + int(count)
    dominant_sorted = sorted(dominant.items(), key=lambda item: item[1], reverse=True)[:DOMINANT_POI_LIMIT]

    no_stop_near_high_hex = ~(
        select(SurveyStopObservation.id)
        .where(
            func.ST_DWithin(
                cast(ActivityGridHex.geometry, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M
            )
        )
        .exists()
    )
    gap_count = (
        await db.execute(
            select(func.count())
            .select_from(ActivityGridHex)
            .where(
                ActivityGridHex.klasifikasi_potensi.in_(HIGH_POTENTIAL),
                func.ST_Intersects(ActivityGridHex.geometry, segment_geom),
                no_stop_near_high_hex,
            )
        )
    ).scalar() or 0

    scores = [hex_cell.skor_total_ahp for hex_cell in hexes]
    primary_hex = max(hexes, key=lambda hex_cell: hex_cell.skor_total_ahp) if hexes else None
    activity_potential = {
        "hex_count": len(hexes),
        "hex_ids": [hex_cell.hex_id for hex_cell in hexes],
        "avg_skor_total_ahp": round(sum(scores) / len(scores), 4) if scores else None,
        "max_skor_total_ahp": max(scores) if scores else None,
        "klasifikasi_potensi": sorted({hex_cell.klasifikasi_potensi for hex_cell in hexes}) or None,
        "dominant_poi_categories": [{"category": category, "count": count} for category, count in dominant_sorted],
    }

    stop_classes = [stop.intervention_class for stop, _ in stop_rows if stop.intervention_class]
    stop_scores = [getattr(stop, "ahp_total_score", None) for stop, _ in stop_rows]
    stop_scores = [score for score in stop_scores if score is not None]
    weak_stop_count = sum(1 for label in stop_classes if label in WEAK_CLASSES)
    activity_class = primary_hex.klasifikasi_potensi if primary_hex else None
    coverage_gap = bool(gap_count)
    if coverage_gap:
        intervention_hint = "add_new_stop"
    elif weak_stop_count:
        intervention_hint = "improve_existing_stop"
    elif activity_class in HIGH_POTENTIAL:
        intervention_hint = "increase_frequency"
    else:
        intervention_hint = None
    stop_assessment = {
        "count": len(stop_rows),
        "scored_count": len(stop_scores),
        "class_counts": dict(Counter(stop_classes)),
        "weak_stop_count": weak_stop_count,
        "min_ahp_total_score": round(min(stop_scores), 4) if stop_scores else None,
        "avg_ahp_total_score": round(sum(stop_scores) / len(stop_scores), 4) if stop_scores else None,
    }

    anchor = await _profile_anchor(db)
    replay_window_start = (
        anchor - timedelta(hours=REPLAY_WINDOW_HOURS - 1)
        if anchor is not None
        else datetime.now(timezone.utc) - timedelta(hours=REPLAY_WINDOW_HOURS)
    )
    series_segment_db_id = emission.road_segment_id if emission is not None else segment.id
    replay_rows = (
        await db.execute(
            select(SegmentEmission)
            .where(
                SegmentEmission.road_segment_id == series_segment_db_id,
                SegmentEmission.ahp_metadata["source_mode"].astext == "REPLAY",
                SegmentEmission.period_start >= replay_window_start,
            )
            .order_by(SegmentEmission.period_start)
        )
    ).scalars().all()
    hourly_series = [_hourly_point(emission) for emission in replay_rows]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segment": {
            "road_segment_id": segment.road_segment_id, "name": segment.name, "length_km": segment.length_km,
            "activity_class": activity_class,
            "activity_score": primary_hex.skor_total_ahp if primary_hex else None,
            "pollutant_totals": emission.pollutant_totals_g_h if emission else None,
            "data_source": emission.vehicle_count_semantics if emission else None,
            "observed_at": emission.period_end.isoformat() if emission else None,
            "data_status": display.data_status if display else "unavailable",
            "is_estimated": bool(display and display.data_status != OBSERVED),
            "borrowed_from": display.borrowed_from if display else None,
            "is_static": bool(display and display.is_static),
            "is_interpolated": bool(display and display.is_interpolated),
        },
        "hourly_series": hourly_series,
        "activity_potential": activity_potential,
        "bus_stops": [
            {
                "source_id": stop.source_id, "title": stop.title, "intervention_class": stop.intervention_class,
                "intervention_rank": stop.intervention_rank, "accessibility_score": stop.accessibility_score,
                "facility_score": stop.facility_score, "environment_score": stop.environment_score,
                "distance_to_segment_m": round(float(distance), 1) if distance is not None else None,
            }
            for stop, distance in stop_rows
        ],
        "stop_assessment": stop_assessment,
        "coverage_gap": coverage_gap,
        "intervention_hint": intervention_hint,
    }


def _totals_kg_h(totals: dict | None) -> tuple[dict, float | None]:
    """Per-pollutant kg/h plus their sum; absent pollutants stay ``None``."""
    values = {
        pollutant.lower(): (totals[pollutant] / 1000 if totals and totals.get(pollutant) is not None else None)
        for pollutant in POLLUTANTS
    }
    present = [value for value in values.values() if value is not None]
    return values, (sum(present) if present else None)


async def _activity_by_segment(db: AsyncSession) -> dict:
    """Highest-scoring intersecting hex per segment -> (score, classification)."""
    rows = (
        await db.execute(
            select(
                RoadSegment.road_segment_id,
                ActivityGridHex.skor_total_ahp,
                ActivityGridHex.klasifikasi_potensi,
            )
            .join(ActivityGridHex, func.ST_Intersects(RoadSegment.geometry, ActivityGridHex.geometry))
            .distinct(RoadSegment.road_segment_id)
            .order_by(RoadSegment.road_segment_id, ActivityGridHex.skor_total_ahp.desc())
        )
    ).all()
    return {segment_id: (score, label) for segment_id, score, label in rows}


async def _coverage_gap_by_segment(db: AsyncSession) -> dict:
    """Count of high-potential hexes intersecting a segment with no stop nearby."""
    no_stop_near_high_hex = ~(
        select(SurveyStopObservation.id)
        .where(
            func.ST_DWithin(
                cast(ActivityGridHex.geometry, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M
            )
        )
        .exists()
    )
    rows = (
        await db.execute(
            select(RoadSegment.road_segment_id, func.count())
            .join(ActivityGridHex, func.ST_Intersects(RoadSegment.geometry, ActivityGridHex.geometry))
            .where(ActivityGridHex.klasifikasi_potensi.in_(HIGH_POTENTIAL), no_stop_near_high_hex)
            .group_by(RoadSegment.road_segment_id)
        )
    ).all()
    return {segment_id: count for segment_id, count in rows}


async def _weak_stops_by_segment(db: AsyncSession) -> dict:
    """Count of weak-class surveyed stops within the K4 buffer of each segment."""
    rows = (
        await db.execute(
            select(RoadSegment.road_segment_id, func.count())
            .join(
                SurveyStopObservation,
                func.ST_DWithin(
                    cast(RoadSegment.geometry, _geog), cast(SurveyStopObservation.geometry, _geog), K4_BUFFER_M
                ),
            )
            .where(SurveyStopObservation.intervention_class.in_(WEAK_CLASSES))
            .group_by(RoadSegment.road_segment_id)
        )
    ).all()
    return {segment_id: count for segment_id, count in rows}


async def build_overview_context(db: AsyncSession) -> dict:
    """Compact whole-dataset context: one aggregate row per corridor.

    Four grouped queries regardless of corridor count (no per-segment loop).
    Sorted by latest total emission descending, so ranking and "normal" questions
    are answerable from the same list. Intervention fields mirror
    :func:`build_context` precedence: coverage gap > weak stops > high activity.
    """
    display_facts = await build_display_facts(db)
    segments = (
        await db.execute(select(RoadSegment.road_segment_id, RoadSegment.name, RoadSegment.length_km))
    ).all()
    activity = await _activity_by_segment(db)
    gaps = await _coverage_gap_by_segment(db)
    weak = await _weak_stops_by_segment(db)

    corridors: dict[str, dict] = {}
    for segment_id, name, length_km in segments:
        fact = display_facts.get(segment_id)
        emission = fact.emission if fact else None
        totals = emission.pollutant_totals_g_h if emission else None
        semantics = emission.vehicle_count_semantics if emission else None
        period_end = emission.period_end if emission else None
        key = name or segment_id
        corridor = corridors.setdefault(key, {
            "name": key,
            "road_segment_ids": [],
            "chunk_count": 0,
            "length_km": 0.0,
            "emission_kg_h": {pollutant.lower(): None for pollutant in POLLUTANTS},
            "emission_total_kg_h": None,
            "activity_class": None,
            "activity_score": None,
            "coverage_gap": False,
            "weak_stop_count": 0,
            "observed_at": None,
            "data_source": None,
            "data_status": OBSERVED,
            "borrowed_from": None,
            "is_static": False,
            "is_interpolated": False,
        })
        corridor["road_segment_ids"].append(segment_id)
        corridor["chunk_count"] += 1
        corridor["length_km"] = round(corridor["length_km"] + (length_km or 0), 3)

        per_pollutant, segment_total = _totals_kg_h(totals)
        for pollutant, value in per_pollutant.items():
            if value is not None:
                corridor["emission_kg_h"][pollutant] = (corridor["emission_kg_h"][pollutant] or 0) + value
        if segment_total is not None:
            corridor["emission_total_kg_h"] = (corridor["emission_total_kg_h"] or 0) + segment_total

        score, label = activity.get(segment_id, (None, None))
        if score is not None and (corridor["activity_score"] is None or score > corridor["activity_score"]):
            corridor["activity_score"] = score
            corridor["activity_class"] = label
            corridor["data_source"] = semantics
        observed = period_end.isoformat() if period_end else None
        if observed and (corridor["observed_at"] is None or observed > corridor["observed_at"]):
            corridor["observed_at"] = observed
        if gaps.get(segment_id):
            corridor["coverage_gap"] = True
        corridor["weak_stop_count"] += weak.get(segment_id, 0)
        if fact is not None and fact.data_status != OBSERVED:
            corridor["data_status"] = "estimated"
            corridor["borrowed_from"] = corridor["borrowed_from"] or fact.borrowed_from
        corridor["is_static"] = corridor["is_static"] or bool(fact and fact.is_static)
        corridor["is_interpolated"] = corridor["is_interpolated"] or bool(fact and fact.is_interpolated)

    for corridor in corridors.values():
        if corridor["coverage_gap"]:
            corridor["intervention_hint"] = "add_new_stop"
        elif corridor["weak_stop_count"]:
            corridor["intervention_hint"] = "improve_existing_stop"
        elif corridor["activity_class"] in HIGH_POTENTIAL:
            corridor["intervention_hint"] = "increase_frequency"
        else:
            corridor["intervention_hint"] = None

    ordered = sorted(
        corridors.values(),
        key=lambda corridor: corridor["emission_total_kg_h"]
        if corridor["emission_total_kg_h"] is not None else -1.0,
        reverse=True,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "overview",
        "metric": "emission_total_kg_h = jumlah seluruh polutan dari data emisi terbaru tiap segmen",
        "corridor_count": len(ordered),
        "corridors": ordered,
    }


def _emission_bands(ranked: list[dict]) -> dict[str, str]:
    """Relative severity by rank: top tercile Tinggi, bottom tercile Rendah."""
    total = len(ranked)
    bands: dict[str, str] = {}
    for index, corridor in enumerate(ranked):
        if index < total / 3:
            bands[corridor["name"]] = "Tinggi"
        elif index >= (2 * total) / 3:
            bands[corridor["name"]] = "Rendah"
        else:
            bands[corridor["name"]] = "Sedang"
    return bands


def _overview_row(corridor: dict, band: str) -> dict:
    value = corridor.get("emission_total_kg_h")
    hint = corridor.get("intervention_hint")
    return {
        "nama": corridor["name"],
        "total_emisi": round(value, 2) if value is not None else None,
        "kelas_aktivitas": corridor.get("activity_class"),
        "pita_emisi": band,
        "rekomendasi_intervensi": INTERVENTION_LABELS.get(hint) if hint else None,
        "status_data": "perkiraan" if corridor.get("data_status") == "estimated" else "terukur",
    }


def overview_payload(context: dict) -> dict:
    """Small, prompt-shaped view of :func:`build_overview_context`.

    The full per-corridor aggregation is far too large to send to Groq's free
    tier; this keeps only ranking/intervention essentials plus the highest,
    median, and lowest rows so most/least/normal questions stay answerable.
    Emission severity is computed here (relative terciles) so the model never
    invents a "high emission" threshold, and intervention enums are translated
    to Indonesian so no internal identifiers leak into the answer.
    """
    corridors = context.get("corridors") or []
    ranked = sorted(
        [corridor for corridor in corridors if corridor.get("emission_total_kg_h") is not None],
        key=lambda corridor: corridor["emission_total_kg_h"],
        reverse=True,
    )
    bands = _emission_bands(ranked)

    def row(corridor: dict) -> dict:
        return _overview_row(corridor, bands.get(corridor["name"], "Sedang"))

    median = ranked[len(ranked) // 2] if ranked else None
    needs = sorted(
        (row(corridor) for corridor in corridors if corridor.get("intervention_hint")),
        key=lambda item: item["total_emisi"] if item["total_emisi"] is not None else -1.0,
        reverse=True,
    )
    distribution: dict[str, int] = {}
    estimated = 0
    static = 0
    for corridor in ranked:
        band = bands[corridor["name"]]
        distribution[band] = distribution.get(band, 0) + 1
        if corridor.get("data_status") == "estimated":
            estimated += 1
        if corridor.get("is_static"):
            static += 1
    return {
        "scope": "overview",
        "jumlah_koridor": context.get("corridor_count"),
        "satuan_emisi": "kg/jam (jumlah seluruh polutan)",
        "sebaran_emisi": distribution,
        "jumlah_perkiraan": estimated,
        "jumlah_data_statis": static,
        "catatan_data": (
            "Sebagian koridor tidak punya kamera; nilainya adalah perkiraan dari segmen terdekat "
            "dan wajib disebut sebagai perkiraan, bukan pengukuran."
        ) if estimated else "Semua nilai berasal dari data terukur.",
        "ringkasan": {
            "tertinggi": row(ranked[0]) if ranked else None,
            "median": row(median) if median else None,
            "terendah": row(ranked[-1]) if ranked else None,
        },
        "emisi_tertinggi": [row(corridor) for corridor in ranked[:OVERVIEW_TOP_LIMIT]],
        "emisi_terendah": [row(corridor) for corridor in ranked[-OVERVIEW_BOTTOM_LIMIT:]],
        "butuh_intervensi": needs[:OVERVIEW_INTERVENTION_LIMIT],
        "intervensi_dipotong": len(needs) > OVERVIEW_INTERVENTION_LIMIT,
    }


async def segments_for_hex(db: AsyncSession, hex_id: int) -> list[str]:
    """Reverse of the hex-intersection query: segments crossing one hex cell."""
    hex_geom = select(ActivityGridHex.geometry).where(ActivityGridHex.hex_id == hex_id).scalar_subquery()
    rows = (
        await db.execute(
            select(RoadSegment.road_segment_id).where(func.ST_Intersects(RoadSegment.geometry, hex_geom))
        )
    ).scalars().all()
    return list(rows)


async def segment_for_stop(db: AsyncSession, stop_id: str) -> str | None:
    """Nearest road segment to a surveyed bus stop within the K4 buffer."""
    stop_geom = (
        select(SurveyStopObservation.geometry)
        .where(SurveyStopObservation.source_id == stop_id)
        .scalar_subquery()
    )
    row = (
        await db.execute(
            select(RoadSegment.road_segment_id)
            .where(func.ST_DWithin(cast(RoadSegment.geometry, _geog), cast(stop_geom, _geog), K4_BUFFER_M))
            .order_by(func.ST_Distance(cast(RoadSegment.geometry, _geog), cast(stop_geom, _geog)))
            .limit(1)
        )
    ).first()
    return row[0] if row else None


def _stop_quality(stop: SurveyStopObservation) -> dict:
    """AHP quality evidence for one surveyed stop (0-100 components)."""
    facilities = stop.facility_checklist or {}
    damages = stop.damage_indicators or {}
    return {
        "source_id": stop.source_id,
        "title": stop.title,
        "skor_total": round(stop.ahp_total_score, 2) if stop.ahp_total_score is not None else None,
        "kelas": stop.ahp_classification or stop.intervention_class,
        "aksesibilitas": stop.accessibility_score_100,
        "kondisi": stop.condition_score_100,
        "lingkungan": stop.environment_score_100,
        "jumlah_fasilitas": sum(1 for present in facilities.values() if present),
        "jumlah_kerusakan": sum(1 for flagged in damages.values() if flagged),
        "observed_at": stop.observed_at.isoformat() if stop.observed_at else None,
    }


async def build_bus_stop_overview_context(db: AsyncSession) -> dict:
    """Whole-dataset halte quality ranking by AHP total score (higher = better).

    This is the retrieval path that makes "halte terbaik/terburuk" answerable:
    the quality scores already live on ``SurveyStopObservation`` and were simply
    never assembled into a context before.
    """
    stops = (await db.execute(select(SurveyStopObservation))).scalars().all()
    ranked = sorted(
        (stop for stop in stops if stop.ahp_total_score is not None),
        key=lambda stop: stop.ahp_total_score,
        reverse=True,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "bus_stops",
        "metric": "skor_total = skor AHP kualitas halte 0-100 (aksesibilitas + kondisi + lingkungan); makin tinggi makin baik",
        "stop_count": len(stops),
        "scored_count": len(ranked),
        "stops": [_stop_quality(stop) for stop in ranked],
    }


def bus_stop_payload(context: dict) -> dict:
    """Compact, prompt-shaped view of :func:`build_bus_stop_overview_context`.

    Keeps only best/median/worst plus the top and bottom lists, translated to
    Indonesian so no internal identifiers leak and the ranking is never invented
    by the model.
    """
    ranked = sorted(context.get("stops") or [], key=lambda stop: stop["skor_total"], reverse=True)

    def row(stop: dict) -> dict:
        return {
            "nama": stop["title"],
            "skor_total": stop["skor_total"],
            "kelas": stop["kelas"],
            "aksesibilitas": stop["aksesibilitas"],
            "kondisi": stop["kondisi"],
            "lingkungan": stop["lingkungan"],
            "jumlah_fasilitas": stop["jumlah_fasilitas"],
            "jumlah_kerusakan": stop["jumlah_kerusakan"],
        }

    median = ranked[len(ranked) // 2] if ranked else None
    return {
        "scope": "bus_stops",
        "jumlah_halte": context.get("stop_count"),
        "jumlah_dinilai": context.get("scored_count"),
        "satuan_skor": "skor total AHP 0-100; makin tinggi makin baik (bobot: aksesibilitas, kondisi, lingkungan)",
        "ringkasan": {
            "terbaik": row(ranked[0]) if ranked else None,
            "median": row(median) if median else None,
            "terburuk": row(ranked[-1]) if ranked else None,
        },
        "halte_terbaik": [row(stop) for stop in ranked[:BUS_STOP_RANKING_LIMIT]],
        "halte_terburuk": [row(stop) for stop in ranked[-BUS_STOP_RANKING_LIMIT:]],
    }


async def build_stop_context(db: AsyncSession, stop_id: str) -> dict | None:
    """One stop's own quality evidence plus the nearest corridor's context."""
    stop = (
        await db.execute(select(SurveyStopObservation).where(SurveyStopObservation.source_id == stop_id))
    ).scalar_one_or_none()
    if stop is None:
        return None
    segment_id = await segment_for_stop(db, stop_id)
    segment_context = await build_context(db, segment_id) if segment_id else None
    return {
        "subject": {"type": "stop", "id": stop_id},
        "stop": _stop_quality(stop),
        "nearest_segment": segment_id,
        **(segment_context or {}),
    }


def _hex_cell_context(hex_cell: ActivityGridHex) -> dict:
    """AHP / POI evidence for one hex cell (geometry omitted from LLM payload)."""
    return {
        "hex_id": hex_cell.hex_id,
        "luas_km2": hex_cell.luas_km2,
        "poi_total": hex_cell.poi_total,
        "poi_breakdown": hex_cell.poi_breakdown,
        "penduduk": hex_cell.penduduk,
        "volume_mean": hex_cell.volume_mean,
        "skor_total_ahp": hex_cell.skor_total_ahp,
        "ranking": hex_cell.ranking,
        "klasifikasi_potensi": hex_cell.klasifikasi_potensi,
        "ahp_weight_version": hex_cell.ahp_weight_version,
        "source": hex_cell.source,
    }


def _hour_view(entry: dict) -> dict:
    """Only the fields the hour lens changes; static POI/population stay put."""
    return {
        "norm_volume": entry.get("norm_volume"),
        "skor_total_ahp": entry.get("skor_total_ahp"),
        "ranking": entry.get("ranking"),
        "klasifikasi_potensi": entry.get("klasifikasi_potensi"),
        "data_status": entry.get("data_status"),
        "is_interpolated": bool(entry.get("is_interpolated")),
        "fallback_from": entry.get("fallback_from"),
        "no_data_reason": entry.get("no_data_reason"),
        "source_segments": entry.get("source_segments"),
    }


async def _hex_hour_entry(db: AsyncSession, hex_id: int, hour: datetime | None) -> tuple[datetime | None, dict | None]:
    """Scored hour entry for one hex, resolved onto the static 24h profile.

    ``hour=None`` resolves to the profile anchor (latest bucket), preserving the
    previous behavior. Returns ``(moment, entry)``; both ``None`` when no profile
    exists yet (live-only dev DB), so callers fall back to the static snapshot.
    """
    moment = await profile_hour(db, hour)
    if moment is None:
        return None, None
    _, scores = await hour_scores(db, moment)
    return moment, scores.get(hex_id, {})


async def build_hex_context(db: AsyncSession, hex_id: int, hour: datetime | None = None) -> dict | None:
    """Hex cell evidence plus the corridor contexts crossing that cell.

    Returns ``None`` for an unknown hex. When ``hour`` is given, the cell's
    score/class/ranking are the ones the map displays at that hour (the static
    offline snapshot is kept under ``static`` for reference); this is what keeps
    the answer aligned with the panel the user is looking at. ``corridor_contexts``
    is an empty list (not ``None``) when no road segment crosses the cell, so
    callers can still answer from the cell's own AHP data.
    """
    hex_cell = (
        await db.execute(select(ActivityGridHex).where(ActivityGridHex.hex_id == hex_id))
    ).scalar_one_or_none()
    if hex_cell is None:
        return None
    segment_ids = await segments_for_hex(db, hex_id)
    corridor_contexts = [
        context for context in [await build_context(db, sid) for sid in segment_ids] if context
    ]
    hex_context = _hex_cell_context(hex_cell)
    moment, entry = await _hex_hour_entry(db, hex_id, hour)
    observed_hour = None
    if moment is not None and entry is not None:
        observed_hour = moment.isoformat()
        hex_context["static"] = {
            "skor_total_ahp": hex_cell.skor_total_ahp,
            "ranking": hex_cell.ranking,
            "klasifikasi_potensi": hex_cell.klasifikasi_potensi,
            "volume_mean": hex_cell.volume_mean,
        }
        hex_context.update(_hour_view(entry))
        hex_context["observed_hour"] = observed_hour
    return {"hex_cell": hex_context, "observed_hour": observed_hour, "corridor_contexts": corridor_contexts}

