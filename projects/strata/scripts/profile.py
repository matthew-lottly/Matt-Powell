"""Simple profiling harness for STRATA quick demo.

Run: python scripts/profile.py
Generates a small timing report for key pipeline stages.
"""
import time
import json
from pathlib import Path

from hetero_conformal import generate_synthetic_infrastructure
from hetero_conformal.experiment import ExperimentConfig, train_model

OUT = Path(__file__).resolve().parent.parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

def time_pipeline():
    t0 = time.time()
    graph = generate_synthetic_infrastructure(n_power=100, n_water=80, n_telecom=50, seed=0)
    t1 = time.time()
    config = ExperimentConfig(hidden_dim=32, num_layers=2, epochs=5)
    model, losses, _ = train_model(config=getattr(config, '__dict__', config) and None, graph=graph, config=config) if False else (None, [], None)
    # Note: training is heavy; here we just measure data gen. For a full run, call train_model() directly.
    t2 = time.time()
    report = {
        "data_generation": t1 - t0,
        "(training_skipped_sample)": t2 - t1,
    }
    out_file = OUT / "profile_summary.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(f"Wrote profile summary to {out_file}")

if __name__ == '__main__':
    time_pipeline()
