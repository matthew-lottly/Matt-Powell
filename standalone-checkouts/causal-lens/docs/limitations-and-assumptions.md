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
7. The package currently focuses on point treatment settings rather than panel, staggered adoption, IV, or continuous-treatment designs.

## Why these limits are acceptable for the current paper

For a software paper, the main claim is not methodological novelty. The relevant claim is that CausalLens exposes estimators and diagnostics in a reproducible and testable way. These limitations therefore narrow the scope of the paper, but they do not undermine the core software contribution.

## Reviewer-facing phrasing

If used in the manuscript, the key sentence should be:

"CausalLens does not claim to establish causal identification automatically; rather, it packages common observational estimators together with the diagnostic evidence needed to critique those estimates reproducibly."
