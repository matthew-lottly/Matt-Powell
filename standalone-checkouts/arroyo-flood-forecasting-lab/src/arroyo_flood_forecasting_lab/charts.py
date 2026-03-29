from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


CHART_FILENAMES = {
    "hydrograph": "hydrograph-overview.png",
    "lag_diagnostics": "lag-diagnostics.png",
    "pmse": "pmse-by-order.png",
    "holdout": "holdout-forecast-comparison.png",
    "exceedance": "threshold-exceedance-probability.png",
    "comparison": "wavelet-benefit-comparison.png",
}


def _parse_timestamps(timestamps: list[str]) -> list[datetime]:
    return [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps]


def _save_figure(figure: plt.Figure, output_path: Path) -> None:
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _export_hydrograph_chart(
    output_path: Path,
    timestamps: list[datetime],
    raw_series: np.ndarray,
    denoised_series: np.ndarray,
    holdout_count: int,
    review_threshold_ft: float,
) -> None:
    figure, axis = plt.subplots(figsize=(11, 5.5))
    axis.plot(timestamps, raw_series, color="#5d6d7e", linewidth=2.0, label="Raw stage")
    axis.plot(timestamps, denoised_series, color="#1e6f5c", linewidth=2.2, label="Denoised stage")
    axis.axhline(review_threshold_ft, color="#b04a2d", linestyle="--", linewidth=1.8, label="Review threshold")
    axis.axvspan(timestamps[-holdout_count], timestamps[-1], color="#d8a21d", alpha=0.12, label="Holdout window")
    axis.set_title("Hydrograph Overview")
    axis.set_ylabel("Stage (ft)")
    axis.legend(loc="best")
    axis.grid(alpha=0.25)
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    _save_figure(figure, output_path)


def _export_pmse_chart(output_path: Path, report: dict[str, Any]) -> None:
    raw_candidates = report["candidateModels"]["raw"]["candidates"]
    denoised_candidates = report["candidateModels"]["denoised"]["candidates"]
    orders = [candidate["order"] for candidate in raw_candidates]
    raw_pmse = [candidate["pmse"] for candidate in raw_candidates]
    denoised_pmse = [candidate["pmse"] for candidate in denoised_candidates]

    figure, axis = plt.subplots(figsize=(9, 5))
    axis.plot(orders, raw_pmse, marker="o", linewidth=2.2, color="#5d6d7e", label="Raw signal")
    axis.plot(orders, denoised_pmse, marker="o", linewidth=2.2, color="#1e6f5c", label="Denoised signal")
    axis.set_title("PMSE by AR Order")
    axis.set_xlabel("AR order")
    axis.set_ylabel("PMSE")
    axis.set_xticks(orders)
    axis.grid(alpha=0.25)
    axis.legend(loc="best")
    _save_figure(figure, output_path)


def _plot_lag_panel(axis: plt.Axes, values: list[float], title: str) -> None:
    lags = np.arange(1, len(values) + 1)
    axis.axhline(0.0, color="#55606e", linewidth=1.0)
    axis.vlines(lags, 0.0, values, colors="#1e6f5c", linewidth=2.0)
    axis.scatter(lags, values, color="#d8a21d", s=36, zorder=3)
    axis.set_title(title)
    axis.set_xticks(lags)
    axis.grid(alpha=0.2)


def _export_lag_chart(output_path: Path, report: dict[str, Any]) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True, sharey=True)
    _plot_lag_panel(axes[0, 0], report["lagDiagnostics"]["raw"]["acf"], "Raw ACF")
    _plot_lag_panel(axes[0, 1], report["lagDiagnostics"]["raw"]["pacf"], "Raw PACF")
    _plot_lag_panel(axes[1, 0], report["lagDiagnostics"]["denoised"]["acf"], "Denoised ACF")
    _plot_lag_panel(axes[1, 1], report["lagDiagnostics"]["denoised"]["pacf"], "Denoised PACF")
    figure.suptitle("Lag Diagnostics")
    _save_figure(figure, output_path)


def _export_holdout_chart(output_path: Path, report: dict[str, Any], holdout_timestamps: list[datetime]) -> None:
    actual = report["hydrographProfile"]["rawStageTail"]
    raw_best = report["candidateModels"]["raw"]["candidates"][0]["forecast"]
    denoised_best = report["candidateModels"]["denoised"]["candidates"][0]["forecast"]
    median = report["monteCarlo"]["medianForecast"]
    p10 = report["monteCarlo"]["p10Forecast"]
    p90 = report["monteCarlo"]["p90Forecast"]
    review_threshold = report["summary"]["reviewThresholdFt"]

    figure, axis = plt.subplots(figsize=(11, 5.5))
    axis.plot(holdout_timestamps, actual, color="#28323c", linewidth=2.3, marker="o", label="Observed holdout")
    axis.plot(holdout_timestamps, raw_best, color="#5d6d7e", linewidth=2.0, label="Best raw forecast")
    axis.plot(holdout_timestamps, denoised_best, color="#1e6f5c", linewidth=2.0, label="Best denoised forecast")
    axis.plot(holdout_timestamps, median, color="#d8a21d", linewidth=2.2, linestyle="--", label="Monte Carlo median")
    axis.fill_between(holdout_timestamps, p10, p90, color="#d8a21d", alpha=0.18, label="P10-P90 band")
    axis.axhline(review_threshold, color="#b04a2d", linestyle="--", linewidth=1.6, label="Review threshold")
    axis.set_title("Holdout Forecast Comparison")
    axis.set_ylabel("Stage (ft)")
    axis.grid(alpha=0.25)
    axis.legend(loc="best")
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    _save_figure(figure, output_path)


