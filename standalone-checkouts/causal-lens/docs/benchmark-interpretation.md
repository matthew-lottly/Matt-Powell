# Benchmark Interpretation

This note translates the current artifact outputs into paper-facing language. It is not a substitute for a full methods evaluation, but it helps distinguish what the current evidence does support from what it does not.

## Bottom line

The current benchmark stack is strong enough for a software paper. NHEFS estimates match the Hernán & Robins textbook within 0.2 kg. Lalonde regression and matching fall within the published Dehejia & Wahba range. IPW volatility on Lalonde is consistent with published literature showing extreme sensitivity on this dataset.

For a detailed comparison against published reference values, see [literature-comparison.md](literature-comparison.md).

## Synthetic validation dataset

Source artifact: [outputs/tables/synthetic_validation_dataset_estimator_summary.csv](../outputs/tables/synthetic_validation_dataset_estimator_summary.csv)

Current pattern:

1. regression adjustment estimates about 1.98
2. matching estimates about 1.80
3. IPW estimates about 1.91
4. doubly robust estimates about 1.94

Interpretation:

1. the known-effect synthetic target is close to 2.0, so regression adjustment, IPW, and doubly robust are behaving coherently
2. matching is slightly lower than the others, but still directionally correct and substantially improves balance
3. IPW and doubly robust produce the strongest post-adjustment balance, reducing mean absolute SMD from about 0.41 to about 0.016

What this supports:

1. the estimators are implemented coherently enough for software validation
2. the diagnostics respond in the expected direction when confounding is present
3. the reporting layer captures meaningful method differences rather than flattening them

## Fixed observational fixture

Source artifact: [outputs/tables/real_dataset_estimator_summary.csv](../outputs/tables/real_dataset_estimator_summary.csv)

Current pattern:

1. all four estimators produce an effect near -0.0445
2. overlap is acceptable for all estimators
3. the fixture is already well balanced before adjustment, so weighting improves balance only modestly and matching changes little

Interpretation:

1. this is now a stable reproducibility fixture rather than a stress test
2. agreement across estimators is a software-quality signal, not empirical proof
3. the fixture is suitable for documentation, tests, and stable manuscript figures

What this supports:

1. reproducibility
2. estimator agreement checks
3. CLI and artifact stability

What it does not support:

1. strong real-world causal claims
2. external validity arguments

## Lalonde public benchmark

Source artifact: [outputs/tables/lalonde_public_benchmark_estimator_summary.csv](../outputs/tables/lalonde_public_benchmark_estimator_summary.csv)

Experimental reference: ~$1,794 (LaLonde 1986, NSW randomized estimate)

Current pattern:

1. regression adjustment estimates about $1,548 — within the Dehejia & Wahba (1999) range of $1,281–$1,776
2. matching estimates about $1,540 — within the DW99 matching range of $1,434–$2,180
3. IPW estimates about $232 — within the published range of -$252 to $2,281 (Huber et al. 2013, Busso et al. 2014)
4. doubly robust estimates about $799 — reflects expected tension between good outcome model and volatile propensity model
5. all estimators report acceptable overlap
6. matching improves mean absolute balance from about 0.509 to about 0.073

Interpretation:

1. regression and matching are performing well, producing estimates within the published literature range
2. IPW instability on Lalonde is a well-documented phenomenon — our result is consistent with published findings
3. the doubly robust estimate reflects the expected behavior when the propensity model is weaker than the outcome model
4. the estimator spread is itself informative: CausalLens correctly surfaces specification sensitivity

What this supports:

1. CausalLens results are consistent with published literature on a canonical benchmark
2. the diagnostics and estimator comparison are working as intended
3. matching and regression produce paper-ready estimates in the expected range

What this does not yet support:

1. any claim that one implemented estimator is clearly best on this problem
2. a need for richer propensity specifications (polynomial features, flexible learners) is visible from the IPW/DR estimates

## NHEFS public benchmark

Source artifacts:

1. [outputs/tables/nhefs_public_benchmark_estimator_summary.csv](../outputs/tables/nhefs_public_benchmark_estimator_summary.csv)
2. [outputs/tables/nhefs_public_benchmark_subgroup_summary.csv](../outputs/tables/nhefs_public_benchmark_subgroup_summary.csv)

Current pattern:

1. regression adjustment estimates about 3.33 kg
2. matching estimates about 3.21 kg
3. IPW estimates about 3.26 kg
4. doubly robust estimates about 3.29 kg
5. IPW and doubly robust reduce mean absolute balance from about 0.152 to about 0.013
6. subgroup effects by sex are similar in direction and magnitude

Interpretation:

1. all estimators match the Hernán & Robins textbook reference of ~3.4 kg within 0.2 kg
2. estimator agreement is tight (range 3.21 – 3.33 kg)
3. balance improvement is strong and consistent
4. the subgroup output looks stable enough for descriptive heterogeneity discussion

What this supports:

1. externally recognizable public-benchmark evidence for the software paper
2. a strong example of diagnostics and estimates moving together coherently
3. a public-health benchmark that is easier to explain in a manuscript than the fixed internal fixture

## Overall interpretation for publication

The current evidence is strong enough for:

1. a JOSS-style software paper with literature-validated benchmark results
2. a repo narrative centered on reproducibility, diagnostics, and reviewable outputs
3. a manuscript claim that CausalLens reduces the distance between estimation and causal critique
4. claims of implementation correctness verified by reference parity tests and synthetic target recovery
5. claims of stability verified by repeated-run analysis across seeds and settings

The current evidence is not yet strong enough for:

1. a methodological paper comparing CausalLens favorably against mature causal libraries
2. an applied paper whose main contribution is a substantive causal conclusion

## Supporting evidence artifacts

1. [literature-comparison.md](literature-comparison.md) — detailed comparison against published reference values
2. `outputs/tables/stability_summary.csv` — repeated-run stability across seeds, bootstrap counts, and calipers
3. `outputs/tables/external_comparison.csv` — verification that CausalLens matches manual implementations to machine precision
4. `tests/test_public_datasets.py` — automated tests verifying literature-consistent estimate ranges
5. `tests/test_reference_parity.py` — automated tests verifying numerical parity with manual formulas