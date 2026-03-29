from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DiagnosticSummary:
    propensity_min: float
    propensity_max: float
    treated_mean_propensity: float
    control_mean_propensity: float
    overlap_ok: bool
    balance_before: dict[str, float]
    balance_after: dict[str, float]
    variance_ratios: dict[str, float] | None = None
    ess_treated: float | None = None
    ess_control: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CausalEstimate:
    method: str
    estimand: str
    effect: float
    ci_low: float | None
    ci_high: float | None
    treated_count: int
    control_count: int
    diagnostics: DiagnosticSummary
    se: float | None = None
    p_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["diagnostics"] = self.diagnostics.to_dict()
        return payload


@dataclass(frozen=True)
class SensitivityScenario:
    bias: float
    adjusted_effect: float
    adjusted_ci_low: float | None
    adjusted_ci_high: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SensitivitySummary:
    bias_to_zero_effect: float
    bias_to_zero_ci: float
    standardized_bias_to_zero_effect: float
    standardized_bias_to_zero_ci: float
    scenarios: list[SensitivityScenario]
    e_value: float | None = None
    e_value_ci: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [scenario.to_dict() for scenario in self.scenarios]
        return payload


@dataclass(frozen=True)
class SubgroupEstimate:
    subgroup: str
    rows: int
    treated_count: int
    control_count: int
    effect: float
    ci_low: float | None
    ci_high: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RosenbaumSensitivity:
    gamma: float
    p_upper: float
    significant_at_05: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlaceboResult:
    placebo_outcome: str
    method: str
    effect: float
    ci_low: float | None
    ci_high: float | None
    passes: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
