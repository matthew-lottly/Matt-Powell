import json
from typing import Any

from sports_sim.mc.tuning import MonteCarloTuner


def test_tuner_checkpoint_and_parallel(tmp_path):
    tuner = MonteCarloTuner()
    grid: dict[str, Any] = {"attack": [0.9, 1.0], "defense": [0.9, 1.0]}
    checkpoint = tmp_path / "checkpoint.json"
    out = tuner.tune(grid, n_iter=4, sims=20, seed=7, checkpoint_path=str(checkpoint), workers=2)
    assert "best_params" in out and out["results"]
    assert checkpoint.exists()
    data = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert "best_score" in data and "results" in data
