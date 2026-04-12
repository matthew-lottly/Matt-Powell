from __future__ import annotations

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.equations import prompt_decay
from geoprompt.interop import geopandas_available
from geoprompt.tools import (
    bootstrap_confidence_interval,
    build_scenario_report,
    optimize_decay_parameters,
    validate_numeric_series,
    vectorized_decay,
)


def test_optimize_decay_parameters_refines_grid_search() -> None:
    observed_pairs = [(distance, prompt_decay(distance, scale=1.3, power=1.8)) for distance in [0.2, 0.5, 1.0, 2.0, 3.0]]
    result = optimize_decay_parameters(observed_pairs, method="power", refinement_steps=8)
    assert result["rmse"] < 1e-4
    assert result["scale"] == pytest.approx(1.3, abs=0.15)
    assert result["power"] == pytest.approx(1.8, abs=0.2)


def test_bootstrap_confidence_interval_mean() -> None:
    summary = bootstrap_confidence_interval([1.0, 2.0, 3.0, 4.0, 5.0], iterations=200, seed=3)
    assert summary["lower"] <= summary["observed"] <= summary["upper"]
    assert summary["confidence_level"] == pytest.approx(0.95)


def test_build_scenario_report_structure() -> None:
    report = build_scenario_report(
        {"deficit": 0.2, "served": 100.0},
        {"deficit": 0.1, "served": 110.0},
        higher_is_better=["served"],
        uncertainty={"served": {"lower": 105.0, "upper": 115.0}},
        metadata={"scenario_id": "demo"},
    )
    assert report["summary"]["metric_count"] == 2
    assert "deficit" in report["summary"]["improved_metrics"]
    assert report["metadata"]["scenario_id"] == "demo"


def test_vectorized_decay_matches_scalar() -> None:
    distances = [0.0, 0.5, 1.0, 2.0]
    vectorized = vectorized_decay(distances, method="exponential", rate=0.8)
    scalar = [__import__("geoprompt.equations", fromlist=["exponential_decay"]).exponential_decay(d, rate=0.8) for d in distances]
    assert vectorized == pytest.approx(scalar)


def test_validate_numeric_series_rejects_nan() -> None:
    with pytest.raises(ValueError, match="must not contain NaN"):
        validate_numeric_series([1.0, float("nan")])


def test_validate_numeric_series_bounds() -> None:
    cleaned = validate_numeric_series([1.0, 2.0, 3.0], min_value=1.0, max_value=3.0)
    assert cleaned == [1.0, 2.0, 3.0]


def test_geopandas_availability_returns_bool() -> None:
    assert isinstance(geopandas_available(), bool)


def test_interop_roundtrip_or_missing_dependency() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": (-111.9, 40.7)}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": (-112.0, 40.8)}},
        ],
        crs="EPSG:4326",
    )

    if not geopandas_available():
        from geoprompt.interop import to_geopandas

        with pytest.raises(RuntimeError, match="GeoPandas support"):
            to_geopandas(frame)
        return

    from geoprompt.interop import from_geopandas, to_geopandas

    gdf = to_geopandas(frame)
    restored = from_geopandas(gdf)
    assert len(restored) == len(frame)
    assert restored.crs == frame.crs
