# Article Positioning

This note is a drafting aid for a future software paper.

## Likely central claim

CausalLens provides a lightweight, reproducible causal inference workflow for observational tabular data that treats diagnostics as part of estimation rather than as optional post-processing.

## Evidence needed

1. tests showing stable behavior across synthetic known-effect data
2. a fixed observational sample showing estimator agreement and balance improvement
3. public benchmark results showing recognizable behavior on Lalonde and NHEFS-style data
4. reference-parity tests showing agreement with direct formulas and external model fits
5. examples demonstrating that the result objects expose the evidence needed to judge identification quality
6. clear discussion of why the package uses regression adjustment, matching, IPW, and doubly robust estimation as the initial estimator set

## What not to claim

1. do not claim novel causal theory unless a later release adds it
2. do not claim that software diagnostics prove unconfoundedness
3. do not claim that the fixed monitoring dataset is a real benchmark truth set

## Stronger software-paper angle

The strongest paper angle is that CausalLens reduces the distance between causal estimation and causal critique. Instead of returning only an effect size, it returns effect size plus overlap, balance, sensitivity, and subgroup evidence in one consistent interface.

## Current publication-ready differences

1. diagnostics are mandatory outputs of estimation
2. fixed observational fixtures are versioned in the repository
3. synthetic, fixed-data, and public-benchmark evidence are all present
4. the CLI exports a reviewable causal report rather than only printing a coefficient
