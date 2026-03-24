from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from causal_lens.data import DataSpec, validate_observational_frame
from causal_lens.diagnostics import standardized_mean_difference, summarize_overlap
from causal_lens.results import (
    CausalEstimate,
    DiagnosticSummary,
    SensitivityScenario,
    SensitivitySummary,
    SubgroupEstimate,
)


@dataclass
class BaseEstimator:
    treatment_col: str
    outcome_col: str
    confounders: list[str]
    estimand: str = "ATE"
    bootstrap_repeats: int = 40
    bootstrap_seed: int = 42

    def _prepare(self, frame: pd.DataFrame) -> pd.DataFrame:
        spec = DataSpec(
            treatment_col=self.treatment_col,
            outcome_col=self.outcome_col,
            confounders=self.confounders,
        )
        return validate_observational_frame(frame, spec)

    def _fit_propensity(self, frame: pd.DataFrame) -> np.ndarray:
        scaler = StandardScaler()
        x_matrix = scaler.fit_transform(frame[self.confounders])
        y_vector = frame[self.treatment_col]
        model = LogisticRegression(max_iter=5_000)
        model.fit(x_matrix, y_vector)
        propensity = model.predict_proba(x_matrix)[:, 1]
        return np.clip(propensity, 1e-2, 1.0 - 1e-2)

    def _build_diagnostics(
        self,
        frame: pd.DataFrame,
        propensity: np.ndarray,
        weights: np.ndarray | None = None,
    ) -> DiagnosticSummary:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        overlap = summarize_overlap(propensity, treatment)
        balance_before = standardized_mean_difference(frame, self.treatment_col, self.confounders)
        balance_after = standardized_mean_difference(
            frame,
            self.treatment_col,
            self.confounders,
            weights=weights,
        )
        return DiagnosticSummary(
            propensity_min=float(overlap["propensity_min"]),
            propensity_max=float(overlap["propensity_max"]),
            treated_mean_propensity=float(overlap["treated_mean_propensity"]),
            control_mean_propensity=float(overlap["control_mean_propensity"]),
            overlap_ok=bool(overlap["overlap_ok"]),
            balance_before=balance_before,
            balance_after=balance_after,
        )

    def _bootstrap_interval(self, frame: pd.DataFrame) -> tuple[float, float]:
        rng = np.random.default_rng(self.bootstrap_seed)
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        treated_indices = np.where(treatment == 1)[0]
        control_indices = np.where(treatment == 0)[0]
        if len(treated_indices) == 0 or len(control_indices) == 0:
            raise ValueError("Bootstrap interval requires both treatment classes to be present")
        estimates: list[float] = []
        for _ in range(self.bootstrap_repeats):
            treated_sample = rng.choice(treated_indices, size=len(treated_indices), replace=True)
            control_sample = rng.choice(control_indices, size=len(control_indices), replace=True)
            sample_indices = np.concatenate([treated_sample, control_sample])
            rng.shuffle(sample_indices)
            sample = frame.iloc[sample_indices].reset_index(drop=True)
            estimates.append(float(self._estimate_effect(sample)))
        interval = np.quantile(np.array(estimates), [0.025, 0.975])
        return float(interval[0]), float(interval[1])

    def fit(self, frame: pd.DataFrame) -> CausalEstimate:
        prepared = self._prepare(frame)
        effect = float(self._estimate_effect(prepared))
        propensity = self._fit_propensity(prepared)
        weights = self._diagnostic_weights(prepared, propensity)
        diagnostics = self._build_diagnostics(prepared, propensity, weights=weights)
        ci_low, ci_high = self._bootstrap_interval(prepared)
        treatment = prepared[self.treatment_col].to_numpy(dtype=int)
        return CausalEstimate(
            method=self.__class__.__name__,
            estimand=self.estimand,
            effect=effect,
            ci_low=ci_low,
            ci_high=ci_high,
            treated_count=int(treatment.sum()),
            control_count=int((1 - treatment).sum()),
            diagnostics=diagnostics,
        )

    def sensitivity_analysis(
        self,
        frame: pd.DataFrame,
        *,
        steps: int = 6,
        max_fraction: float = 1.25,
    ) -> SensitivitySummary:
        prepared = self._prepare(frame)
        estimate = self.fit(prepared)
        outcome_std = float(prepared[self.outcome_col].std(ddof=1))
        sign = 1.0 if estimate.effect >= 0.0 else -1.0
        bias_to_zero_effect = abs(estimate.effect)
        if estimate.ci_low is None or estimate.ci_high is None or estimate.ci_low <= 0.0 <= estimate.ci_high:
            bias_to_zero_ci = 0.0
        elif sign > 0.0:
            bias_to_zero_ci = abs(estimate.ci_low)
        else:
            bias_to_zero_ci = abs(estimate.ci_high)

        scenarios: list[SensitivityScenario] = []
        bias_grid = np.linspace(0.0, bias_to_zero_effect * max_fraction, num=steps)
        for bias in bias_grid:
            shift = sign * float(bias)
            adjusted_ci_low = None if estimate.ci_low is None else float(estimate.ci_low - shift)
            adjusted_ci_high = None if estimate.ci_high is None else float(estimate.ci_high - shift)
            scenarios.append(
                SensitivityScenario(
                    bias=float(bias),
                    adjusted_effect=float(estimate.effect - shift),
                    adjusted_ci_low=adjusted_ci_low,
                    adjusted_ci_high=adjusted_ci_high,
                )
            )

        scale = outcome_std if outcome_std > 1e-12 else 1.0
        return SensitivitySummary(
            bias_to_zero_effect=float(bias_to_zero_effect),
            bias_to_zero_ci=float(bias_to_zero_ci),
            standardized_bias_to_zero_effect=float(bias_to_zero_effect / scale),
            standardized_bias_to_zero_ci=float(bias_to_zero_ci / scale),
            scenarios=scenarios,
        )

    def subgroup_effects(
        self,
        frame: pd.DataFrame,
        subgroup_col: str,
        *,
        min_rows: int = 40,
        min_group_size: int = 10,
    ) -> list[SubgroupEstimate]:
        if subgroup_col not in frame.columns:
            raise ValueError(f"Missing subgroup column: {subgroup_col}")

        subgroup_results: list[SubgroupEstimate] = []
        for subgroup_value, subset in frame.groupby(subgroup_col, dropna=False, observed=False):
            subset = subset.reset_index(drop=True)
            treatment = subset[self.treatment_col].to_numpy(dtype=int)
            treated_count = int(treatment.sum())
            control_count = int((1 - treatment).sum())
            if len(subset) < min_rows:
                continue
            if treated_count < min_group_size or control_count < min_group_size:
                continue
            estimate = self.fit(subset)
            subgroup_results.append(
                SubgroupEstimate(
                    subgroup=str(subgroup_value),
                    rows=int(len(subset)),
                    treated_count=treated_count,
                    control_count=control_count,
                    effect=float(estimate.effect),
                    ci_low=estimate.ci_low,
                    ci_high=estimate.ci_high,
                )
            )
        return subgroup_results

    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        raise NotImplementedError

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        return None


