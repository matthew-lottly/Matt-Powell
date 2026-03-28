"""Run a compact ablation sweep and save a CSV summary."""

from __future__ import annotations

import csv
from pathlib import Path

from hetero_conformal.experiment import ExperimentConfig, run_ablation_study


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = run_ablation_study(
        base_config=ExperimentConfig(epochs=80, patience=10),
        alphas=[0.05, 0.10, 0.15, 0.20],
        seeds=[42, 123, 456],
    )

    out_file = out_dir / "ablation_results.csv"
    with out_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["seed", "alpha", "marginal_cov", "mean_width", "ece"])
        for result in results:
            writer.writerow([
                result.config.seed,
                result.config.alpha,
                result.marginal_cov,
                result.mean_width,
                result.ece,
            ])
    print(f"Wrote ablation results to {out_file}")


if __name__ == "__main__":
    main()
