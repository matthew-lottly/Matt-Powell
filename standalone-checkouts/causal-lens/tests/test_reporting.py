from __future__ import annotations

from pathlib import Path

from causal_lens.comparison import export_external_comparison_artifacts
from causal_lens.data import load_monitoring_intervention_sample
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
    run_placebo_test,
)
from causal_lens.reporting import (
    export_dataset_artifacts,
    export_placebo_artifacts,
    export_rosenbaum_artifacts,
    results_to_frame,
    sensitivity_to_frame,
)
from causal_lens.stability import export_stability_artifacts


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


def test_export_external_comparison_artifacts_writes_table(tmp_path: Path) -> None:
    frame = export_external_comparison_artifacts(tmp_path)
    assert len(frame) == 6
    assert frame["match"].all()
    assert (tmp_path / "tables" / "external_comparison.csv").exists()


def test_export_stability_artifacts_writes_tables(tmp_path: Path) -> None:
    raw, summary = export_stability_artifacts(tmp_path, quick=True)
    assert not raw.empty
    assert not summary.empty
    assert (tmp_path / "tables" / "stability_raw.csv").exists()
    assert (tmp_path / "tables" / "stability_summary.csv").exists()


def test_results_frame_includes_se_and_p_value() -> None:
    payload = _payload()
    frame = results_to_frame(payload["results"])
    assert "se" in frame.columns
    assert "p_value" in frame.columns
    assert "ess_treated" in frame.columns
    assert "ess_control" in frame.columns


def test_export_dataset_artifacts_writes_love_plot(tmp_path: Path) -> None:
    payload = _payload()
    export_dataset_artifacts("real_dataset", payload, tmp_path)
    assert (tmp_path / "charts" / "real_dataset_love_plot.png").exists()


def test_export_placebo_artifacts_writes_csv(tmp_path: Path) -> None:
    dataset = load_monitoring_intervention_sample()
    confounders = ["sensor_age_years", "maintenance_backlog_days", "baseline_alert_rate"]
    results = run_placebo_test(
        dataset,
        treatment_col="treatment",
        placebo_outcome="staffing_ratio",
        confounders=confounders,
        bootstrap_repeats=10,
    )
    frame = export_placebo_artifacts([r.to_dict() for r in results], tmp_path)
    assert len(frame) == 4
    assert (tmp_path / "tables" / "placebo_test.csv").exists()


def test_export_rosenbaum_artifacts_writes_csv(tmp_path: Path) -> None:
    dataset = load_monitoring_intervention_sample()
    confounders = ["sensor_age_years", "maintenance_backlog_days", "baseline_alert_rate", "staffing_ratio"]
    matcher = PropensityMatcher("treatment", "outcome_alert_rate", confounders, caliper=None, bootstrap_repeats=10)
    bounds = matcher.rosenbaum_sensitivity(dataset)
    frame = export_rosenbaum_artifacts([r.to_dict() for r in bounds], tmp_path)
    assert len(frame) == 7
    assert (tmp_path / "tables" / "rosenbaum_bounds.csv").exists()
