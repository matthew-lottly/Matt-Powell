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
- Nearest-neighbor propensity matching with optional calipers and Abadie-Imbens analytic standard errors
- Inverse probability weighting with stabilized weights and weight capping for ATE and ATT targets
- Doubly robust estimation that combines outcome and propensity models with weight trimming
- Cross-fitted doubly robust estimation (DML/AIPW style) with 5-fold out-of-fold nuisance estimates to avoid overfitting bias
- Flexible doubly robust estimation using gradient boosting outcome models for nonlinear confounding
- T-learner and S-learner meta-learners for conditional average treatment effect (CATE) estimation with optional GBM
- Analytic standard errors from OLS (regression), Hajek sandwich variance (IPW), Abadie-Imbens matched-pair variance (matching), and semiparametric influence functions (doubly robust)
- Covariate-balance summaries using standardized mean differences and variance ratios
- Kish effective sample size for weighted estimators to detect unstable weights
- Common-support and overlap diagnostics for positivity review
- Additive-bias sensitivity summaries for explain-away analysis on the outcome scale
- E-values for unmeasured confounding (VanderWeele & Ding 2017) quantifying the minimum confounder strength to explain away the effect
- Rosenbaum sensitivity bounds for matched-pair designs quantifying hidden-bias tolerance
- Placebo/falsification tests on pre-treatment outcomes for specification validation
- Subgroup treatment-effect summaries for quick heterogeneous-effect review
- A small command-line demo that exports a reproducible causal report
- A real-style observational intervention fixture for stable estimator-comparison tests
- Publication-oriented methodology notes explaining why the initial estimator set is justified
- Reference parity tests against manual formulas and direct statistical-model fits
- Paper-ready chart and table exports for estimator comparison, balance, sensitivity, and subgroup effects
- Love plots showing covariate-level balance before and after adjustment with standard |SMD| thresholds
- Propensity-score overlap histograms for visual positivity assessment
- Manuscript drafting docs, figure captions, and cross-dataset benchmark tables for the software-paper path
- Packaged public benchmarks based on Lalonde and NHEFS so installed users can reproduce the evidence stack without a source checkout
- Literature comparison table showing CausalLens results match published reference values from Dehejia & Wahba (1999) and Hernán & Robins (2020)
- Repeated-run stability analysis across seeds, bootstrap counts, and caliper settings
- External comparison script verifying CausalLens matches manual sklearn/statsmodels implementations to machine precision

## Current Output

The default command writes `outputs/causal_report.json` with:

- a fixed real-style observational dataset section with estimator comparisons
- a Lalonde benchmark section with public observational training-program data, using light propensity-overlap trimming for the weighting estimators
- an NHEFS benchmark section with public smoking-cessation observational data
- a synthetic validation dataset section with known-effect comparisons
- overlap summary and propensity score range checks
- covariate balance before/after weighting, variance ratios, and effective sample sizes
- lightweight bootstrap intervals for the selected estimate
- analytic standard errors and p-values from influence functions (DR, IPW) and OLS (regression)
- additive-bias sensitivity summaries with E-values for the primary doubly robust estimate
- subgroup treatment-effect estimates
- placebo/falsification test results on pre-treatment outcomes
- Rosenbaum sensitivity bounds for matched-pair designs
- external comparison and stability-analysis summaries for the exported benchmark artifacts

It also writes paper-oriented artifacts under `outputs/charts/` and `outputs/tables/` including:

- estimator comparison charts with confidence intervals
- balance before/after summary charts
- sensitivity curves
- subgroup effect charts
- estimator summary tables in CSV and Markdown
- `external_comparison.csv` showing parity against manual sklearn/statsmodels implementations
- `stability_raw.csv` and `stability_summary.csv` capturing repeated-run variability across benchmark settings
- `placebo_test.csv` showing falsification test results on pre-treatment outcomes
- `rosenbaum_bounds.csv` showing matched-pair sensitivity to hidden bias at each Gamma level
- Love plots and propensity-score overlap histograms for each benchmark dataset

## Next Upgrade Path

- add panel-data estimators such as difference-in-differences
- add instrumental variables and 2SLS workflows
- add article figures, benchmark tables, and formal estimator-comparison writeups

Current artifact generation already supports the first wave of article figures and summary tables, including public benchmark comparisons.

## Installation

```bash
pip install .
```

Or in development mode:

```bash
pip install -e .
```

## Quick Start

```python
from causal_lens import (
    generate_synthetic_observational_data,
    RegressionAdjustmentEstimator,
    DoublyRobustEstimator,
    CrossFittedDREstimator,
)

data = generate_synthetic_observational_data(rows=600, seed=42)
confounders = ["age", "severity", "baseline_score"]

# Regression adjustment
reg = RegressionAdjustmentEstimator("treatment", "outcome", confounders)
result_reg = reg.fit(data)

# Doubly robust with cross-fitting
dr = CrossFittedDREstimator("treatment", "outcome", confounders)
result_dr = dr.fit(data)

for r in [result_reg, result_dr]:
    print(f"{r.method:35s}  effect={r.effect:.2f}  SE={r.se:.3f}  p={r.p_value:.4f}")
```

## Documentation

See [docs/architecture.md](docs/architecture.md) for the design notes.
See [docs/methodology.md](docs/methodology.md) for assumptions, reasoning, and estimator justification.
See [docs/public-benchmarks.md](docs/public-benchmarks.md) for the public dataset choices and benchmark rationale.
See [docs/benchmark-interpretation.md](docs/benchmark-interpretation.md) for a results-oriented reading of the current benchmark artifacts.
See [docs/reference-validation.md](docs/reference-validation.md) for executable validation logic tied to the future journal article.
See [docs/limitations-and-assumptions.md](docs/limitations-and-assumptions.md) for a paper-ready limitations section.
