# Manuscript Outline

This outline is intended for a software-paper submission path such as JOSS first and a longer statistical software manuscript later if the package matures further.

## Working title

CausalLens: a reproducible Python toolkit for observational treatment-effect estimation with integrated causal diagnostics

## Abstract skeleton

1. Motivation: causal effect estimation in observational tabular data is often split across estimators, diagnostics, and ad hoc notebook code.
2. Package contribution: CausalLens provides a compact Python workflow that couples regression adjustment, matching, weighting, doubly robust estimation, balance checks, overlap checks, sensitivity summaries, subgroup effects, and report exports.
3. Evidence: synthetic known-effect validation, fixed observational reproducibility fixtures, reference-parity tests, and paper-ready figures/tables.
4. Availability: open-source Python package with tests, documentation, and reproducible outputs.

## Section plan

### 1. Introduction

State the gap: many workflows return effect estimates, but the diagnostic evidence needed to interpret them is scattered and inconsistently reported.

### 2. Package scope and design goals

Describe:

1. estimator-oriented API
2. diagnostics as mandatory outputs
3. separation between synthetic validation, fixed observational fixtures, and public benchmarks
4. reproducible report artifacts for software evaluation and manuscript use

### 3. Implemented methods

Briefly summarize:

1. regression adjustment
2. propensity score matching
3. inverse probability weighting
4. doubly robust estimation
5. additive-bias sensitivity summaries
6. subgroup effect summaries

### 4. Validation strategy

Organize the evidence into five layers:

1. synthetic known-effect tests
2. fixed observational fixture tests
3. public benchmark comparisons on Lalonde and NHEFS-style data
4. reference-parity checks against direct formulas and explicit model fits
5. report artifact generation tests

### 5. Generated outputs

Use the chart and table artifacts to show:

1. estimator comparison across datasets
2. balance before and after adjustment
3. sensitivity curves
4. subgroup effect summaries
5. cross-dataset benchmark summary table

### 6. Limitations

Point to the limitations document and state clearly that diagnostics do not prove identification and that the fixed observational dataset is for reproducibility rather than empirical truth claims.

### 7. Conclusion

Frame CausalLens as infrastructure that reduces the distance between estimation and critique in observational causal workflows.

## Current artifact map

1. Estimator comparison figures: [outputs/charts](../outputs/charts)
2. Summary tables: [outputs/tables](../outputs/tables)
3. Method justification: [methodology.md](methodology.md)
4. Validation logic: [reference-validation.md](reference-validation.md)
5. Positioning: [article-positioning.md](article-positioning.md)
