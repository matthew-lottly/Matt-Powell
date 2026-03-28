---
title: 'CausalLens: A reproducible Python toolkit for observational treatment-effect estimation with integrated causal diagnostics'
tags:
  - Python
  - causal inference
  - observational studies
  - treatment effects
  - diagnostics
authors:
  - name: Matt Powell
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 24 March 2026
bibliography: paper.bib
---

# Summary

Observational causal inference workflows are often fragmented across separate estimation, diagnostic, and reporting steps. Analysts may compute treatment-effect estimates in one tool, inspect covariate balance in another, and assemble manuscript-ready outputs through ad hoc notebook code. This fragmentation increases the chance that diagnostic evidence will be omitted or inconsistently reported. CausalLens is a lightweight Python toolkit that addresses this problem by coupling effect estimation with mandatory diagnostic outputs and reproducible report generation.

CausalLens currently implements regression adjustment, propensity score matching, inverse probability weighting, and doubly robust estimation for binary-treatment observational tabular data. The package returns consistent result objects containing treatment effects, confidence intervals, overlap summaries, covariate-balance diagnostics, sensitivity summaries, and subgroup results. In addition to the Python API, CausalLens includes a command-line workflow that exports JSON reports, tables, and charts for software evaluation and manuscript reuse.

# Statement of need

Many existing causal workflows rely on flexible notebook-based analysis but leave diagnostic rigor to user discipline. In practice, this means that a reported treatment effect can be detached from the evidence needed to judge whether the estimate is interpretable. CausalLens is designed around a different principle: diagnostics are part of estimation, not optional post-processing. The package aims to reduce the distance between causal estimation and causal critique by making overlap, balance, sensitivity, and subgroup summaries part of the default workflow.

The package is not introduced as a novel estimator. Its contribution is software-oriented. CausalLens provides:

1. a compact estimator-oriented API for common observational treatment-effect workflows
2. default diagnostic outputs that travel with the estimate
3. reproducible benchmark artifacts suitable for review and manuscript drafting
4. an evidence stack spanning synthetic data, fixed reproducibility fixtures, and public benchmark datasets

This scope aligns well with software publication venues such as JOSS, where the contribution is the usability and reproducibility of the research software rather than a new statistical theorem [@smith2018joss].

# Implemented methods

CausalLens currently supports four phase-1 estimators that are widely used in observational causal inference: regression adjustment, propensity score matching, inverse probability weighting, and doubly robust estimation [@lalonde1986; @dehejia1999; @hernan2020]. These methods were selected because they are interpretable, widely cited, and useful for benchmarking one another in a transparent software setting.

The propensity model uses standardized covariates via scikit-learn's StandardScaler to ensure stable estimation regardless of covariate scale. IPW uses stabilized weights (normalized by treatment prevalence) with configurable weight capping to reduce the influence of extreme propensity scores. The doubly robust estimator applies the same weight trimming to its augmented IPW correction term.

Several estimators now produce analytic standard errors alongside bootstrap confidence intervals. Regression adjustment reports OLS standard errors directly from statsmodels. The IPW estimator computes Hajek influence-function standard errors. The doubly robust estimator computes influence-function standard errors derived from its augmented IPW pseudo-scores, reflecting the semiparametric efficiency bound. All three report two-sided p-values from the corresponding z-tests.

The package exposes rich diagnostic summaries alongside every estimate. These include standardized mean differences before and after adjustment, variance ratios per covariate (treated/control, where values near 1.0 indicate balance), propensity-score overlap summaries, Kish effective sample sizes for weighted estimators, additive-bias sensitivity summaries with E-values for unmeasured confounding [@vanderweele2017], Rosenbaum sensitivity bounds for matched-pair designs [@rosenbaum2002], placebo/falsification tests on pre-treatment outcomes, and subgroup estimates. The result is an interface that emphasizes interpretability and reviewability rather than estimator variety alone.

# Evidence and current benchmark behavior

The current repository uses a four-part evidence strategy: synthetic validation, fixed reproducibility fixtures, public benchmark evaluation with literature comparison, and implementation verification.

**Synthetic validation.** A synthetic dataset with a known treatment effect of 2.0 provides correctness-oriented checks. On this benchmark, regression adjustment, inverse probability weighting, and doubly robust estimation all recover the target within 3.5%, while weighting-based estimators reduce mean absolute covariate imbalance from about 0.41 to about 0.016.

