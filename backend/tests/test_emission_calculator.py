import pytest
from cv.emission_factors import calculate_emission, EMISSION_FACTORS


class TestCalculateEmission:

    def test_basic_counts(self):
        counts = {"car": 10, "motorcycle": 20, "bus": 2, "truck": 1}
        result = calculate_emission(counts)

        assert result["total_g_per_min"] == (
            10 * 120 + 20 * 40 + 2 * 350 + 1 * 350
        )

    def test_returns_kg_per_hr(self):
        counts = {"car": 10, "motorcycle": 0, "bus": 0, "truck": 0}
        result = calculate_emission(counts)
        # 10 cars × 120 g/min × 60 min / 1000 = 72 kg/hr
        assert result["total_kg_per_hr"] == 72.0

    def test_all_zeros(self):
        counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
        result = calculate_emission(counts)
        assert result["total_g_per_min"] == 0.0
        assert result["total_kg_per_hr"] == 0.0

    def test_missing_keys_treated_as_zero(self):
        # Only cars provided — others should default to 0
        result = calculate_emission({"car": 5})
        assert result["breakdown"]["motorcycle"] == 0.0
        assert result["breakdown"]["bus"] == 0.0
        assert result["breakdown"]["truck"] == 0.0
        assert result["total_g_per_min"] == 5 * 120

    def test_extra_keys_are_ignored(self):
        # "bicycle" is not a tracked class — should not crash or affect total
        counts = {"car": 1, "bicycle": 100}
        result = calculate_emission(counts)
        assert result["total_g_per_min"] == 1 * 120

    def test_breakdown_keys_match_emission_factors(self):
        result = calculate_emission({"car": 1, "motorcycle": 1, "bus": 1, "truck": 1})
        assert set(result["breakdown"].keys()) == set(EMISSION_FACTORS.keys())

    def test_single_motorcycle(self):
        result = calculate_emission({"motorcycle": 1})
        assert result["total_g_per_min"] == 40.0

    def test_single_bus(self):
        result = calculate_emission({"bus": 1})
        assert result["total_g_per_min"] == 350.0

    def test_output_types(self):
        result = calculate_emission({"car": 3})
        assert isinstance(result["total_g_per_min"], float)
        assert isinstance(result["total_kg_per_hr"], float)
        assert isinstance(result["breakdown"], dict)

    def test_empty_dict(self):
        result = calculate_emission({})
        assert result["total_g_per_min"] == 0.0