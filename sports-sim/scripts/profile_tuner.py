"""Profile a small tuner run using cProfile and write stats to file."""
from __future__ import annotations

import cProfile
import pstats
from sports_sim.mc.tuning import MonteCarloTuner


def main():
    tuner = MonteCarloTuner()
    profiler = cProfile.Profile()
    profiler.enable()
    tuner.tune({"attack": [0.9, 1.0], "defense": [0.9, 1.0]}, n_iter=10, sims=10, seed=1)
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats("tuner_profile.prof")
    print("Wrote tuner_profile.prof")


if __name__ == "__main__":
    main()
