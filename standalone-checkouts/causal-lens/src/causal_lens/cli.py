from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from causal_lens.comparison import export_external_comparison_artifacts
from causal_lens.data import (
    LALONDE_CONFOUNDERS,
    NHEFS_COMPLETE_CONFOUNDERS,
    load_lalonde_benchmark,
    load_monitoring_intervention_sample,
    load_nhefs_complete_benchmark,
)
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
    run_placebo_test,
)
from causal_lens.reporting import (
    export_benchmark_artifacts,
    export_dataset_artifacts,
    export_placebo_artifacts,
    export_propensity_overlap,
    export_rosenbaum_artifacts,
)
from causal_lens.stability import export_stability_artifacts
from causal_lens.synthetic import generate_synthetic_observational_data


def _analyze_dataset(
    dataset: pd.DataFrame,
    *,
    outcome_col: str,
    confounders: list[str],
    bootstrap_repeats: int,
    matcher_caliper: float | None,
    propensity_trim_bounds: tuple[float, float] | None = None,
    subgroup_col: str | None = None,
    min_rows: int = 0,
    min_group_size: int = 0,
) -> dict:
    primary_estimator = DoublyRobustEstimator(
        "treatment",
        outcome_col,
        confounders,
        bootstrap_repeats=bootstrap_repeats,
        propensity_trim_bounds=propensity_trim_bounds,
    )
    results = [
        estimator.fit(dataset).to_dict()
        for estimator in [
            RegressionAdjustmentEstimator(
                "treatment",
                outcome_col,
                confounders,
                bootstrap_repeats=bootstrap_repeats,
                propensity_trim_bounds=propensity_trim_bounds,
            ),
            PropensityMatcher(
                "treatment",
                outcome_col,
                confounders,
                caliper=matcher_caliper,
                bootstrap_repeats=bootstrap_repeats,
                propensity_trim_bounds=propensity_trim_bounds,
            ),
            IPWEstimator(
                "treatment",
                outcome_col,
                confounders,
                bootstrap_repeats=bootstrap_repeats,
                propensity_trim_bounds=propensity_trim_bounds,
            ),
            primary_estimator,
        ]
    ]
    subgroups = []
    if subgroup_col is not None:
        subgroups = [
            subgroup.to_dict()
            for subgroup in primary_estimator.subgroup_effects(
                dataset,
                subgroup_col,
                min_rows=min_rows,
                min_group_size=min_group_size,
            )
        ]
    return {
        "rows": int(len(dataset)),
        "confounders": confounders,
        "results": results,
        "primary_sensitivity": primary_estimator.sensitivity_analysis(dataset, steps=6).to_dict(),
        "subgroups": subgroups,
    }


