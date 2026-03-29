from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from math import sqrt
from pathlib import Path
from typing import Any, Sequence

from station_risk_classification_lab.workflow_base import ReportWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "station_risk_samples.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REGISTRY_NAME = "run_registry.json"
DEFAULT_TEST_SIZE = 3
FEATURE_NAMES = (
    "recentMean",
    "variability",
    "trend",
    "anomalyRate",
    "maintenanceLag",
    "exceedanceDays",
)


@dataclass(slots=True)
class SampleRecord:
    station_id: str
    metric: str
    risk_label: str
    recent_mean: float
    variability: float
    trend: float
    anomaly_rate: float
    maintenance_lag: float
    exceedance_days: float

    def feature_value(self, feature_name: str) -> float:
        feature_map = {
            "recentMean": self.recent_mean,
            "variability": self.variability,
            "trend": self.trend,
            "anomalyRate": self.anomaly_rate,
            "maintenanceLag": self.maintenance_lag,
            "exceedanceDays": self.exceedance_days,
        }
        return feature_map[feature_name]


@dataclass(slots=True)
class ModelEvaluation:
    model: str
    feature_set: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    predictions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "featureSet": self.feature_set,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1Score": self.f1_score,
            "truePositives": self.true_positives,
            "trueNegatives": self.true_negatives,
            "falsePositives": self.false_positives,
            "falseNegatives": self.false_negatives,
            "predictions": self.predictions,
        }