def _export_exceedance_chart(output_path: Path, report: dict[str, Any]) -> None:
    probabilities = report["monteCarlo"]["reviewThresholdExceedanceProbability"]
    horizon = np.arange(1, len(probabilities) + 1)

    figure, axis = plt.subplots(figsize=(9, 4.8))
    axis.plot(horizon, probabilities, color="#b04a2d", marker="o", linewidth=2.2)
    axis.fill_between(horizon, probabilities, 0.0, color="#b04a2d", alpha=0.12)
    axis.set_title("Review-Threshold Exceedance Probability")
    axis.set_xlabel("Forecast hour")
    axis.set_ylabel("Probability")
    axis.set_ylim(0.0, 1.0)
    axis.set_xticks(horizon)
    axis.grid(alpha=0.25)
    _save_figure(figure, output_path)


def export_comparison_chart(output_dir: Path, chart_dirname: str, comparison_report: dict[str, Any]) -> str:
    chart_dir = output_dir / chart_dirname
    chart_dir.mkdir(parents=True, exist_ok=True)
    output_path = chart_dir / CHART_FILENAMES["comparison"]
    sites = comparison_report["sites"]
    labels = [site["siteCode"] for site in sites]
    volatility = [site["hourToHourVolatility"] for site in sites]
    wavelet_benefit = [site["waveletPmseBenefit"] for site in sites]

    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    axes[0].bar(labels, volatility, color=["#5d6d7e", "#1e6f5c"])
    axes[0].set_title("Hour-to-Hour Volatility")
    axes[0].set_ylabel("Std. dev. of hourly change")
    axes[0].grid(axis="y", alpha=0.25)

    bar_colors = ["#1e6f5c" if value >= 0 else "#b04a2d" for value in wavelet_benefit]
    axes[1].bar(labels, wavelet_benefit, color=bar_colors)
    axes[1].axhline(0.0, color="#55606e", linewidth=1.0)
    axes[1].set_title("Wavelet PMSE Benefit")
    axes[1].set_ylabel("Raw PMSE - denoised PMSE")
    axes[1].grid(axis="y", alpha=0.25)

    figure.suptitle("Cross-Site Wavelet Benefit Review")
    _save_figure(figure, output_path)
    return f"{chart_dirname}/{CHART_FILENAMES['comparison']}"


def export_chart_pack(
    output_dir: Path,
    chart_dirname: str,
    report: dict[str, Any],
    timestamps: list[str],
    raw_series: np.ndarray,
    denoised_series: np.ndarray,
    review_threshold_ft: float,
) -> list[str]:
    chart_dir = output_dir / chart_dirname
    chart_dir.mkdir(parents=True, exist_ok=True)
    parsed_timestamps = _parse_timestamps(timestamps)
    holdout_count = int(report["summary"]["holdoutCount"])
    holdout_timestamps = parsed_timestamps[-holdout_count:]

    hydrograph_path = chart_dir / CHART_FILENAMES["hydrograph"]
    _export_hydrograph_chart(hydrograph_path, parsed_timestamps, raw_series, denoised_series, holdout_count, review_threshold_ft)

    lag_path = chart_dir / CHART_FILENAMES["lag_diagnostics"]
    _export_lag_chart(lag_path, report)

    pmse_path = chart_dir / CHART_FILENAMES["pmse"]
    _export_pmse_chart(pmse_path, report)

    holdout_path = chart_dir / CHART_FILENAMES["holdout"]
    _export_holdout_chart(holdout_path, report, holdout_timestamps)

    exceedance_path = chart_dir / CHART_FILENAMES["exceedance"]
    _export_exceedance_chart(exceedance_path, report)

    return [
        f"{chart_dirname}/{CHART_FILENAMES['hydrograph']}",
        f"{chart_dirname}/{CHART_FILENAMES['lag_diagnostics']}",
        f"{chart_dirname}/{CHART_FILENAMES['pmse']}",
        f"{chart_dirname}/{CHART_FILENAMES['holdout']}",
        f"{chart_dirname}/{CHART_FILENAMES['exceedance']}",
    ]