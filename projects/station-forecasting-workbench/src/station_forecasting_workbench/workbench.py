from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from station_forecasting_workbench.workflow_base import ReportWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "forecast_histories.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REGISTRY_NAME = "run_registry.json"
DEFAULT_VALIDATION_HORIZON = 1
DEFAULT_TEST_HORIZON = 1
DEFAULT_PROJECTION_HORIZON = 3


def load_histories(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["series"]


def _mae(actual: list[float], predicted: list[float]) -> float:
    return round(
        sum(abs(actual_value - predicted_value) for actual_value, predicted_value in zip(actual, predicted, strict=True)) / len(actual),
        2,
    )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _sample_stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return round(variance ** 0.5, 2)


def _trailing_average_forecast(values: list[float], horizon: int, window: int = 3) -> list[float]:
    trailing_average = round(_mean(values[-window:]), 2)
    return [trailing_average for _ in range(horizon)]


def _last_value_forecast(values: list[float], horizon: int) -> list[float]:
    return [round(values[-1], 2) for _ in range(horizon)]


def _drift_forecast(values: list[float], horizon: int) -> list[float]:
    if len(values) < 2:
        return _last_value_forecast(values, horizon)
    slope = (values[-1] - values[0]) / (len(values) - 1)
    return [round(values[-1] + slope * (step + 1), 2) for step in range(horizon)]


def _linear_regression_forecast(values: list[float], horizon: int) -> list[float]:
    if len(values) < 2:
        return _last_value_forecast(values, horizon)

    x_values = list(range(len(values)))
    x_mean = _mean(x_values)
    y_mean = _mean(values)
    numerator = sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(x_values, values, strict=True))
    denominator = sum((x_value - x_mean) ** 2 for x_value in x_values)
    slope = numerator / denominator if denominator else 0.0
    intercept = y_mean - slope * x_mean
    return [round(intercept + slope * (len(values) + step), 2) for step in range(horizon)]


def _build_feature_profile(values: list[float]) -> dict[str, float]:
    trailing_window = values[-3:]
    slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
    return {
        "lastValue": round(values[-1], 2),
        "trailingMean3": round(_mean(trailing_window), 2),
        "trailingStdDev3": _sample_stddev(trailing_window),
        "momentum1": round(values[-1] - values[-2], 2),
        "seriesSlope": round(slope, 2),
    }


def _candidate_predictions(values: list[float], horizon: int) -> dict[str, list[float]]:
    return {
        "last_value": _last_value_forecast(values, horizon),
        "trailing_average_3": _trailing_average_forecast(values, horizon),
        "drift": _drift_forecast(values, horizon),
        "linear_regression": _linear_regression_forecast(values, horizon),
    }


def _feature_set_for_model(model_name: str) -> str:
    if model_name in {"drift", "linear_regression"}:
        return "trend_profile"
    return "recent_level"


def _split_series(values: list[float], validation_horizon: int, test_horizon: int) -> tuple[list[float], list[float], list[float]]:
    train_end = len(values) - validation_horizon - test_horizon
    train = values[:train_end]
    validation = values[train_end:train_end + validation_horizon]
    test = values[-test_horizon:]
    return train, validation, test


