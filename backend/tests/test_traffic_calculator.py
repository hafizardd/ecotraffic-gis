import pytest

from app.services.traffic_calculator import volume_per_hour, vkt_by_category


def test_interval_counts_are_converted_to_hourly_volume():
    result = volume_per_hour({"motorcycle": 120}, 600)
    assert result["motorcycle"] == 720
    assert result["gasoline_car"] == 0


def test_already_hourly_input_is_not_scaled_again():
    assert volume_per_hour({"truck": 100}, 60, already_hourly=True)["truck"] == 100


def test_vkt_uses_authoritative_length_in_kilometres():
    volume = volume_per_hour({"gasoline_car": 100}, 3600, already_hourly=True)
    assert vkt_by_category(volume, 2)["gasoline_car"] == 200


@pytest.mark.parametrize("duration", [0, -1, float("nan")])
def test_invalid_duration_is_rejected(duration):
    with pytest.raises(ValueError, match="duration"):
        volume_per_hour({}, duration)


@pytest.mark.parametrize("length", [0, -1, float("inf")])
def test_invalid_length_is_rejected(length):
    with pytest.raises(ValueError, match="road_length"):
        vkt_by_category({}, length)
