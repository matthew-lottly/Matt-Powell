from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "station_histories.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"


def load_histories(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["series"]


def _rolling_mean(values: list[float], window: int) -> list[float]:
    means: list[float] = []
    for index in range(len(values) - window + 1):
        segment = values[index:index + window]
        means.append(round(sum(segment) / window, 2))
    return means


def build_time_series_report(
    data_path: Path = DEFAULT_DATA_PATH,
    window: int = 3,
    report_name: str = "Environmental Time Series Lab",
) -> dict[str, Any]:
    histories = load_histories(data_path)
    summaries = []

    for series in histories:
        values = series["values"]
        trend_value = round(values[-1] - values[0], 2)
        summaries.append(
            {
                "stationId": series["stationId"],
                "metric": series["metric"],
                "rollingMean": _rolling_mean(values, window),
                "trendValue": trend_value,
                "trendLabel": "upward" if trend_value > 0.5 else "downward" if trend_value < -0.5 else "stable",
                "latestValue": values[-1],
            }
        )

    return {
        "reportName": report_name,
        "summary": {
            "seriesCount": len(histories),
            "window": window,
            "upwardTrends": sum(item["trendLabel"] == "upward" for item in summaries),
        },
        "seriesSummaries": summaries,
        "notes": [
            "Designed as a public-safe time-series analysis workflow.",
            "The same structure can grow into richer decomposition, seasonal baselines, or model-ready feature extraction.",
        ],
    }


def export_time_series_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Environmental Time Series Lab",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_time_series_report(report_name=report_name)
    output_path = output_dir / "time_series_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample time-series report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Environmental Time Series Lab", help="Display name embedded in the output report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_time_series_report(args.output_dir, report_name=args.report_name)
    print(f"Wrote time-series report to {output_path}")


if __name__ == "__main__":
    main()