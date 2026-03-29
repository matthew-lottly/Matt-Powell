"""Compare baseline STRATA calibration methods on public real-data graphs."""

from __future__ import annotations

import csv
from pathlib import Path

from hetero_conformal import load_activsg200, load_ieee118
from hetero_conformal.experiment import ExperimentConfig, run_experiment

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _run(name: str, loader, seed: int, propagation: bool) -> dict[str, float | int | str]:
    graph = loader(seed=seed)
    result = run_experiment(
        ExperimentConfig(
            seed=seed,
            epochs=100,
            patience=15,
            use_propagation_aware=propagation,
            neighborhood_weight=0.3,
        ),
        graph=graph,
        verbose=False,
    )
    return {
        "dataset": name,
        "method": "chmp" if propagation else "mondrian",
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
        for propagation in (False, True):
            rows.append(_run("ACTIVSg200", load_activsg200, seed, propagation))
            rows.append(_run("IEEE118", load_ieee118, seed, propagation))

    out_file = OUT_DIR / "real_method_comparison.csv"
    with out_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote real-data method comparison to {out_file}")


if __name__ == "__main__":
    main()