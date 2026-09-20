"""Source selection must not mix Replay derivatives into imported observations."""
from datetime import datetime, timedelta, timezone
from sqlalchemy.dialects import postgresql
from app.services.emission_analytics import AnalyticsFilter, fact_query


def test_source_scopes():
    end = datetime.now(timezone.utc)
    for mode in ['CSV_AND_LIVE', 'ACTIVE_LIVE', 'HISTORICAL']:
        query = fact_query(AnalyticsFilter(end-timedelta(days=1), end, source_mode=mode))
        sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        if mode == 'CSV_AND_LIVE':
            assert "'CSV_HISTORY'" in sql and "'LIVE'" in sql
        if mode == 'ACTIVE_LIVE':
            assert "cameras.is_active IS true" in sql and "cameras.data_source = 'LIVE'" in sql
            assert "'CSV_HISTORY'" not in sql
        if mode == 'HISTORICAL':
            assert "'CSV_HISTORY'" in sql


def test_newest_preserves_long_history_with_bounded_chart_buckets():
    end = datetime.now(timezone.utc)
    filters = AnalyticsFilter(end-timedelta(days=365), end, newest=True)
    _, seconds = filters.bucket()
    assert (filters.end-filters.start).total_seconds() / seconds <= 2000
    try:
        AnalyticsFilter(end-timedelta(days=365), end)
    except ValueError:
        pass
    else:
        raise AssertionError('Explicit dates must still validate range limits')