def main() -> None:
    real_dataset = load_monitoring_intervention_sample()
    lalonde_dataset = load_lalonde_benchmark()
    nhefs_dataset = load_nhefs_complete_benchmark()
    synthetic_dataset = generate_synthetic_observational_data()
    synthetic_dataset["severity_group"] = pd.qcut(
        synthetic_dataset["severity"],
        q=3,
        labels=["low", "mid", "high"],
        duplicates="drop",
    )
    nhefs_dataset = nhefs_dataset.copy()
    nhefs_dataset["sex_group"] = nhefs_dataset["sex"].map({0: "female", 1: "male"}).fillna("unknown")

    real_confounders = [
        "sensor_age_years",
        "maintenance_backlog_days",
        "baseline_alert_rate",
        "staffing_ratio",
    ]
    synthetic_confounders = ["age", "severity", "baseline_score"]

    output_dir = Path(__file__).resolve().parents[2] / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "causal_report.json"
    payload = {
        "real_dataset": _analyze_dataset(
            real_dataset,
            outcome_col="outcome_alert_rate",
            confounders=real_confounders,
            bootstrap_repeats=30,
            matcher_caliper=None,
            propensity_trim_bounds=None,
            subgroup_col="region",
            min_rows=8,
            min_group_size=3,
        ),
        "lalonde_public_benchmark": _analyze_dataset(
            lalonde_dataset,
            outcome_col="outcome",
            confounders=LALONDE_CONFOUNDERS,
            bootstrap_repeats=20,
            matcher_caliper=0.05,
            propensity_trim_bounds=(0.03, 0.97),
        ),
        "nhefs_public_benchmark": _analyze_dataset(
            nhefs_dataset,
            outcome_col="outcome",
            confounders=NHEFS_COMPLETE_CONFOUNDERS,
            bootstrap_repeats=20,
            matcher_caliper=0.02,
            propensity_trim_bounds=None,
            subgroup_col="sex_group",
            min_rows=200,
            min_group_size=80,
        ),
        "synthetic_validation_dataset": _analyze_dataset(
            synthetic_dataset,
            outcome_col="outcome",
            confounders=synthetic_confounders,
            bootstrap_repeats=30,
            matcher_caliper=0.02,
            propensity_trim_bounds=None,
            subgroup_col="severity_group",
            min_rows=80,
            min_group_size=20,
        ),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for dataset_key, dataset_payload in payload.items():
        export_dataset_artifacts(dataset_key, dataset_payload, output_dir)
    export_benchmark_artifacts(payload, output_dir)
    comparison = export_external_comparison_artifacts(output_dir)
    _, stability_summary = export_stability_artifacts(output_dir, quick=True)

    # Placebo/falsification test: treatment should not predict pre-treatment earnings (re74)
    placebo_confounders = [c for c in LALONDE_CONFOUNDERS if c != "re74"]
    placebo_results = run_placebo_test(
        lalonde_dataset,
        treatment_col="treatment",
        placebo_outcome="re74",
        confounders=placebo_confounders,
        bootstrap_repeats=20,
        matcher_caliper=0.05,
    )
    export_placebo_artifacts([r.to_dict() for r in placebo_results], output_dir)

    # Rosenbaum sensitivity for Lalonde matched pairs
    lalonde_matcher = PropensityMatcher(
        "treatment",
        "outcome",
        LALONDE_CONFOUNDERS,
        caliper=0.05,
        bootstrap_repeats=10,
        propensity_trim_bounds=(0.03, 0.97),
    )
    rosenbaum_results = lalonde_matcher.rosenbaum_sensitivity(lalonde_dataset)
    export_rosenbaum_artifacts([r.to_dict() for r in rosenbaum_results], output_dir)

    # Propensity overlap histograms for public benchmarks
    import numpy as np
    from causal_lens.estimators import BaseEstimator

    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    for label, ds, conf in [
        ("lalonde", lalonde_dataset, LALONDE_CONFOUNDERS),
        ("nhefs", nhefs_dataset, NHEFS_COMPLETE_CONFOUNDERS),
    ]:
        dummy = BaseEstimator("treatment", "outcome", conf)
        prep = dummy._prepare(ds)
        pscore = dummy._fit_propensity(prep)
        t_arr = prep["treatment"].to_numpy(dtype=int)
        export_propensity_overlap(
            pscore,
            t_arr,
            title=f"{label.title()} propensity score overlap",
            output_path=charts_dir / f"{label}_propensity_overlap.png",
        )

    payload["external_comparison"] = {
        "rows": int(len(comparison)),
        "all_match": bool(comparison["match"].all()),
        "datasets": sorted(comparison["dataset"].unique().tolist()),
    }
    payload["stability_analysis"] = {
        "rows": int(len(stability_summary)),
        "datasets": sorted(stability_summary["dataset"].unique().tolist()),
        "methods": sorted(stability_summary["method"].unique().tolist()),
        "quick_mode": True,
    }
    payload["placebo_test"] = {
        "outcome": "re74",
        "all_pass": all(r.passes for r in placebo_results),
        "results": [r.to_dict() for r in placebo_results],
    }
    payload["rosenbaum_sensitivity"] = {
        "dataset": "lalonde",
        "caliper": 0.05,
        "gamma_at_loss_of_significance": next(
            (r.gamma for r in rosenbaum_results if not r.significant_at_05),
            None,
        ),
        "results": [r.to_dict() for r in rosenbaum_results],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
