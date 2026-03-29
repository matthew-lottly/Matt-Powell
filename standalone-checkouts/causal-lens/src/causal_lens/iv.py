"""Instrumental variables estimator: two-stage least squares (2SLS).

Implements the standard IV/2SLS approach for estimating causal effects
when unobserved confounding is present but a valid instrument exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


@dataclass(frozen=True)
class IVEstimate:
    """Result container for an instrumental variables estimate."""
    method: str
    effect: float
    se: float
    p_value: float
    ci_low: float
    ci_high: float
    first_stage_f: float
    first_stage_r_squared: float
    n_obs: int
    n_instruments: int
    weak_instrument: bool

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class TwoStageLeastSquares:
    """Two-stage least squares (2SLS) instrumental variables estimator.

    Implements the standard 2SLS procedure:
      Stage 1: Regress endogenous treatment on instruments + covariates
      Stage 2: Regress outcome on predicted treatment + covariates

    Standard errors are computed using the proper 2SLS variance formula
    (not the naive second-stage OLS SEs, which are wrong).

    Parameters
    ----------
    treatment_col : str
        The endogenous treatment variable.
    outcome_col : str
        The outcome variable.
    instrument_cols : list[str]
        One or more instrumental variables.
    covariate_cols : list[str]
        Exogenous covariates included in both stages.
    """

    def __init__(
        self,
        treatment_col: str,
        outcome_col: str,
        instrument_cols: list[str],
        covariate_cols: list[str] | None = None,
    ) -> None:
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.instrument_cols = instrument_cols
        self.covariate_cols = covariate_cols or []

    def fit(self, frame: pd.DataFrame) -> IVEstimate:
        """Estimate the LATE/Wald estimate via 2SLS."""
        y = frame[self.outcome_col].to_numpy(dtype=float)
        d = frame[self.treatment_col].to_numpy(dtype=float)
        n = len(y)

        # Exogenous regressors: constant + covariates
        x_exog = np.column_stack([
            np.ones(n),
            *(frame[c].to_numpy(dtype=float).reshape(-1, 1) for c in self.covariate_cols),
        ]) if self.covariate_cols else np.ones((n, 1))

        # Instruments
        z_instruments = np.column_stack([
            frame[c].to_numpy(dtype=float).reshape(-1, 1) for c in self.instrument_cols
        ])

        # Full instrument matrix: exogenous + instruments
        z_full = np.column_stack([x_exog, z_instruments])

        # Stage 1: Regress D on Z
        z_tz = z_full.T @ z_full
        z_td = z_full.T @ d
        try:
            gamma_hat = np.linalg.solve(z_tz, z_td)
        except np.linalg.LinAlgError:
            gamma_hat = np.linalg.lstsq(z_full, d, rcond=None)[0]
        d_hat = z_full @ gamma_hat

        # First-stage diagnostics
        d_mean = d.mean()
        ss_total = float(np.sum((d - d_mean) ** 2))
        ss_residual_1st = float(np.sum((d - d_hat) ** 2))
        r_squared_1st = 1.0 - ss_residual_1st / ss_total if ss_total > 1e-12 else 0.0

        # First-stage F-statistic for instrument relevance
        # F = ((SS_restricted - SS_unrestricted) / q) / (SS_unrestricted / (n - k))
        # where q = number of instruments, k = total regressors in first stage
        d_hat_restricted = x_exog @ np.linalg.lstsq(x_exog, d, rcond=None)[0]
        ss_restricted = float(np.sum((d - d_hat_restricted) ** 2))
        q = len(self.instrument_cols)
        k = z_full.shape[1]
        denom = ss_residual_1st / (n - k) if n > k else 1e-12
        f_stat = ((ss_restricted - ss_residual_1st) / q) / denom if denom > 1e-12 else 0.0

        # Stage 2: Regress Y on D_hat + X_exog
        x_2nd = np.column_stack([x_exog, d_hat])
        try:
            beta_hat = np.linalg.solve(x_2nd.T @ x_2nd, x_2nd.T @ y)
        except np.linalg.LinAlgError:
            beta_hat = np.linalg.lstsq(x_2nd, y, rcond=None)[0]

        effect = float(beta_hat[-1])  # coefficient on d_hat

        # Proper 2SLS standard errors (using actual D, not D_hat, for residuals)
        x_actual = np.column_stack([x_exog, d])
        residuals = y - x_actual @ beta_hat
        sigma2 = float(np.sum(residuals ** 2)) / (n - x_actual.shape[1])

        # Var(beta) = sigma^2 * (X'P_Z X)^{-1}  where P_Z = Z(Z'Z)^{-1}Z'
        try:
            z_tz_inv = np.linalg.inv(z_tz)
        except np.linalg.LinAlgError:
            z_tz_inv = np.linalg.pinv(z_tz)
        p_z = z_full @ z_tz_inv @ z_full.T
        x_pz_x = x_actual.T @ p_z @ x_actual
        try:
            var_beta = sigma2 * np.linalg.inv(x_pz_x)
        except np.linalg.LinAlgError:
            var_beta = sigma2 * np.linalg.pinv(x_pz_x)

        se = float(np.sqrt(var_beta[-1, -1]))
        z_score = effect / se if se > 1e-12 else 0.0
        p_value = float(2.0 * (1.0 - norm.cdf(abs(z_score))))
        ci_low = effect - 1.96 * se
        ci_high = effect + 1.96 * se

        return IVEstimate(
            method="TwoStageLeastSquares",
            effect=effect,
            se=se,
            p_value=p_value,
            ci_low=ci_low,
            ci_high=ci_high,
            first_stage_f=float(f_stat),
            first_stage_r_squared=float(r_squared_1st),
            n_obs=n,
            n_instruments=q,
            weak_instrument=f_stat < 10.0,
        )