class RegressionAdjustmentEstimator(BaseEstimator):
    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        design = sm.add_constant(frame[[self.treatment_col, *self.confounders]])
        outcome = frame[self.outcome_col]
        model = sm.OLS(outcome, design).fit()
        return float(model.params[self.treatment_col])


class PropensityMatcher(BaseEstimator):
    def __init__(
        self,
        treatment_col: str,
        outcome_col: str,
        confounders: list[str],
        estimand: str = "ATT",
        caliper: float | None = 0.15,
        bootstrap_repeats: int = 40,
        bootstrap_seed: int = 42,
    ) -> None:
        super().__init__(
            treatment_col,
            outcome_col,
            confounders,
            estimand=estimand,
            bootstrap_repeats=bootstrap_repeats,
            bootstrap_seed=bootstrap_seed,
        )
        self.caliper = caliper

    def _matched_pairs(self, frame: pd.DataFrame, propensity: np.ndarray) -> list[tuple[int, int]]:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        treated_idx = np.where(treatment == 1)[0]
        remaining_controls = list(np.where(treatment == 0)[0])
        matched_pairs: list[tuple[int, int]] = []
        sorted_treated_idx = sorted(treated_idx, key=lambda index: float(propensity[index]))
        for treated_position in sorted_treated_idx:
            if not remaining_controls:
                break
            control_distances = np.abs(propensity[remaining_controls] - propensity[treated_position])
            best_position = int(np.argmin(control_distances))
            distance = float(control_distances[best_position])
            if self.caliper is not None and distance > self.caliper:
                continue
            control_position = remaining_controls.pop(best_position)
            matched_pairs.append((treated_position, control_position))
        if not matched_pairs:
            raise ValueError("No matched pairs found under the current caliper")
        return matched_pairs

    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        propensity = self._fit_propensity(frame)
        matched_pairs = self._matched_pairs(frame, propensity)
        deltas = [
            float(frame.iloc[treated][self.outcome_col] - frame.iloc[control][self.outcome_col])
            for treated, control in matched_pairs
        ]
        return float(np.mean(deltas))

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        matched_pairs = self._matched_pairs(frame, propensity)
        weights = np.zeros(len(frame), dtype=float)
        for treated_index, control_index in matched_pairs:
            weights[treated_index] += 1.0
            weights[control_index] += 1.0
        return weights


class IPWEstimator(BaseEstimator):
    weight_cap: float = 20.0

    def _ipw_weights(self, treatment: np.ndarray, propensity: np.ndarray) -> np.ndarray:
        p_treat = treatment.mean()
        if self.estimand.upper() == "ATT":
            raw = np.where(treatment == 1, 1.0, propensity / (1.0 - propensity))
        else:
            raw = np.where(
                treatment == 1,
                p_treat / propensity,
                (1.0 - p_treat) / (1.0 - propensity),
            )
        return np.clip(raw, 0.0, self.weight_cap)

    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        propensity = self._fit_propensity(frame)
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        weights = self._ipw_weights(treatment, propensity)
        treated_mean = np.average(outcome[treatment == 1], weights=weights[treatment == 1])
        control_mean = np.average(outcome[treatment == 0], weights=weights[treatment == 0])
        return float(treated_mean - control_mean)

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        return self._ipw_weights(treatment, propensity)


class DoublyRobustEstimator(BaseEstimator):
    weight_cap: float = 20.0

    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        propensity = self._fit_propensity(frame)
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        x_matrix = sm.add_constant(frame[self.confounders])

        treated_model = sm.OLS(outcome[treatment == 1], x_matrix[treatment == 1]).fit()
        control_model = sm.OLS(outcome[treatment == 0], x_matrix[treatment == 0]).fit()
        mu1 = treated_model.predict(x_matrix)
        mu0 = control_model.predict(x_matrix)
        w1 = np.clip(1.0 / propensity, 0.0, self.weight_cap)
        w0 = np.clip(1.0 / (1.0 - propensity), 0.0, self.weight_cap)
        pseudo = mu1 - mu0 + treatment * (outcome - mu1) * w1 - (1 - treatment) * (outcome - mu0) * w0
        return float(np.mean(pseudo))

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        raw = np.where(treatment == 1, 1.0 / propensity, 1.0 / (1.0 - propensity))
        return np.clip(raw, 0.0, self.weight_cap)
