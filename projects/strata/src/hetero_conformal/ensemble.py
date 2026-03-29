"""Ensemble heterogeneous GNN for epistemic uncertainty decomposition.

Trains M independent HeteroGNN models with different random seeds.
Epistemic uncertainty = prediction variance across ensemble members.
This is used as a normalization signal for conformal calibration.

The ensemble enables:
- Epistemic vs. aleatoric uncertainty decomposition
- More robust point predictions (ensemble mean)
- Variance-based σ_i for adaptive conformal intervals
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from .conformal import ConformalResult
from .model import HeteroGNN

if TYPE_CHECKING:
    from .experiment import ExperimentConfig
    from .graph import HeteroInfraGraph


class EnsembleHeteroGNN:
    """Manages an ensemble of HeteroGNN models.

    Trains M models with different random seeds and provides
    ensemble mean predictions and variance estimates.
    """

    def __init__(self, n_members: int = 5):
        self.n_members = n_members
        self.models: List[HeteroGNN] = []

    def build_and_train(
        self,
        graph: "HeteroInfraGraph",
        config: "ExperimentConfig",
        base_seed: int = 42,
    ) -> List[list]:
        """Train M ensemble members with different seeds.

        Returns list of training loss histories (one per member).
        """
        from .experiment import train_model
        from .graph import HeteroInfraGraph

        in_dims = {ntype: f.shape[1] for ntype, f in graph.node_features.items()}
        edge_types = list(graph.edge_index.keys())
        all_losses = []

        for m in range(self.n_members):
            seed = base_seed + m * 1000
            torch.manual_seed(seed)
            np.random.seed(seed)

            model = HeteroGNN(
                in_dims=in_dims,
                hidden_dim=config.hidden_dim,
                num_layers=config.num_layers,
                edge_types=edge_types,
                dropout=config.dropout,
            ).to(config.device)

            model, losses, _ = train_model(model, graph, config)
            self.models.append(model)
            all_losses.append(losses)

        return all_losses

    @torch.no_grad()
    def predict(
        self,
        graph: "HeteroInfraGraph",
        device: str = "cpu",
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """Get ensemble mean predictions and variance.

        Returns
        -------
        mean_preds : dict
            Ensemble mean prediction per node type.
        var_preds : dict
            Ensemble prediction variance per node type (epistemic uncertainty).
        """
        all_preds: Dict[str, List[np.ndarray]] = {}

        for model in self.models:
            model.eval()
            x = {
                ntype: torch.tensor(f, dtype=torch.float32, device=device)
                for ntype, f in graph.node_features.items()
            }
            edge_index = {
                etype: torch.tensor(ei, dtype=torch.long, device=device)
                for etype, ei in graph.edge_index.items()
            }
            preds = model(x, edge_index, graph.num_nodes)
            for ntype, p in preds.items():
                all_preds.setdefault(ntype, []).append(p.cpu().numpy())

        mean_preds = {
            ntype: np.mean(np.stack(ps), axis=0) for ntype, ps in all_preds.items()
        }
        var_preds = {
            ntype: np.var(np.stack(ps), axis=0) for ntype, ps in all_preds.items()
        }
        return mean_preds, var_preds

    @torch.no_grad()
    def get_hidden_representations(
        self,
        graph: "HeteroInfraGraph",
        device: str = "cpu",
    ) -> Dict[str, torch.Tensor]:
        """Extract mean hidden representations across ensemble.

        Useful for CQR quantile heads that operate on hidden states.
        Returns hidden states from the first model (representative).
        """
        model = self.models[0]
        model.eval()
        x = {
            ntype: torch.tensor(f, dtype=torch.float32, device=device)
            for ntype, f in graph.node_features.items()
        }
        edge_index = {
            etype: torch.tensor(ei, dtype=torch.long, device=device)
            for etype, ei in graph.edge_index.items()
        }

        # Forward through GNN layers (skip output heads)
        h: Dict[str, torch.Tensor] = {}
        for ntype in x:
            h[ntype] = F.relu(model.input_proj[ntype](x[ntype]))
        for layer in model.mp_layers:
            h_new = layer(h, edge_index, graph.num_nodes)
            for ntype in h:
                h_new[ntype] = F.relu(h_new[ntype])
                h_new[ntype] = h_new[ntype] + h[ntype]
            h = h_new
        return h


class EnsembleCalibrator:
    """Conformal calibration using ensemble variance for normalization.

    σ_i = 1 + λ · √(epistemic_variance_i)

    The epistemic variance captures model uncertainty, which is higher
    for nodes in under-represented parts of the graph.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        neighborhood_weight: float = 0.5,
    ):
        self.alpha = alpha
        self.neighborhood_weight = neighborhood_weight
        self.quantiles: Dict[str, float] = {}
        self._sigma: Dict[str, np.ndarray] = {}
        self._calibrated = False

    def calibrate(
        self,
        mean_predictions: Dict[str, np.ndarray],
        var_predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        cal_masks: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """Calibrate using ensemble variance for normalization."""
        for ntype in cal_masks:
            cal_mask = cal_masks[ntype]
            epistemic_std = np.sqrt(var_predictions[ntype])
            sigma = 1.0 + self.neighborhood_weight * epistemic_std
            self._sigma[ntype] = sigma.astype(np.float32)

            cal_resid = np.abs(labels[ntype][cal_mask] - mean_predictions[ntype][cal_mask])
            normalized = cal_resid / sigma[cal_mask]
            n_cal = len(normalized)
            if n_cal == 0:
                self.quantiles[ntype] = float("inf")
                continue
            level = min(np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal, 1.0)
            self.quantiles[ntype] = float(np.quantile(normalized, level))

        self._calibrated = True
        return dict(self.quantiles)

    def predict(
        self,
        mean_predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() first")
        lower, upper, point = {}, {}, {}
        for ntype in mean_predictions:
            pred = mean_predictions[ntype]
            q = self.quantiles[ntype]
            sigma = self._sigma[ntype]
            width = q * sigma
            lo, hi = pred - width, pred + width
            if test_masks is not None and ntype in test_masks:
                mask = test_masks[ntype]
                lower[ntype], upper[ntype], point[ntype] = lo[mask], hi[mask], pred[mask]
            else:
                lower[ntype], upper[ntype], point[ntype] = lo, hi, pred
        return ConformalResult(lower, upper, point, self.alpha, dict(self.quantiles))
