from pathlib import Path
from typing import Any

from sports_sim.mc.tuning import MonteCarloTuner


def test_persistence_resume(tmp_path: Path):
    db_file = tmp_path / "tuning.db"
    tuner = MonteCarloTuner()
    grid: dict[str, Any] = {"attack": [0.9, 1.0], "defense": [0.9, 1.0]}

    # First run: 3 iterations
    tuner.tune(grid, n_iter=3, sims=5, seed=3, db_path=str(db_file))
    assert db_file.exists()

    # Second run: request 5 iterations, should resume and append
    out2 = tuner.tune(grid, n_iter=5, sims=5, seed=3, db_path=str(db_file))
    # basic sanity: results present and best_score numeric
    assert "best_score" in out2 and isinstance(out2["best_score"], float)
