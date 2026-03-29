"""Panel-data estimators: Difference-in-Differences and Synthetic Control.

These estimators handle repeated-observation (panel) data where units are
observed in both pre-treatment and post-treatment periods.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


@dataclass(frozen=True)
class DiDEstimate:
    """Result container for a difference-in-differences estimate."""
    method: str
    effect: float
    se: float | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    treated_pre_mean: float
    treated_post_mean: float
    control_pre_mean: float
    control_post_mean: float
    n_treated: int
    n_control: int

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass(frozen=True)
class SyntheticControlEstimate:
    """Result container for a synthetic control estimate."""
    method: str
    effect: float
    pre_treatment_rmse: float
    weights: dict[str, float]
    treated_unit: str
    treated_post_mean: float
    synthetic_post_mean: float
    placebo_p_value: float | None

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class DifferenceInDifferences:
    """Two-period, two-group difference-in-differences estimator.

    Supports both a simple 2x2 DiD and a regression-based DiD with optional
    covariates for improved precision. Cluster-robust standard errors are
    available when a cluster column is provided.

    Parameters
    ----------
    unit_col : str
        Column identifying individual units.
    time_col : str
        Column identifying time periods.
    treatment_col : str
        Binary column: 1 for units in the treatment group, 0 for control.
    outcome_col : str
        Column with the outcome variable.
    post_col : str
        Binary column: 1 for post-treatment periods, 0 for pre-treatment.
    covariates : list[str] | None
        Optional covariates for regression-based DiD.
    cluster_col : str | None
        Column for cluster-robust standard errors; defaults to unit_col.
    """

    def __init__(
        self,
        unit_col: str,
        time_col: str,
        treatment_col: str,
        outcome_col: str,
        post_col: str,
        covariates: list[str] | None = None,
        cluster_col: str | None = None,
    ) -> None:
        self.unit_col = unit_col
        self.time_col = time_col
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.post_col = post_col
        self.covariates = covariates or []
        self.cluster_col = cluster_col or unit_col

    def fit(self, frame: pd.DataFrame) -> DiDEstimate:
        """Estimate the ATT using difference-in-differences."""
        treatment = frame[self.treatment_col].to_numpy(dtype=int)
        post = frame[self.post_col].to_numpy(dtype=int)
        outcome = frame[self.outcome_col].to_numpy(dtype=float)

        # Group means for the 2x2 table
        t1_pre = outcome[(treatment == 1) & (post == 0)]
        t1_post = outcome[(treatment == 1) & (post == 1)]
        t0_pre = outcome[(treatment == 0) & (post == 0)]
        t0_post = outcome[(treatment == 0) & (post == 1)]

        if len(t1_pre) == 0 or len(t1_post) == 0 or len(t0_pre) == 0 or len(t0_post) == 0:
            raise ValueError("All four cells (treated/control × pre/post) must be non-empty")

        treated_pre_mean = float(t1_pre.mean())
        treated_post_mean = float(t1_post.mean())
        control_pre_mean = float(t0_pre.mean())
        control_post_mean = float(t0_post.mean())

        # Regression DiD: Y = b0 + b1*treat + b2*post + b3*(treat*post) + covariates + e
        import statsmodels.api as sm

        interact = treatment * post
        x_cols = np.column_stack([
            np.ones(len(frame)),
            treatment,
            post,
            interact,
        ])
        col_names = ["const", "treat", "post", "treat_x_post"]

        if self.covariates:
            cov_data = frame[self.covariates].to_numpy(dtype=float)
            x_cols = np.column_stack([x_cols, cov_data])
            col_names.extend(self.covariates)

        x_df = pd.DataFrame(x_cols, columns=col_names)
        model = sm.OLS(outcome, x_df).fit(
            cov_type="cluster",
            cov_kwds={"groups": frame[self.cluster_col].to_numpy()},
        )

        effect = float(model.params["treat_x_post"])
        se = float(model.bse["treat_x_post"])
        p_value = float(model.pvalues["treat_x_post"])
        ci = model.conf_int().loc["treat_x_post"]
        ci_low = float(ci[0])
        ci_high = float(ci[1])

        n_treated = int(frame[self.treatment_col].sum())
        n_control = int((1 - frame[self.treatment_col]).sum())

        return DiDEstimate(
            method="DifferenceInDifferences",
            effect=effect,
            se=se,
            p_value=p_value,
            ci_low=ci_low,
            ci_high=ci_high,
            treated_pre_mean=treated_pre_mean,
            treated_post_mean=treated_post_mean,
            control_pre_mean=control_pre_mean,
            control_post_mean=control_post_mean,
            n_treated=n_treated,
            n_control=n_control,
        )

    def parallel_trends_test(
        self,
        frame: pd.DataFrame,
        pre_periods: list[Any] | None = None,
    ) -> dict[str, float]:
        """Test parallel pre-trends by regressing outcome on treat × period interactions.

        Returns the F-statistic and p-value for the joint test that all
        pre-treatment treat×period interactions are zero.
        """
        import statsmodels.api as sm

        pre_data = frame[frame[self.post_col] == 0].copy()
        if pre_periods is not None:
            pre_data = pre_data[pre_data[self.time_col].isin(pre_periods)]

        periods = sorted(pre_data[self.time_col].unique())
        if len(periods) < 2:
            return {"f_statistic": 0.0, "p_value": 1.0, "n_periods": len(periods)}

        # Reference period is the first one
        ref_period = periods[0]
        treatment = pre_data[self.treatment_col].to_numpy(dtype=int)
        outcome = pre_data[self.outcome_col].to_numpy(dtype=float)

        # Build period dummies and interactions
        x_parts = [np.ones(len(pre_data)), treatment.astype(float)]
        col_names = ["const", "treat"]
        interact_cols: list[str] = []

        for period in periods[1:]:
            period_dummy = (pre_data[self.time_col] == period).to_numpy(dtype=float)
            interact = treatment * period_dummy
            x_parts.extend([period_dummy, interact])
            col_names.extend([f"period_{period}", f"treat_x_period_{period}"])
            interact_cols.append(f"treat_x_period_{period}")

        x_df = pd.DataFrame(np.column_stack(x_parts), columns=col_names)
        model = sm.OLS(outcome, x_df).fit()

        # Joint F-test on the interaction terms
        if interact_cols:
            restriction = " = ".join(interact_cols) + " = 0" if len(interact_cols) == 1 else None
            if len(interact_cols) == 1:
                f_stat = float(model.tvalues[interact_cols[0]] ** 2)
                p_val = float(model.pvalues[interact_cols[0]])
            else:
                r_matrix = np.zeros((len(interact_cols), len(col_names)))
                for i, col in enumerate(interact_cols):
                    r_matrix[i, col_names.index(col)] = 1.0
                f_result = model.f_test(r_matrix)
                f_stat = float(f_result.fvalue)
                p_val = float(f_result.pvalue)
        else:
            f_stat = 0.0
            p_val = 1.0

        return {"f_statistic": f_stat, "p_value": p_val, "n_periods": len(periods)}


class SyntheticControl:
    """Synthetic control method (Abadie, Diamond & Hainmueller 2010).

    Constructs a weighted combination of control units that best matches
    the treated unit's pre-treatment outcome trajectory, then estimates
    the treatment effect as the post-treatment divergence.

    Parameters
    ----------
    unit_col : str
        Column identifying individual units.
    time_col : str
        Column identifying time periods.
    outcome_col : str
        Column with the outcome variable.
    treated_unit : any
        The identifier of the treated unit.
    treatment_time : any
        The first period of treatment.
    """

    def __init__(
        self,
        unit_col: str,
        time_col: str,
        outcome_col: str,
        treated_unit: str,
        treatment_time: int | float,
    ) -> None:
        self.unit_col = unit_col
        self.time_col = time_col
        self.outcome_col = outcome_col
        self.treated_unit = treated_unit
        self.treatment_time = treatment_time

    def _build_matrices(
        self,
        frame: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Build pre-treatment outcome matrices for treated and control units."""
        pre = frame[frame[self.time_col] < self.treatment_time]
        pivot = pre.pivot(index=self.time_col, columns=self.unit_col, values=self.outcome_col)

        treated_series = pivot[self.treated_unit].to_numpy(dtype=float)
        control_units = [c for c in pivot.columns if c != self.treated_unit]
        control_matrix = pivot[control_units].to_numpy(dtype=float)

        return treated_series, control_matrix, control_units

    def _solve_weights(
        self,
        treated_pre: np.ndarray,
        control_pre: np.ndarray,
    ) -> np.ndarray:
        """Solve for synthetic control weights via constrained least squares.

        Minimizes ||treated_pre - control_pre @ w||^2
        subject to w >= 0, sum(w) = 1.
        """
        from scipy.optimize import minimize

        n_controls = control_pre.shape[1]
        if n_controls == 0:
            raise ValueError("No control units available")

        def objective(w: np.ndarray) -> float:
            synthetic = control_pre @ w
            return float(np.sum((treated_pre - synthetic) ** 2))

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0)] * n_controls
        w0 = np.ones(n_controls) / n_controls

        result = minimize(
            objective, w0, method="SLSQP",
            bounds=bounds, constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )
        return result.x

    def fit(self, frame: pd.DataFrame, *, _run_placebo: bool = True) -> SyntheticControlEstimate:
        """Estimate the treatment effect using synthetic control."""
        treated_pre, control_pre, control_units = self._build_matrices(frame)
        weights = self._solve_weights(treated_pre, control_pre)

        # Pre-treatment fit quality
        synthetic_pre = control_pre @ weights
        pre_rmse = float(np.sqrt(np.mean((treated_pre - synthetic_pre) ** 2)))

        # Post-treatment effect
        post = frame[frame[self.time_col] >= self.treatment_time]
        pivot_post = post.pivot(index=self.time_col, columns=self.unit_col, values=self.outcome_col)

        treated_post = pivot_post[self.treated_unit].to_numpy(dtype=float)
        control_post = pivot_post[control_units].to_numpy(dtype=float)
        synthetic_post = control_post @ weights

        effect = float(np.mean(treated_post - synthetic_post))
        treated_post_mean = float(treated_post.mean())
        synthetic_post_mean = float(synthetic_post.mean())

        weight_dict = {unit: float(w) for unit, w in zip(control_units, weights) if w > 1e-4}

        # Placebo inference: run synthetic control for each control unit
        if _run_placebo:
            placebo_effects = self._placebo_test(frame, control_units, pre_rmse)
        else:
            placebo_effects = None
        if placebo_effects is not None and len(placebo_effects) > 0:
            rank = sum(1 for pe in placebo_effects if abs(pe) >= abs(effect))
            placebo_p = (rank + 1) / (len(placebo_effects) + 1)
        else:
            placebo_p = None

        return SyntheticControlEstimate(
            method="SyntheticControl",
            effect=effect,
            pre_treatment_rmse=pre_rmse,
            weights=weight_dict,
            treated_unit=str(self.treated_unit),
            treated_post_mean=treated_post_mean,
            synthetic_post_mean=synthetic_post_mean,
            placebo_p_value=placebo_p,
        )

    def _placebo_test(
        self,
        frame: pd.DataFrame,
        control_units: list[str],
        treated_pre_rmse: float,
    ) -> list[float] | None:
        """Run placebo synthetic control for each control unit."""
        effects: list[float] = []
        threshold = max(treated_pre_rmse * 5.0, 1e-6)
        for unit in control_units:
            try:
                placebo = SyntheticControl(
                    self.unit_col, self.time_col, self.outcome_col,
                    treated_unit=unit,
                    treatment_time=self.treatment_time,
                )
                remaining = [u for u in control_units if u != unit]
                remaining.append(self.treated_unit)
                placebo_frame = frame[frame[self.unit_col].isin(remaining + [unit])]
                result = placebo.fit(placebo_frame, _run_placebo=False)
                # Only include placebos with reasonable pre-treatment fit
                if result.pre_treatment_rmse < threshold:
                    effects.append(result.effect)
            except (ValueError, KeyError):
                continue
        return effects if effects else None