**Fixed reproducibility fixture.** A public-safe observational fixture supports software-level claims about estimator agreement, artifact generation, and reproducibility. All four estimators produce consistent results, making it suitable for stable documentation figures and regression tests.

**Public benchmark evaluation.** CausalLens packages two canonical public datasets: the Lalonde job-training benchmark and the complete-case NHEFS smoking-cessation benchmark [@dehejia1999; @hernan2020].

On the NHEFS benchmark, all four estimators produce weight-gain estimates between 3.21 and 3.33 kg, matching the Hernan and Robins textbook values of approximately 3.4 kg. Post-adjustment balance improvement is substantial (mean absolute SMD from 0.152 to 0.013 for weighting methods). This benchmark demonstrates that the core methods are correctly implemented.

On the Lalonde benchmark (experimental reference: approximately $1,794), regression adjustment produces $1,548 and propensity matching produces $1,540, both within the published Dehejia and Wahba range of $1,281-$1,776. IPW produces $232, which falls within the published range of -$252 to $2,281 reported by Huber, Lechner, and Wunsch for IPW on this notoriously difficult dataset. The doubly robust estimate of $799 reflects the expected tension between a well-specified outcome model and a volatile propensity model. This pattern of estimator disagreement is itself informative: CausalLens surfaces the specification sensitivity that makes Lalonde a canonical benchmark, rather than hiding it.

**Implementation verification.** Reference parity tests confirm that each CausalLens estimator produces numerically identical results to manual implementations using raw sklearn and statsmodels calls. A stability analysis across 5 random seeds, 3 bootstrap repeat counts, and 3 caliper settings shows that point estimates are deterministic and that matching estimates vary smoothly with caliper choice (NHEFS matching CV = 0.015; Lalonde matching CV = 0.167).

**Sensitivity to unmeasured confounding.** The E-value [@vanderweele2017] quantifies the minimum strength of association an unmeasured confounder would need with both treatment and outcome to explain away the observed effect. On the NHEFS benchmark, the doubly robust estimate (3.29 kg, SE = 0.50, p < 0.001) has an E-value of 2.29; an unmeasured confounder would need at least a 2.29-fold association with both variables to reduce the effect to null. The Lalonde trimmed estimate ($1,710, SE = 672, p = 0.011) has a point E-value of 1.80. Rosenbaum bounds for the Lalonde matched-pair design quantify how large hidden bias Gamma would need to be to overturn the significance of the matched-pair Wilcoxon test.

**Falsification checks.** A placebo test runs all estimators on a pre-treatment outcome (1974 earnings for Lalonde) that treatment should not predict. Most methods detect a spurious signal; three out of four estimators produce significant effects on re74. This correctly reveals the pre-treatment selection bias inherent in the Lalonde observational comparison group. This surfaces the specification sensitivity that makes Lalonde a canonical benchmark, and it reinforces why trimming and diagnostics are essential rather than optional.

These five evidence layers; synthetic recovery, reproducibility, literature-consistent public benchmarks, implementation verification, and built-in falsification checks; together support the claim that CausalLens is a correctly implemented, diagnostically rigorous, and reproducible causal inference toolkit.

# Limitations

CausalLens should be understood as a reproducible causal workflow toolkit rather than a complete causal inference platform. The current implementation is limited to binary treatment settings with a focused set of phase-1 estimators. Diagnostics help assess overlap and balance, but they do not prove exchangeability or identify causal effects on their own. E-values and Rosenbaum bounds quantify sensitivity to unmeasured confounding but cannot rule it out.

The influence-function standard errors assume correct specification of nuisance models (propensity and/or outcome). In the presence of misspecification, bootstrap confidence intervals remain the more conservative inference tool. The Lalonde placebo test demonstrates that even well-implemented estimators can produce spurious signals when the comparison group is fundamentally dissimilar; a warning against uncritical application of any observational method.

The benchmark evidence demonstrates implementation correctness and literature consistency across recognized public datasets. It does not claim that CausalLens outperforms mature causal inference libraries for any specific applied problem, nor is that the goal of a software-focused contribution. The package is positioned as a well-tested, reproducible toolkit with transparent diagnostic outputs, with room for later expansion into richer nuisance models, panel-data estimators, and instrumental variable methods.

# Availability

CausalLens is implemented in Python and distributed as an installable package with a typed source layout, automated tests, packaged benchmark datasets, and a command-line interface for generating reviewable causal reports.

# References