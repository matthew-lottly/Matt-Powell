from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

from causal_lens.data import DataSpec, validate_observational_frame
from causal_lens.diagnostics import (
    compute_e_value,
    compute_e_value_ci,
    effective_sample_size,
    rosenbaum_bounds,
    standardized_mean_difference,
    summarize_overlap,
    variance_ratio,
)
from causal_lens.results import (
    CausalEstimate,
    DiagnosticSummary,
    PlaceboResult,
    RosenbaumSensitivity,
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
    bootstrap_repeats: int = 200
    bootstrap_seed: int = 42
    propensity_trim_bounds: tuple[float, float] | None = None

    def _prepare(self, frame: pd.DataFrame) -> pd.DataFrame:
        spec = DataSpec(
            treatment_col=self.treatment_col,
            outcome_col=self.outcome_col,
            confounders=self.confounders,
        )
        prepared = validate_observational_frame(frame, spec)
        if self.propensity_trim_bounds is None:
            return prepared
        lower, upper = self.propensity_trim_bounds
        if not 0.0 <= lower < upper <= 1.0:
            raise ValueError("propensity_trim_bounds must satisfy 0.0 <= lower < upper <= 1.0")
        propensity = self._fit_propensity(prepared)
        keep_mask = (propensity >= lower) & (propensity <= upper)
        trimmed = prepared.loc[keep_mask].reset_index(drop=True)
        return validate_observational_frame(trimmed, spec)

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
        var_ratios = variance_ratio(frame, self.treatment_col, self.confounders, weights=weights)
        ess_t: float | None = None
        ess_c: float | None = None
        if weights is not None:
            ess_t, ess_c = effective_sample_size(weights, treatment)
        return DiagnosticSummary(
            propensity_min=float(overlap["propensity_min"]),
            propensity_max=float(overlap["propensity_max"]),
            treated_mean_propensity=float(overlap["treated_mean_propensity"]),
            control_mean_propensity=float(overlap["control_mean_propensity"]),
            overlap_ok=bool(overlap["overlap_ok"]),
            balance_before=balance_before,
            balance_after=balance_after,
            variance_ratios=var_ratios,
            ess_treated=ess_t,
            ess_control=ess_c,
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
        se = getattr(self, "_last_se", None)
        p_value = getattr(self, "_last_p_value", None)
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
            se=se,
            p_value=p_value,
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
        e_val = compute_e_value(estimate.effect, outcome_std)
        if estimate.ci_low is not None and estimate.ci_high is not None and not (estimate.ci_low <= 0.0 <= estimate.ci_high):
            ci_bound_near_null = min(abs(estimate.ci_low), abs(estimate.ci_high))
            e_val_ci = compute_e_value_ci(ci_bound_near_null, outcome_std)
        else:
            e_val_ci = 1.0
        return SensitivitySummary(
            bias_to_zero_effect=float(bias_to_zero_effect),
            bias_to_zero_ci=float(bias_to_zero_ci),
            standardized_bias_to_zero_effect=float(bias_to_zero_effect / scale),
            standardized_bias_to_zero_ci=float(bias_to_zero_ci / scale),
            scenarios=scenarios,
            e_value=e_val,
            e_value_ci=e_val_ci,
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
        self._last_se = float(model.bse[self.treatment_col])
        self._last_p_value = float(model.pvalues[self.treatment_col])
        return float(model.params[self.treatment_col])


class PropensityMatcher(BaseEstimator):
    def __init__(
        self,
        treatment_col: str,
        outcome_col: str,
        confounders: list[str],
        estimand: str = "ATT",
        caliper: float | None = 0.15,
        bootstrap_repeats: int = 200,
        bootstrap_seed: int = 42,
        propensity_trim_bounds: tuple[float, float] | None = None,
    ) -> None:
        super().__init__(
            treatment_col,
            outcome_col,
            confounders,
            estimand=estimand,
            bootstrap_repeats=bootstrap_repeats,
            bootstrap_seed=bootstrap_seed,
            propensity_trim_bounds=propensity_trim_bounds,
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
        deltas = np.array([
            float(frame.iloc[treated][self.outcome_col] - frame.iloc[control][self.outcome_col])
            for treated, control in matched_pairs
        ])
        effect = float(np.mean(deltas))
        # Abadie-Imbens (2006) variance estimator for matched pairs
        n_pairs = len(deltas)
        if n_pairs > 1:
            self._last_se = float(np.sqrt(np.var(deltas, ddof=1) / n_pairs))
            if self._last_se > 1e-12:
                z = effect / self._last_se
                self._last_p_value = float(2.0 * (1.0 - norm.cdf(abs(z))))
            else:
                self._last_p_value = None
        else:
            self._last_se = None
            self._last_p_value = None
        return effect

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        matched_pairs = self._matched_pairs(frame, propensity)
        weights = np.zeros(len(frame), dtype=float)
        for treated_index, control_index in matched_pairs:
            weights[treated_index] += 1.0
            weights[control_index] += 1.0
        return weights

    def rosenbaum_sensitivity(
        self,
        frame: pd.DataFrame,
        gamma_values: list[float] | None = None,
    ) -> list[RosenbaumSensitivity]:
        """Rosenbaum bounds for hidden-bias sensitivity on matched pairs."""
        prepared = self._prepare(frame)
        propensity = self._fit_propensity(prepared)
        matched_pairs = self._matched_pairs(prepared, propensity)
        differences = np.array([
            float(prepared.iloc[t][self.outcome_col] - prepared.iloc[c][self.outcome_col])
            for t, c in matched_pairs
        ])
        bounds = rosenbaum_bounds(differences, gamma_values)
        return [
            RosenbaumSensitivity(gamma=g, p_upper=p, significant_at_05=sig)
            for g, p, sig in bounds
        ]


class IPWEstimator(BaseEstimator):
    weight_cap: float = 20.0
    account_for_propensity_estimation: bool = True

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
        scaler = StandardScaler()
        x_matrix = scaler.fit_transform(frame[self.confounders])
        y_vector = frame[self.treatment_col]
        ps_model = LogisticRegression(max_iter=5_000)
        ps_model.fit(x_matrix, y_vector)
        propensity = np.clip(ps_model.predict_proba(x_matrix)[:, 1], 1e-2, 1.0 - 1e-2)

        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        weights = self._ipw_weights(treatment, propensity)
        treated_mean = np.average(outcome[treatment == 1], weights=weights[treatment == 1])
        control_mean = np.average(outcome[treatment == 0], weights=weights[treatment == 0])
        effect = float(treated_mean - control_mean)

        n = len(outcome)
        sum_w1 = weights[treatment == 1].sum()
        sum_w0 = weights[treatment == 0].sum()

        # Base Hajek influence function
        influence = np.where(
            treatment == 1,
            weights * (outcome - treated_mean) / sum_w1,
            -weights * (outcome - control_mean) / sum_w0,
        )

        if n > 1 and self.account_for_propensity_estimation:
            # Lunceford & Davidian (2004) correction for estimated propensity scores.
            # The stacked estimating equations yield an augmented influence function
            # that adds the projection of the IPW score onto the propensity score
            # equation, which generally *reduces* the variance (Hirano, Imbens &
            # Ridder 2003 showed the semiparametric efficiency gain).
            #
            # Correction term: H @ V_gamma_inv @ S_gamma
            # where S_gamma is the propensity score function for each observation,
            # H is the Jacobian d(IPW_influence)/d(gamma), and V_gamma is the
            # Fisher information of the propensity model.

            # Score of logistic propensity model: S_i = (t_i - e_i) * x_i
            e = propensity
            score_matrix = (treatment - e).reshape(-1, 1) * x_matrix  # (n, p)

            # Hessian / Fisher info of logistic model: V = X' diag(e*(1-e)) X / n
            w_diag = e * (1.0 - e)  # (n,)
            fisher = (x_matrix * w_diag.reshape(-1, 1)).T @ x_matrix / n  # (p, p)
            try:
                fisher_inv = np.linalg.inv(fisher)
            except np.linalg.LinAlgError:
                fisher_inv = np.linalg.pinv(fisher)

            # Jacobian: how changing gamma shifts the IPW influence
            # For Hajek IPW: d(phi_i)/d(gamma) involves de/dgamma = e(1-e)*x
            de_dgamma = (e * (1.0 - e)).reshape(-1, 1) * x_matrix  # (n, p)

            p_treat = treatment.mean()
            # Derivative of weights w.r.t. propensity
            if self.estimand.upper() == "ATT":
                dw_de = np.where(treatment == 1, 0.0, 1.0 / (1.0 - e)**2)
            else:
                dw_de = np.where(treatment == 1, -p_treat / e**2, (1.0 - p_treat) / (1.0 - e)**2)
            dw_de = np.clip(dw_de, -self.weight_cap, self.weight_cap)

            # H_i = d(phi_i)/d(gamma) = dw_de_i * residual_i / sum_w * de_dgamma_i
            residual_part = np.where(
                treatment == 1,
                (outcome - treated_mean) / sum_w1,
                -(outcome - control_mean) / sum_w0,
            )
            h_matrix = (dw_de * residual_part).reshape(-1, 1) * de_dgamma  # (n, p)

            # Mean of H across observations
            h_mean = h_matrix.mean(axis=0)  # (p,)

            # Correction to influence: subtract H_mean @ fisher_inv @ score_i
            correction = score_matrix @ fisher_inv @ h_mean  # (n,)
            influence_adjusted = influence - correction

            self._last_se = float(np.sqrt(np.var(influence_adjusted, ddof=1) * n))
        elif n > 1:
            # Hajek SE without propensity correction
            self._last_se = float(np.sqrt(np.var(influence, ddof=1) * n))
        else:
            self._last_se = None
            self._last_p_value = None
            return effect

        if self._last_se is not None and self._last_se > 1e-12:
            z = effect / self._last_se
            self._last_p_value = float(2.0 * (1.0 - norm.cdf(abs(z))))
        else:
            self._last_p_value = None

        return effect

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
        effect = float(np.mean(pseudo))
        # Influence-function analytic SE (semiparametric efficiency bound)
        n = len(pseudo)
        if n > 1:
            self._last_se = float(np.sqrt(np.var(pseudo, ddof=1) / n))
            if self._last_se > 1e-12:
                z = effect / self._last_se
                self._last_p_value = float(2.0 * (1.0 - norm.cdf(abs(z))))
            else:
                self._last_p_value = None
        else:
            self._last_se = None
            self._last_p_value = None
        return effect

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        raw = np.where(treatment == 1, 1.0 / propensity, 1.0 / (1.0 - propensity))
        return np.clip(raw, 0.0, self.weight_cap)


class CrossFittedDREstimator(BaseEstimator):
    """Doubly robust estimator with K-fold cross-fitting (DML/AIPW style).

    Avoids overfitting bias by using out-of-fold nuisance estimates.
    """
    weight_cap: float = 20.0
    n_folds: int = 5

    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        x_raw = frame[self.confounders].to_numpy(dtype=float)
        n = len(outcome)

        rng = np.random.default_rng(self.bootstrap_seed)
        fold_ids = np.zeros(n, dtype=int)
        indices = rng.permutation(n)
        fold_size = n // self.n_folds
        for k in range(self.n_folds):
            start = k * fold_size
            end = start + fold_size if k < self.n_folds - 1 else n
            fold_ids[indices[start:end]] = k

        mu1_hat = np.zeros(n)
        mu0_hat = np.zeros(n)
        ps_hat = np.zeros(n)

        for k in range(self.n_folds):
            train_mask = fold_ids != k
            test_mask = fold_ids == k
            x_train, x_test = x_raw[train_mask], x_raw[test_mask]
            t_train = treatment[train_mask]
            y_train = outcome[train_mask]

            # Propensity model
            scaler = StandardScaler()
            x_train_s = scaler.fit_transform(x_train)
            x_test_s = scaler.transform(x_test)
            ps_model = LogisticRegression(max_iter=5_000)
            ps_model.fit(x_train_s, t_train)
            ps_hat[test_mask] = np.clip(ps_model.predict_proba(x_test_s)[:, 1], 1e-2, 1.0 - 1e-2)

            # Outcome models (separate for treated and control)
            x_train_t1 = sm.add_constant(x_train[t_train == 1])
            x_train_t0 = sm.add_constant(x_train[t_train == 0])
            x_test_c = sm.add_constant(x_test)
            y_t1 = y_train[t_train == 1]
            y_t0 = y_train[t_train == 0]

            if len(y_t1) > len(self.confounders) + 1 and len(y_t0) > len(self.confounders) + 1:
                m1 = sm.OLS(y_t1, x_train_t1).fit()
                m0 = sm.OLS(y_t0, x_train_t0).fit()
                mu1_hat[test_mask] = m1.predict(x_test_c)
                mu0_hat[test_mask] = m0.predict(x_test_c)
            else:
                mu1_hat[test_mask] = outcome[test_mask]
                mu0_hat[test_mask] = outcome[test_mask]

        w1 = np.clip(1.0 / ps_hat, 0.0, self.weight_cap)
        w0 = np.clip(1.0 / (1.0 - ps_hat), 0.0, self.weight_cap)
        pseudo = (
            mu1_hat - mu0_hat
            + treatment * (outcome - mu1_hat) * w1
            - (1 - treatment) * (outcome - mu0_hat) * w0
        )
        effect = float(np.mean(pseudo))
        if n > 1:
            self._last_se = float(np.sqrt(np.var(pseudo, ddof=1) / n))
            if self._last_se > 1e-12:
                z = effect / self._last_se
                self._last_p_value = float(2.0 * (1.0 - norm.cdf(abs(z))))
            else:
                self._last_p_value = None
        else:
            self._last_se = None
            self._last_p_value = None
        return effect

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        raw = np.where(treatment == 1, 1.0 / propensity, 1.0 / (1.0 - propensity))
        return np.clip(raw, 0.0, self.weight_cap)


class FlexibleDoublyRobustEstimator(BaseEstimator):
    """Doubly robust estimator using gradient boosting for outcome models.

    Uses GBM for mu1/mu0 to capture nonlinear confounding, with logistic
    regression for propensity scores and cross-fitting for both.
    """
    weight_cap: float = 20.0
    n_folds: int = 5

    def _estimate_effect(self, frame: pd.DataFrame) -> float:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        x_raw = frame[self.confounders].to_numpy(dtype=float)
        n = len(outcome)

        rng = np.random.default_rng(self.bootstrap_seed)
        fold_ids = np.zeros(n, dtype=int)
        indices = rng.permutation(n)
        fold_size = n // self.n_folds
        for k in range(self.n_folds):
            start = k * fold_size
            end = start + fold_size if k < self.n_folds - 1 else n
            fold_ids[indices[start:end]] = k

        mu1_hat = np.zeros(n)
        mu0_hat = np.zeros(n)
        ps_hat = np.zeros(n)

        for k in range(self.n_folds):
            train_mask = fold_ids != k
            test_mask = fold_ids == k
            x_train, x_test = x_raw[train_mask], x_raw[test_mask]
            t_train = treatment[train_mask]
            y_train = outcome[train_mask]

            # Propensity model (logistic regression)
            scaler = StandardScaler()
            x_train_s = scaler.fit_transform(x_train)
            x_test_s = scaler.transform(x_test)
            ps_model = LogisticRegression(max_iter=5_000)
            ps_model.fit(x_train_s, t_train)
            ps_hat[test_mask] = np.clip(ps_model.predict_proba(x_test_s)[:, 1], 1e-2, 1.0 - 1e-2)

            # Outcome models (gradient boosting)
            t1_mask = t_train == 1
            t0_mask = t_train == 0
            if t1_mask.sum() > 5 and t0_mask.sum() > 5:
                gbm1 = GradientBoostingRegressor(
                    n_estimators=100, max_depth=3, learning_rate=0.1, random_state=self.bootstrap_seed,
                )
                gbm0 = GradientBoostingRegressor(
                    n_estimators=100, max_depth=3, learning_rate=0.1, random_state=self.bootstrap_seed,
                )
                gbm1.fit(x_train[t1_mask], y_train[t1_mask])
                gbm0.fit(x_train[t0_mask], y_train[t0_mask])
                mu1_hat[test_mask] = gbm1.predict(x_test)
                mu0_hat[test_mask] = gbm0.predict(x_test)
            else:
                mu1_hat[test_mask] = outcome[test_mask]
                mu0_hat[test_mask] = outcome[test_mask]

        w1 = np.clip(1.0 / ps_hat, 0.0, self.weight_cap)
        w0 = np.clip(1.0 / (1.0 - ps_hat), 0.0, self.weight_cap)
        pseudo = (
            mu1_hat - mu0_hat
            + treatment * (outcome - mu1_hat) * w1
            - (1 - treatment) * (outcome - mu0_hat) * w0
        )
        effect = float(np.mean(pseudo))
        if n > 1:
            self._last_se = float(np.sqrt(np.var(pseudo, ddof=1) / n))
            if self._last_se > 1e-12:
                z = effect / self._last_se
                self._last_p_value = float(2.0 * (1.0 - norm.cdf(abs(z))))
            else:
                self._last_p_value = None
        else:
            self._last_se = None
            self._last_p_value = None
        return effect

    def _diagnostic_weights(self, frame: pd.DataFrame, propensity: np.ndarray) -> np.ndarray | None:
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        raw = np.where(treatment == 1, 1.0 / propensity, 1.0 / (1.0 - propensity))
        return np.clip(raw, 0.0, self.weight_cap)


class TLearner:
    """T-learner for conditional average treatment effect (CATE) estimation.

    Fits separate outcome models for treated and control groups, then
    estimates CATE as mu1(x) - mu0(x) for each unit.
    """

    def __init__(
        self,
        treatment_col: str,
        outcome_col: str,
        confounders: list[str],
        *,
        use_gbm: bool = False,
        seed: int = 42,
    ) -> None:
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.confounders = confounders
        self.use_gbm = use_gbm
        self.seed = seed

    def estimate(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return the original frame with an added 'cate' column."""
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        x = frame[self.confounders].to_numpy(dtype=float)

        t1_mask = treatment == 1
        t0_mask = treatment == 0

        if self.use_gbm:
            m1 = GradientBoostingRegressor(
                n_estimators=100, max_depth=3, learning_rate=0.1, random_state=self.seed,
            )
            m0 = GradientBoostingRegressor(
                n_estimators=100, max_depth=3, learning_rate=0.1, random_state=self.seed,
            )
            m1.fit(x[t1_mask], outcome[t1_mask])
            m0.fit(x[t0_mask], outcome[t0_mask])
            mu1 = m1.predict(x)
            mu0 = m0.predict(x)
        else:
            x_c = sm.add_constant(x)
            m1 = sm.OLS(outcome[t1_mask], x_c[t1_mask]).fit()
            m0 = sm.OLS(outcome[t0_mask], x_c[t0_mask]).fit()
            mu1 = m1.predict(x_c)
            mu0 = m0.predict(x_c)

        result = frame.copy()
        result["cate"] = mu1 - mu0
        return result

    def ate(self, frame: pd.DataFrame) -> float:
        """Average treatment effect (mean of CATE estimates)."""
        result = self.estimate(frame)
        return float(result["cate"].mean())


class SLearner:
    """S-learner for conditional average treatment effect (CATE) estimation.

    Fits a single outcome model including treatment as a feature, then
    estimates CATE as mu(x, t=1) - mu(x, t=0).
    """

    def __init__(
        self,
        treatment_col: str,
        outcome_col: str,
        confounders: list[str],
        *,
        use_gbm: bool = False,
        seed: int = 42,
    ) -> None:
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.confounders = confounders
        self.use_gbm = use_gbm
        self.seed = seed

    def estimate(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return the original frame with an added 'cate' column."""
        outcome = frame[self.outcome_col].to_numpy(dtype=float)
        x_base = frame[self.confounders].to_numpy(dtype=float)
        treatment = frame[self.treatment_col].to_numpy(dtype=float).reshape(-1, 1)
        x_full = np.hstack([x_base, treatment])

        x1 = np.hstack([x_base, np.ones((len(frame), 1))])
        x0 = np.hstack([x_base, np.zeros((len(frame), 1))])

        if self.use_gbm:
            model = GradientBoostingRegressor(
                n_estimators=100, max_depth=3, learning_rate=0.1, random_state=self.seed,
            )
            model.fit(x_full, outcome)
            mu1 = model.predict(x1)
            mu0 = model.predict(x0)
        else:
            x_full_c = np.column_stack([np.ones(len(frame)), x_full])
            x1_c = np.column_stack([np.ones(len(frame)), x1])
            x0_c = np.column_stack([np.ones(len(frame)), x0])
            model = sm.OLS(outcome, x_full_c).fit()
            mu1 = model.predict(x1_c)
            mu0 = model.predict(x0_c)

        result = frame.copy()
        result["cate"] = mu1 - mu0
        return result

    def ate(self, frame: pd.DataFrame) -> float:
        """Average treatment effect (mean of CATE estimates)."""
        result = self.estimate(frame)
        return float(result["cate"].mean())


def run_placebo_test(
    frame: pd.DataFrame,
    *,
    treatment_col: str,
    placebo_outcome: str,
    confounders: list[str],
    bootstrap_repeats: int = 20,
    matcher_caliper: float | None = 0.15,
) -> list[PlaceboResult]:
    """Run all estimators on a pre-treatment outcome as a falsification check.

    All CIs should include zero if the method is valid for this dataset.
    """
    results: list[PlaceboResult] = []
    estimators: list[BaseEstimator] = [
        RegressionAdjustmentEstimator(treatment_col, placebo_outcome, confounders, bootstrap_repeats=bootstrap_repeats),
        PropensityMatcher(treatment_col, placebo_outcome, confounders, caliper=matcher_caliper, bootstrap_repeats=bootstrap_repeats),
        IPWEstimator(treatment_col, placebo_outcome, confounders, bootstrap_repeats=bootstrap_repeats),
        DoublyRobustEstimator(treatment_col, placebo_outcome, confounders, bootstrap_repeats=bootstrap_repeats),
    ]
    for est in estimators:
        estimate = est.fit(frame)
        passes = (
            estimate.ci_low is not None
            and estimate.ci_high is not None
            and estimate.ci_low <= 0.0 <= estimate.ci_high
        )
        results.append(
            PlaceboResult(
                placebo_outcome=placebo_outcome,
                method=est.__class__.__name__,
                effect=estimate.effect,
                ci_low=estimate.ci_low,
                ci_high=estimate.ci_high,
                passes=passes,
            )
        )
    return results
