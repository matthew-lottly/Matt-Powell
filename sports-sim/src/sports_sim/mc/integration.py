"""Integration between Monte Carlo tuner and the real Simulation engine.

Provides an evaluator that maps numeric params to `TeamSliders` and runs
real simulations to compute an objective score (average goal difference).
"""
from __future__ import annotations

from typing import Dict, Any, List

from concurrent.futures import ProcessPoolExecutor

from sports_sim.mc.tuning import MonteCarloTuner
from sports_sim.mc.worker import run_engine_sim_once
from sports_sim.core.models import SimulationConfig, SportType, TeamSliders
from sports_sim.core.engine import Simulation


class EngineEvaluator(MonteCarloTuner):
    """Evaluate parameter candidates by running the Simulation engine."""

    def params_to_sliders(self, params: Dict[str, float]) -> TeamSliders:
        # Map common numeric params to TeamSliders fields conservatively
        sliders = TeamSliders()
        if "attack_factor" in params:
            val = float(params["attack_factor"])
            sliders.offensive_aggression = max(0.0, min(1.0, val))
        if "defense_factor" in params:
            val = float(params["defense_factor"])
            sliders.defensive_intensity = max(0.0, min(1.0, val))
        if "pace" in params:
            sliders.pace = float(params["pace"])
        return sliders

    def evaluate(self, params: Dict[str, float], n_sims: int = 20, sport: str = "soccer") -> float:
        """Run `n_sims` engine simulations and return average home goal difference.

        If `workers` is provided in `kwargs` use a process pool for parallel execution.
        """
        total_diff = 0.0
        # If called with workers kwarg, run in parallel
        workers = None
        try:
            workers = kwargs.get("workers") if "kwargs" in locals() else None
        except Exception:
            workers = None

        if workers and workers > 1:
            tasks = []
            with ProcessPoolExecutor(max_workers=workers) as ex:
                for i in range(n_sims):
                    tasks.append(ex.submit(run_engine_sim_once, params, i, sport))
                for f in tasks:
                    total_diff += float(f.result())
            return total_diff / float(n_sims)

        # fallback sequential
        sliders = self.params_to_sliders(params)
        for i in range(n_sims):
            cfg = SimulationConfig(
                sport=SportType(sport),
                seed=i,
                fidelity="fast",
                ticks_per_second=5,
                home_sliders=sliders,
                away_sliders=None,
            )
            sim = Simulation(cfg)
            final = sim.run()
            diff = float(final.home_team.score - final.away_team.score)
            total_diff += diff
        return total_diff / float(n_sims)


__all__ = ["EngineEvaluator"]