@dataclass(slots=True)
class TestCaseReview:
    station_id: str
    metric: str
    actual_label: str
    predicted_label: str
    scorecard_risk: float
    top_risk_drivers: list[dict[str, float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stationId": self.station_id,
            "metric": self.metric,
            "actualLabel": self.actual_label,
            "predictedLabel": self.predicted_label,
            "scorecardRisk": self.scorecard_risk,
            "topRiskDrivers": self.top_risk_drivers,
        }


def load_samples(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["samples"]


def _load_sample_records(path: Path) -> list[SampleRecord]:
    raw_samples = load_samples(path)
    return [
        SampleRecord(
            station_id=str(sample["stationId"]),
            metric=str(sample["metric"]),
            risk_label=str(sample["riskLabel"]),
            recent_mean=float(sample["recentMean"]),
            variability=float(sample["variability"]),
            trend=float(sample["trend"]),
            anomaly_rate=float(sample["anomalyRate"]),
            maintenance_lag=float(sample["maintenanceLag"]),
            exceedance_days=float(sample["exceedanceDays"]),
        )
        for sample in raw_samples
    ]


def _feature_vector(sample: SampleRecord) -> list[float]:
    return [sample.feature_value(feature_name) for feature_name in FEATURE_NAMES]


def _scorecard_weights() -> dict[str, float]:
    return {
        "recentMean": 0.12,
        "variability": 0.8,
        "trend": 6.0,
        "anomalyRate": 12.0,
        "maintenanceLag": 0.35,
        "exceedanceDays": 0.9,
    }


def _scorecard_risk_score(sample: SampleRecord) -> float:
    weights = _scorecard_weights()
    return round(sum(sample.feature_value(feature_name) * weight for feature_name, weight in weights.items()), 2)


def _scorecard_predict(sample: SampleRecord) -> str:
    return "high" if _scorecard_risk_score(sample) >= 8.3 else "low"


def _profile_rules_predict(sample: SampleRecord) -> str:
    if sample.anomaly_rate >= 0.25:
        return "high"
    if sample.trend >= 0.45 and sample.variability >= 2.0:
        return "high"
    if sample.maintenance_lag >= 6 and sample.exceedance_days >= 3:
        return "high"
    return "low"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _fit_centroids(samples: Sequence[SampleRecord]) -> dict[str, list[float]]:
    grouped_vectors: dict[str, list[list[float]]] = {"high": [], "low": []}
    for sample in samples:
        grouped_vectors[sample.risk_label].append(_feature_vector(sample))
    return {
        label: [round(_mean(component_values), 4) for component_values in zip(*vectors, strict=True)]
        for label, vectors in grouped_vectors.items()
        if vectors
    }


def _distance(left: Sequence[float], right: Sequence[float]) -> float:
    return sqrt(sum((left_value - right_value) ** 2 for left_value, right_value in zip(left, right, strict=True)))


def _centroid_predict(sample: SampleRecord, centroids: dict[str, list[float]]) -> str:
    sample_vector = _feature_vector(sample)
    return min(centroids.items(), key=lambda item: (_distance(sample_vector, item[1]), item[0]))[0]


def _classification_metrics(actual: Sequence[str], predicted: Sequence[str]) -> dict[str, Any]:
    true_positives = sum(actual_label == "high" and predicted_label == "high" for actual_label, predicted_label in zip(actual, predicted, strict=True))
    true_negatives = sum(actual_label == "low" and predicted_label == "low" for actual_label, predicted_label in zip(actual, predicted, strict=True))
    false_positives = sum(actual_label == "low" and predicted_label == "high" for actual_label, predicted_label in zip(actual, predicted, strict=True))
    false_negatives = sum(actual_label == "high" and predicted_label == "low" for actual_label, predicted_label in zip(actual, predicted, strict=True))
    precision = round(true_positives / (true_positives + false_positives), 2) if true_positives + false_positives else 0.0
    recall = round(true_positives / (true_positives + false_negatives), 2) if true_positives + false_negatives else 0.0
    accuracy = round((true_positives + true_negatives) / len(actual), 2)
    f1_score = round(2 * precision * recall / (precision + recall), 2) if precision + recall else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1Score": f1_score,
        "truePositives": true_positives,
        "trueNegatives": true_negatives,
        "falsePositives": false_positives,
        "falseNegatives": false_negatives,
    }


def _top_risk_drivers(sample: SampleRecord) -> list[dict[str, float]]:
    weights = _scorecard_weights()
    contributions = [
        {
            "feature": feature_name,
            "contribution": round(sample.feature_value(feature_name) * weight, 2),
        }
        for feature_name, weight in weights.items()
    ]
    contributions.sort(key=lambda item: item["contribution"], reverse=True)
    return contributions[:3]


def _build_training_profile(samples: Sequence[SampleRecord]) -> dict[str, Any]:
    risk_scores = [_scorecard_risk_score(sample) for sample in samples]
    labels = Counter(sample.risk_label for sample in samples)
    return {
        "sampleCount": len(samples),
        "averageScorecardRisk": round(_mean(risk_scores), 2),
        "classBalance": dict(sorted(labels.items())),
        "averageRecentMean": round(_mean([sample.recent_mean for sample in samples]), 2),
        "averageAnomalyRate": round(_mean([sample.anomaly_rate for sample in samples]), 2),
    }


@dataclass(slots=True)
class RiskClassificationLab(ReportWorkflow):
    data_path: Path = DEFAULT_DATA_PATH
    test_size: int = DEFAULT_TEST_SIZE
    report_name: str = "Station Risk Classification Lab"
    run_label: str = "candidate-classifier-review"
    registry_name: str = DEFAULT_REGISTRY_NAME

    @property
    def output_filename(self) -> str:
        return "station_risk_report.json"

    def load_samples(self) -> list[dict[str, Any]]:
        return load_samples(self.data_path)

    def load_sample_records(self) -> list[SampleRecord]:
        return _load_sample_records(self.data_path)

    def _build_candidate_predictions(
        self,
        test_samples: Sequence[SampleRecord],
        centroids: dict[str, list[float]],
    ) -> dict[str, list[str]]:
        return {
            "scorecard_classifier": [_scorecard_predict(sample) for sample in test_samples],
            "centroid_classifier": [_centroid_predict(sample, centroids) for sample in test_samples],
            "profile_rules": [_profile_rules_predict(sample) for sample in test_samples],
        }

    def _build_leaderboard(
        self,
        candidate_predictions: dict[str, list[str]],
        actual_labels: Sequence[str],
        feature_sets: dict[str, str],
    ) -> list[ModelEvaluation]:
        leaderboard: list[ModelEvaluation] = []
        for model_name, predictions in candidate_predictions.items():
            metrics = _classification_metrics(actual_labels, predictions)
            leaderboard.append(
                ModelEvaluation(
                    model=model_name,
                    feature_set=feature_sets[model_name],
                    accuracy=float(metrics["accuracy"]),
                    precision=float(metrics["precision"]),
                    recall=float(metrics["recall"]),
                    f1_score=float(metrics["f1Score"]),
                    true_positives=int(metrics["truePositives"]),
                    true_negatives=int(metrics["trueNegatives"]),
                    false_positives=int(metrics["falsePositives"]),
                    false_negatives=int(metrics["falseNegatives"]),
                    predictions=predictions,
                )
            )
        leaderboard.sort(key=lambda candidate: (-candidate.f1_score, -candidate.accuracy, candidate.model))
        return leaderboard

    def _build_test_cases(self, test_samples: Sequence[SampleRecord], predictions: Sequence[str]) -> list[TestCaseReview]:
        return [
            TestCaseReview(
                station_id=sample.station_id,
                metric=sample.metric,
                actual_label=sample.risk_label,
                predicted_label=predicted_label,
                scorecard_risk=_scorecard_risk_score(sample),
                top_risk_drivers=_top_risk_drivers(sample),
            )
            for sample, predicted_label in zip(test_samples, predictions, strict=True)
        ]

    def build_report(self) -> dict[str, Any]:
        sample_records = self.load_sample_records()
        if len(sample_records) <= self.test_size:
            raise ValueError("The dataset must be larger than the requested test size.")

        train_samples = sample_records[:-self.test_size]
        test_samples = sample_records[-self.test_size:]
        centroids = _fit_centroids(train_samples)
        actual_labels = [sample.risk_label for sample in test_samples]
        feature_sets = {
            "scorecard_classifier": "weighted_scorecard",
            "centroid_classifier": "full_feature_vector",
            "profile_rules": "handcrafted_rules",
        }
        candidate_predictions = self._build_candidate_predictions(test_samples, centroids)
        leaderboard = self._build_leaderboard(candidate_predictions, actual_labels, feature_sets)
        selected_model = leaderboard[0].model
        selected_predictions = candidate_predictions[selected_model]
        test_cases = self._build_test_cases(test_samples, selected_predictions)

        class_distribution = Counter(sample.risk_label for sample in sample_records)
        return {
            "reportName": self.report_name,
            "experiment": {
                "runLabel": self.run_label,
                "generatedAt": datetime.now(UTC).isoformat(),
                "registryFile": self.registry_name,
                "candidateModelCount": len(candidate_predictions),
                "testSize": self.test_size,
                "featureNames": list(FEATURE_NAMES),
            },
            "summary": {
                "sampleCount": len(sample_records),
                "trainCount": len(train_samples),
                "testCount": len(test_samples),
                "classDistribution": dict(sorted(class_distribution.items())),
                "selectedModel": selected_model,
                "selectedFeatureSet": feature_sets[selected_model],
                "selectedAccuracy": leaderboard[0].accuracy,
                "selectedF1": leaderboard[0].f1_score,
            },
            "trainingProfile": _build_training_profile(train_samples),
            "centroids": centroids,
            "modelLeaderboard": [candidate.to_dict() for candidate in leaderboard],
            "testCases": [test_case.to_dict() for test_case in test_cases],
            "notes": [
                "Designed as a public-safe classification workflow with candidate-model comparison and explainable holdout review.",
                "The selected classifier is chosen by holdout F1 and accuracy rather than a single hard-coded threshold.",
                "The same structure can later support calibrated probabilities, richer feature engineering, or external experiment tracking.",
            ],
        }

    def build_registry_entry(self, report: dict[str, Any], output_path: Path) -> dict[str, Any]:
        return {
            "runLabel": report["experiment"]["runLabel"],
            "generatedAt": report["experiment"]["generatedAt"],
            "reportName": report["reportName"],
            "reportFile": output_path.name,
            "sampleCount": report["summary"]["sampleCount"],
            "selectedModel": report["summary"]["selectedModel"],
            "selectedAccuracy": report["summary"]["selectedAccuracy"],
            "selectedF1": report["summary"]["selectedF1"],
        }

    def export_report(self, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
        return super().export_report(output_dir)


def build_risk_report(
    data_path: Path = DEFAULT_DATA_PATH,
    test_size: int = DEFAULT_TEST_SIZE,
    report_name: str = "Station Risk Classification Lab",
    run_label: str = "candidate-classifier-review",
    registry_name: str = DEFAULT_REGISTRY_NAME,
) -> dict[str, Any]:
    lab = RiskClassificationLab(
        data_path=data_path,
        test_size=test_size,
        report_name=report_name,
        run_label=run_label,
        registry_name=registry_name,
    )
    return lab.build_report()


def export_risk_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_name: str = "Station Risk Classification Lab",
    run_label: str = "candidate-classifier-review",
    test_size: int = DEFAULT_TEST_SIZE,
    registry_name: str = DEFAULT_REGISTRY_NAME,
) -> Path:
    lab = RiskClassificationLab(
        report_name=report_name,
        run_label=run_label,
        test_size=test_size,
        registry_name=registry_name,
    )
    return lab.export_report(output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample station risk classification report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--report-name", default="Station Risk Classification Lab", help="Display name embedded in the output report.")
    parser.add_argument("--run-label", default="candidate-classifier-review", help="Label stored with the experiment-style report output.")
    parser.add_argument("--registry-name", default=DEFAULT_REGISTRY_NAME, help="Name of the JSON file used to store appended run metadata.")
    parser.add_argument("--test-size", type=int, default=DEFAULT_TEST_SIZE, help="Number of trailing samples reserved for holdout review.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_risk_report(
        output_dir=args.output_dir,
        report_name=args.report_name,
        run_label=args.run_label,
        test_size=args.test_size,
        registry_name=args.registry_name,
    )
    print(f"Wrote station risk report to {output_path}")


if __name__ == "__main__":
    main()