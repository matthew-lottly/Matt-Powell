from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm


KernelName = Literal["triangular", "uniform", "epanechnikov"]
BunchSide = Literal["left", "right", "both"]
RDDesign = Literal["sharp", "fuzzy"]


def _as_float_array(series: pd.Series) -> np.ndarray:
    values = series.to_numpy(dtype=float)
    if np.isnan(values).any():
        raise ValueError("Input columns must not contain missing values")
    return values


def _resolve_bandwidth(values: np.ndarray, bandwidth: float | None) -> float:
    if bandwidth is not None:
        if bandwidth <= 0.0:
            raise ValueError("bandwidth must be positive")
        return float(bandwidth)

    if len(values) < 10:
        raise ValueError("Automatic bandwidth selection requires at least 10 rows")

    sigma = float(np.std(values, ddof=1))
    q75, q25 = np.percentile(values, [75.0, 25.0])
    iqr_scale = float((q75 - q25) / 1.349) if q75 > q25 else 0.0
    positive_scales = [scale for scale in (sigma, iqr_scale) if scale > 0.0]
    scale = min(positive_scales) if positive_scales else 1.0
    return float(1.84 * scale * (len(values) ** (-1.0 / 5.0)))


def _kernel_weights(scaled_distance: np.ndarray, kernel: KernelName) -> np.ndarray:
    u = np.abs(scaled_distance)
    if kernel == "triangular":
        return np.clip(1.0 - u, 0.0, None)
    if kernel == "uniform":
        return (u <= 1.0).astype(float)
    if kernel == "epanechnikov":
        return 0.75 * np.clip(1.0 - u ** 2, 0.0, None)
    raise ValueError(f"Unsupported kernel: {kernel}")


def _resolve_bin_width(values: np.ndarray, bin_width: float | None) -> float:
    if bin_width is not None:
        if bin_width <= 0.0:
            raise ValueError("bin_width must be positive")
        return float(bin_width)

    q75, q25 = np.percentile(values, [75.0, 25.0])
    iqr = float(q75 - q25)
    width = 2.0 * iqr * (len(values) ** (-1.0 / 3.0)) if iqr > 0.0 else 0.0
    if width <= 0.0:
        sigma = float(np.std(values, ddof=1))
        width = sigma / 8.0 if sigma > 0.0 else 0.1
    return float(width)


@dataclass(frozen=True)
class RDEstimate:
    method: str
    design: str
    effect: float
    se: float | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    cutoff: float
    bandwidth: float
    kernel: str
    degree: int
    n_left: int
    n_right: int
    mean_left: float
    mean_right: float
    density_ratio: float | None
    bias_corrected_effect: float | None = None
    robust_se: float | None = None
    robust_p_value: float | None = None
    robust_ci_low: float | None = None
    robust_ci_high: float | None = None
    pilot_bandwidth: float | None = None
    first_stage_effect: float | None = None
    first_stage_se: float | None = None
    first_stage_f: float | None = None
    reduced_form_effect: float | None = None
    reduced_form_se: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {field_name: getattr(self, field_name) for field_name in self.__dataclass_fields__}


@dataclass(frozen=True)
class McCraryResult:
    """Result of the McCrary (2008) density discontinuity test."""
    density_left: float
    density_right: float
    density_ratio: float
    z_statistic: float
    p_value: float
    manipulation_detected: bool
    bandwidth: float
    n_left: int
    n_right: int

    def to_dict(self) -> dict[str, Any]:
        return {field_name: getattr(self, field_name) for field_name in self.__dataclass_fields__}


@dataclass(frozen=True)
class BunchingElasticity:
    """Result of structural bunching elasticity estimation."""
    elasticity: float
    excess_mass: float
    normalized_bunching: float
    counterfactual_at_kink: float
    implied_dz_star: float
    kink_point: float
    tax_rate_below: float
    tax_rate_above: float
    net_of_tax_change: float
    ci_low: float | None = None
    ci_high: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {field_name: getattr(self, field_name) for field_name in self.__dataclass_fields__}


