# Methodology

This document records the reasoning behind the current CausalLens design and the assumptions behind the implemented estimators. It is written to support later journal-article drafting rather than only day-to-day development.

## Scope

CausalLens currently targets observational tabular data with binary treatment assignment. The package intentionally starts with estimators that are standard, interpretable, and widely cited, because the early journal value of the project is not a new estimator. The value is a disciplined implementation that makes assumptions, diagnostics, and estimator comparison explicit.

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

## Current evidence strategy

The validation strategy is intentionally three-track:

1. synthetic data with known treatment effects for correctness checks
2. fixed real-style data for reproducible estimator-agreement and diagnostic checks
3. public benchmark data for externally recognizable estimator-comparison evidence

This split is important for a journal article. Synthetic data supports identification-level reasoning, the real-style fixture supports software reproducibility and user comprehension, and the public benchmarks support reviewer-facing credibility beyond an internal fixture.

## Executable evidence beyond behavior tests

The repository now also includes reference-parity tests. These compare package outputs against direct formulas and explicit model fits rather than only checking coarse behavioral expectations. That matters for publication because it provides evidence that CausalLens is implementing recognizable statistical estimators rather than only returning numerically plausible answers.
