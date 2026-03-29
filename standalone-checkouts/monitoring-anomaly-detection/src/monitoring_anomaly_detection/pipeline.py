from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from monitoring_anomaly_detection.workflow_base import ReportWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "station_observations.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REGISTRY_NAME = "run_registry.json"
DEFAULT_WARMUP_WINDOW = 3
DETECTOR_THRESHOLDS = {
    "global_zscore": 1.35,
    "rolling_zscore": 1.2,
    "mad_score": 2.2,
    "delta_zscore": 1.25,
}


def load_observations(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as file_handle:
        rows = list(csv.DictReader(file_handle))
    observations = [
        {
            "stationId": row["station_id"],
            "metric": row["metric"],
            "timestamp": row["timestamp"],
            "value": float(row["value"]),
            "isKnownEvent": row.get("is_known_event", "false").lower() == "true",
        }
        for row in rows
    ]
    observations.sort(key=lambda observation: (observation["stationId"], observation["timestamp"]))
    return observations


def _safe_stddev(values: list[float]) -> float:
    return pstdev(values) or 1.0


def _mad_score(values: list[float], current_value: float) -> float:
    center = median(values)
    absolute_deviations = [abs(value - center) for value in values]
    mad = median(absolute_deviations)
    if mad == 0:
        return 0.0
    return 0.6745 * abs(current_value - center) / mad


def _delta_zscore(values: list[float], current_value: float) -> float:
    if len(values) < 2:
        return 0.0
    diffs = [later - earlier for earlier, later in zip(values[:-1], values[1:], strict=True)]
    current_delta = current_value - values[-1]
    return abs(current_delta - mean(diffs)) / _safe_stddev(diffs)


def _detector_scores(history: list[float], current_value: float, warmup_window: int) -> dict[str, float]:
    rolling_history = history[-warmup_window:]
    return {
        "global_zscore": abs(current_value - mean(history)) / _safe_stddev(history),
        "rolling_zscore": abs(current_value - mean(rolling_history)) / _safe_stddev(rolling_history),
        "mad_score": _mad_score(history, current_value),
        "delta_zscore": _delta_zscore(history, current_value),
    }


def _f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 2)


def _evaluate_detector(events: list[dict[str, Any]], detector_name: str) -> dict[str, Any]:
    true_positives = sum(event["isKnownEvent"] and event["flags"][detector_name] for event in events)
    false_positives = sum((not event["isKnownEvent"]) and event["flags"][detector_name] for event in events)
    false_negatives = sum(event["isKnownEvent"] and (not event["flags"][detector_name]) for event in events)
    precision = round(true_positives / (true_positives + false_positives), 2) if true_positives + false_positives else 0.0
    recall = round(true_positives / (true_positives + false_negatives), 2) if true_positives + false_negatives else 0.0
    return {
        "detector": detector_name,
        "precision": precision,
        "recall": recall,
        "f1Score": _f1_score(precision, recall),
        "alertCount": sum(event["flags"][detector_name] for event in events),
        "truePositives": true_positives,
        "falsePositives": false_positives,
        "falseNegatives": false_negatives,
    }