@dataclass(frozen=True)
class BunchingEstimate:
    method: str
    threshold: float
    side: str
    excess_mass: float
    excess_mass_ratio: float
    observed_mass: float
    counterfactual_mass: float
    ci_low: float | None
    ci_high: float | None
    bin_width: float
    analysis_window: float
    excluded_window: float
    polynomial_degree: int
    bunching_bin_count: int
    fitting_bin_count: int

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in self.__dataclass_fields__}


class RegressionDiscontinuity:
    """Local-polynomial regression discontinuity estimator.

    Supports sharp and fuzzy designs, conventional and robust bias-corrected
    inference (following the CCT 2014 approach), optional covariate adjustment,
    and a built-in McCrary density test for manipulation checking.
    """

    def __init__(
        self,
        running_col: str,
        outcome_col: str,
        *,
        cutoff: float = 0.0,
        bandwidth: float | None = None,
        degree: int = 1,
        kernel: KernelName = "triangular",
        covariates: list[str] | None = None,
        treatment_col: str | None = None,
        pilot_bandwidth_factor: float = 1.5,
    ) -> None:
        if degree < 1 or degree > 2:
            raise ValueError("degree must be 1 or 2")
        self.running_col = running_col
        self.outcome_col = outcome_col
        self.cutoff = float(cutoff)
        self.bandwidth = bandwidth
        self.degree = degree
        self.kernel = kernel
        self.covariates = covariates or []
        self.treatment_col = treatment_col
        self.pilot_bandwidth_factor = pilot_bandwidth_factor

    @property
    def design(self) -> RDDesign:
        return "fuzzy" if self.treatment_col is not None else "sharp"

    def _design_matrix(self, centered_running: np.ndarray, right: np.ndarray, frame: pd.DataFrame, degree: int) -> pd.DataFrame:
        payload: dict[str, np.ndarray] = {
            "const": np.ones(len(centered_running), dtype=float),
            "right": right.astype(float),
        }
        for power in range(1, degree + 1):
            running_power = centered_running ** power
            payload[f"running_{power}"] = running_power
            payload[f"right_running_{power}"] = right * running_power
        for covariate in self.covariates:
            payload[covariate] = frame[covariate].to_numpy(dtype=float)
        return pd.DataFrame(payload)

    def _local_linear_fit(
        self,
        outcome: np.ndarray,
        running: np.ndarray,
        right: np.ndarray,
        weights: np.ndarray,
        frame: pd.DataFrame,
        degree: int,
    ) -> sm.regression.linear_model.RegressionResultsWrapper:
        design = self._design_matrix(running, right, frame, degree)
        return sm.WLS(outcome, design, weights=weights).fit(cov_type="HC1")

    def _bias_correction(
        self,
        outcome: np.ndarray,
        running: np.ndarray,
        right: np.ndarray,
        frame: pd.DataFrame,
        bandwidth: float,
    ) -> tuple[float, float]:
        """Estimate leading bias via a pilot local quadratic/cubic fit."""
        pilot_bw = bandwidth * self.pilot_bandwidth_factor
        pilot_degree = self.degree + 1
        mask_pilot = np.abs(running) <= pilot_bw
        if int(mask_pilot.sum()) < max(40, 8 * (pilot_degree + 1)):
            return 0.0, 0.0

        local_pilot = frame.loc[mask_pilot].reset_index(drop=True)
        running_pilot = running[mask_pilot]
        outcome_pilot = outcome[mask_pilot]
        right_pilot = (running_pilot >= 0.0).astype(float)
        weights_pilot = _kernel_weights(running_pilot / pilot_bw, self.kernel)

        model_pilot = self._local_linear_fit(
            outcome_pilot, running_pilot, right_pilot, weights_pilot, local_pilot, pilot_degree,
        )

        # Extract curvature coefficients for bias estimation
        curvature_key = f"running_{pilot_degree}"
        interaction_key = f"right_running_{pilot_degree}"
        if curvature_key not in model_pilot.params.index or interaction_key not in model_pilot.params.index:
            return 0.0, 0.0

        curv_left = float(model_pilot.params[curvature_key])
        curv_interaction = float(model_pilot.params[interaction_key])
        curv_right = curv_left + curv_interaction

        scale = (0.5 * bandwidth ** pilot_degree) if pilot_degree == 2 else (bandwidth ** pilot_degree / 6.0)
        bias = scale * (curv_right - curv_left)

        # Variance contribution from bias estimate
        idx_c = list(model_pilot.params.index).index(curvature_key)
        idx_i = list(model_pilot.params.index).index(interaction_key)
        cov = model_pilot.cov_params().iloc
        var_bias = scale ** 2 * (cov[idx_c, idx_c] + cov[idx_i, idx_i] + 2 * cov[idx_c, idx_i])

        return float(bias), float(var_bias)

    def fit(self, frame: pd.DataFrame) -> RDEstimate:
        required = [self.running_col, self.outcome_col, *self.covariates]
        if self.treatment_col is not None:
            required.append(self.treatment_col)
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        running = _as_float_array(frame[self.running_col]) - self.cutoff
        outcome = _as_float_array(frame[self.outcome_col])
        bandwidth = _resolve_bandwidth(running, self.bandwidth)

        mask = np.abs(running) <= bandwidth
        if int(mask.sum()) < max(40, 8 * (self.degree + 1)):
            raise ValueError("Not enough observations inside bandwidth for RD estimation")

        local = frame.loc[mask].reset_index(drop=True)
        local_running = running[mask]
        local_outcome = outcome[mask]
        right = (local_running >= 0.0).astype(float)

        n_left = int((right == 0.0).sum())
        n_right = int((right == 1.0).sum())
        if n_left <= self.degree + 1 or n_right <= self.degree + 1:
            raise ValueError("Need observations on both sides of the cutoff inside bandwidth")

        weights = _kernel_weights(local_running / bandwidth, self.kernel)

        # --- Sharp or reduced-form fit ---
        model = self._local_linear_fit(local_outcome, local_running, right, weights, local, self.degree)
        effect = float(model.params["right"])
        se = float(model.bse["right"])
        p_value = float(model.pvalues["right"])
        ci_low, ci_high = [float(v) for v in model.conf_int().loc["right"]]

        # --- Fuzzy RD: Wald / local IV ---
        first_stage_effect: float | None = None
        first_stage_se: float | None = None
        first_stage_f: float | None = None
        reduced_form_effect: float | None = None
        reduced_form_se: float | None = None

        if self.treatment_col is not None:
            treatment = _as_float_array(frame[self.treatment_col])
            local_treatment = treatment[mask]
            model_fs = self._local_linear_fit(local_treatment, local_running, right, weights, local, self.degree)
            first_stage_effect = float(model_fs.params["right"])
            first_stage_se = float(model_fs.bse["right"])
            first_stage_f = float((first_stage_effect / first_stage_se) ** 2) if first_stage_se > 0 else None

            reduced_form_effect = effect
            reduced_form_se = se

            if abs(first_stage_effect) > 1e-10:
                effect = reduced_form_effect / first_stage_effect
                # Delta method SE for the Wald ratio
                se = float(np.sqrt(
                    (reduced_form_se / first_stage_effect) ** 2
                    + (reduced_form_effect * first_stage_se / first_stage_effect ** 2) ** 2
                ))
                z = effect / se if se > 0 else 0.0
                p_value = float(2 * (1 - norm.cdf(abs(z))))
                ci_low = effect - 1.96 * se
                ci_high = effect + 1.96 * se

        # --- Robust bias correction (CCT 2014 approach) ---
        bias, var_bias = self._bias_correction(outcome[mask], local_running, right, local, bandwidth)
        bc_effect = effect - bias
        var_robust = se ** 2 + var_bias
        robust_se = float(np.sqrt(var_robust))
        z_robust = bc_effect / robust_se if robust_se > 0 else 0.0
        robust_p = float(2 * (1 - norm.cdf(abs(z_robust))))
        robust_ci_low = bc_effect - 1.96 * robust_se
        robust_ci_high = bc_effect + 1.96 * robust_se

        # --- Density ratio for manipulation check ---
        half_bandwidth = bandwidth / 2.0
        local_density_mask = np.abs(running) <= half_bandwidth
        density_left = int(((running < 0.0) & local_density_mask).sum())
        density_right = int(((running >= 0.0) & local_density_mask).sum())
        density_ratio = None if density_left == 0 else float(density_right / density_left)

        mean_left = float(local_outcome[right == 0.0].mean())
        mean_right = float(local_outcome[right == 1.0].mean())

        return RDEstimate(
            method="RegressionDiscontinuity",
            design=self.design,
            effect=effect,
            se=se,
            p_value=p_value,
            ci_low=ci_low,
            ci_high=ci_high,
            cutoff=self.cutoff,
            bandwidth=bandwidth,
            kernel=self.kernel,
            degree=self.degree,
            n_left=n_left,
            n_right=n_right,
            mean_left=mean_left,
            mean_right=mean_right,
            density_ratio=density_ratio,
            bias_corrected_effect=bc_effect,
            robust_se=robust_se,
            robust_p_value=robust_p,
            robust_ci_low=robust_ci_low,
            robust_ci_high=robust_ci_high,
            pilot_bandwidth=bandwidth * self.pilot_bandwidth_factor,
            first_stage_effect=first_stage_effect,
            first_stage_se=first_stage_se,
            first_stage_f=first_stage_f,
            reduced_form_effect=reduced_form_effect,
            reduced_form_se=reduced_form_se,
        )

    def mccrary_test(self, frame: pd.DataFrame, *, test_bandwidth: float | None = None) -> McCraryResult:
        """McCrary (2008) density discontinuity test for manipulation of the running variable."""
        running = _as_float_array(frame[self.running_col])
        centered = running - self.cutoff
        bw = _resolve_bandwidth(centered, test_bandwidth)

        left_mask = (centered >= -bw) & (centered < 0.0)
        right_mask = (centered >= 0.0) & (centered <= bw)
        n_left = int(left_mask.sum())
        n_right = int(right_mask.sum())
        total = n_left + n_right

        if total < 20:
            raise ValueError("Not enough observations near cutoff for McCrary test")

        # Local density estimates using kernel-weighted counts
        left_vals = centered[left_mask]
        right_vals = centered[right_mask]
        density_left = float(np.sum(_kernel_weights(left_vals / bw, self.kernel))) / (total * bw)
        density_right = float(np.sum(_kernel_weights(right_vals / bw, self.kernel))) / (total * bw)

        # Binomial test: under H0, P(right of cutoff) = 0.5
        theta = n_right / total if total > 0 else 0.5
        se_theta = float(np.sqrt(0.25 / total))
        z_stat = float((theta - 0.5) / se_theta)
        p_val = float(2 * (1 - norm.cdf(abs(z_stat))))

        density_ratio = density_right / density_left if density_left > 0 else float("inf")

        return McCraryResult(
            density_left=density_left,
            density_right=density_right,
            density_ratio=density_ratio,
            z_statistic=z_stat,
            p_value=p_val,
            manipulation_detected=p_val < 0.05,
            bandwidth=bw,
            n_left=n_left,
            n_right=n_right,
        )


