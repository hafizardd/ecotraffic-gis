from pathlib import Path
from scripts.import_emission_history import load, prepare, number, timestamp


def test_repository_csv_profile():
    path = Path(__file__).resolve().parents[1] / 'data/history/emission-history.csv'
    digest, records = load(path)
    buckets, profiles = prepare(records)
    assert len(digest) == 64
    assert len(records) == 9173
    assert len(profiles) == 44
    assert len(buckets) == 24
    assert sum(24-len(hours) for hours in profiles.values()) == 196
    assert all(len({tuple(r[f'volume_{k}'] for k in ('car','motorcycle','bus','truck')) for r in hours.values()}) > 1 for hours in profiles.values())
    assert all(r['source_mode'] == 'CSV_HISTORY' and r['raw_counts'] == {} for _, r in records)
    for _, r in records:
        assert r['calculation_metadata']['original_source_mode'] in ('LIVE','SNAPSHOT_REAL')


def test_invalid_metrics_and_timezone():
    for value in ['nan','inf','-1']:
        try:
            number(value)
        except ValueError:
            pass
        else:
            raise AssertionError(value)
    try:
        timestamp('2026-09-11T00:00:00')
    except ValueError:
        pass
    else:
        raise AssertionError('Naive timestamp accepted')
