# Architecture

CausalLens uses an estimator-oriented design with small, composable modules.

## Core modules

- `data.py`: schema validation and dataframe preparation
- `diagnostics.py`: balance and overlap diagnostics
- `estimators.py`: regression adjustment, matching, IPW, and doubly robust estimators
- `results.py`: typed result containers and report serialization
- `synthetic.py`: synthetic observational datasets with known treatment effects
- `data.py`: fixed observational CSV loading helpers for reproducible examples and tests
- `cli.py`: command-line demo and JSON export path

## Phase 2 extensions

1. Estimators now expose `sensitivity_analysis()` for additive-bias explain-away summaries.
2. Estimators now expose `subgroup_effects()` for quick heterogeneous-effect scans over categorical or binned subgroup columns.
3. The CLI uses the doubly robust estimator as the primary summary estimator for these Phase 2 exports.
4. The repository now ships a fixed observational intervention sample to support reproducible testing and paper-ready examples.

## Design goals

1. Keep the public API dataframe-friendly.
2. Use shared result objects across estimators.
3. Make diagnostics first-class rather than optional afterthoughts.
4. Preserve room for later panel and IV estimators without breaking the v0.1 surface.
5. Maintain two evidence modes: synthetic correctness fixtures and fixed observational reproducibility fixtures.
