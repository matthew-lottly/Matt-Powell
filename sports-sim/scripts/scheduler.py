"""Simple scheduler to run Monte Carlo tuning jobs periodically and export Prometheus metrics."""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from prometheus_client import start_http_server

from sports_sim.mc.integration import EngineEvaluator
from sports_sim.metrics import tuning_runs_total, tuning_last_duration_seconds, tuning_best_score


def run_job(db_path: str | None, jsonl_path: str | None, workers: int, sims: int):
    tuner = EngineEvaluator()
    grid = {"attack_factor": [0.9, 1.0, 1.1], "defense_factor": [0.9, 1.0, 1.1]}
    start = time.time()
    res = tuner.tune(grid, n_iter=5, sims=sims, seed=int(time.time()) % 10000, workers=workers, db_path=db_path, jsonl_path=jsonl_path)
    duration = time.time() - start
    tuning_runs_total.inc()
    tuning_last_duration_seconds.observe(duration)
    if res.get("best_score") is not None:
        tuning_best_score.set(float(res["best_score"]))
    return res


def main():
    parser = argparse.ArgumentParser(description="Scheduler for tuning jobs + Prometheus metrics")
    parser.add_argument("--interval", type=int, default=3600, help="Run interval in seconds")
    parser.add_argument("--db", type=str, default="tuning.db")
    parser.add_argument("--jsonl", type=str, default="tuning.jsonl")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--sims", type=int, default=10)
    parser.add_argument("--metrics-port", type=int, default=8001)
    args = parser.parse_args()

    # Start Prometheus metrics HTTP server
    start_http_server(args.metrics_port)
    print(f"Prometheus metrics available on :{args.metrics_port}")

    # Ensure db/jsonl paths exist
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    Path(args.jsonl).parent.mkdir(parents=True, exist_ok=True)

    # Run initial job
    run_job(args.db, args.jsonl, args.workers, args.sims)

    # Periodic loop
    with ThreadPoolExecutor(max_workers=1) as ex:
        while True:
            time.sleep(args.interval)
            ex.submit(run_job, args.db, args.jsonl, args.workers, args.sims)


if __name__ == "__main__":
    main()
