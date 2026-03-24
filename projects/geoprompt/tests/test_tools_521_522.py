"""Smoke tests for tools 521-522."""

import pytest

from geoprompt import GeoPromptFrame


@pytest.fixture()
def sample_frame():
    records = []
    for index in range(12):
        x_coord = float(index % 4)
        y_coord = float(index // 4)
        value = 2.5 * x_coord + 3.0 * y_coord + (index % 3)
        records.append({
            "geometry": {"type": "Point", "coordinates": [x_coord, y_coord]},
            "val": value,
            "income": 1000.0 + 200.0 * x_coord + 100.0 * y_coord,
            "education": 8.0 + 0.5 * x_coord + 0.3 * y_coord,
            "supply": 3.0 + (index % 4),
        })
    return GeoPromptFrame.from_records(records, crs="EPSG:4326")


TOOL_CASES = [
    # Tool 521 — transport-aware hotspot (no supply column)
    {
        "method": "transport_aware_hotspot",
        "args": ("val",),
        "kwargs": {"n_radii": 4},
        "cols": ["hotspot_score_tah", "weighted_score_tah", "accessibility_tah", "best_radius_tah", "is_hotspot_tah"],
        "len": 12,
    },
    # Tool 521 — with explicit supply column
    {
        "method": "transport_aware_hotspot",
        "args": ("val",),
        "kwargs": {"supply_column": "supply", "n_radii": 4, "suffix": "tah2"},
        "cols": ["hotspot_score_tah2", "weighted_score_tah2", "accessibility_tah2"],
        "len": 12,
    },
    # Tool 522 — counterfactual GWR
    {
        "method": "counterfactual_gwr",
        "args": ("val", ["income", "education"], {"income": 500.0}),
        "kwargs": {},
        "cols": ["predicted_cfgwr", "counterfactual_cfgwr", "effect_cfgwr", "coeff_income_cfgwr", "coeff_education_cfgwr"],
        "len": 12,
    },
    # Tool 522 — with auto bandwidth
    {
        "method": "counterfactual_gwr",
        "args": ("val", ["income", "education"], {"income": 500.0, "education": 1.0}),
        "kwargs": {"auto_bandwidth": True, "suffix": "cf2"},
        "cols": ["predicted_cf2", "counterfactual_cf2", "effect_cf2"],
        "len": 12,
    },
]


@pytest.mark.parametrize("case", TOOL_CASES, ids=[f"{case['method']}_{i}" for i, case in enumerate(TOOL_CASES)])
def test_tools_521_522_smoke(sample_frame, case):
    method = getattr(sample_frame, case["method"])
    result = method(*case.get("args", ()), **case.get("kwargs", {}))
    records = result.to_records()
    assert len(records) == case["len"]
    for column in case["cols"]:
        assert column in records[0]


def test_counterfactual_effect_is_nonzero(sample_frame):
    """With a nonzero scenario perturbation, the effect should differ from zero for at least some points."""
    result = sample_frame.counterfactual_gwr(
        "val",
        ["income", "education"],
        {"income": 1000.0},
    )
    effects = [r["effect_cfgwr"] for r in result.to_records()]
    assert any(abs(e) > 1e-8 for e in effects), "Expected at least one nonzero effect"


def test_transport_hotspot_accessibility_positive(sample_frame):
    """Accessibility should be positive for all features."""
    result = sample_frame.transport_aware_hotspot("val", n_radii=3)
    for r in result.to_records():
        assert r["accessibility_tah"] > 0


def test_counterfactual_zero_scenario_gives_zero_effect(sample_frame):
    """A scenario with zero perturbation should produce zero effects."""
    result = sample_frame.counterfactual_gwr(
        "val",
        ["income", "education"],
        {"income": 0.0, "education": 0.0},
    )
    for r in result.to_records():
        assert abs(r["effect_cfgwr"]) < 1e-6
