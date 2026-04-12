from __future__ import annotations

import csv
import json
import math
import random
import statistics
import time
from html import escape
from pathlib import Path
from typing import Any, Callable, Sequence

from .equations import (
    exponential_decay,
    gaussian_decay,
    gravity_interaction,
    logistic_service_probability,
    prompt_decay,
    weighted_accessibility_score,
)
from .table import PromptTable

try:
    import numpy as _np
except ImportError:  # pragma: no cover - optional dependency
    _np = None


def _validate_observed_pairs(observed_pairs: Sequence[tuple[float, float]]) -> tuple[list[float], list[float]]:
    if not observed_pairs:
        raise ValueError("observed_pairs must not be empty")

    distances: list[float] = []
    observed: list[float] = []
    for distance, value in observed_pairs:
        distance_float = float(distance)
        value_float = float(value)
        if distance_float < 0:
            raise ValueError("observed distances must be zero or greater")
        if math.isnan(distance_float) or math.isnan(value_float):
            raise ValueError("observed_pairs must not contain NaN values")
        distances.append(distance_float)
        observed.append(value_float)
    return distances, observed


def _rmse(predicted: list[float], observed: list[float]) -> float:
    mse = sum((p - o) ** 2 for p, o in zip(predicted, observed)) / len(observed)
    return mse ** 0.5


