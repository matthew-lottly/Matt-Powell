from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "forecast_histories.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"


def load_histories(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["series"]


def _mae(actual: list[float], predicted: list[float]) -> float:
    return round(sum(abs(actual_value - predicted_value) for actual_value, predicted_value in zip(actual, predicted, strict=True)) / len(actual), 2)


def build_forecast_report(
    data_path: Path = DEFAULT_DATA_PATH,
    horizon: int = 2,
    report_name: str = "Station Forecasting Workbench",
) -> dict[str, Any]:
    histories = load_histories(data_path)
    forecasts = []

    for series in histories:
        values = series["values"]
        train = values[:-horizon]
        holdout = values[-horizon:]
        trailing_average = round(sum(train[-3:]) / 3, 2)
        predicted = [trailing_average for _ in holdout]
        forecasts.append(
            {
                "stationId": series["stationId"],
                "metric": series["metric"],
                "trainingWindow": len(train),
                "holdoutMae": _mae(holdout, predicted),
                "nextForecast": trailing_average,
                "holdoutActual": holdout,
                "holdoutPredicted": predicted,
            }
        )

    return {
        "reportName": report_name,
        "summary": {
            "seriesCount": len(histories),
            "forecastHorizon": horizon,
            "averageMae": round(sum(item["holdoutMae"] for item in forecasts) / len(forecasts), 2),
        },
        "forecasts": forecasts,
        "notes": [
            "Designed as a public-safe forecasting workflow with a baseline model.",
            "The same structure can later support model comparison, cross-validation, and richer feature sets.",
        ],
    }


def export_forecast_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Station Forecasting Workbench",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_forecast_report(report_name=report_name)
    output_path = output_dir / "station_forecast_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample station forecast report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Station Forecasting Workbench", help="Display name embedded in the output report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_forecast_report(args.output_dir, report_name=args.report_name)
    print(f"Wrote station forecast report to {output_path}")


if __name__ == "__main__":
    main()