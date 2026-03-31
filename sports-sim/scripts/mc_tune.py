"""CLI wrapper to run the simple Monte Carlo tuner."""
from __future__ import annotations

import argparse
import json
from sports_sim.mc.tuning import MonteCarloTuner


def main():
    parser = argparse.ArgumentParser(description="Run Monte Carlo tuning")
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--sims", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker processes to use")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint JSON file")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite DB for results")
    parser.add_argument("--jsonl", type=str, default=None, help="Path to JSONL append-only results file")
    parser.add_argument("--optimizer", type=str, choices=["random", "optuna"], default="random")
    args = parser.parse_args()

    # Simple example parameter grid
    grid = {
        "attack_factor": [0.8, 0.9, 1.0, 1.1, 1.2],
        "defense_factor": [0.8, 0.9, 1.0, 1.1],
    }

    tuner = MonteCarloTuner()
    kwargs = {}
    if args.workers and args.workers > 1:
        kwargs["workers"] = args.workers
    if args.checkpoint:
        kwargs["checkpoint_path"] = args.checkpoint

    if args.optimizer == "optuna":
        try:
            from sports_sim.mc.optuna_wrapper import optuna_tune

            def _obj(p):
                return tuner.evaluate({k: float(v) for k, v in p.items()}, n_sims=args.sims)

            out = optuna_tune(_obj, grid, n_trials=args.iters, seed=args.seed)
            print(out)
            return
        except Exception as e:
            print("Optuna tuning failed or optuna not installed:", e)

    result = tuner.tune(grid, n_iter=args.iters, sims=args.sims, seed=args.seed, db_path=args.db, jsonl_path=args.jsonl, checkpoint_path=args.checkpoint, workers=args.workers)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
