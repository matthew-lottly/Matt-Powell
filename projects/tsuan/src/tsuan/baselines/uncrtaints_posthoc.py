"""UnCRtainTS-style post-hoc baseline wrapper for comparison.

Implements the key idea from UnCRtainTS (Ebel et al., CVPRW 2023):
filter reconstructed pixels by their predicted uncertainty, discarding
high-uncertainty regions post-hoc.  This allows a head-to-head comparison:

    TSUAN + SOVD (built-in knowability)  vs.  TSUAN + post-hoc filtering

If SOVD outperforms post-hoc filtering at the same coverage level,
we have a publishable result.

Usage::

    from tsuan.baselines.uncrtaints_posthoc import PostHocUncertaintyFilter

    filt = PostHocUncertaintyFilter(coverage=0.8)
    filtered = filt(model_outputs)
"""

from __future__ import annotations

import numpy as np
import torch


class PostHocUncertaintyFilter:
    """Apply post-hoc uncertainty thresholding à la UnCRtainTS.

    Given a model's reconstruction and per-pixel uncertainty, discard
    the top-(1-coverage) fraction of most-uncertain pixels.

    Parameters
    ----------
    coverage : float
        Fraction of pixels to retain (e.g. 0.8 → discard 20% most uncertain).
    """

    def __init__(self, coverage: float = 0.8):
        if not 0.0 < coverage <= 1.0:
            raise ValueError(f"coverage must be in (0, 1], got {coverage}")
        self.coverage = coverage

    def compute_threshold(self, sigma: torch.Tensor) -> torch.Tensor:
        """Compute the uncertainty threshold for given coverage.

        Parameters
        ----------
        sigma : Tensor — per-pixel uncertainty (any shape, flattened internally)

        Returns
        -------
        threshold : scalar Tensor
        """
        flat = sigma.flatten()
        k = int(len(flat) * self.coverage)
        k = max(1, min(k, len(flat)))
        sorted_vals, _ = torch.sort(flat)
        return sorted_vals[k - 1]

    def __call__(self, outputs: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Apply post-hoc filtering to model outputs.

        Expects ``outputs`` to contain at minimum:
            - x_hat : Tensor — reconstruction
            - sigma_pixel : Tensor — per-pixel uncertainty

        Returns a copy with added keys:
            - posthoc_mask : Tensor (same spatial as sigma_pixel),
              1 where retained, 0 where discarded
            - x_hat_filtered : Tensor — x_hat with discarded pixels zeroed
        """
        sigma = outputs["sigma_pixel"]
        threshold = self.compute_threshold(sigma)

        # 1 = keep, 0 = discard (high uncertainty)
        posthoc_mask = (sigma <= threshold).float()

        # Expand mask to match x_hat spatial dims if needed
        x_hat = outputs["x_hat"]
        if posthoc_mask.shape[-2:] != x_hat.shape[-2:]:
            posthoc_mask_up = torch.nn.functional.interpolate(
                posthoc_mask.reshape(-1, 1, *posthoc_mask.shape[-2:]),
                size=x_hat.shape[-2:],
                mode="nearest",
            ).reshape(*x_hat.shape[:-3], 1, *x_hat.shape[-2:])
        else:
            posthoc_mask_up = posthoc_mask

        result = dict(outputs)
        result["posthoc_mask"] = posthoc_mask
        result["x_hat_filtered"] = x_hat * posthoc_mask_up

        return result

    def compute_metrics(
        self,
        x_hat: torch.Tensor,
        x_target: torch.Tensor,
        sigma: torch.Tensor,
        coverages: list[float] | None = None,
    ) -> list[dict[str, float]]:
        """Compute RMSE at multiple coverage levels.

        Useful for generating coverage-vs-RMSE curves.

        Parameters
        ----------
        x_hat : (B, T, C, H, W)
        x_target : (B, T, C, H, W)
        sigma : (B, T, 1, H', W')
        coverages : list of coverage fractions to evaluate

        Returns
        -------
        List of dicts with keys: coverage, rmse, n_pixels_retained
        """
        if coverages is None:
            coverages = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        # Upsample sigma to target spatial dims if needed
        if sigma.shape[-2:] != x_hat.shape[-2:]:
            sigma_up = torch.nn.functional.interpolate(
                sigma.reshape(-1, 1, *sigma.shape[-2:]),
                size=x_hat.shape[-2:],
                mode="nearest",
            ).reshape(*sigma.shape[:-2], *x_hat.shape[-2:])
        else:
            sigma_up = sigma.squeeze(-3)  # remove channel dim

        flat_sigma = sigma_up.flatten()
        sorted_vals, _ = torch.sort(flat_sigma)

        error = (x_hat - x_target) ** 2  # (B, T, C, H, W)
        pixel_mse = error.mean(dim=2)  # (B, T, H, W)
        flat_mse = pixel_mse.flatten()

        results = []
        for cov in coverages:
            k = max(1, int(len(flat_sigma) * cov))
            thresh = sorted_vals[k - 1]
            mask = flat_sigma <= thresh
            n_retained = int(mask.sum())

            if n_retained == 0:
                results.append({"coverage": cov, "rmse": float("nan"), "n_pixels_retained": 0})
                continue

            masked_mse = flat_mse[mask]
            rmse = float(torch.sqrt(masked_mse.mean()))
            results.append({
                "coverage": round(cov, 2),
                "rmse": round(rmse, 6),
                "n_pixels_retained": n_retained,
            })

        return results
