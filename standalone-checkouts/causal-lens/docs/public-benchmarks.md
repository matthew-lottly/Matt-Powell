# Public Benchmarks

This document records the public benchmark datasets now packaged with CausalLens and the role each one plays in the article evidence stack.

## Included datasets

### Lalonde benchmark

Source: MatchIt / Lalonde dataset based on the National Supported Work Demonstration and PSID comparison sample as analyzed by Dehejia and Wahba.

In CausalLens:

1. treatment: `treatment`
2. outcome: `outcome` mapped from `re78`
3. confounders: age, education, marriage, degree status, prior earnings, and race indicators

Why it is included:

1. it is one of the most recognizable benchmark datasets in causal inference
2. it gives the package a public labor-economics treatment-effect example
3. it tests how the estimators behave under a classic nonexperimental training-program setup

### NHEFS complete benchmark

Source: complete-case NHEFS follow-up data documented in Hernán and Robins' Causal Inference text.

In CausalLens:

1. treatment: `treatment` mapped from smoking cessation indicator `qsmk`
2. outcome: `outcome` mapped from weight change `wt82_71`
3. confounders: sex, race, age, school, smoking intensity, smoking years, exercise, activity, and baseline weight

Why it is included:

1. it is a standard observational benchmark tied directly to modern causal inference teaching
2. it adds a public health example with a different outcome scale and confounding structure
3. it provides a benchmark where overlap and balance diagnostics remain central to the interpretation

## Why these benchmarks matter

The fixed project fixture is still useful for reproducibility, but it is not enough on its own for publication credibility. The public benchmarks improve the evidence stack because they:

1. connect the package to datasets that reviewers may already know
2. demonstrate estimator behavior on real published data rather than only internal fixtures
3. give the report pipeline multiple public examples that can be cited directly in a manuscript

## Current limits

These integrations do not turn CausalLens into a benchmark leader by themselves. They are a first public-data layer, not the final paper package. A stronger publication path would still add:

1. explicit comparison against published benchmark estimates from the literature
2. multi-seed or resampling stability summaries for the public benchmarks
3. richer nuisance-model specifications beyond the current phase-1 linear and logistic setup