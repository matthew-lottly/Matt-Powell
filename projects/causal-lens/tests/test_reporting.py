from __future__ import annotations

from pathlib import Path

from causal_lens.data import load_monitoring_intervention_sample
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
)
from causal_lens.reporting import export_dataset_artifacts, results_to_frame, sensitivity_to_frame


def _payload() -> dict:
    dataset = load_monitoring_intervention_sample()
    confounders = [
        "sensor_age_years",
        "maintenance_backlog_days",
        "baseline_alert_rate",
        "staffing_ratio",
    ]
    primary = DoublyRobustEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=10)
    results = [
        estimator.fit(dataset).to_dict()
        for estimator in [
            RegressionAdjustmentEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=10),
            PropensityMatcher("treatment", "outcome_alert_rate", confounders, caliper=None, bootstrap_repeats=10),
            IPWEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=10),
            primary,
        ]
    ]
    return {
        "rows": len(dataset),
        "confounders": confounders,
        "results": results,
        "primary_sensitivity": primary.sensitivity_analysis(dataset, steps=4).to_dict(),
        "subgroups": [
            subgroup.to_dict()
            for subgroup in primary.subgroup_effects(dataset, "region_category", min_rows=3, min_group_size=1)
        ],
    }


def test_results_frame_contains_publication_columns() -> None:
    payload = _payload()
    frame = results_to_frame(payload["results"])
    assert "mean_abs_balance_before" in frame.columns
    assert "mean_abs_balance_after" in frame.columns
    assert len(frame) == 4


def test_sensitivity_frame_contains_scenario_rows() -> None:
    payload = _payload()
    frame = sensitivity_to_frame(payload["primary_sensitivity"])
    assert len(frame) == 4
    assert "adjusted_effect" in frame.columns


def test_export_dataset_artifacts_writes_tables_and_charts(tmp_path: Path) -> None:
    payload = _payload()
    export_dataset_artifacts("real_dataset", payload, tmp_path)
    assert (tmp_path / "tables" / "real_dataset_estimator_summary.csv").exists()
    assert (tmp_path / "tables" / "real_dataset_estimator_summary.md").exists()
    assert (tmp_path / "charts" / "real_dataset_estimator_comparison.png").exists()
    assert (tmp_path / "charts" / "real_dataset_balance_summary.png").exists()
    assert (tmp_path / "charts" / "real_dataset_sensitivity_curve.png").exists()
    assert (tmp_path / "charts" / "real_dataset_subgroup_effects.png").exists()
