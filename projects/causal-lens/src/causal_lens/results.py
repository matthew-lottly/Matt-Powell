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


@dataclass(frozen=True)
class OVBBound:
    """Omitted-variable bias bound following Cinelli & Hazlett (2020)."""
    r2yz_dx: float
    r2dz_x: float
    adjusted_effect: float
    adjusted_se: float | None
    adjusted_ci_low: float | None
    adjusted_ci_high: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OVBSummary:
    """Summary of omitted-variable bias analysis."""
    treatment_effect: float
    treatment_se: float
    r2_y_treatment: float
    r2_y_full: float
    robustness_value: float
    robustness_value_alpha: float | None
    bounds: list[OVBBound]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bounds"] = [b.to_dict() for b in self.bounds]
        return payload


@dataclass(frozen=True)
class StaggeredDiDEstimate:
    """Result container for a staggered difference-in-differences estimate."""
    method: str
    att: float
    se: float | None
    ci_low: float | None
    ci_high: float | None
    group_effects: dict[Any, float]
    group_weights: dict[Any, float]
    n_groups: int
    n_units: int
    n_periods: int

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass(frozen=True)
class DesignDiagnostic:
    """Diagnostic summary for a single identification strategy."""
    design: str
    estimand: str
    key_assumption: str
    diagnostic_name: str
    diagnostic_value: float
    passes: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
