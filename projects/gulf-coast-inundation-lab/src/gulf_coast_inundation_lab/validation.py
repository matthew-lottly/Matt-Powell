from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from gulf_coast_inundation_lab.workflow_base import ReportWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "gauge_validation_sample.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REGISTRY_NAME = "run_registry.json"


@dataclass(slots=True)
class ValidationRecord:
    gauge_id: str
    gauge_name: str
    date: str
    stage_ft: float
    percent_inundated: float


def _load_validation_records(input_path: Path) -> list[ValidationRecord]:
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records = [
            ValidationRecord(
                gauge_id=str(row["gaugeId"]).strip(),
                gauge_name=str(row["gaugeName"]).strip(),
                date=str(row["date"]).strip(),
                stage_ft=float(row["stageFt"]),
                percent_inundated=float(row["percentInundated"]),
            )
            for row in reader
        ]
    if not records:
        raise ValueError("Validation input must contain at least one record.")
    return records


def _coefficient_of_determination(stage_values: list[float], inundation_values: list[float]) -> tuple[float, float, float]:
    if len(stage_values) != len(inundation_values):
        raise ValueError("Stage and inundation series must have matching lengths.")
    if len(stage_values) < 2:
        raise ValueError("At least two observations are required to compute R^2.")

    mean_stage = mean(stage_values)
    mean_inundation = mean(inundation_values)
    variance_stage = sum((value - mean_stage) ** 2 for value in stage_values)
    variance_inundation = sum((value - mean_inundation) ** 2 for value in inundation_values)
    if variance_stage == 0 or variance_inundation == 0:
        return 0.0, 0.0, round(mean_inundation, 4)

    covariance = sum(
        (stage - mean_stage) * (inundation - mean_inundation)
        for stage, inundation in zip(stage_values, inundation_values, strict=True)
    )
    slope = covariance / variance_stage
    intercept = mean_inundation - slope * mean_stage
    predictions = [(slope * stage) + intercept for stage in stage_values]
    residual_sum = sum(
        (actual - predicted) ** 2
        for actual, predicted in zip(inundation_values, predictions, strict=True)
    )
    r_squared = max(0.0, min(1.0, 1.0 - (residual_sum / variance_inundation)))
    return round(r_squared, 4), round(slope, 4), round(intercept, 4)


def _validation_category(r_squared: float) -> str:
    if r_squared >= 0.8:
        return "very_strong"
    if r_squared >= 0.6:
        return "adequate"
    if r_squared >= 0.25:
        return "weak_to_moderate"
    return "poor"


@dataclass(slots=True)
class GulfCoastValidationWorkflow(ReportWorkflow):
    input_path: Path = DEFAULT_INPUT_PATH
    report_name: str = "Gulf Coast Inundation Lab Validation Summary"
    run_label: str = "gauge-validation-review"
    registry_name: str = DEFAULT_REGISTRY_NAME

    @property
    def output_filename(self) -> str:
        return "gulf_coast_validation_summary.json"

    def build_report(self) -> dict[str, Any]:
        records = _load_validation_records(self.input_path)
        grouped: dict[str, list[ValidationRecord]] = {}
        for record in records:
            grouped.setdefault(record.gauge_id, []).append(record)

        gauges: list[dict[str, Any]] = []
        for gauge_id, gauge_records in grouped.items():
            stage_values = [record.stage_ft for record in gauge_records]
            inundation_values = [record.percent_inundated for record in gauge_records]
            r_squared, slope, intercept = _coefficient_of_determination(stage_values, inundation_values)
            gauges.append(
                {
                    "gaugeId": gauge_id,
                    "gaugeName": gauge_records[0].gauge_name,
                    "observationCount": len(gauge_records),
                    "stageRangeFt": round(max(stage_values) - min(stage_values), 3),
                    "inundationRangePct": round(max(inundation_values) - min(inundation_values), 3),
                    "rSquared": r_squared,
                    "slope": slope,
                    "intercept": intercept,
                    "category": _validation_category(r_squared),
                }
            )

        gauges.sort(key=lambda gauge: (-float(gauge["rSquared"]), gauge["gaugeId"]))
        adequate_gauges = [gauge for gauge in gauges if float(gauge["rSquared"]) >= 0.6]
        very_strong_gauges = [gauge for gauge in gauges if float(gauge["rSquared"]) >= 0.8]
        mean_r_squared = round(mean(float(gauge["rSquared"]) for gauge in gauges), 4)

        return {
            "reportName": self.report_name,
            "experiment": {
                "runLabel": self.run_label,
                "generatedAt": datetime.now(UTC).isoformat(),
                "inputFile": self.input_path.name,
                "registryFile": self.registry_name,
                "adequateThreshold": 0.6,
            },
            "summary": {
                "gaugeCount": len(gauges),
                "observationCount": len(records),
                "adequateGaugeCount": len(adequate_gauges),
                "veryStrongGaugeCount": len(very_strong_gauges),
                "meanRSquared": mean_r_squared,
                "strongestGaugeId": gauges[0]["gaugeId"],
                "weakestGaugeId": gauges[-1]["gaugeId"],
            },
            "gauges": gauges,
            "notes": [
                "This report summarizes merged gauge-stage and percent-inundated observations after Earth Engine export.",
                "An R^2 value above 0.6 is treated as adequate validation in line with the study framing.",
                "Low-support or weakly correlated gauges should be reviewed alongside observation counts and local scene coverage.",
            ],
        }

    def build_registry_entry(self, report: dict[str, Any], output_path: Path) -> dict[str, Any]:
        return {
            "runLabel": report["experiment"]["runLabel"],
            "generatedAt": report["experiment"]["generatedAt"],
            "reportName": report["reportName"],
            "reportFile": output_path.name,
            "gaugeCount": report["summary"]["gaugeCount"],
            "adequateGaugeCount": report["summary"]["adequateGaugeCount"],
            "meanRSquared": report["summary"]["meanRSquared"],
        }


def build_validation_report(input_path: Path = DEFAULT_INPUT_PATH) -> dict[str, Any]:
    workflow = GulfCoastValidationWorkflow(input_path=input_path)
    return workflow.build_report()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Gulf Coast gauge-validation summary from merged AOI export data.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH, help="Merged CSV containing gauge stage and percent inundated values.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Gulf Coast Inundation Lab Validation Summary", help="Display name embedded in the output report.")
    parser.add_argument("--run-label", default="gauge-validation-review", help="Label stored with the report output.")
    parser.add_argument("--registry-name", default=DEFAULT_REGISTRY_NAME, help="Name of the JSON file used to store appended run metadata.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workflow = GulfCoastValidationWorkflow(
        input_path=args.input_path,
        report_name=args.report_name,
        run_label=args.run_label,
        registry_name=args.registry_name,
    )
    output_path = workflow.export_report(args.output_dir)
    print(f"Wrote Gulf Coast validation summary to {output_path}")


__all__ = [
    "GulfCoastValidationWorkflow",
    "ValidationRecord",
    "build_validation_report",
    "main",
]


if __name__ == "__main__":
    main()