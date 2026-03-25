# Limitations And Assumptions

This document is written in a style that can later be adapted directly into a manuscript limitations section.

## Assumptions

1. Binary treatment assignment.
2. Observational exchangeability conditional on measured confounders.
3. Positivity within the supplied covariate support.
4. Stable unit treatment value assumption in the current implementation.
5. Linear outcome modeling in the current regression-adjustment and doubly robust nuisance fits.

## Current limitations

1. CausalLens does not prove that exchangeability holds. It only reports evidence that should affect how users judge that assumption.
2. The fixed monitoring intervention dataset is a reproducible software fixture, not a ground-truth scientific benchmark.
3. Small subgroup intervals can remain unstable even with stratified bootstrap if subgroup counts are very low.
4. The current doubly robust implementation uses simple parametric nuisance models rather than flexible cross-fitted machine-learning nuisances.
5. The matching implementation is nearest-neighbor on the scalar propensity score and does not yet include richer optimal-matching variants.
6. Overlap diagnostics are descriptive. Poor overlap can be flagged, but not automatically repaired in a principled way.
7. The RD implementation follows the CCT 2014 bias-correction approach but does not implement their MSE-optimal bandwidth selector. Bandwidth selection uses a Silverman-style rule-of-thumb rather than the Calonico, Cattaneo, and Farrell (2020) optimal procedure.
8. The fuzzy RD uses a local Wald ratio with delta-method standard errors. It does not implement the full local-IV procedure available in rdrobust.
9. The McCrary manipulation test uses a kernel-weighted binomial approach. It does not implement the formal local-polynomial density estimator of Cattaneo, Jansson, and Ma (2020).
10. The structural bunching elasticity implements the Saez (2010) / Kleven (2016) formula for kink-point designs. It does not yet cover notch designs, round-number bunching corrections, or diffuse bunching.
11. The package now supports staggered-adoption DiD following Callaway & Sant'Anna (2021) logic with never-treated and not-yet-treated control groups; it does not yet implement doubly-robust group-time ATTs or bootstrapped simultaneous confidence bands.
12. The omitted-variable bias analysis follows Cinelli & Hazlett (2020) partial-R² formulation. It does not implement the contour-plot visualization or the formal sensitivity-statistics package features beyond robustness values and benchmark bounds.

## Why these limits are acceptable for the current paper

For a software paper, the main claim is not methodological novelty. The relevant claim is that CausalLens exposes estimators and diagnostics in a reproducible and testable way. These limitations therefore narrow the scope of the paper, but they do not undermine the core software contribution.

## Reviewer-facing phrasing

If used in the manuscript, the key sentence should be:

"CausalLens does not claim to establish causal identification automatically; rather, it packages established causal estimators across five identification strategies with the diagnostic evidence needed to critique those estimates reproducibly."