@dataclass(slots=True)
class AnomalyDetectionWorkflow(ReportWorkflow):
    data_path: Path = DEFAULT_DATA_PATH
    report_name: str = "Monitoring Anomaly Detection"
    run_label: str = "detector-comparison-pass"
    warmup_window: int = DEFAULT_WARMUP_WINDOW
    registry_name: str = DEFAULT_REGISTRY_NAME

    @property
    def output_filename(self) -> str:
        return "anomaly_report.json"

    def load_observations(self) -> list[dict[str, Any]]:
        return load_observations(self.data_path)

    def build_report(self) -> dict[str, Any]:
        observations = self.load_observations()
        grouped_values: dict[str, list[float]] = defaultdict(list)

        for observation in observations:
            grouped_values[observation["stationId"]].append(observation["value"])

        baselines = {
            station_id: {
                "mean": round(mean(values), 2),
                "stddev": round(_safe_stddev(values), 2),
            }
            for station_id, values in grouped_values.items()
        }

        scored_events: list[dict[str, Any]] = []
        selected_alerts: list[dict[str, Any]] = []
        station_alert_counts: dict[str, int] = defaultdict(int)
        detector_wins: Counter[str] = Counter()

        station_histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for observation in observations:
            station_histories[observation["stationId"]].append(observation)

        for station_id, station_observations in station_histories.items():
            for index, observation in enumerate(station_observations):
                if index < self.warmup_window:
                    continue
                history_values = [item["value"] for item in station_observations[:index]]
                scores = {
                    detector: round(score, 2)
                    for detector, score in _detector_scores(history_values, observation["value"], self.warmup_window).items()
                }
                flags = {
                    detector: score >= DETECTOR_THRESHOLDS[detector]
                    for detector, score in scores.items()
                }
                scored_events.append(
                    {
                        "stationId": station_id,
                        "metric": observation["metric"],
                        "timestamp": observation["timestamp"],
                        "value": observation["value"],
                        "isKnownEvent": observation["isKnownEvent"],
                        "scores": scores,
                        "flags": flags,
                    }
                )

        detector_leaderboard = [_evaluate_detector(scored_events, detector) for detector in DETECTOR_THRESHOLDS]
        detector_leaderboard.sort(key=lambda detector: (-detector["f1Score"], -detector["precision"], detector["detector"]))
        selected_detector = detector_leaderboard[0]["detector"]
        detector_wins[selected_detector] += 1

        for event in scored_events:
            if event["flags"][selected_detector]:
                baseline = baselines[event["stationId"]]
                selected_alerts.append(
                    {
                        "stationId": event["stationId"],
                        "metric": event["metric"],
                        "timestamp": event["timestamp"],
                        "value": event["value"],
                        "isKnownEvent": event["isKnownEvent"],
                        "baselineMean": baseline["mean"],
                        "selectedScore": event["scores"][selected_detector],
                        "selectedDetector": selected_detector,
                    }
                )
                station_alert_counts[event["stationId"]] += 1

        scored_events.sort(key=lambda event: event["scores"][selected_detector], reverse=True)
        selected_alerts.sort(key=lambda alert: alert["selectedScore"], reverse=True)

        return {
            "reportName": self.report_name,
            "experiment": {
                "runLabel": self.run_label,
                "generatedAt": datetime.now(UTC).isoformat(),
                "registryFile": self.registry_name,
                "warmupWindow": self.warmup_window,
                "detectorCount": len(DETECTOR_THRESHOLDS),
                "thresholds": DETECTOR_THRESHOLDS,
            },
            "summary": {
                "observationCount": len(observations),
                "stationCount": len(grouped_values),
                "scoredEventCount": len(scored_events),
                "knownEventCount": sum(observation["isKnownEvent"] for observation in observations),
                "selectedAlertCount": len(selected_alerts),
                "selectedDetector": selected_detector,
                "selectedDetectorF1": detector_leaderboard[0]["f1Score"],
                "detectorWins": dict(detector_wins),
            },
            "stationBaselines": baselines,
            "detectorLeaderboard": detector_leaderboard,
            "rankedEvents": scored_events,
            "selectedAlerts": selected_alerts,
            "stationAlertCounts": dict(sorted(station_alert_counts.items())),
            "notes": [
                "Designed as a public-safe anomaly-detection workflow with detector comparison and experiment-style metadata.",
                "The selected detector is chosen by labeled-event F1 rather than a single hard-coded scoring rule.",
                "The same structure can later support richer event labels, rolling retraining, and external experiment tracking.",
            ],
        }

    def build_registry_entry(self, report: dict[str, Any], output_path: Path) -> dict[str, Any]:
        return {
            "runLabel": report["experiment"]["runLabel"],
            "generatedAt": report["experiment"]["generatedAt"],
            "reportName": report["reportName"],
            "reportFile": output_path.name,
            "stationCount": report["summary"]["stationCount"],
            "selectedDetector": report["summary"]["selectedDetector"],
            "selectedDetectorF1": report["summary"]["selectedDetectorF1"],
            "selectedAlertCount": report["summary"]["selectedAlertCount"],
        }

    def export_report(self, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
        return super().export_report(output_dir)


def build_anomaly_report(
    data_path: Path = DEFAULT_DATA_PATH,
    report_name: str = "Monitoring Anomaly Detection",
    run_label: str = "detector-comparison-pass",
    warmup_window: int = DEFAULT_WARMUP_WINDOW,
    registry_name: str = DEFAULT_REGISTRY_NAME,
) -> dict[str, Any]:
    workflow = AnomalyDetectionWorkflow(
        data_path=data_path,
        report_name=report_name,
        run_label=run_label,
        warmup_window=warmup_window,
        registry_name=registry_name,
    )
    return workflow.build_report()


def export_anomaly_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Monitoring Anomaly Detection",
    run_label: str = "detector-comparison-pass",
    warmup_window: int = DEFAULT_WARMUP_WINDOW,
    registry_name: str = DEFAULT_REGISTRY_NAME,
) -> Path:
    workflow = AnomalyDetectionWorkflow(
        report_name=report_name,
        run_label=run_label,
        warmup_window=warmup_window,
        registry_name=registry_name,
    )
    return workflow.export_report(output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample anomaly-detection report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Monitoring Anomaly Detection", help="Display name embedded in the output report.")
    parser.add_argument("--run-label", default="detector-comparison-pass", help="Label stored with the experiment-style report output.")
    parser.add_argument("--registry-name", default=DEFAULT_REGISTRY_NAME, help="Name of the JSON file used to store appended run metadata.")
    parser.add_argument("--warmup-window", type=int, default=DEFAULT_WARMUP_WINDOW, help="Number of historical observations required before scoring a station event.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_anomaly_report(
        output_dir=args.output_dir,
        report_name=args.report_name,
        run_label=args.run_label,
        warmup_window=args.warmup_window,
        registry_name=args.registry_name,
    )
    print(f"Wrote anomaly report to {output_path}")


if __name__ == "__main__":
    main()