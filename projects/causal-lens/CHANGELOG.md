# Changelog

All notable changes to CausalLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.5.0] — 2026-03-25

### Added
- Difference-in-differences estimator (`DifferenceInDifferences`) with regression-based ATT, cluster-robust standard errors via statsmodels, and parallel-trends pre-test with joint F-test.
- Synthetic control method (`SyntheticControl`) with constrained least-squares donor weights (scipy SLSQP) and placebo inference via leave-one-out control-unit permutation.
- Two-stage least squares estimator (`TwoStageLeastSquares`) with proper IV variance formula, first-stage F-statistic, and weak-instrument detection (F < 10).
- Monte Carlo simulation framework (`run_simulation`, `summarize_simulation`, `run_quick_simulation`) with five data-generating processes (linear, nonlinear_outcome, nonlinear_propensity, double_nonlinear, strong_confounding) evaluating bias, RMSE, coverage, MAE, and SE calibration ratio across all estimators.
- IPW propensity-score estimation uncertainty correction using Lunceford & Davidian (2004) stacked estimating equations, enabled by default via `account_for_propensity_estimation` flag.
- Result dataclasses: `DiDEstimate`, `SyntheticControlEstimate`, `IVEstimate`.
- 20 new tests covering panel estimators, IV, simulation, and IPW propensity correction.

## [0.2.0] — 2026-03-24

### Added
- Cross-fitted doubly robust estimator (`CrossFittedDREstimator`) implementing DML/AIPW-style sample splitting for unbiased nuisance estimation.
- Flexible doubly robust estimator (`FlexibleDoublyRobustEstimator`) using gradient boosting for outcome models to capture nonlinear confounding.
- T-learner (`TLearner`) for conditional average treatment effect (CATE) estimation with optional GBM backend.
- S-learner (`SLearner`) for CATE estimation with a single pooled outcome model.
- Abadie-Imbens variance estimator for propensity score matching, providing analytic standard errors and p-values for `PropensityMatcher`.
- `CONTRIBUTING.md` with development workflow and guidelines.
- `CITATION.cff` for machine-readable citation metadata.
- This changelog.

### Fixed
- IPW standard error formula: corrected from `sqrt(var * n)` to `sqrt(var / n)` matching the proper Hajek influence-function variance of the mean.
- Lalonde evidence inconsistency: `comparison.py` now applies the same propensity-trim bounds `(0.03, 0.97)` as `cli.py` so external-comparison and CLI results are consistent.

### Changed
- Default bootstrap resamples increased from 40 to 200 for more stable confidence intervals.
- Stability analysis sweep expanded from 2 seeds to 12 seeds with higher bootstrap counts (50/200/500) for a credible variability assessment.
- Quick stability mode now uses 5 seeds (up from 2) and 50 bootstrap resamples (up from 20).

## [0.1.0] — 2026-03-24

### Added
- Initial release with four estimators: regression adjustment, propensity matching, IPW, and doubly robust.
- Analytic standard errors for regression (OLS), IPW (Hajek IF), and DR (semiparametric IF).
- Covariate balance diagnostics: standardized mean differences, variance ratios, Kish effective sample size.
- Sensitivity analysis: additive-bias scenarios, E-values (VanderWeele & Ding 2017), Rosenbaum bounds.
- Placebo/falsification tests on pre-treatment outcomes.
- Subgroup treatment-effect summaries.
- Love plots and propensity-score overlap histograms.
- Public benchmarks: Lalonde (job training), NHEFS (smoking cessation), synthetic (known effect = 2.0).
- External comparison script verifying parity against manual sklearn/statsmodels implementations.
- Repeated-run stability analysis across seeds, bootstrap counts, and caliper settings.
- CLI entry point exporting JSON reports, charts, and tables.
