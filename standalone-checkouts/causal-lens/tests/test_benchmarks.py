from __future__ import annotations

from pathlib import Path

import pandas as pd

from causal_lens.reporting import benchmark_to_frame, export_benchmark_artifacts


def _sample_payload() -> dict:
    return {
        "real_dataset": {
            "results": [
                {
                    "method": "RegressionAdjustmentEstimator",
                    "estimand": "ATE",
                    "effect": -0.08,
                    "ci_low": -0.10,
                    "ci_high": -0.06,
                    "diagnostics": {
                        "overlap_ok": False,
                        "balance_before": {"x1": 2.0, "x2": 1.0},
                        "balance_after": {"x1": 2.0, "x2": 1.0},
                    },
                },
                {
                    "method": "IPWEstimator",
                    "estimand": "ATE",
                    "effect": -0.03,
                    "ci_low": -0.05,
                    "ci_high": -0.01,
                    "diagnostics": {
                        "overlap_ok": False,
                        "balance_before": {"x1": 2.0, "x2": 1.0},
                        "balance_after": {"x1": 1.5, "x2": 0.8},
                    },
                },
            ]
        },
        "lalonde_public_benchmark": {
            "results": [
                {
                    "method": "DoublyRobustEstimator",
                    "estimand": "ATE",
                    "effect": 640.0,
                    "ci_low": 120.0,
                    "ci_high": 1100.0,
                    "diagnostics": {
                        "overlap_ok": True,
                        "balance_before": {"x1": 0.9, "x2": 0.4},
                        "balance_after": {"x1": 0.2, "x2": 0.1},
                    },
                }
            ]
        },
        "synthetic_validation_dataset": {
            "results": [
                {
                    "method": "RegressionAdjustmentEstimator",
                    "estimand": "ATE",
                    "effect": 2.0,
                    "ci_low": 1.8,
                    "ci_high": 2.2,
                    "diagnostics": {
                        "overlap_ok": True,
                        "balance_before": {"x1": 0.4, "x2": 0.3},
                        "balance_after": {"x1": 0.4, "x2": 0.3},
                    },
                }
            ]
        },
    }


def test_benchmark_frame_contains_expected_columns() -> None:
    frame = benchmark_to_frame(_sample_payload())
    assert set(["dataset", "method", "effect", "ci_width", "balance_improvement"]).issubset(frame.columns)
    assert len(frame) == 4


def test_export_benchmark_artifacts_writes_files(tmp_path: Path) -> None:
    export_benchmark_artifacts(_sample_payload(), tmp_path)
    csv_path = tmp_path / "tables" / "cross_dataset_benchmark_summary.csv"
    md_path = tmp_path / "tables" / "cross_dataset_benchmark_summary.md"
    assert csv_path.exists()
    assert md_path.exists()
    frame = pd.read_csv(csv_path)
    assert len(frame) == 4