class BunchingEstimator:
    """Excess-mass estimator around a threshold with optional structural elasticity.

    The descriptive mode follows the reduced-form bunching logic used in applied
    public-finance work: fit a smooth counterfactual histogram away from the bunch
    window, then compare observed and predicted mass near the threshold.

    The structural mode (via ``elasticity()``) extends this to recover a
    compensated elasticity from a kink-point design following Saez (2010),
    Chetty et al. (2011), and Kleven (2016).
    """

    def __init__(
        self,
        running_col: str,
        *,
        threshold: float = 0.0,
        side: BunchSide = "left",
        bin_width: float | None = None,
        analysis_window: float | None = None,
        excluded_window: float | None = None,
        polynomial_degree: int = 4,
        bootstrap_repeats: int = 100,
        bootstrap_seed: int = 42,
    ) -> None:
        if polynomial_degree < 1:
            raise ValueError("polynomial_degree must be at least 1")
        self.running_col = running_col
        self.threshold = float(threshold)
        self.side = side
        self.bin_width = bin_width
        self.analysis_window = analysis_window
        self.excluded_window = excluded_window
        self.polynomial_degree = polynomial_degree
        self.bootstrap_repeats = bootstrap_repeats
        self.bootstrap_seed = bootstrap_seed

    def _resolve_windows(self, centered: np.ndarray, bin_width: float) -> tuple[float, float]:
        analysis_window = self.analysis_window
        if analysis_window is None:
            q = float(np.percentile(np.abs(centered), 60.0))
            analysis_window = max(q, 8.0 * bin_width)
        if analysis_window <= 0.0:
            raise ValueError("analysis_window must be positive")

        excluded_window = self.excluded_window if self.excluded_window is not None else 2.0 * bin_width
        if excluded_window <= 0.0:
            raise ValueError("excluded_window must be positive")
        if excluded_window >= analysis_window:
            raise ValueError("excluded_window must be smaller than analysis_window")
        return float(analysis_window), float(excluded_window)

    def _bunching_mask(self, mids: np.ndarray, excluded_window: float) -> np.ndarray:
        if self.side == "left":
            return (mids >= self.threshold - excluded_window) & (mids < self.threshold)
        if self.side == "right":
            return (mids >= self.threshold) & (mids <= self.threshold + excluded_window)
        return np.abs(mids - self.threshold) <= excluded_window

    def _estimate_from_values(self, values: np.ndarray) -> tuple[float, float, float, float, int, int, float, float]:
        centered = values - self.threshold
        bin_width = _resolve_bin_width(centered, self.bin_width)
        analysis_window, excluded_window = self._resolve_windows(centered, bin_width)

        in_window = np.abs(centered) <= analysis_window
        if int(in_window.sum()) < 100:
            raise ValueError("Not enough observations for bunching analysis")

        edges = np.arange(self.threshold - analysis_window, self.threshold + analysis_window + bin_width, bin_width)
        counts, edges = np.histogram(values[in_window], bins=edges)
        mids = (edges[:-1] + edges[1:]) / 2.0
        bunch_mask = self._bunching_mask(mids, excluded_window)
        fit_mask = ~bunch_mask

        if int(bunch_mask.sum()) == 0 or int(fit_mask.sum()) <= self.polynomial_degree + 1:
            raise ValueError("Histogram configuration does not leave enough bins for estimation")

        centered_mids = mids - self.threshold
        design = np.column_stack([centered_mids[fit_mask] ** power for power in range(self.polynomial_degree + 1)])
        coefficients = np.linalg.lstsq(design, counts[fit_mask].astype(float), rcond=None)[0]
        prediction_design = np.column_stack([centered_mids ** power for power in range(self.polynomial_degree + 1)])
        predicted = prediction_design @ coefficients
        predicted = np.clip(predicted, 1e-6, None)

        observed_mass = float(counts[bunch_mask].sum())
        counterfactual_mass = float(predicted[bunch_mask].sum())
        excess_mass = float(observed_mass - counterfactual_mass)
        excess_mass_ratio = float(excess_mass / counterfactual_mass)
        return (
            excess_mass,
            excess_mass_ratio,
            observed_mass,
            counterfactual_mass,
            int(bunch_mask.sum()),
            int(fit_mask.sum()),
            bin_width,
            analysis_window,
        )

    def fit(self, frame: pd.DataFrame) -> BunchingEstimate:
        if self.running_col not in frame.columns:
            raise ValueError(f"Missing required column: {self.running_col}")

        values = _as_float_array(frame[self.running_col])
        (
            excess_mass,
            excess_mass_ratio,
            observed_mass,
            counterfactual_mass,
            bunching_bin_count,
            fitting_bin_count,
            bin_width,
            analysis_window,
        ) = self._estimate_from_values(values)

        excluded_window = self.excluded_window if self.excluded_window is not None else 2.0 * bin_width

        ci_low: float | None = None
        ci_high: float | None = None
        if self.bootstrap_repeats > 1:
            rng = np.random.default_rng(self.bootstrap_seed)
            bootstrap_effects: list[float] = []
            for _ in range(self.bootstrap_repeats):
                sampled = rng.choice(values, size=len(values), replace=True)
                try:
                    bootstrap_effects.append(self._estimate_from_values(sampled)[1])
                except ValueError:
                    continue
            if len(bootstrap_effects) >= 10:
                ci_low, ci_high = [float(value) for value in np.quantile(bootstrap_effects, [0.025, 0.975])]

        return BunchingEstimate(
            method="BunchingEstimator",
            threshold=self.threshold,
            side=self.side,
            excess_mass=excess_mass,
            excess_mass_ratio=excess_mass_ratio,
            observed_mass=observed_mass,
            counterfactual_mass=counterfactual_mass,
            ci_low=ci_low,
            ci_high=ci_high,
            bin_width=bin_width,
            analysis_window=analysis_window,
            excluded_window=float(excluded_window),
            polynomial_degree=self.polynomial_degree,
            bunching_bin_count=bunching_bin_count,
            fitting_bin_count=fitting_bin_count,
        )

    def elasticity(
        self,
        frame: pd.DataFrame,
        *,
        tax_rate_below: float,
        tax_rate_above: float,
        bootstrap_repeats: int | None = None,
    ) -> BunchingElasticity:
        """Recover a structural elasticity from a kink-point bunching design.

        Follows the logic of Saez (2010) and Kleven (2016): excess mass at the
        kink is converted to a compensated elasticity via the implied shift in
        the budget set.  Requires the user to supply the marginal tax rates
        below and above the kink.
        """
        if tax_rate_below < 0.0 or tax_rate_below >= 1.0:
            raise ValueError("tax_rate_below must be in [0, 1)")
        if tax_rate_above <= tax_rate_below or tax_rate_above >= 1.0:
            raise ValueError("tax_rate_above must be in (tax_rate_below, 1)")

        values = _as_float_array(frame[self.running_col])
        net_of_tax_change = (tax_rate_above - tax_rate_below) / (1.0 - tax_rate_below)

        def _elasticity_from_sample(vals: np.ndarray) -> float:
            centered = vals - self.threshold
            bin_width = _resolve_bin_width(centered, self.bin_width)
            analysis_window, excluded_window = self._resolve_windows(centered, bin_width)

            in_window = np.abs(centered) <= analysis_window
            if int(in_window.sum()) < 100:
                raise ValueError("Not enough observations")

            # Center bins on the kink point
            half = bin_width / 2.0
            edges = np.arange(self.threshold - analysis_window - half, self.threshold + analysis_window + bin_width, bin_width)
            counts, edges_ = np.histogram(vals[in_window], bins=edges)
            mids = (edges_[:-1] + edges_[1:]) / 2.0

            kink_idx = int(np.argmin(np.abs(mids - self.threshold)))

            # Exclude a narrow band: kink bin ± some bins
            n_excl = max(1, int(np.ceil(excluded_window / bin_width)))
            excl_mask = np.zeros(len(mids), dtype=bool)
            excl_lo = max(0, kink_idx - n_excl)
            excl_hi = min(len(mids), kink_idx + n_excl + 1)
            excl_mask[excl_lo:excl_hi] = True
            fit_mask = ~excl_mask

            if int(fit_mask.sum()) <= self.polynomial_degree + 1:
                raise ValueError("Not enough fitting bins")

            centered_mids = (mids - self.threshold) / max(analysis_window, 1.0)
            design_fit = np.column_stack([centered_mids[fit_mask] ** p for p in range(self.polynomial_degree + 1)])
            coeffs = np.linalg.lstsq(design_fit, counts[fit_mask].astype(float), rcond=None)[0]
            design_all = np.column_stack([centered_mids ** p for p in range(self.polynomial_degree + 1)])
            predicted = design_all @ coeffs
            predicted = np.clip(predicted, 1.0, None)

            h0 = float(predicted[kink_idx])
            excess = float(counts[kink_idx]) - h0
            b = excess / h0
            dz_star = b * bin_width
            return dz_star / (self.threshold * net_of_tax_change) if self.threshold != 0 else 0.0

        e_point = _elasticity_from_sample(values)

        # Detailed results from point estimate pass
        centered = values - self.threshold
        bin_width = _resolve_bin_width(centered, self.bin_width)
        analysis_window, excluded_window = self._resolve_windows(centered, bin_width)
        half = bin_width / 2.0
        edges = np.arange(self.threshold - analysis_window - half, self.threshold + analysis_window + bin_width, bin_width)
        counts, edges_ = np.histogram(values[np.abs(centered) <= analysis_window], bins=edges)
        mids = (edges_[:-1] + edges_[1:]) / 2.0
        kink_idx = int(np.argmin(np.abs(mids - self.threshold)))

        n_excl = max(1, int(np.ceil(excluded_window / bin_width)))
        excl_mask = np.zeros(len(mids), dtype=bool)
        excl_mask[max(0, kink_idx - n_excl):min(len(mids), kink_idx + n_excl + 1)] = True
        fit_mask = ~excl_mask
        centered_mids = (mids - self.threshold) / max(analysis_window, 1.0)
        design_fit = np.column_stack([centered_mids[fit_mask] ** p for p in range(self.polynomial_degree + 1)])
        coeffs = np.linalg.lstsq(design_fit, counts[fit_mask].astype(float), rcond=None)[0]
        design_all = np.column_stack([centered_mids ** p for p in range(self.polynomial_degree + 1)])
        predicted = np.clip(design_all @ coeffs, 1.0, None)
        h0 = float(predicted[kink_idx])
        excess_at_kink = float(counts[kink_idx]) - h0
        b_normalized = excess_at_kink / h0
        dz_star = b_normalized * bin_width

        # Bootstrap CI for elasticity
        ci_low: float | None = None
        ci_high: float | None = None
        n_boot = bootstrap_repeats if bootstrap_repeats is not None else self.bootstrap_repeats
        if n_boot > 1:
            rng = np.random.default_rng(self.bootstrap_seed)
            boot_e: list[float] = []
            for _ in range(n_boot):
                sampled = rng.choice(values, size=len(values), replace=True)
                try:
                    boot_e.append(_elasticity_from_sample(sampled))
                except (ValueError, ZeroDivisionError):
                    continue
            if len(boot_e) >= 10:
                ci_low, ci_high = [float(v) for v in np.quantile(boot_e, [0.025, 0.975])]

        return BunchingElasticity(
            elasticity=e_point,
            excess_mass=excess_at_kink,
            normalized_bunching=b_normalized,
            counterfactual_at_kink=h0,
            implied_dz_star=dz_star,
            kink_point=self.threshold,
            tax_rate_below=tax_rate_below,
            tax_rate_above=tax_rate_above,
            net_of_tax_change=net_of_tax_change,
            ci_low=ci_low,
            ci_high=ci_high,
        )