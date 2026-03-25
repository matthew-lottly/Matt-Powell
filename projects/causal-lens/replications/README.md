# Replication Scripts

Standalone scripts that reproduce the key results from the CausalLens software paper.
Each script is self-contained and writes outputs to `replications/outputs/`.
A single runner script is also provided to execute the full stack from one command
and then regenerate the manuscript-ready tables and figures under `outputs/paper/`.

## Scripts

| Script | Benchmark | Expected Runtime |
|--------|-----------|-----------------|
| `run_all.py` | Runs the full replication stack | <1 min without simulation; ~5 min quick / ~45 min full |
| `replicate_lalonde.py` | Dehejia & Wahba (1999) job-training ATT | ~2 min |
| `replicate_nhefs.py` | Hernán & Robins (2020) NHEFS weight gain | ~1 min |
| `replicate_simulation.py` | Monte Carlo bias/RMSE/coverage study | ~5 min quick / ~45 min full |
| `replicate_cross_design.py` | Cross-design diagnostic comparison | <30 sec |

## Running

```bash
# From the project root:
pip install -e .
python replications/run_all.py --skip-simulation
python replications/run_all.py              # includes quick simulation
python replications/run_all.py --full       # includes full simulation
python replications/replicate_lalonde.py
python replications/replicate_nhefs.py
python replications/replicate_simulation.py          # quick mode
python replications/replicate_simulation.py --full   # full 200-rep study
python replications/replicate_cross_design.py
```

## Outputs

- Replication CSVs are written to `replications/outputs/` and are git-ignored.
- The one-command runner also refreshes the manuscript-ready bundle under `outputs/paper/`.
- Supporting benchmark, comparison, and stability tables are written under `outputs/tables/`.
