"""Unit tests for labeled borrowed estimates (no DB)."""

from types import SimpleNamespace

from app.services.segment_estimate import DisplayFact, is_interpolated_of, source_mode_of


def _emission(source_mode=None, data_source=None, interpolated=None):
    metadata = {"data_source": data_source}
    if source_mode is not None:
        metadata["source_mode"] = source_mode
    if interpolated is not None:
        metadata["calculation_metadata"] = {"is_interpolated": interpolated}
    return SimpleNamespace(ahp_metadata=metadata)


def test_source_mode_falls_back_to_data_source_and_historical():
    assert source_mode_of(_emission(source_mode="REPLAY")) == "REPLAY"
    assert source_mode_of(_emission(data_source="HISTORICAL")) == "SYNTHETIC"
    assert source_mode_of(_emission(data_source="LIVE")) == "LIVE"
    assert source_mode_of(SimpleNamespace(ahp_metadata={})) == "HISTORICAL"


def test_display_fact_classifies_static_and_estimated():
    observed = DisplayFact(emission=_emission(source_mode="REPLAY", interpolated=True), data_status="observed")
    assert observed.is_static is True
    assert observed.is_interpolated is True

    borrowed = DisplayFact(
        emission=_emission(source_mode="REPLAY"), data_status="estimated", borrowed_from="SEG-0002"
    )
    assert borrowed.is_static is True
    assert borrowed.borrowed_from == "SEG-0002"

    live = DisplayFact(emission=_emission(data_source="LIVE"), data_status="observed")
    assert live.is_static is False
    assert is_interpolated_of(live.emission) is False

    unavailable = DisplayFact(emission=None, data_status="unavailable")
    assert unavailable.source_mode is None
    assert unavailable.is_static is False
    assert unavailable.is_interpolated is False
