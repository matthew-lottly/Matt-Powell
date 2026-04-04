from __future__ import annotations

import json
import importlib
from pathlib import Path

performance_checks = importlib.import_module("vp_lcp.scripts.check_performance_thresholds")


def test_evaluate_thresholds_passes() -> None:
    benchmark_payload = {
        "best_by_runtime_penalized_score": {
            "runtime_seconds": 1.0,
            "path_voxel_count": 15,
            "graph_nodes": 500,
            "informative_3d": True,
        }
    }
    thresholds = {
        "max_runtime_seconds": 2.0,
        "min_path_voxel_count": 10,
        "min_graph_nodes": 200,
        "require_informative_3d": True,
        "min_informative_count": 1,
    }
    summary_payload = {"informative_count": 1}

    failures = performance_checks.evaluate_thresholds(benchmark_payload, thresholds, summary_payload)
    assert failures == []


def test_evaluate_thresholds_reports_multiple_failures() -> None:
    benchmark_payload = {
        "best_by_runtime_penalized_score": {
            "runtime_seconds": 6.0,
            "path_voxel_count": 2,
            "graph_nodes": 50,
            "informative_3d": False,
        }
    }
    thresholds = {
        "max_runtime_seconds": 2.0,
        "min_path_voxel_count": 10,
        "min_graph_nodes": 200,
        "require_informative_3d": True,
        "min_informative_count": 1,
    }
    summary_payload = {"informative_count": 0}

    failures = performance_checks.evaluate_thresholds(benchmark_payload, thresholds, summary_payload)
    assert len(failures) == 5
    assert any("runtime_seconds=" in failure for failure in failures)
    assert any("path_voxel_count=" in failure for failure in failures)
    assert any("graph_nodes=" in failure for failure in failures)
    assert any("not informative_3d" in failure for failure in failures)
    assert any("informative_count=" in failure for failure in failures)


def test_evaluate_thresholds_requires_summary_when_requested() -> None:
    benchmark_payload = {
        "best_by_runtime_penalized_score": {
            "runtime_seconds": 1.0,
            "path_voxel_count": 15,
            "graph_nodes": 500,
            "informative_3d": True,
        }
    }
    thresholds = {"min_informative_count": 1}

    failures = performance_checks.evaluate_thresholds(benchmark_payload, thresholds, summary_payload=None)
    assert failures == ["min_informative_count is set but --summary-json was not provided"]


def test_smoke_threshold_config_is_valid_json() -> None:
    project_root = Path(__file__).resolve().parents[1]
    cfg_path = project_root / "configs" / "smoke_performance_thresholds.json"
    with cfg_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["max_runtime_seconds"] > 0
    assert payload["min_path_voxel_count"] >= 1
    assert payload["min_graph_nodes"] >= 1
