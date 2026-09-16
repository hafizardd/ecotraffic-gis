"""Import an exported CSV and atomically replace the derived 24-hour Replay profile.

Source facts retain original provenance under CSV_HISTORY (version 5). Only
segments present in the file are included; absent segments are never fabricated.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from app.core.database import get_sync_db
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission
from app.services.segment_emission_store import _values
from scripts.build_replay_dataset import (
    HOUR, POLLUTANTS, VEHICLE_KEYS, METRIC_FIELDS, _gap_plan, _filled_series,
    _source_hours, _replay_result,
)


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('CSV timestamps must include a timezone')
    return result.astimezone(timezone.utc)


def number(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError('CSV metrics must be finite and nonnegative')
    return result


def load(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    records = []
    keys = set()
    with path.open(encoding='utf-8-sig', newline='') as source:
        for row in csv.DictReader(source):
            start, end = timestamp(row['period_start']), timestamp(row['period_end'])
            key = (row['segment_id'], start)
            if key in keys or end <= start:
                raise ValueError(f'Duplicate or invalid period: {key}')
            keys.add(key)
            if row['vehicle_count_semantics'] != 'snapshot_occupancy':
                raise ValueError('Only snapshot occupancy exports are supported')
            metadata = json.loads(row['calculation_metadata'] or '{}')
            metadata.update(csv_sha256=digest, csv_file=path.name,
                            original_source_mode=row['source_mode'],
                            original_calculation_version=int(row['calculation_version']),
                            original_quality_status=row['quality_status'])
            result = dict(
                period_start=start, period_end=end,
                calculated_at=timestamp(row['processed_at']), calculation_version=5,
                observation_duration_seconds=number(row['observation_duration_seconds']),
                data_source='HISTORICAL', source_mode='CSV_HISTORY',
                calculation_mode=row['calculation_mode'], observed_at=row['observed_at'],
                vehicle_count_semantics='snapshot_occupancy',
                raw_counts={},  # Export does not contain raw counts; never reconstruct them.
                volume_per_hour={k: number(row[f'{k}_vehicles_h']) for k in VEHICLE_KEYS},
                vkt_km_h={k: number(row[f'{k}_vkt_km_h']) for k in VEHICLE_KEYS},
                emissions={'totals_g_h': {p: number(row[f'{p.lower()}_kg_h']) * 1000 for p in POLLUTANTS}},
                calculation_metadata=metadata,
                provenance=dict(source_cameras=json.loads(row['source_cameras']),
                                source_streams=json.loads(row['source_streams']),
                                source_observation_count=int(row['source_observation_count'])),
            )
            records.append((row['segment_id'], result))
    if not records:
        raise ValueError('CSV is empty')
    return digest, records


def prepare(records):
    end = max(r['period_start'] for _, r in records).replace(minute=0, second=0, microsecond=0) + HOUR
    buckets = [end - (24 - i) * HOUR for i in range(24)]
    grouped = defaultdict(lambda: defaultdict(list))
    for segment, result in records:
        hour = result['period_start'].replace(minute=0, second=0, microsecond=0)
        if buckets[0] <= hour < end:
            grouped[segment][hour].append(result)
    profiles = {}
    for segment, hours in grouped.items():
        if len(hours) < 2:
            raise ValueError(f'{segment}: at least two observed hours required')
        means = {}
        for hour, samples in hours.items():
            values = {field: None for field in METRIC_FIELDS}
            for p in POLLUTANTS:
                values[f'{p.lower()}_kg_h'] = sum(r['emissions']['totals_g_h'][p] for r in samples) / len(samples) / 1000
            for k in VEHICLE_KEYS:
                for prefix, field in [('volume', 'volume_per_hour'), ('vkt', 'vkt_km_h')]:
                    values[f'{prefix}_{k}'] = sum(r[field][k] for r in samples) / len(samples)
            values.update(sample_count=len(samples), observed_at=max(r['observed_at'] for r in samples))
            means[hour] = values
        profiles[segment] = means
    return buckets, profiles


def run(path, dry_run=False):
    digest, records = load(path)
    buckets, profiles = prepare(records)
    with get_sync_db() as db:
        segments = dict(db.execute(select(RoadSegment.road_segment_id, RoadSegment.id)).all())
        unknown = sorted({s for s, _ in records} - segments.keys())
        if unknown:
            raise ValueError(f'Unknown segments: {unknown}')
        report = dict(csv_sha256=digest, source_rows=len(records), segments=len(profiles),
                      start=buckets[0].isoformat(), end_exclusive=(buckets[-1]+HOUR).isoformat(),
                      observed_hours_min=min(map(len, profiles.values())),
                      observed_hours_max=max(map(len, profiles.values())),
                      replay_rows=24*len(profiles),
                      interpolated_hours=sum(24-len(h) for h in profiles.values()), dry_run=dry_run)
        print(json.dumps(report, indent=2), flush=True)
        if dry_run:
            return report
        values = [_values(segments[s], r) for s, r in records]
        for offset in range(0, len(values), 250):
            stmt = insert(SegmentEmission).values(values[offset:offset+250])
            db.execute(stmt.on_conflict_do_update(
                constraint='uq_segment_emission_period_version',
                set_={k: getattr(stmt.excluded, k) for k in values[0] if k != 'road_segment_id'},
            ))
        # Replace derived profile only, in the same transaction as source import.
        db.execute(delete(SegmentEmission).where(SegmentEmission.ahp_metadata['source_mode'].astext == 'REPLAY'))
        replay = []
        for segment, means in profiles.items():
            plan = _gap_plan([b in means for b in buckets])
            series = _filled_series(means, buckets, plan)
            for i, bucket in enumerate(buckets):
                result = _replay_result(segment, bucket, {k: v[i] for k, v in series.items()},
                    plan=plan[i], sample_count=means.get(bucket, {}).get('sample_count', 0),
                    observed_at=means.get(bucket, {}).get('observed_at'),
                    interpolated_from=_source_hours(buckets, plan[i]) if plan[i] else [])
                result['calculation_metadata'].update(replay_source='CSV_HISTORY', replay_source_version=5,
                                                       csv_sha256=digest, csv_file=path.name)
                replay.append(_values(segments[segment], result))
        for offset in range(0, len(replay), 250):
            db.execute(insert(SegmentEmission).values(replay[offset:offset+250]))
    print('Committed CSV import and Replay profile.', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=Path('data/history/emission-history.csv'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run(args.file, args.dry_run)
