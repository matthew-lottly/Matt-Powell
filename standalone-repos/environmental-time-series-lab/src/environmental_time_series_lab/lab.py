from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "station_histories.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REVIEW_WINDOW = 2
DEFAULT_SHORT_WINDOW = 3
DEFAULT_LONG_WINDOW = 5


def load_histories(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["series"]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    return round(
        sum(abs(actual_value - predicted_value) for actual_value, predicted_value in zip(actual, predicted, strict=True)) / len(actual),
        2,
    )


def _rolling_mean(values: Sequence[float], window: int) -> list[float]:
    means: list[float] = []
    for index in range(len(values) - window + 1):
        segment = values[index:index + window]
        means.append(round(_mean(segment), 2))
    return means


def _first_differences(values: Sequence[float]) -> list[float]:
    return [round(current - previous, 2) for previous, current in zip(values, values[1:])]


def _sample_stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return round(variance ** 0.5, 2)


def _last_value_projection(values: Sequence[float], horizon: int) -> list[float]:
    return [round(values[-1], 2) for _ in range(horizon)]


def _trailing_mean_projection(values: Sequence[float], horizon: int, window: int) -> list[float]:
    trailing_window = values[-min(window, len(values)):]
    projected_value = round(_mean(trailing_window), 2)
    return [projected_value for _ in range(horizon)]


def _drift_projection(values: Sequence[float], horizon: int) -> list[float]:
    if len(values) < 2:
        return _last_value_projection(values, horizon)
    slope = (values[-1] - values[0]) / (len(values) - 1)
    return [round(values[-1] + slope * (step + 1), 2) for step in range(horizon)]


def _candidate_review_predictions(values: Sequence[float], horizon: int) -> dict[str, list[float]]:
    return {
        "last_value": _last_value_projection(values, horizon),
        "trailing_mean_2": _trailing_mean_projection(values, horizon, window=2),
        "trailing_mean_3": _trailing_mean_projection(values, horizon, window=3),
        "drift": _drift_projection(values, horizon),
    }


def _trend_label(total_change: float) -> str:
    if total_change > 0.5:
        return "upward"
    if total_change < -0.5:
        return "downward"
    return "stable"


def _build_feature_profile(values: Sequence[float], short_window: int, long_window: int) -> dict[str, float]:
    effective_short_window = min(short_window, len(values))
    effective_long_window = min(long_window, len(values))
    first_differences = _first_differences(values)
    slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
    recent_change = first_differences[-1] if first_differences else 0.0
    return {
        "latestValue": round(values[-1], 2),
        "meanValue": round(_mean(values), 2),
        "shortRollingMean": round(_mean(values[-effective_short_window:]), 2),
        "longRollingMean": round(_mean(values[-effective_long_window:]), 2),
        "recentChange": round(recent_change, 2),
        "seriesSlope": round(slope, 2),
        "variability": _sample_stddev(values),
    }


def build_time_series_report(
    data_path: Path = DEFAULT_DATA_PATH,
    review_window: int = DEFAULT_REVIEW_WINDOW,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
    report_name: str = "Environmental Time Series Lab",
    run_label: str = "temporal-diagnostics-review",
) -> dict[str, Any]:
    histories = load_histories(data_path)
    summaries = []
    winning_baselines: Counter[str] = Counter()
    trend_labels: Counter[str] = Counter()

    for series in histories:
        values = [float(value) for value in series["values"]]
        if len(values) <= review_window:
            raise ValueError("Each series must have more observations than the review window.")

        calibration = values[:-review_window]
        review = values[-review_window:]
        feature_profile = _build_feature_profile(calibration, short_window=short_window, long_window=long_window)
        baseline_predictions = _candidate_review_predictions(calibration, review_window)
        leaderboard = [
            {
                "baseline": baseline_name,
                "reviewMae": _mae(review, predictions),
                "reviewPrediction": predictions,
            }
            for baseline_name, predictions in baseline_predictions.items()
        ]
        leaderboard.sort(key=lambda candidate: (candidate["reviewMae"], candidate["baseline"]))
        selected_baseline = leaderboard[0]["baseline"]
        winning_baselines[selected_baseline] += 1

        total_change = round(values[-1] - values[0], 2)
        trend_label = _trend_label(total_change)
        trend_labels[trend_label] += 1

        summaries.append(
            {
                "stationId": series["stationId"],
                "metric": series["metric"],
                "analysisWindow": len(calibration),
                "reviewWindow": len(review),
                "featureProfile": feature_profile,
                "rollingMeanShort": _rolling_mean(values, min(short_window, len(values))),
                "rollingMeanLong": _rolling_mean(values, min(long_window, len(values))),
                "firstDifferences": _first_differences(values),
                "trendValue": total_change,
                "trendLabel": trend_label,
                "baselineLeaderboard": leaderboard,
                "selectedBaseline": selected_baseline,
                "selectedReviewMae": leaderboard[0]["reviewMae"],
                "reviewActual": review,
                "reviewPrediction": leaderboard[0]["reviewPrediction"],
                "latestValue": values[-1],
            }
        )

    return {
        "reportName": report_name,
        "experiment": {
            "runLabel": run_label,
            "generatedAt": datetime.now(UTC).isoformat(),
            "reviewWindow": review_window,
            "shortWindow": short_window,
            "longWindow": long_window,
            "candidateBaselineCount": 4,
        },
        "summary": {
            "seriesCount": len(histories),
            "reviewWindow": review_window,
            "shortWindow": short_window,
            "longWindow": long_window,
            "averageSelectedReviewMae": round(sum(item["selectedReviewMae"] for item in summaries) / len(summaries), 2),
            "trendLabels": dict(sorted(trend_labels.items())),
            "baselineWins": dict(sorted(winning_baselines.items())),
        },
        "seriesDiagnostics": summaries,
        "notes": [
            "Designed as a public-safe temporal diagnostics workflow with split-based review windows and candidate baseline comparison.",
            "The lab captures feature profiles, rolling summaries, and baseline leaderboard output before handing off to forecasting or anomaly pipelines.",
            "The same structure can grow into decomposition, seasonal baselines, change-point detection, or external experiment tracking.",
        ],
    }


def export_time_series_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Environmental Time Series Lab",
    run_label: str = "temporal-diagnostics-review",
    review_window: int = DEFAULT_REVIEW_WINDOW,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_time_series_report(
        report_name=report_name,
        run_label=run_label,
        review_window=review_window,
        short_window=short_window,
        long_window=long_window,
    )
    output_path = output_dir / "time_series_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample time-series report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Environmental Time Series Lab", help="Display name embedded in the output report.")
    parser.add_argument("--run-label", default="temporal-diagnostics-review", help="Label stored with the experiment-style report output.")
    parser.add_argument("--review-window", type=int, default=DEFAULT_REVIEW_WINDOW, help="Number of trailing observations reserved for baseline review.")
    parser.add_argument("--short-window", type=int, default=DEFAULT_SHORT_WINDOW, help="Short rolling window used in diagnostics output.")
    parser.add_argument("--long-window", type=int, default=DEFAULT_LONG_WINDOW, help="Long rolling window used in diagnostics output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_time_series_report(
        args.output_dir,
        report_name=args.report_name,
        run_label=args.run_label,
        review_window=args.review_window,
        short_window=args.short_window,
        long_window=args.long_window,
    )
    print(f"Wrote time-series report to {output_path}")


if __name__ == "__main__":
    main()