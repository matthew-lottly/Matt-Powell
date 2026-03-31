"""Worker functions for running engine simulations in separate processes.

These functions are module-level so they can be pickled by ProcessPoolExecutor.
"""
from __future__ import annotations

from typing import Dict, Any

from sports_sim.core.models import SimulationConfig, SportType, TeamSliders
from sports_sim.core.engine import Simulation


def _make_config_from_params(params: Dict[str, float], seed: int, sport: str = "soccer") -> SimulationConfig:
    sliders = TeamSliders()
    if "attack_factor" in params:
        sliders.offensive_aggression = float(params["attack_factor"])
    if "defense_factor" in params:
        sliders.defensive_intensity = float(params["defense_factor"])
    if "pace" in params:
        sliders.pace = float(params["pace"])

    cfg = SimulationConfig(
        sport=SportType(sport),
        seed=seed,
        fidelity="fast",
        ticks_per_second=5,
        home_sliders=sliders,
        away_sliders=None,
    )
    return cfg


def run_engine_sim_once(params: Dict[str, float], seed: int = 0, sport: str = "soccer") -> float:
    """Run one engine simulation and return home_score - away_score as float."""
    cfg = _make_config_from_params(params, seed, sport)
    sim = Simulation(cfg)
    final = sim.run()
    return float(final.home_team.score - final.away_team.score)


__all__ = ["run_engine_sim_once"]
