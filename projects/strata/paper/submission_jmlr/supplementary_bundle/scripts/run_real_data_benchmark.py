"""Run STRATA on public MATPOWER-based real-data benchmarks.

Benchmarks currently supported:
- ACTIVSg200 (200-bus Central Illinois synthetic-realistic grid)
- IEEE 118-bus test case

Usage:
    d:/GitHub/.venv/Scripts/python.exe scripts/run_real_data_benchmark.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from hetero_conformal import load_activsg200, load_ieee118
from hetero_conformal.experiment import ExperimentConfig, run_experiment

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _run_dataset(name: str, graph_loader, seed: int) -> dict[str, float | int | str]:
    graph = graph_loader(seed=seed)
    result = run_experiment(
        config=ExperimentConfig(seed=seed, epochs=100, patience=15, use_propagation_aware=True),
        verbose=False,
        graph=graph,
    )
    return {
        "dataset": name,
        "seed": seed,
        "marginal_cov": result.marginal_cov,
        "mean_width": result.mean_width,
        "ece": result.ece,
        "power_cov": result.type_cov.get("power", float("nan")),
        "water_cov": result.type_cov.get("water", float("nan")),
        "telecom_cov": result.type_cov.get("telecom", float("nan")),
    }


def main() -> None:
    rows: list[dict[str, float | int | str]] = []
    for seed in (42, 123, 456):
        rows.append(_run_dataset("ACTIVSg200", load_activsg200, seed))
        rows.append(_run_dataset("IEEE118", load_ieee118, seed))

    out_file = OUT_DIR / "real_data_benchmark.csv"
    with out_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote real-data benchmark to {out_file}")


if __name__ == "__main__":
    main()