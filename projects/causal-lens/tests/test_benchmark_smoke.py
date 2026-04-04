from __future__ import annotations

from pathlib import Path

from causal_lens.cli import _analyze_dataset
from causal_lens.data import LALONDE_CONFOUNDERS, load_lalonde_benchmark, load_monitoring_intervention_sample
from causal_lens.reporting import export_benchmark_artifacts


REAL_CONFOUNDERS = [
    "sensor_age_years",
    "maintenance_backlog_days",
    "baseline_alert_rate",
    "staffing_ratio",
]


def test_export_benchmark_artifacts_writes_cross_dataset_summary(tmp_path: Path) -> None:
    real_payload = _analyze_dataset(
        load_monitoring_intervention_sample(),
        outcome_col="outcome_alert_rate",
        confounders=REAL_CONFOUNDERS,
        bootstrap_repeats=5,
        matcher_caliper=None,
        subgroup_col="region",
        min_rows=3,
        min_group_size=1,
    )
    lalonde_payload = _analyze_dataset(
        load_lalonde_benchmark(),
        outcome_col="outcome",
        confounders=LALONDE_CONFOUNDERS,
        bootstrap_repeats=5,
        matcher_caliper=0.05,
        propensity_trim_bounds=(0.03, 0.97),
    )

    export_benchmark_artifacts(
        {
            "real_dataset": real_payload,
            "lalonde_public_benchmark": lalonde_payload,
        },
        tmp_path,
    )

    csv_path = tmp_path / "tables" / "cross_dataset_benchmark_summary.csv"
    md_path = tmp_path / "tables" / "cross_dataset_benchmark_summary.md"

    assert csv_path.exists()
    assert md_path.exists()
    assert "real_dataset" in csv_path.read_text(encoding="utf-8")
    assert "lalonde_public_benchmark" in md_path.read_text(encoding="utf-8")