@dataclass(slots=True)
class ForecastWorkbench(ReportWorkflow):
    data_path: Path = DEFAULT_DATA_PATH
    validation_horizon: int = DEFAULT_VALIDATION_HORIZON
    test_horizon: int = DEFAULT_TEST_HORIZON
    projection_horizon: int = DEFAULT_PROJECTION_HORIZON
    report_name: str = "Station Forecasting Workbench"
    run_label: str = "baseline-model-review"
    registry_name: str = DEFAULT_REGISTRY_NAME

    @property
    def output_filename(self) -> str:
        return "station_forecast_report.json"

    def load_histories(self) -> list[dict[str, Any]]:
        return load_histories(self.data_path)

    def build_report(self) -> dict[str, Any]:
        histories = self.load_histories()
        forecasts = []
        winning_models: Counter[str] = Counter()
        feature_set_wins: Counter[str] = Counter()

        for series in histories:
            values = series["values"]
            train, validation, test = _split_series(values, self.validation_horizon, self.test_horizon)
            feature_profile = _build_feature_profile(train)
            validation_predictions = _candidate_predictions(train, self.validation_horizon)
            leaderboard = [
                {
                    "model": model_name,
                    "featureSet": _feature_set_for_model(model_name),
                    "validationMae": _mae(validation, predictions),
                    "validationPredictions": predictions,
                }
                for model_name, predictions in validation_predictions.items()
            ]
            leaderboard.sort(key=lambda candidate: (candidate["validationMae"], candidate["model"]))
            selected_model = leaderboard[0]["model"]
            selected_feature_set = leaderboard[0]["featureSet"]
            winning_models[selected_model] += 1
            feature_set_wins[selected_feature_set] += 1

            refit_history = train + validation
            test_predictions = _candidate_predictions(refit_history, self.test_horizon)
            selected_test_prediction = test_predictions[selected_model]
            future_projections = _candidate_predictions(values, self.projection_horizon)[selected_model]

            forecasts.append(
                {
                    "stationId": series["stationId"],
                    "metric": series["metric"],
                    "trainingWindow": len(train),
                    "validationWindow": len(validation),
                    "testWindow": len(test),
                    "featureProfile": feature_profile,
                    "datasetSplit": {
                        "train": train,
                        "validation": validation,
                        "test": test,
                    },
                    "modelLeaderboard": leaderboard,
                    "selectedModel": selected_model,
                    "selectedFeatureSet": selected_feature_set,
                    "selectedValidationMae": leaderboard[0]["validationMae"],
                    "testActual": test,
                    "testPrediction": selected_test_prediction,
                    "selectedTestMae": _mae(test, selected_test_prediction),
                    "projectionHorizon": self.projection_horizon,
                    "projection": future_projections,
                    "nextForecast": future_projections[0],
                }
            )

        return {
            "reportName": self.report_name,
            "experiment": {
                "runLabel": self.run_label,
                "generatedAt": datetime.now(UTC).isoformat(),
                "registryFile": self.registry_name,
                "candidateModelCount": 4,
                "validationHorizon": self.validation_horizon,
                "testHorizon": self.test_horizon,
                "projectionHorizon": self.projection_horizon,
            },
            "summary": {
                "seriesCount": len(histories),
                "validationHorizon": self.validation_horizon,
                "testHorizon": self.test_horizon,
                "projectionHorizon": self.projection_horizon,
                "averageValidationMae": round(sum(item["selectedValidationMae"] for item in forecasts) / len(forecasts), 2),
                "averageTestMae": round(sum(item["selectedTestMae"] for item in forecasts) / len(forecasts), 2),
                "modelWins": dict(sorted(winning_models.items())),
                "featureSetWins": dict(sorted(feature_set_wins.items())),
            },
            "forecasts": forecasts,
            "notes": [
                "Designed as a public-safe forecasting workflow with feature profiling, candidate-model comparison, and experiment-style evaluation.",
                "The workbench selects models on validation performance and records separate test error for each station series.",
                "The same structure can later support richer feature engineering, run registries, and external experiment tracking backends.",
            ],
        }

    def build_registry_entry(self, report: dict[str, Any], output_path: Path) -> dict[str, Any]:
        return {
            "runLabel": report["experiment"]["runLabel"],
            "generatedAt": report["experiment"]["generatedAt"],
            "reportName": report["reportName"],
            "reportFile": output_path.name,
            "seriesCount": report["summary"]["seriesCount"],
            "averageValidationMae": report["summary"]["averageValidationMae"],
            "averageTestMae": report["summary"]["averageTestMae"],
            "modelWins": report["summary"]["modelWins"],
        }

    def export_report(self, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
        return super().export_report(output_dir)


def build_forecast_report(
    data_path: Path = DEFAULT_DATA_PATH,
    validation_horizon: int = DEFAULT_VALIDATION_HORIZON,
    test_horizon: int = DEFAULT_TEST_HORIZON,
    projection_horizon: int = DEFAULT_PROJECTION_HORIZON,
    report_name: str = "Station Forecasting Workbench",
    run_label: str = "baseline-model-review",
    registry_name: str = DEFAULT_REGISTRY_NAME,
) -> dict[str, Any]:
    workbench = ForecastWorkbench(
        data_path=data_path,
        validation_horizon=validation_horizon,
        test_horizon=test_horizon,
        projection_horizon=projection_horizon,
        report_name=report_name,
        run_label=run_label,
        registry_name=registry_name,
    )
    return workbench.build_report()


def export_forecast_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Station Forecasting Workbench",
    run_label: str = "baseline-model-review",
    validation_horizon: int = DEFAULT_VALIDATION_HORIZON,
    test_horizon: int = DEFAULT_TEST_HORIZON,
    projection_horizon: int = DEFAULT_PROJECTION_HORIZON,
    registry_name: str = DEFAULT_REGISTRY_NAME,
) -> Path:
    workbench = ForecastWorkbench(
        validation_horizon=validation_horizon,
        test_horizon=test_horizon,
        projection_horizon=projection_horizon,
        report_name=report_name,
        run_label=run_label,
        registry_name=registry_name,
    )
    return workbench.export_report(output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample station forecast report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Station Forecasting Workbench", help="Display name embedded in the output report.")
    parser.add_argument("--run-label", default="baseline-model-review", help="Label stored with the experiment-style report output.")
    parser.add_argument("--registry-name", default=DEFAULT_REGISTRY_NAME, help="Name of the JSON file used to store appended run metadata.")
    parser.add_argument("--validation-horizon", type=int, default=DEFAULT_VALIDATION_HORIZON, help="Number of validation steps used for model selection.")
    parser.add_argument("--test-horizon", type=int, default=DEFAULT_TEST_HORIZON, help="Number of test steps used for post-selection evaluation.")
    parser.add_argument("--projection-horizon", type=int, default=DEFAULT_PROJECTION_HORIZON, help="Number of future steps projected by the selected model.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_forecast_report(
        output_dir=args.output_dir,
        report_name=args.report_name,
        run_label=args.run_label,
        validation_horizon=args.validation_horizon,
        test_horizon=args.test_horizon,
        projection_horizon=args.projection_horizon,
        registry_name=args.registry_name,
    )
    print(f"Wrote station forecast report to {output_path}")


if __name__ == "__main__":
    main()