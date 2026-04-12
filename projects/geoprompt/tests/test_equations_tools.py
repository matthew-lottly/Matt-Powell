from __future__ import annotations

import math

import pytest

from geoprompt.equations import (
    accessibility_gini,
    age_adjusted_failure_rate,
    composite_resilience_index,
    expected_outage_impact,
    exponential_decay,
    gaussian_decay,
    gravity_interaction,
    logistic_service_probability,
    prompt_decay,
    weighted_accessibility_score,
)
from geoprompt.tools import (
    benchmark_function,
    calibrate_decay_parameters,
    compare_scenarios,
    monte_carlo_interval,
    normalize_units,
    sensitivity_analysis,
)


def test_exponential_and_gaussian_decay_bounds() -> None:
    assert 0.0 < exponential_decay(1.0, rate=0.5) < 1.0
    assert 0.0 < gaussian_decay(1.0, sigma=1.0) < 1.0


def test_gravity_interaction_positive() -> None:
    score = gravity_interaction(100.0, 50.0, generalized_cost=5.0, alpha=1.0, beta=1.0, gamma=1.2)
    assert score > 0


def test_logistic_service_probability_range() -> None:
    probability = logistic_service_probability(
        predictors={"pressure": 1.5, "distance": -0.8},
        coefficients={"pressure": 0.9, "distance": 0.4},
        intercept=-0.2,
    )
    assert 0.0 <= probability <= 1.0


def test_reliability_equations() -> None:
    failure = age_adjusted_failure_rate(base_failure_rate=0.01, asset_age_years=30, aging_factor=0.04)
    impact = expected_outage_impact(failure_probability=0.2, consequence=2000.0)
    assert failure > 0.01
    assert impact == 400.0


def test_accessibility_and_gini() -> None:
    accessibility = weighted_accessibility_score(
        supply_values=[100.0, 70.0, 40.0],
        travel_costs=[1.0, 2.0, 4.0],
        decay_method="power",
        scale=2.0,
        power=1.5,
    )
    gini = accessibility_gini([10.0, 10.0, 10.0, 10.0])
    assert accessibility > 0
    assert gini == pytest.approx(0.0)


def test_composite_resilience_index() -> None:
    score = composite_resilience_index(
        redundancy=0.8,
        recovery_speed=0.7,
        robustness=0.75,
        service_deficit=0.1,
    )
    assert score > 0


def test_calibrate_decay_parameters_power() -> None:
    observed_pairs = []
    for distance in [0.2, 0.5, 1.0, 2.0, 3.0]:
        observed_pairs.append((distance, prompt_decay(distance, scale=1.0, power=2.0)))

    result = calibrate_decay_parameters(
        observed_pairs,
        method="power",
        scale_candidates=[0.5, 1.0, 2.0],
        power_candidates=[1.0, 2.0, 3.0],
    )
    assert result["rmse"] < 1e-8
    assert result["scale"] == pytest.approx(1.0)
    assert result["power"] == pytest.approx(2.0)


def test_compare_scenarios_direction() -> None:
    result = compare_scenarios(
        baseline_metrics={"service_deficit": 0.2, "served_customers": 100.0},
        candidate_metrics={"service_deficit": 0.1, "served_customers": 110.0},
        higher_is_better=["served_customers"],
    )
    assert result["service_deficit"]["direction"] == "improved"
    assert result["served_customers"]["direction"] == "improved"


def _simple_model(a: float, b: float) -> float:
    return a * a + b


def test_sensitivity_analysis() -> None:
    rows = sensitivity_analysis(_simple_model, {"a": 2.0, "b": 1.0}, variation_fraction=0.25)
    assert rows
    assert rows[0]["parameter"] in {"a", "b"}


def test_monte_carlo_interval() -> None:
    summary = monte_carlo_interval(
        _simple_model,
        parameter_bounds={"a": (1.0, 2.0), "b": (0.0, 1.0)},
        iterations=200,
        seed=7,
    )
    assert summary["min"] <= summary["p10"] <= summary["p50"] <= summary["p90"] <= summary["max"]


def test_normalize_units_distance_and_flow() -> None:
    assert normalize_units(1.0, "km", "m", quantity="distance") == pytest.approx(1000.0)
    assert normalize_units(1000.0, "lps", "m3s", quantity="flow") == pytest.approx(1.0)


def test_benchmark_function() -> None:
    stats = benchmark_function(math.sqrt, 4.0, repeats=3)
    assert stats["runs"] == 3.0
    assert stats["mean_seconds"] >= 0.0
