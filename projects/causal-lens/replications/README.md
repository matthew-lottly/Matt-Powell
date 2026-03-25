# Replication Scripts

Standalone scripts that reproduce the key results from the CausalLens software paper.
Each script is self-contained and writes outputs to `replications/outputs/`.

## Scripts

| Script | Benchmark | Expected Runtime |
|--------|-----------|-----------------|
| `replicate_lalonde.py` | Dehejia & Wahba (1999) job-training ATT | ~2 min |
| `replicate_nhefs.py` | Hernán & Robins (2020) NHEFS weight gain | ~1 min |
| `replicate_simulation.py` | Monte Carlo bias/RMSE/coverage study | 3–20 min |
| `replicate_cross_design.py` | Cross-design diagnostic comparison | <30 sec |

## Running

```bash
# From the project root:
pip install -e .
python replications/replicate_lalonde.py
python replications/replicate_nhefs.py
python replications/replicate_simulation.py          # quick mode
python replications/replicate_simulation.py --full   # full 200-rep study
python replications/replicate_cross_design.py
```

## Outputs

All CSVs are written to `replications/outputs/` and are git-ignored.
