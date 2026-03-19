from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "station_observations.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANOMALY_SCORE_THRESHOLD = 1.3


def load_observations(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as file_handle:
        rows = list(csv.DictReader(file_handle))
    return [
        {
            "stationId": row["station_id"],
            "metric": row["metric"],
            "timestamp": row["timestamp"],
            "value": float(row["value"]),
        }
        for row in rows
    ]


def build_anomaly_report(
    data_path: Path = DEFAULT_DATA_PATH,
    report_name: str = "Monitoring Anomaly Detection",
) -> dict[str, Any]:
    observations = load_observations(data_path)
    grouped_values: dict[str, list[float]] = defaultdict(list)

    for observation in observations:
        grouped_values[observation["stationId"]].append(observation["value"])

    baselines = {
        station_id: {
            "mean": round(mean(values), 2),
            "stddev": round(pstdev(values) or 1.0, 2),
        }
        for station_id, values in grouped_values.items()
    }

    anomalies: list[dict[str, Any]] = []
    station_alert_counts: dict[str, int] = defaultdict(int)

    for observation in observations:
        baseline = baselines[observation["stationId"]]
        stddev = baseline["stddev"] or 1.0
        score = abs(observation["value"] - baseline["mean"]) / stddev
        if score >= ANOMALY_SCORE_THRESHOLD:
            anomalies.append(
                {
                    "stationId": observation["stationId"],
                    "metric": observation["metric"],
                    "timestamp": observation["timestamp"],
                    "value": observation["value"],
                    "baselineMean": baseline["mean"],
                    "deviationScore": round(score, 2),
                }
            )
            station_alert_counts[observation["stationId"]] += 1

    anomalies.sort(key=lambda anomaly: anomaly["deviationScore"], reverse=True)

    return {
        "reportName": report_name,
        "summary": {
            "observationCount": len(observations),
            "stationCount": len(grouped_values),
            "anomalyCount": len(anomalies),
        },
        "stationBaselines": baselines,
        "anomalies": anomalies,
        "stationAlertCounts": dict(sorted(station_alert_counts.items())),
        "notes": [
            "Designed as a public-safe anomaly-detection workflow for monitoring telemetry.",
            "The scoring logic can later be upgraded to rolling windows, seasonality-aware baselines, or model-based detectors.",
        ],
    }


def export_anomaly_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Monitoring Anomaly Detection",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_anomaly_report(report_name=report_name)
    output_path = output_dir / "anomaly_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample anomaly-detection report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Monitoring Anomaly Detection", help="Display name embedded in the output report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_anomaly_report(args.output_dir, report_name=args.report_name)
    print(f"Wrote anomaly report to {output_path}")


if __name__ == "__main__":
    main()