from pathlib import Path


def test_segment_migration_declares_all_pipeline_tables():
    migration_dir = Path(__file__).parents[1] / "migrations" / "versions"
    source = next(migration_dir.glob("*_add_segment_emission_pipeline.py")).read_text()
    for table in ("road_segments", "camera_road_segments", "segment_traffic_observations", "segment_emissions"):
        assert f'"{table}"' in source