def _predict_decay_values(
    distances: Sequence[float],
    method: str,
    *,
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> list[float]:
    if method == "power":
        return [prompt_decay(distance, scale=scale, power=power) for distance in distances]
    if method == "exponential":
        return [exponential_decay(distance, rate=rate) for distance in distances]
    if method == "gaussian":
        return [gaussian_decay(distance, sigma=sigma) for distance in distances]
    raise ValueError("method must be one of: power, exponential, gaussian")


def calibrate_decay_parameters(
    observed_pairs: Sequence[tuple[float, float]],
    method: str = "power",
    scale_candidates: Sequence[float] | None = None,
    power_candidates: Sequence[float] | None = None,
    rate_candidates: Sequence[float] | None = None,
    sigma_candidates: Sequence[float] | None = None,
) -> dict[str, float]:
    """Grid-search calibration for decay models using RMSE."""
    distances, observed = _validate_observed_pairs(observed_pairs)

    scale_grid = list(scale_candidates or [0.1, 0.25, 0.5, 1.0, 2.0, 5.0])
    power_grid = list(power_candidates or [1.0, 1.5, 2.0, 2.5, 3.0])
    rate_grid = list(rate_candidates or [0.1, 0.25, 0.5, 1.0, 2.0])
    sigma_grid = list(sigma_candidates or [0.1, 0.25, 0.5, 1.0, 2.0])

    best_rmse = float("inf")
    best: dict[str, float] = {"rmse": best_rmse}

    if method == "power":
        for scale in scale_grid:
            for power in power_grid:
                preds = _predict_decay_values(distances, method, scale=scale, power=power)
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    best_rmse = rmse
                    best = {"rmse": rmse, "scale": float(scale), "power": float(power)}
    elif method == "exponential":
        for rate in rate_grid:
            preds = _predict_decay_values(distances, method, rate=rate)
            rmse = _rmse(preds, observed)
            if rmse < best_rmse:
                best_rmse = rmse
                best = {"rmse": rmse, "rate": float(rate)}
    elif method == "gaussian":
        for sigma in sigma_grid:
            preds = _predict_decay_values(distances, method, sigma=sigma)
            rmse = _rmse(preds, observed)
            if rmse < best_rmse:
                best_rmse = rmse
                best = {"rmse": rmse, "sigma": float(sigma)}
    else:
        raise ValueError("method must be one of: power, exponential, gaussian")

    return best


def optimize_decay_parameters(
    observed_pairs: Sequence[tuple[float, float]],
    method: str = "power",
    refinement_steps: int = 12,
) -> dict[str, float]:
    """Refine decay parameters beyond the coarse grid search.

    Uses a small coordinate-descent style local search so it stays dependency-free.
    """
    if refinement_steps <= 0:
        raise ValueError("refinement_steps must be greater than zero")

    distances, observed = _validate_observed_pairs(observed_pairs)
    current = calibrate_decay_parameters(observed_pairs, method=method)

    if method == "power":
        scale = float(current["scale"])
        power = float(current["power"])
        scale_step = max(0.01, scale * 0.5)
        power_step = max(0.05, power * 0.5)
        best_rmse = float(current["rmse"])
        for _ in range(refinement_steps):
            scale_candidates = [max(1e-6, scale + scale_step * offset / 3.0) for offset in range(-3, 4)]
            power_candidates = [max(1e-6, power + power_step * offset / 3.0) for offset in range(-3, 4)]
            improved = False
            for candidate_scale in scale_candidates:
                for candidate_power in power_candidates:
                    if candidate_scale == scale and candidate_power == power:
                        continue
                    preds = _predict_decay_values(distances, method, scale=candidate_scale, power=candidate_power)
                    rmse = _rmse(preds, observed)
                    if rmse < best_rmse:
                        scale = candidate_scale
                        power = candidate_power
                        best_rmse = rmse
                        improved = True
            if not improved:
                scale_step *= 0.5
                power_step *= 0.5
            else:
                scale_step *= 0.8
                power_step *= 0.8
            if scale_step < 1e-6 and power_step < 1e-6:
                break
        return {"rmse": best_rmse, "scale": scale, "power": power}

    if method == "exponential":
        rate = float(current["rate"])
        rate_step = max(0.01, rate * 0.5)
        best_rmse = float(current["rmse"])
        for _ in range(refinement_steps):
            candidates = [max(1e-6, rate + rate_step * offset / 3.0) for offset in range(-3, 4)]
            improved = False
            for candidate_rate in candidates:
                if candidate_rate == rate:
                    continue
                preds = _predict_decay_values(distances, method, rate=candidate_rate)
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    rate = candidate_rate
                    best_rmse = rmse
                    improved = True
            rate_step *= 0.5 if not improved else 0.8
            if rate_step < 1e-6:
                break
        return {"rmse": best_rmse, "rate": rate}

    if method == "gaussian":
        sigma = float(current["sigma"])
        sigma_step = max(0.01, sigma * 0.5)
        best_rmse = float(current["rmse"])
        for _ in range(refinement_steps):
            candidates = [max(1e-6, sigma + sigma_step * offset / 3.0) for offset in range(-3, 4)]
            improved = False
            for candidate_sigma in candidates:
                if candidate_sigma == sigma:
                    continue
                preds = _predict_decay_values(distances, method, sigma=candidate_sigma)
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    sigma = candidate_sigma
                    best_rmse = rmse
                    improved = True
            sigma_step *= 0.5 if not improved else 0.8
            if sigma_step < 1e-6:
                break
        return {"rmse": best_rmse, "sigma": sigma}

    raise ValueError("method must be one of: power, exponential, gaussian")


def compare_scenarios(
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    higher_is_better: Sequence[str] | None = None,
) -> dict[str, dict[str, float | str]]:
    """Compute absolute and percent deltas for scenario metrics."""
    preferred = set(higher_is_better or [])
    keys = sorted(set(baseline_metrics) | set(candidate_metrics))
    results: dict[str, dict[str, float | str]] = {}

    for key in keys:
        baseline = float(baseline_metrics.get(key, 0.0))
        candidate = float(candidate_metrics.get(key, 0.0))
        delta = candidate - baseline
        pct = 0.0 if baseline == 0 else (delta / abs(baseline)) * 100.0
        if key in preferred:
            direction = "improved" if delta >= 0 else "worsened"
        else:
            direction = "improved" if delta <= 0 else "worsened"
        results[key] = {
            "baseline": baseline,
            "candidate": candidate,
            "delta": delta,
            "delta_percent": pct,
            "direction": direction,
        }

    return results


def sensitivity_analysis(
    model: Callable[..., float],
    base_parameters: dict[str, float],
    variation_fraction: float = 0.2,
) -> list[dict[str, float | str]]:
    """One-at-a-time sensitivity analysis around a baseline parameter set."""
    if variation_fraction <= 0:
        raise ValueError("variation_fraction must be greater than zero")

    baseline_value = float(model(**base_parameters))
    rows: list[dict[str, float | str]] = []

    for key, value in base_parameters.items():
        value = float(value)
        lower = value * (1.0 - variation_fraction)
        upper = value * (1.0 + variation_fraction)

        params_low = dict(base_parameters)
        params_high = dict(base_parameters)
        params_low[key] = lower
        params_high[key] = upper

        low_value = float(model(**params_low))
        high_value = float(model(**params_high))
        rows.append(
            {
                "parameter": key,
                "baseline_output": baseline_value,
                "low_output": low_value,
                "high_output": high_value,
                "sensitivity_span": abs(high_value - low_value),
            }
        )

    rows.sort(key=lambda item: -float(item["sensitivity_span"]))
    return rows


def monte_carlo_interval(
    model: Callable[..., float],
    parameter_bounds: dict[str, tuple[float, float]],
    iterations: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Monte Carlo simulation returning percentile intervals for model output."""
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if not parameter_bounds:
        raise ValueError("parameter_bounds must not be empty")

    rng = random.Random(seed)
    values: list[float] = []

    for _ in range(iterations):
        params: dict[str, float] = {}
        for name, (low, high) in parameter_bounds.items():
            if high < low:
                raise ValueError(f"invalid bounds for {name}: high must be >= low")
            params[name] = rng.uniform(float(low), float(high))
        values.append(float(model(**params)))

    values.sort()
    p10_index = int(0.10 * (len(values) - 1))
    p50_index = int(0.50 * (len(values) - 1))
    p90_index = int(0.90 * (len(values) - 1))

    return {
        "mean": float(statistics.fmean(values)),
        "p10": float(values[p10_index]),
        "p50": float(values[p50_index]),
        "p90": float(values[p90_index]),
        "min": float(values[0]),
        "max": float(values[-1]),
    }


def bootstrap_confidence_interval(
    values: Sequence[float],
    confidence_level: float = 0.95,
    iterations: int = 1000,
    statistic: Callable[[Sequence[float]], float] | None = None,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap confidence interval for a sample statistic."""
    if not values:
        raise ValueError("values must not be empty")
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")

    stat_func = statistic or (lambda sample: float(statistics.fmean(sample)))
    cleaned = [float(value) for value in values]
    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(iterations):
        sample = [cleaned[rng.randrange(len(cleaned))] for _ in range(len(cleaned))]
        stats.append(float(stat_func(sample)))
    stats.sort()

    alpha = (1.0 - confidence_level) / 2.0
    lower_index = int(alpha * (len(stats) - 1))
    upper_index = int((1.0 - alpha) * (len(stats) - 1))
    observed = float(stat_func(cleaned))
    return {
        "observed": observed,
        "lower": float(stats[lower_index]),
        "upper": float(stats[upper_index]),
        "confidence_level": confidence_level,
    }


def build_scenario_report(
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    *,
    baseline_name: str = "baseline",
    candidate_name: str = "candidate",
    higher_is_better: Sequence[str] | None = None,
    uncertainty: dict[str, dict[str, float]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact machine-friendly scenario comparison report."""
    metric_comparison = compare_scenarios(
        baseline_metrics,
        candidate_metrics,
        higher_is_better=higher_is_better,
    )
    improved = [name for name, item in metric_comparison.items() if item["direction"] == "improved"]
    worsened = [name for name, item in metric_comparison.items() if item["direction"] == "worsened"]
    return {
        "baseline_name": baseline_name,
        "candidate_name": candidate_name,
        "metadata": dict(metadata or {}),
        "summary": {
            "metric_count": len(metric_comparison),
            "improved_metrics": improved,
            "worsened_metrics": worsened,
        },
        "metrics": metric_comparison,
        "uncertainty": dict(uncertainty or {}),
    }


def _scenario_report_rows(report: dict[str, Any]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for metric_name, values in report.get("metrics", {}).items():
        if not isinstance(values, dict):
            continue
        rows.append(
            {
                "metric": str(metric_name),
                "baseline": float(values.get("baseline", 0.0)),
                "candidate": float(values.get("candidate", 0.0)),
                "delta": float(values.get("delta", 0.0)),
                "delta_percent": float(values.get("delta_percent", 0.0)),
                "direction": str(values.get("direction", "")),
            }
        )
    return rows


def scenario_report_table(report: dict[str, Any]) -> PromptTable:
    """Return the metric comparison section of a scenario report as a lightweight table."""
    return PromptTable.from_records(_scenario_report_rows(report))


def batch_accessibility_table(
    supply_rows: Sequence[Sequence[float]],
    travel_cost_rows: Sequence[Sequence[float]],
    decay_method: str = "power",
    *,
    row_ids: Sequence[str] | None = None,
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> PromptTable:
    scores = batch_accessibility_scores(
        supply_rows,
        travel_cost_rows,
        decay_method=decay_method,
        scale=scale,
        power=power,
        rate=rate,
        sigma=sigma,
    )
    identifiers = list(row_ids) if row_ids is not None else [str(index) for index in range(len(scores))]
    if len(identifiers) != len(scores):
        raise ValueError("row_ids must match the number of score rows")
    return PromptTable.from_records(
        {
            "row_id": row_id,
            "accessibility_score": score,
            "decay_method": decay_method,
        }
        for row_id, score in zip(identifiers, scores, strict=True)
    )


def gravity_interaction_table(
    origin_masses: Sequence[float],
    destination_masses: Sequence[float],
    generalized_costs: Sequence[float],
    *,
    row_ids: Sequence[str] | None = None,
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
    scale_factor: float = 1.0,
) -> PromptTable:
    values = vectorized_gravity_interaction(
        origin_masses,
        destination_masses,
        generalized_costs,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        scale_factor=scale_factor,
    )
    identifiers = list(row_ids) if row_ids is not None else [str(index) for index in range(len(values))]
    if len(identifiers) != len(values):
        raise ValueError("row_ids must match the number of interaction rows")
    return PromptTable.from_records(
        {
            "row_id": row_id,
            "origin_mass": float(origin_mass),
            "destination_mass": float(destination_mass),
            "generalized_cost": float(cost),
            "gravity_interaction": value,
        }
        for row_id, origin_mass, destination_mass, cost, value in zip(
            identifiers,
            origin_masses,
            destination_masses,
            generalized_costs,
            values,
            strict=True,
        )
    )


def service_probability_table(
    predictor_rows: Sequence[dict[str, float]],
    coefficients: dict[str, float],
    intercept: float = 0.0,
    *,
    row_ids: Sequence[str] | None = None,
) -> PromptTable:
    probabilities = vectorized_service_probability(predictor_rows, coefficients, intercept=intercept)
    identifiers = list(row_ids) if row_ids is not None else [str(index) for index in range(len(probabilities))]
    if len(identifiers) != len(probabilities):
        raise ValueError("row_ids must match the number of predictor rows")
    rows: list[dict[str, float | str]] = []
    for row_id, predictors, probability in zip(identifiers, predictor_rows, probabilities, strict=True):
        row: dict[str, float | str] = {"row_id": row_id, "service_probability": probability}
        for key, value in predictors.items():
            row[key] = float(value)
        rows.append(row)
    return PromptTable.from_records(rows)


def _scenario_report_svg(rows: Sequence[dict[str, float | str]]) -> str:
    if not rows:
        return ""
    max_magnitude = max(abs(float(row["delta_percent"])) for row in rows) or 1.0
    bar_rows: list[str] = []
    width = 560
    height = 36 * len(rows) + 24
    center_x = width / 2
    for index, row in enumerate(rows):
        delta_percent = float(row["delta_percent"])
        bar_width = abs(delta_percent) / max_magnitude * 220.0
        y = 18 + index * 32
        color = "#1d8f6a" if str(row["direction"]) == "improved" else "#c75050"
        x = center_x if delta_percent >= 0 else center_x - bar_width
        bar_rows.append(
            f"<text x=\"8\" y=\"{y + 12}\" font-size=\"12\" fill=\"#1f2937\">{escape(str(row['metric']))}</text>"
            f"<rect x=\"{x:.1f}\" y=\"{y}\" width=\"{bar_width:.1f}\" height=\"18\" fill=\"{color}\" rx=\"4\" />"
            f"<text x=\"{center_x + 228:.1f}\" y=\"{y + 12}\" font-size=\"12\" fill=\"#4b5563\">{delta_percent:.2f}%</text>"
        )
    return (
        f"<svg viewBox=\"0 0 {width} {height}\" width=\"100%\" height=\"{height}\" role=\"img\" aria-label=\"Metric delta percent chart\">"
        f"<line x1=\"{center_x:.1f}\" y1=\"0\" x2=\"{center_x:.1f}\" y2=\"{height}\" stroke=\"#9ca3af\" stroke-dasharray=\"4 4\" />"
        + "".join(bar_rows)
        + "</svg>"
    )


def _scenario_uncertainty_svg(uncertainty: dict[str, dict[str, float]]) -> str:
    points = [
        (metric, values)
        for metric, values in uncertainty.items()
        if {"lower", "upper"}.issubset(values)
    ]
    if not points:
        return ""

    all_values = [float(values[key]) for _, values in points for key in values if key in {"lower", "upper", "observed"}]
    min_value = min(all_values)
    max_value = max(all_values)
    span = max(max_value - min_value, 1e-9)
    width = 560
    height = 36 * len(points) + 24
    rows: list[str] = []
    for index, (metric, values) in enumerate(points):
        y = 18 + index * 32
        lower = float(values["lower"])
        upper = float(values["upper"])
        observed = float(values.get("observed", (lower + upper) / 2.0))
        start_x = 140 + ((lower - min_value) / span) * 360
        end_x = 140 + ((upper - min_value) / span) * 360
        observed_x = 140 + ((observed - min_value) / span) * 360
        rows.append(
            f"<text x=\"8\" y=\"{y + 12}\" font-size=\"12\" fill=\"#1f2937\">{escape(str(metric))}</text>"
            f"<line x1=\"{start_x:.1f}\" y1=\"{y + 9}\" x2=\"{end_x:.1f}\" y2=\"{y + 9}\" stroke=\"#2563eb\" stroke-width=\"4\" stroke-linecap=\"round\" />"
            f"<circle cx=\"{observed_x:.1f}\" cy=\"{y + 9}\" r=\"5\" fill=\"#111827\" />"
        )
    return (
        f"<svg viewBox=\"0 0 {width} {height}\" width=\"100%\" height=\"{height}\" role=\"img\" aria-label=\"Uncertainty interval chart\">"
        + "".join(rows)
        + "</svg>"
    )


def _scenario_ranking_html(rows: Sequence[dict[str, float | str]]) -> str:
    if not rows:
        return ""
    ranked = sorted(rows, key=lambda row: abs(float(row["delta_percent"])), reverse=True)
    items = "".join(
        f"<li><strong>{escape(str(row['metric']))}</strong>: {float(row['delta_percent']):.2f}% ({escape(str(row['direction']))})</li>"
        for row in ranked
    )
    return f"<ol>{items}</ol>"


def export_scenario_report(
    report: dict[str, Any],
    output_path: str | Path,
    format: str | None = None,
) -> str:
    """Write a scenario report to JSON, CSV, Markdown, or HTML."""
    path = Path(output_path)
    resolved_format = (format or path.suffix.lstrip(".")).lower()
    if resolved_format == "md":
        resolved_format = "markdown"
    if resolved_format not in {"json", "csv", "html", "markdown"}:
        raise ValueError("format must be one of: json, csv, markdown, html")

    path.parent.mkdir(parents=True, exist_ok=True)
    if resolved_format == "json":
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        return str(path)

    rows = _scenario_report_rows(report)
    if resolved_format == "csv":
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["metric", "baseline", "candidate", "delta", "delta_percent", "direction"],
            )
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    if resolved_format == "markdown":
        summary = report.get("summary", {})
        lines = [
            f"# Scenario Report: {report.get('baseline_name', 'baseline')} vs {report.get('candidate_name', 'candidate')}",
            "",
            f"Metrics compared: {int(summary.get('metric_count', 0))}",
            "",
            "| Metric | Baseline | Candidate | Delta | Delta % | Direction |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
        lines.extend(
            f"| {row['metric']} | {row['baseline']:.6g} | {row['candidate']:.6g} | {row['delta']:.6g} | {row['delta_percent']:.3f} | {row['direction']} |"
            for row in rows
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    summary = report.get("summary", {})
    metadata = report.get("metadata", {})
    uncertainty = report.get("uncertainty", {})
    baseline_name = escape(str(report.get("baseline_name", "baseline")))
    candidate_name = escape(str(report.get("candidate_name", "candidate")))
    title = escape(f"Scenario Report: {baseline_name} vs {candidate_name}")
    metadata_items = "".join(
        f"<li><strong>{escape(str(key))}</strong>: {escape(str(value))}</li>" for key, value in metadata.items()
    )
    uncertainty_items = "".join(
        f"<li><strong>{escape(str(key))}</strong>: {escape(json.dumps(value, sort_keys=True))}</li>"
        for key, value in uncertainty.items()
    )
    chart_html = _scenario_report_svg(rows)
    uncertainty_chart_html = _scenario_uncertainty_svg(uncertainty)
    ranking_html = _scenario_ranking_html(rows)
    row_html = "".join(
        "<tr>"
        f"<td>{escape(str(row['metric']))}</td>"
        f"<td>{row['baseline']:.6g}</td>"
        f"<td>{row['candidate']:.6g}</td>"
        f"<td>{row['delta']:.6g}</td>"
        f"<td>{row['delta_percent']:.3f}</td>"
        f"<td>{escape(str(row['direction']))}</td>"
        "</tr>"
        for row in rows
    )
    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{title}</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 2rem; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 0.5rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.6rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .pill {{ display: inline-block; padding: 0.2rem 0.55rem; margin-right: 0.4rem; border-radius: 999px; background: #e5f3ff; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
    <p><span class=\"pill\">metrics: {int(summary.get('metric_count', 0))}</span>
    <span class=\"pill\">improved: {len(summary.get('improved_metrics', []))}</span>
    <span class=\"pill\">worsened: {len(summary.get('worsened_metrics', []))}</span></p>
  <h2>Metrics</h2>
    {chart_html}
  <table>
    <thead>
      <tr><th>Metric</th><th>Baseline</th><th>Candidate</th><th>Delta</th><th>Delta %</th><th>Direction</th></tr>
    </thead>
    <tbody>{row_html}</tbody>
  </table>
    <h2>Top Metric Changes</h2>
    {ranking_html}
  <h2>Metadata</h2>
  <ul>{metadata_items}</ul>
  <h2>Uncertainty</h2>
    {uncertainty_chart_html}
  <ul>{uncertainty_items}</ul>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)


def vectorized_decay(
    distance_values: Sequence[float],
    method: str = "power",
    *,
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> list[float]:
    """Evaluate decay over many distances, using NumPy when available."""
    cleaned = [float(value) for value in distance_values]
    if any(value < 0 for value in cleaned):
        raise ValueError("distance_values must be zero or greater")

    if _np is None:
        return _predict_decay_values(cleaned, method, scale=scale, power=power, rate=rate, sigma=sigma)

    arr = _np.asarray(cleaned, dtype=float)
    if method == "power":
        if scale <= 0 or power <= 0:
            raise ValueError("scale and power must be greater than zero")
        return [float(value) for value in _np.power(1.0 + arr / scale, -power).tolist()]
    if method == "exponential":
        if rate <= 0:
            raise ValueError("rate must be greater than zero")
        return [float(value) for value in _np.exp(-rate * arr).tolist()]
    if method == "gaussian":
        if sigma <= 0:
            raise ValueError("sigma must be greater than zero")
        return [float(value) for value in _np.exp(-(arr**2) / (2.0 * sigma**2)).tolist()]
    raise ValueError("method must be one of: power, exponential, gaussian")


def vectorized_gravity_interaction(
    origin_masses: Sequence[float],
    destination_masses: Sequence[float],
    generalized_costs: Sequence[float],
    *,
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
    scale_factor: float = 1.0,
) -> list[float]:
    """Evaluate gravity interaction across many OD pairs."""
    if len(origin_masses) != len(destination_masses) or len(origin_masses) != len(generalized_costs):
        raise ValueError("origin_masses, destination_masses, and generalized_costs must have the same length")

    origins = [float(value) for value in origin_masses]
    destinations = [float(value) for value in destination_masses]
    costs = [float(value) for value in generalized_costs]
    if any(value < 0 for value in origins) or any(value < 0 for value in destinations):
        raise ValueError("origin_masses and destination_masses must be zero or greater")
    if any(value <= 0 for value in costs):
        raise ValueError("generalized_costs must be greater than zero")

    if _np is None:
        return [
            gravity_interaction(
                origin,
                destination,
                cost,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
                scale_factor=scale_factor,
            )
            for origin, destination, cost in zip(origins, destinations, costs)
        ]

    origin_arr = _np.asarray(origins, dtype=float)
    destination_arr = _np.asarray(destinations, dtype=float)
    cost_arr = _np.asarray(costs, dtype=float)
    values = scale_factor * _np.power(origin_arr, alpha) * _np.power(destination_arr, beta) / _np.power(cost_arr, gamma)
    return [float(value) for value in values.tolist()]


def vectorized_service_probability(
    predictor_rows: Sequence[dict[str, float]],
    coefficients: dict[str, float],
    intercept: float = 0.0,
) -> list[float]:
    """Evaluate logistic service probability for many predictor rows."""
    rows = [{key: float(value) for key, value in row.items()} for row in predictor_rows]
    coefficient_items = [(name, float(value)) for name, value in coefficients.items()]

    if _np is None:
        return [logistic_service_probability(row, coefficients, intercept=intercept) for row in rows]

    if not rows:
        return []
    coefficient_names = [name for name, _ in coefficient_items]
    design = _np.asarray([[row.get(name, 0.0) for name in coefficient_names] for row in rows], dtype=float)
    beta = _np.asarray([value for _, value in coefficient_items], dtype=float)
    linear = design @ beta + float(intercept)
    positive_mask = linear >= 0
    probabilities = _np.empty_like(linear, dtype=float)
    probabilities[positive_mask] = 1.0 / (1.0 + _np.exp(-linear[positive_mask]))
    negative_linear = linear[~positive_mask]
    negative_exp = _np.exp(negative_linear)
    probabilities[~positive_mask] = negative_exp / (1.0 + negative_exp)
    return [float(value) for value in probabilities.tolist()]


def batch_accessibility_scores(
    supply_rows: Sequence[Sequence[float]],
    travel_cost_rows: Sequence[Sequence[float]],
    decay_method: str = "power",
    *,
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> list[float]:
    """Evaluate accessibility scores for many origins against shared destination supplies."""
    if len(supply_rows) != len(travel_cost_rows):
        raise ValueError("supply_rows and travel_cost_rows must have the same length")

    supplies = [[float(value) for value in row] for row in supply_rows]
    costs = [[float(value) for value in row] for row in travel_cost_rows]
    for supply_row, cost_row in zip(supplies, costs):
        if len(supply_row) != len(cost_row):
            raise ValueError("each supply row must match its travel cost row length")

    if _np is None:
        return [
            weighted_accessibility_score(
                supply_row,
                cost_row,
                decay_method=decay_method,
                scale=scale,
                power=power,
                rate=rate,
                sigma=sigma,
            )
            for supply_row, cost_row in zip(supplies, costs)
        ]

    supply_arr = _np.asarray(supplies, dtype=float)
    cost_arr = _np.asarray(costs, dtype=float)
    if _np.any(cost_arr < 0):
        raise ValueError("travel_cost_rows must be zero or greater")
    if decay_method == "power":
        if scale <= 0 or power <= 0:
            raise ValueError("scale and power must be greater than zero")
        decay = _np.power(1.0 + cost_arr / scale, -power)
    elif decay_method == "exponential":
        if rate <= 0:
            raise ValueError("rate must be greater than zero")
        decay = _np.exp(-rate * cost_arr)
    elif decay_method == "gaussian":
        if sigma <= 0:
            raise ValueError("sigma must be greater than zero")
        decay = _np.exp(-(cost_arr**2) / (2.0 * sigma**2))
    else:
        raise ValueError("decay_method must be one of: power, exponential, gaussian")
    return [float(value) for value in (supply_arr * decay).sum(axis=1).tolist()]


def validate_numeric_series(
    values: Sequence[float],
    *,
    name: str = "values",
    min_value: float | None = None,
    max_value: float | None = None,
    allow_nan: bool = False,
) -> list[float]:
    """Validate numeric sequences for downstream modeling and reporting."""
    cleaned: list[float] = []
    for raw in values:
        value = float(raw)
        if math.isnan(value):
            if allow_nan:
                cleaned.append(value)
                continue
            raise ValueError(f"{name} must not contain NaN values")
        if min_value is not None and value < min_value:
            raise ValueError(f"{name} values must be >= {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"{name} values must be <= {max_value}")
        cleaned.append(value)
    return cleaned


_DISTANCE_FACTORS: dict[tuple[str, str], float] = {
    ("m", "km"): 0.001,
    ("km", "m"): 1000.0,
    ("m", "mi"): 1.0 / 1609.344,
    ("mi", "m"): 1609.344,
    ("km", "mi"): 1.0 / 1.609344,
    ("mi", "km"): 1.609344,
}

_FLOW_FACTORS: dict[tuple[str, str], float] = {
    ("gpm", "lps"): 0.0630902,
    ("lps", "gpm"): 1.0 / 0.0630902,
    ("m3s", "lps"): 1000.0,
    ("lps", "m3s"): 0.001,
}


def normalize_units(value: float, from_unit: str, to_unit: str, quantity: str = "distance") -> float:
    """Normalize values across supported distance and flow units."""
    if from_unit == to_unit:
        return float(value)

    if quantity == "distance":
        factor = _DISTANCE_FACTORS.get((from_unit, to_unit))
    elif quantity == "flow":
        factor = _FLOW_FACTORS.get((from_unit, to_unit))
    else:
        raise ValueError("quantity must be 'distance' or 'flow'")

    if factor is None:
        raise ValueError(f"unsupported conversion: {quantity} {from_unit} -> {to_unit}")

    return float(value) * factor


def benchmark_function(
    func: Callable[..., Any],
    *args: Any,
    repeats: int = 5,
    **kwargs: Any,
) -> dict[str, float]:
    """Small benchmark helper returning min/max/mean runtime in seconds."""
    if repeats <= 0:
        raise ValueError("repeats must be greater than zero")

    durations: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        func(*args, **kwargs)
        durations.append(time.perf_counter() - started)

    return {
        "runs": float(repeats),
        "min_seconds": min(durations),
        "max_seconds": max(durations),
        "mean_seconds": float(statistics.fmean(durations)),
    }


__all__ = [
    "batch_accessibility_table",
    "batch_accessibility_scores",
    "benchmark_function",
    "bootstrap_confidence_interval",
    "build_scenario_report",
    "calibrate_decay_parameters",
    "compare_scenarios",
    "export_scenario_report",
    "gravity_interaction_table",
    "monte_carlo_interval",
    "normalize_units",
    "optimize_decay_parameters",
    "scenario_report_table",
    "sensitivity_analysis",
    "service_probability_table",
    "validate_numeric_series",
    "vectorized_decay",
    "vectorized_gravity_interaction",
    "vectorized_service_probability",
]
