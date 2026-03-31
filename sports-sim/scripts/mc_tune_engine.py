"""CLI wrapper to run Monte Carlo tuner using the real Simulation engine."""
from __future__ import annotations

import argparse
import json
from sports_sim.mc.integration import EngineEvaluator


def main():
    parser = argparse.ArgumentParser(description="Run Monte Carlo tuner against engine")
    parser.add_argument("--iters", type=int, default=10)
    parser.add_argument("--sims", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sport", type=str, default="soccer")
    parser.add_argument("--workers", type=int, default=1, help="Worker processes to parallelize engine sims")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint JSON file")
    args = parser.parse_args()

    grid = {
        "attack_factor": [0.8, 0.9, 1.0, 1.1],
        "defense_factor": [0.8, 0.9, 1.0, 1.1],
    }

    tuner = EngineEvaluator()
    kwargs = {}
    if args.workers and args.workers > 1:
        kwargs["workers"] = args.workers
    if args.checkpoint:
        kwargs["checkpoint_path"] = args.checkpoint

    result = tuner.tune(grid, n_iter=args.iters, sims=args.sims, seed=args.seed, **kwargs)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
