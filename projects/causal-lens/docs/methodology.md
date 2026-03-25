# Methodology

This document records the reasoning behind the current CausalLens design and the assumptions behind the implemented estimators. It is written to support later journal-article drafting rather than only day-to-day development.

## Scope

CausalLens currently targets observational tabular data with binary treatment assignment, plus adjacent quasi-experimental settings where local design-based assumptions are credible. The package intentionally centers standard, interpretable, and widely cited estimators because the journal value of the project is not a new estimator. The value is a disciplined implementation that makes assumptions, diagnostics, and estimator comparison explicit.

## Why these estimators

### Regression adjustment

Regression adjustment is the simplest baseline because it estimates a treatment coefficient while conditioning on measured confounders. It is included because every later estimator should be interpretable relative to a transparent parametric baseline.

### Propensity score matching

Matching is included because it operationalizes the balancing-score idea directly. Reviewers and readers often trust matched-sample reasoning more than opaque weighting or black-box nuisance modeling, especially in applied papers.

### Inverse probability weighting

IPW is included because it targets a pseudo-population in which treatment assignment is less confounded by observed covariates. It also makes balance improvement measurable and testable, which is useful for software validation and publication evidence.

### Doubly robust estimation

Doubly robust estimation is included because it is the strongest Phase 1 estimator in the current package. If either the propensity model or the outcome model is correctly specified, the estimator remains consistent. For publication purposes, this gives CausalLens a defensible primary estimator while still letting simpler baselines remain visible.

## Identification assumptions

The package currently assumes:

1. Consistency: the observed outcome under received treatment equals the relevant potential outcome.
2. Exchangeability given measured confounders: there are no unmeasured confounders after conditioning on the supplied covariates.
3. Positivity: all units have nonzero probability of receiving either treatment state within the covariate support.
4. Stable unit treatment value assumption: one unit's treatment does not alter another unit's outcome in the current implementation.

These assumptions are not proved by software. The package instead provides diagnostics that help users reason about where violations are plausible.

## Why diagnostics are first-class

Many causal libraries make diagnostics optional and leave balance checking to custom notebook work. CausalLens takes the opposite position: diagnostics belong inside the core result object because a treatment-effect estimate without overlap and balance information is not persuasive enough for publication.

The implemented diagnostics are therefore part of the API contract, not convenience extras:

1. Covariate balance before and after adjustment
2. Propensity-score range and overlap summaries
3. Sensitivity summaries showing how much additive bias is needed to remove the estimated effect
4. Subgroup effect summaries for early heterogeneity review

## Why a real-style dataset is included

The package now includes a fixed public-safe observational intervention sample in [data/monitoring_intervention_sample.csv](../data/monitoring_intervention_sample.csv). It is not presented as a true scientific ground-truth dataset. Its role is different:

1. make tests reproducible
2. provide a stable example for documentation and article figures
3. show estimator agreement and diagnostic behavior on a non-random fixture
4. support software-paper claims about transparency and repeatability

## Why public benchmarks are now included

The repository now also packages two public datasets that are widely recognized in causal-inference teaching and applied validation:

1. Lalonde / Dehejia-Wahba style job-training data, used here as a public earnings benchmark
2. NHEFS complete-data smoking-cessation data, used here as an observational health benchmark

These benchmarks play a different role from the fixed project fixture.

1. They provide externally recognizable evaluation targets that reviewers are more likely to trust.
2. They show that the API works on public data sets with very different scales and covariate structures.
3. They reduce the gap between a software paper and a later applied or benchmarking paper.

## What is different about CausalLens

The project is not novel because it re-invents matching or weighting. Its differentiators are:

1. a small estimator-oriented API with common result objects
2. diagnostics shipped by default rather than left to ad hoc user code
3. explicit support for both real-style reproducible fixtures and synthetic known-effect validation
4. a publication-oriented design where methods, assumptions, and checks are documented alongside code
5. support for multiple identification strategies in one small package: observational adjustment, panel comparisons (including staggered-adoption DiD), IV, sharp and fuzzy RDD with robust bias-corrected inference, McCrary manipulation testing, and structural bunching elasticity estimation
6. Cinelli & Hazlett (2020) omitted-variable bias sensitivity analysis with robustness values and benchmark-calibrated bounds
7. cross-design diagnostic comparison that lets users view assumption evidence from multiple identification strategies side by side

## Quasi-Experimental Methods

### Regression discontinuity

The `RegressionDiscontinuity` class implements local-polynomial estimation for sharp and fuzzy RD designs.

**Sharp RD.** In the sharp design, treatment is a deterministic function of the running variable crossing a cutoff. The estimator fits kernel-weighted local polynomials (degree 1 or 2) on each side of the cutoff, with the treatment-effect estimate given by the discontinuity in the conditional expectation at the cutoff. Standard errors use HC1 heteroskedasticity-robust inference.

**Fuzzy RD.** In the fuzzy design, crossing the cutoff increases the probability of treatment but does not determine it. The estimator computes a local Wald ratio (reduced form / first stage) where both the outcome-discontinuity and treatment-discontinuity regressions are run on the same kernel-weighted local sample. Standard errors for the Wald ratio use the delta method. The first-stage F-statistic is reported for weak-instrument diagnostics.

**Robust bias-corrected inference.** Following Calonico, Cattaneo, and Titiunik (2014), the estimator computes a bias correction using a pilot local polynomial of one degree higher than the main specification, fitted on a wider bandwidth (default: 1.5x main bandwidth). The leading bias is estimated from the curvature difference across the cutoff, and the variance contribution of the bias estimate is added to produce robust standard errors and confidence intervals that account for smoothing bias.

**McCrary manipulation test.** The `mccrary_test()` method implements a kernel-weighted density comparison around the cutoff, testing whether observations bunch disproportionately on one side. Under the null of no manipulation, the fraction of observations on each side follows a binomial distribution centered at 0.5. A significant departure provides evidence for sorting on the running variable.

### Bunching estimation

The `BunchingEstimator` class measures excess mass around a threshold (kink or notch) by comparing the observed histogram against a smooth polynomial counterfactual fitted on bins outside the excluded window.

**Structural elasticity.** The `elasticity()` method implements the Saez (2010) / Kleven (2016) structural estimation formula. Given marginal tax rates below and above a kink, the excess mass at the kink is converted to an implied shift in taxable income, which yields a compensated elasticity. Bootstrap confidence intervals are computed by resampling the microdata.

### Simulation framework

The Monte Carlo framework now covers data-generating processes for all identification strategies: observational DGPs (linear, nonlinear outcome, nonlinear propensity, double nonlinear, strong confounding), RDD DGPs (sharp RD with polynomial outcome, fuzzy RD with probabilistic treatment compliance), and a bunching DGP (income distribution with bunching at a tax kink point). The `run_rdd_simulation()` function runs both conventional and bias-corrected RD across these DGPs and reports bias, coverage, and SE calibration.

## Current evidence strategy

The validation strategy is intentionally three-track:

1. synthetic data with known treatment effects for correctness checks
2. fixed real-style data for reproducible estimator-agreement and diagnostic checks
3. public benchmark data for externally recognizable estimator-comparison evidence

This split is important for a journal article. Synthetic data supports identification-level reasoning, the real-style fixture supports software reproducibility and user comprehension, and the public benchmarks support reviewer-facing credibility beyond an internal fixture.

## Executable evidence beyond behavior tests

The repository now also includes reference-parity tests. These compare package outputs against direct formulas and explicit model fits rather than only checking coarse behavioral expectations. That matters for publication because it provides evidence that CausalLens is implementing recognizable statistical estimators rather than only returning numerically plausible answers.
