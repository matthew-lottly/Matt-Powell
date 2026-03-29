from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from station_risk_classification_lab.lab import RiskClassificationLab

__all__ = ["RiskClassificationLab", "build_risk_report", "export_risk_report", "load_samples"]


def __getattr__(name: str) -> Any:
    if name == "RiskClassificationLab":
        from station_risk_classification_lab.lab import RiskClassificationLab

        return RiskClassificationLab
    if name == "build_risk_report":
        from station_risk_classification_lab.lab import build_risk_report

        return build_risk_report
    if name == "export_risk_report":
        from station_risk_classification_lab.lab import export_risk_report

        return export_risk_report
    if name == "load_samples":
        from station_risk_classification_lab.lab import load_samples

        return load_samples
    raise AttributeError(f"module 'station_risk_classification_lab' has no attribute {name!r}")