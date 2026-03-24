# CausalLens

Data science portfolio project for causal effect estimation, observational-study diagnostics, and reviewable treatment-effect outputs.

## Snapshot

- Lane: Data science and causal inference
- Domain: Observational treatment-effect estimation
- Stack: Python, pandas, scikit-learn, statsmodels, lightweight estimator objects
- Includes: regression adjustment, propensity scoring, matching, inverse probability weighting, doubly robust estimation, diagnostics, subgroup summaries, sensitivity analysis, tests
- Includes: a fixed observational intervention dataset, two public benchmark datasets, synthetic known-effect validation, and publication-oriented methodology notes

## Overview

CausalLens packages core causal-inference workflows for observational tabular data into a small, testable Python library. The initial release is designed around practical treatment-effect estimation rather than theory-heavy experimentation: estimate treatment effects, inspect overlap and balance, and compare estimators with consistent result objects.

The current repository now uses three complementary evidence tracks:

- a fixed public-safe observational intervention sample under `data/` for reproducible article figures and tests
- public benchmark datasets drawn from the causal inference literature for externally recognizable evaluation
- synthetic known-effect data for correctness-oriented validation of estimator behavior

## What It Demonstrates

- Propensity score estimation with a scikit-learn logistic model with standardized covariates
- Regression-adjustment treatment effects with statsmodels OLS
- Nearest-neighbor propensity matching with optional calipers
- Inverse probability weighting with stabilized weights and weight capping for ATE and ATT targets
- Doubly robust estimation that combines outcome and propensity models with weight trimming
- Covariate-balance summaries using standardized mean differences
- Common-support and overlap diagnostics for positivity review
- Additive-bias sensitivity summaries for explain-away analysis on the outcome scale
- Subgroup treatment-effect summaries for quick heterogeneous-effect review
- A small command-line demo that exports a reproducible causal report
- A real-style observational intervention fixture for stable estimator-comparison tests
- Publication-oriented methodology notes explaining why the initial estimator set is justified
- Reference parity tests against manual formulas and direct statistical-model fits
- Paper-ready chart and table exports for estimator comparison, balance, sensitivity, and subgroup effects
- Manuscript drafting docs, figure captions, and cross-dataset benchmark tables for the software-paper path
- Packaged public benchmarks based on Lalonde and NHEFS so installed users can reproduce the evidence stack without a source checkout
- Literature comparison table showing CausalLens results match published reference values from Dehejia & Wahba (1999) and Hernán & Robins (2020)
- Repeated-run stability analysis across seeds, bootstrap counts, and caliper settings
- External comparison script verifying CausalLens matches manual sklearn/statsmodels implementations to machine precision

## Current Output

The default command writes `outputs/causal_report.json` with:

- a fixed real-style observational dataset section with estimator comparisons
- a Lalonde benchmark section with public observational training-program data
- an NHEFS benchmark section with public smoking-cessation observational data
- a synthetic validation dataset section with known-effect comparisons
- overlap summary and propensity score range checks
- covariate balance before/after weighting
- lightweight bootstrap intervals for the selected estimate
- additive-bias sensitivity summaries for the primary doubly robust estimate
- subgroup treatment-effect estimates

It also writes paper-oriented artifacts under `outputs/charts/` and `outputs/tables/` including:

- estimator comparison charts with confidence intervals
- balance before/after summary charts
- sensitivity curves
- subgroup effect charts
- estimator summary tables in CSV and Markdown

## Next Upgrade Path

- add sensitivity analysis for unmeasured confounding
- add panel-data estimators such as difference-in-differences
- add instrumental variables and 2SLS workflows
- add article figures, benchmark tables, and formal estimator-comparison writeups

Current artifact generation already supports the first wave of article figures and summary tables, including public benchmark comparisons.

See [docs/architecture.md](docs/architecture.md) for the design notes.
See [docs/demo-storyboard.md](docs/demo-storyboard.md) for the reviewer walkthrough.
See [docs/methodology.md](docs/methodology.md) for assumptions, reasoning, and estimator justification.
See [docs/article-positioning.md](docs/article-positioning.md) for software-paper framing.
See [docs/public-benchmarks.md](docs/public-benchmarks.md) for the public dataset choices and benchmark rationale.
See [docs/benchmark-interpretation.md](docs/benchmark-interpretation.md) for a results-oriented reading of the current benchmark artifacts.
See [docs/reference-validation.md](docs/reference-validation.md) for executable validation logic tied to the future journal article.
See [docs/manuscript-outline.md](docs/manuscript-outline.md) for a section-by-section software-paper outline.
See [docs/limitations-and-assumptions.md](docs/limitations-and-assumptions.md) for a paper-ready limitations section.
See [docs/figure-captions.md](docs/figure-captions.md) for reusable captions tied to the generated artifacts.
See [docs/literature-comparison.md](docs/literature-comparison.md) for published reference value comparison.
See [paper.md](paper.md) for the current JOSS-style paper draft.
