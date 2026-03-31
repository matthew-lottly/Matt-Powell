"""Basic betting odds utilities and a simple implied probability model."""
from __future__ import annotations

from typing import Dict


def decimal_to_implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability (no-vig adjustment)."""
    if decimal_odds <= 1.0:
        return 0.0
    return 1.0 / float(decimal_odds)


def normalize_market(odds: Dict[str, float]) -> Dict[str, float]:
    """Given a dict of outcome->decimal_odds, return implied probs normalized to sum to 1 (remove vig)."""
    implied = {k: decimal_to_implied_prob(v) for k, v in odds.items()}
    total = sum(implied.values()) or 1.0
    return {k: float(v) / total for k, v in implied.items()}


__all__ = ["decimal_to_implied_prob", "normalize_market"]
