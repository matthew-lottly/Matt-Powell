"""Simple Monte Carlo tuning harness for the sports-sim engine.

This is a lightweight, deterministic-by-params harness intended for
parameter-search and smoke tests. It uses a reproducible RNG seed
derived from parameter values so results are stable across runs.
"""
from __future__ import annotations

import random
import json
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, Iterable, List
from sports_sim.mc.persistence import TuningDB, append_jsonl


def simulate_once(params: Dict[str, float], run_index: int = 0) -> float:
    """Simulate a single match outcome given parameter dict.

    Returns a numeric score: +1 for win, 0 for draw, -1 for loss.
    The result is deterministic for identical `params` and `run_index`.
    """
    seed_val = int(sum(float(v) for v in params.values()) * 100000) + run_index
    rng = random.Random(seed_val)
    # Base win probability influenced by the sum of params
    strength = sum(float(v) for v in params.values()) / max(1.0, len(params))
    win_prob = 0.45 * (1.0 + (strength - 1.0) * 0.5)
    draw_prob = 0.2
    r = rng.random()
    if r < max(0.0, min(1.0, win_prob)):
        return 1.0
    if r < max(0.0, min(1.0, win_prob + draw_prob)):
        return 0.0
    return -1.0


class MonteCarloTuner:
    """A simple random-search Monte Carlo tuner.

    Usage:
        tuner = MonteCarloTuner()
        best = tuner.tune(param_grid, n_iter=50, sims=100)
    """

    def evaluate(self, params: Dict[str, float], n_sims: int = 50) -> float:
        """Run `n_sims` simulations and return the average score."""
        total = 0.0
        for i in range(n_sims):
            total += simulate_once(params, run_index=i)
        return total / float(n_sims)

    def evaluate_parallel(self, params: Dict[str, float], n_sims: int = 50, workers: int | None = None) -> float:
        """Parallelized evaluation using multiple processes.

        Falls back to sequential when ProcessPoolExecutor isn't desirable.
        """
        if workers is None or workers <= 1:
            return self.evaluate(params, n_sims=n_sims)

        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(simulate_once, params, i) for i in range(n_sims)]
            total = sum(f.result() for f in futures)
        return total / float(n_sims)

    def sample_from_grid(self, grid: Dict[str, Iterable[Any]], rng: random.Random) -> Dict[str, Any]:
        choice = {}
        for k, vals in grid.items():
            vals_list = list(vals)
            choice[k] = rng.choice(vals_list)
        return choice

    def tune(
        self,
        param_grid: Dict[str, Iterable[Any]],
        n_iter: int = 20,
        sims: int = 50,
        seed: int = 1,
        checkpoint_path: str | None = None,
        workers: int | None = None,
        db_path: str | None = None,
        jsonl_path: str | None = None,
    ) -> Dict[str, Any]:
        """Random-search over `param_grid` for `n_iter` samples.

        Optional checkpointing supported via `checkpoint_path` in `kwargs`.
        If `workers` provided in `kwargs`, runs per-candidate sims in parallel.

        Returns a dict with `best_params`, `best_score`, and `results`.
        """
        rng = random.Random(seed)
        best_score = float('-inf')
        best_params = None
        results: List[Dict[str, Any]] = []

        # If db_path provided, load existing results to resume
        db = None
        if db_path:
            try:
                db = TuningDB(db_path)
                existing = db.all_results()
                for r in existing:
                    results.append({"params": r["params"], "score": r["score"]})
                    if r["score"] > best_score:
                        best_score = r["score"]
                        best_params = r["params"]
            except Exception:
                db = None

        for i in range(n_iter):
            candidate = self.sample_from_grid(param_grid, rng)
            numeric_candidate = {k: float(v) for k, v in candidate.items()}
            if workers:
                score = self.evaluate_parallel(numeric_candidate, n_sims=sims, workers=workers)
            else:
                score = self.evaluate(numeric_candidate, n_sims=sims)
            results.append({"params": candidate, "score": score})
            if score > best_score:
                best_score = score
                best_params = candidate

            # persist per-candidate
            if db is not None:
                try:
                    db.insert_result(candidate, score)
                except Exception:
                    pass
            if jsonl_path:
                try:
                    append_jsonl(jsonl_path, candidate, score)
                except Exception:
                    pass

            if checkpoint_path:
                payload = {"best_params": best_params, "best_score": best_score, "results": results}
                try:
                    with open(checkpoint_path, "w", encoding="utf-8") as fh:
                        json.dump(payload, fh, indent=2)
                except Exception:
                    # Don't fail tuner due to checkpoint IO issues
                    pass

        if db is not None:
            db.close()
        return {"best_params": best_params, "best_score": best_score, "results": results}


__all__ = ["MonteCarloTuner", "simulate_once"]
