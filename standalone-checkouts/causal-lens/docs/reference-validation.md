# Reference Validation

This document explains the executable validation strategy used to support later journal submission. The goal is not to claim new theory. The goal is to show that the implemented estimators agree with transparent reference calculations and that the software exposes the assumptions needed to interpret those calculations.

## Why reference parity tests matter

For a software paper, reviewers usually need stronger evidence than "the code runs" and weaker claims than a theorem-proving methods paper. Reference parity tests are a good middle ground because they show that the implementation reproduces known formulas and standard modeling workflows.

In CausalLens, these tests play two roles:

1. They reduce the chance that the package is only internally self-consistent.
2. They give article reviewers concrete evidence that the main estimators are implemented as intended.

## Current parity checks

### Regression adjustment

The regression-adjustment estimator is compared directly against a separate `statsmodels.OLS` fit using the same design matrix. The treatment effect returned by CausalLens must match the treatment coefficient from the reference OLS fit.

### Propensity score matching

The matching estimator is compared against an explicit manual nearest-neighbor search on the scalar propensity score. This avoids treating the package's own helper methods as proof of correctness.

### Inverse probability weighting

The IPW estimator is checked against the manual weighted-mean formula using externally reconstructed propensity scores and the standard ATE weighting rule.

### Doubly robust estimation

The doubly robust estimator is checked against an explicit augmented inverse-probability-weighted pseudo-outcome calculation using separately fit treated and control outcome regressions.

## Why this is stronger than unit tests alone

Ordinary unit tests often only check sign, type, or coarse magnitude. CausalLens now includes those behavioral tests, but it also includes reference-formula parity tests. That is more valuable for publication because it shows the software aligns with recognizable statistical definitions.

## Bootstrap reasoning

Bootstrap intervals in CausalLens now use stratified resampling by treatment group. This is a deliberate design choice. In small observational subgroups, naive bootstrap samples can drop one treatment class entirely, which makes propensity modeling or outcome modeling undefined. Stratified resampling preserves class support and is therefore a more stable and more defensible default for the current package.

## Limits of the current evidence

These checks do not prove identification assumptions. They also do not prove that the chosen estimators are correct for every empirical study. What they do show is that the software reproduces intended formulas and exposes balance and overlap evidence that users need before treating the estimates as credible.

## Next validation layers

The next publication-oriented validation steps should be:

1. benchmark tables comparing CausalLens outputs to external software on standardized synthetic scenarios
2. figure generation for overlap, balance, and subgroup summaries
3. narrative examples showing how diagnostics change the interpretation of the same effect estimate
