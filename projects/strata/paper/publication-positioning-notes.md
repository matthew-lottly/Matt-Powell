# Publication Positioning Notes

## Adjacent keyword clusters checked

- graph conformal prediction
- graph neural network uncertainty quantification
- Bayesian graph neural network conformal prediction
- adaptive or similarity-based conformal prediction on graphs
- conditional shift robust conformal prediction for GNNs
- heterogeneous graph forecasting and infrastructure risk modeling

## Working assessment

The closest adjacent literature appears to be recent graph conformal prediction work on homogeneous GNN settings, adaptive prediction sets, or Bayesian calibration. I did not find a clear direct overlap with STRATA's current combination of:

- node-level regression on heterogeneous infrastructure graphs
- per-type Mondrian-style calibration
- propagation-aware normalization using frozen training residuals
- spatial diagnostics for coverage behavior

This supports a publishable positioning, but not a strong "first-ever" claim without a cleaner manual related-work pass.

## Recommended framing

- Present STRATA as a principled framework for heterogeneous infrastructure uncertainty quantification.
- Avoid claiming universal superiority over simpler conformal baselines.
- Prefer wording such as "to our knowledge" or "we are not aware of prior work combining..." if you later add explicit recent graph-CP citations.
- Emphasize that the main contribution is topology-aware redistribution of uncertainty under valid coverage.

## Reviewer-facing risks to resolve before submission

- Add a few recent graph conformal prediction citations from 2023 to 2025 after manual vetting.
- Make sure novelty claims are framed against graph conformal prediction broadly, not only against classical split CP and CQR.
- Keep the real-topology section labeled as limited feasibility evidence, not definitive field validation.
- Ensure every table and prose claim matches the current supplementary bundle outputs.