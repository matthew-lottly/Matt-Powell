"""Profile a compact STRATA run and emit timing plus cProfile output."""

from __future__ import annotations

import cProfile
import json
import pstats
import time
from pathlib import Path

from hetero_conformal.experiment import ExperimentConfig, run_experiment

OUT = Path(__file__).resolve().parent.parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def time_pipeline() -> None:
    profile_path = OUT / "profile_run.prof"
    summary_path = OUT / "profile_summary.json"
    stats_path = OUT / "profile_top_functions.txt"

    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    result = run_experiment(
        ExperimentConfig(n_power=80, n_water=60, n_telecom=40, hidden_dim=32, num_layers=2, epochs=10, patience=5),
        verbose=False,
    )
    profiler.disable()
    elapsed = time.perf_counter() - t0
    profiler.dump_stats(profile_path)

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumtime")
    with stats_path.open("w", encoding="utf-8") as handle:
        stats.stream = handle
        stats.print_stats(25)

    summary_path.write_text(
        json.dumps(
            {
                "elapsed_seconds": elapsed,
                "marginal_coverage": result.marginal_cov,
                "mean_width": result.mean_width,
                "ece": result.ece,
                "profile_file": str(profile_path),
                "top_functions_file": str(stats_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote profile summary to {summary_path}")


if __name__ == "__main__":
    time_pipeline()