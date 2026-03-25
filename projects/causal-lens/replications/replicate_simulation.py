#!/usr/bin/env python
"""Run the Monte Carlo simulation study and export summary tables.

Evaluates bias, RMSE, coverage, and SE calibration across five DGPs
and multiple sample sizes.  True effect = 2.0.

Usage:
    python replications/replicate_simulation.py          # quick (≈ 5 min)
    python replications/replicate_simulation.py --full   # full  (≈ 45 min)
"""
from __future__ import annotations

import sys
from pathlib import Path

from causal_lens import SimulationConfig, run_simulation, summarize_simulation

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    full = "--full" in sys.argv
    if full:
        config = SimulationConfig(
            n_replications=200,
            bootstrap_repeats=15,
            verbose=True,
            progress_every=10,
        )
        print("Running FULL simulation (200 reps × 5 DGPs × 3 sample sizes)...\n")
    else:
        config = SimulationConfig(
            n_replications=10,
            sample_sizes=(200,),
            bootstrap_repeats=2,
            verbose=True,
            progress_every=5,
        )
        print("Running QUICK simulation (10 reps × 5 DGPs × 1 sample size)...\n")

    raw = run_simulation(config)
    summary = summarize_simulation(raw)

    raw.to_csv(OUTPUT_DIR / "simulation_raw.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "simulation_summary.csv", index=False)

    # Print summary table grouped by DGP
    for dgp in summary["dgp"].unique():
        print(f"--- {dgp} ---")
        sub = summary[summary["dgp"] == dgp][
            ["estimator", "n", "bias", "rmse", "coverage", "se_ratio"]
        ]
        print(sub.to_string(index=False))
        print()

    print(f"Outputs written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
