from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def results_to_frame(results: list[dict]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for result in results:
        diagnostics = result["diagnostics"]
        balance_before = diagnostics["balance_before"]
        balance_after = diagnostics["balance_after"]
        rows.append(
            {
                "method": result["method"],
                "estimand": result["estimand"],
                "effect": result["effect"],
                "ci_low": result["ci_low"],
                "ci_high": result["ci_high"],
                "overlap_ok": diagnostics["overlap_ok"],
                "mean_abs_balance_before": sum(abs(value) for value in balance_before.values()) / len(balance_before),
                "mean_abs_balance_after": sum(abs(value) for value in balance_after.values()) / len(balance_after),
            }
        )
    return pd.DataFrame(rows)


def subgroup_to_frame(subgroups: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(subgroups)


def sensitivity_to_frame(summary: dict) -> pd.DataFrame:
    return pd.DataFrame(summary["scenarios"])


def export_dataset_artifacts(dataset_key: str, payload: dict, output_dir: Path) -> None:
    charts_dir = output_dir / "charts"
    tables_dir = output_dir / "tables"
    charts_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    results_frame = results_to_frame(payload["results"])
    sensitivity_frame = sensitivity_to_frame(payload["primary_sensitivity"])
    subgroup_frame = subgroup_to_frame(payload["subgroups"])

    results_csv = tables_dir / f"{dataset_key}_estimator_summary.csv"
    subgroup_csv = tables_dir / f"{dataset_key}_subgroup_summary.csv"
    sensitivity_csv = tables_dir / f"{dataset_key}_sensitivity_summary.csv"
    results_md = tables_dir / f"{dataset_key}_estimator_summary.md"

    results_frame.to_csv(results_csv, index=False)
    subgroup_frame.to_csv(subgroup_csv, index=False)
    sensitivity_frame.to_csv(sensitivity_csv, index=False)
    results_md.write_text(_frame_to_markdown(results_frame), encoding="utf-8")

    _plot_estimator_comparison(
        results_frame,
        title=f"{_display_name(dataset_key)} estimator comparison",
        output_path=charts_dir / f"{dataset_key}_estimator_comparison.png",
    )
    _plot_balance_summary(
        results_frame,
        title=f"{_display_name(dataset_key)} balance summary",
        output_path=charts_dir / f"{dataset_key}_balance_summary.png",
    )
    _plot_sensitivity_summary(
        sensitivity_frame,
        title=f"{_display_name(dataset_key)} sensitivity curve",
        output_path=charts_dir / f"{dataset_key}_sensitivity_curve.png",
    )
    if not subgroup_frame.empty:
        _plot_subgroup_effects(
            subgroup_frame,
            title=f"{_display_name(dataset_key)} subgroup effects",
            output_path=charts_dir / f"{dataset_key}_subgroup_effects.png",
        )


def export_benchmark_artifacts(report_payload: dict, output_dir: Path) -> None:
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    benchmark_frame = benchmark_to_frame(report_payload)
    benchmark_csv = tables_dir / "cross_dataset_benchmark_summary.csv"
    benchmark_md = tables_dir / "cross_dataset_benchmark_summary.md"
    benchmark_frame.to_csv(benchmark_csv, index=False)
    benchmark_md.write_text(_frame_to_markdown(benchmark_frame), encoding="utf-8")


def benchmark_to_frame(report_payload: dict) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for dataset_key, dataset in report_payload.items():
        if not isinstance(dataset, dict) or "results" not in dataset:
            continue
        results_frame = results_to_frame(dataset["results"]).copy()
        results_frame["dataset"] = dataset_key
        for _, row in results_frame.iterrows():
            ci_width = float(row["ci_high"] - row["ci_low"])
            rows.append(
                {
                    "dataset": dataset_key,
                    "method": row["method"],
                    "effect": float(row["effect"]),
                    "ci_width": ci_width,
                    "overlap_ok": bool(row["overlap_ok"]),
                    "mean_abs_balance_before": float(row["mean_abs_balance_before"]),
                    "mean_abs_balance_after": float(row["mean_abs_balance_after"]),
                    "balance_improvement": float(row["mean_abs_balance_before"] - row["mean_abs_balance_after"]),
                }
            )
    return pd.DataFrame(rows)


def _plot_estimator_comparison(results_frame: pd.DataFrame, title: str, output_path: Path) -> None:
    frame = results_frame.copy().sort_values("effect")
    effect = frame["effect"].astype(float).to_numpy()
    ci_low = frame["ci_low"].astype(float).to_numpy()
    ci_high = frame["ci_high"].astype(float).to_numpy()
    lower = (effect - ci_low).clip(min=0.0)
    upper = (ci_high - effect).clip(min=0.0)
    plt.figure(figsize=(8.5, 4.8))
    plt.barh(frame["method"], effect, color="#476C9B")
    plt.errorbar(effect, frame["method"], xerr=[lower, upper], fmt="none", ecolor="#1F2A44", capsize=4)
    plt.axvline(0.0, color="#A44A3F", linestyle="--", linewidth=1.6)
    plt.title(title)
    plt.xlabel("Estimated effect")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_balance_summary(results_frame: pd.DataFrame, title: str, output_path: Path) -> None:
    frame = results_frame.copy()
    x_positions = range(len(frame))
    width = 0.38
    plt.figure(figsize=(8.8, 4.8))
    plt.bar([position - width / 2 for position in x_positions], frame["mean_abs_balance_before"], width=width, label="Before", color="#C96E35")
    plt.bar([position + width / 2 for position in x_positions], frame["mean_abs_balance_after"], width=width, label="After", color="#4C8B72")
    plt.xticks(list(x_positions), frame["method"], rotation=20, ha="right")
    plt.ylabel("Mean absolute SMD")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_sensitivity_summary(sensitivity_frame: pd.DataFrame, title: str, output_path: Path) -> None:
    plt.figure(figsize=(8.5, 4.8))
    plt.plot(sensitivity_frame["bias"], sensitivity_frame["adjusted_effect"], marker="o", color="#8C4C7D", linewidth=2.0)
    plt.fill_between(
        sensitivity_frame["bias"],
        sensitivity_frame["adjusted_ci_low"],
        sensitivity_frame["adjusted_ci_high"],
        color="#D8B4D0",
        alpha=0.35,
    )
    plt.axhline(0.0, color="#A44A3F", linestyle="--", linewidth=1.6)
    plt.title(title)
    plt.xlabel("Additive bias")
    plt.ylabel("Adjusted effect")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_subgroup_effects(subgroup_frame: pd.DataFrame, title: str, output_path: Path) -> None:
    frame = subgroup_frame.copy().sort_values("effect")
    effect = frame["effect"].astype(float).to_numpy()
    ci_low = frame["ci_low"].astype(float).to_numpy()
    ci_high = frame["ci_high"].astype(float).to_numpy()
    lower = (effect - ci_low).clip(min=0.0)
    upper = (ci_high - effect).clip(min=0.0)
    y_positions = list(range(len(frame)))
    plt.figure(figsize=(9.0, 5.2))
    plt.barh(y_positions, effect, color="#5B7C99")
    plt.errorbar(effect, y_positions, xerr=[lower, upper], fmt="none", ecolor="#22324A", capsize=4)
    plt.axvline(0.0, color="#A44A3F", linestyle="--", linewidth=1.6)
    plt.title(title)
    plt.xlabel("Estimated effect")
    plt.yticks(y_positions, frame["subgroup"])
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _display_name(dataset_key: str) -> str:
    return dataset_key.replace("_", " ").title()


def _frame_to_markdown(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [header, divider]
    for _, row in frame.iterrows():
        values = [str(row[column]) for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows) + "\n"
