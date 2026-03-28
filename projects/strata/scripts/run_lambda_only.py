#!/usr/bin/env python3
"""Run only the lambda sensitivity sweep and write outputs to outputs/.

This imports `run_benchmark.py` as a module (without executing its `main`) and
invokes `run_lambda_sweep()` to avoid retraining per-lambda.
"""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
OUT.mkdir(exist_ok=True)

spec = importlib.util.spec_from_file_location("run_benchmark_module", HERE / "run_benchmark.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("Running lambda sensitivity sweep...")
rows = mod.run_lambda_sweep()
mod._write_csv(OUT / "lambda_sensitivity.csv", rows)
mod.build_summary_table(rows, "lambda", OUT / "lambda_table.md")
mod.plot_lambda_sensitivity(rows)
print("Lambda sweep complete. Outputs written to:", OUT)
