"""Fail CI when benchmark outputs fall outside accepted performance thresholds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_thresholds(
    benchmark_payload: dict,
    thresholds: dict,
    summary_payload: dict | None = None,
) -> list[str]:
    failures: list[str] = []

    best = benchmark_payload.get("best_by_runtime_penalized_score")
    if best is None:
        failures.append("benchmark_results.json has no best_by_runtime_penalized_score row")
        return failures

    max_runtime_seconds = thresholds.get("max_runtime_seconds")
    if max_runtime_seconds is not None:
        runtime = float(best.get("runtime_seconds", 0.0))
        if runtime > float(max_runtime_seconds):
            failures.append(
                f"runtime_seconds={runtime:.6f} exceeds max_runtime_seconds={float(max_runtime_seconds):.6f}"
            )

    min_path_voxel_count = thresholds.get("min_path_voxel_count")
    if min_path_voxel_count is not None:
        path_voxels = int(best.get("path_voxel_count", 0))
        if path_voxels < int(min_path_voxel_count):
            failures.append(
                f"path_voxel_count={path_voxels} is below min_path_voxel_count={int(min_path_voxel_count)}"
            )

    min_graph_nodes = thresholds.get("min_graph_nodes")
    if min_graph_nodes is not None:
        graph_nodes = int(best.get("graph_nodes", 0))
        if graph_nodes < int(min_graph_nodes):
            failures.append(
                f"graph_nodes={graph_nodes} is below min_graph_nodes={int(min_graph_nodes)}"
            )

    require_informative = bool(thresholds.get("require_informative_3d", False))
    if require_informative and not bool(best.get("informative_3d", False)):
        failures.append("best benchmark row is not informative_3d=true")

    min_informative_count = thresholds.get("min_informative_count")
    if min_informative_count is not None:
        if summary_payload is None:
            failures.append("min_informative_count is set but --summary-json was not provided")
        else:
            informative_count = int(summary_payload.get("informative_count", 0))
            if informative_count < int(min_informative_count):
                failures.append(
                    "informative_count="
                    f"{informative_count} is below min_informative_count={int(min_informative_count)}"
                )

    return failures


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Check benchmark outputs against performance thresholds.",
    )
    parser.add_argument(
        "--benchmark-json",
        required=True,
        help="Path to benchmark_results.json produced by benchmark_real_tile.",
    )
    parser.add_argument(
        "--thresholds",
        required=True,
        help="Path to thresholds JSON.",
    )
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Optional path to three_d_summary.json for informative-count checks.",
    )
    args = parser.parse_args(argv)

    benchmark_payload = _load_json(args.benchmark_json)
    thresholds = _load_json(args.thresholds)
    summary_payload = _load_json(args.summary_json) if args.summary_json else None

    failures = evaluate_thresholds(benchmark_payload, thresholds, summary_payload)
    if failures:
        print("Performance threshold check failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("Performance threshold check passed.")
    print(f"Benchmark: {args.benchmark_json}")
    print(f"Thresholds: {args.thresholds}")
    if args.summary_json:
        print(f"Summary: {args.summary_json}")


if __name__ == "__main__":
    main()
