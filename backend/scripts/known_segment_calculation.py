"""Print the implementation-plan two-stream known-value calculation."""

from datetime import datetime, timedelta, timezone

from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_observation import SegmentTrafficObservation


def main() -> None:
    start = datetime(2026, 9, 3, 10, tzinfo=timezone.utc)
    observations = [
        SegmentTrafficObservation("camera-a", "segment-001", "northbound", start, 60, {"motorcycle": 40, "gasoline_car": 10, "bus": 1, "truck": 2}),
        SegmentTrafficObservation("camera-b", "segment-001", "southbound", start, 60, {"motorcycle": 35, "gasoline_car": 12, "bus": 0, "truck": 1}),
    ]
    result = calculate_segment_emission(observations, period_start=start, period_end=start + timedelta(minutes=1), road_length_km=0.8)
    print({
        "motorcycle_volume_per_hour": result["volume_per_hour"]["motorcycle"],
        "motorcycle_vkt_km_h": result["vkt_km_h"]["motorcycle"],
        "motorcycle_co_g_h": result["emissions"]["by_category_g_h"]["motorcycle"]["CO"],
        "spatial_criteria_status": result["spatial_criteria_status"],
    })


if __name__ == "__main__":
    main()
