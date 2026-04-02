from typing import Any

from sports_sim.mc.tuning import MonteCarloTuner


def test_mc_tuner_runs_quick():
    tuner = MonteCarloTuner()
    grid: dict[str, Any] = {"attack": [0.9, 1.0], "defense": [0.9, 1.0]}
    out = tuner.tune(grid, n_iter=5, sims=10, seed=42)
    assert isinstance(out, dict)
    assert "best_params" in out and "best_score" in out and "results" in out
    assert isinstance(out["results"], list)
