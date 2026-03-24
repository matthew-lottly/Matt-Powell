from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

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
)
from causal_lens.reporting import export_dataset_artifacts
from causal_lens.reporting import export_benchmark_artifacts
from causal_lens.synthetic import generate_synthetic_observational_data


def _analyze_dataset(
    dataset: pd.DataFrame,
    *,
    outcome_col: str,
    confounders: list[str],
    bootstrap_repeats: int,
    matcher_caliper: float | None,
    subgroup_col: str | None = None,
    min_rows: int = 0,
    min_group_size: int = 0,
) -> dict:
    primary_estimator = DoublyRobustEstimator(
        "treatment",
        outcome_col,
        confounders,
        bootstrap_repeats=bootstrap_repeats,
    )
    results = [
        estimator.fit(dataset).to_dict()
        for estimator in [
            RegressionAdjustmentEstimator("treatment", outcome_col, confounders, bootstrap_repeats=bootstrap_repeats),
            PropensityMatcher(
                "treatment",
                outcome_col,
                confounders,
                caliper=matcher_caliper,
                bootstrap_repeats=bootstrap_repeats,
            ),
            IPWEstimator("treatment", outcome_col, confounders, bootstrap_repeats=bootstrap_repeats),
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
        ),
        "nhefs_public_benchmark": _analyze_dataset(
            nhefs_dataset,
            outcome_col="outcome",
            confounders=NHEFS_COMPLETE_CONFOUNDERS,
            bootstrap_repeats=20,
            matcher_caliper=0.02,
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
            subgroup_col="severity_group",
            min_rows=80,
            min_group_size=20,
        ),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for dataset_key, dataset_payload in payload.items():
        export_dataset_artifacts(dataset_key, dataset_payload, output_dir)
    export_benchmark_artifacts(payload, output_dir)


if __name__ == "__main__":
    main()
