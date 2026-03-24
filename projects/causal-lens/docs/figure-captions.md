# Figure Captions

These captions are drafted in a paper-friendly style so the current artifact files can be reused directly in a manuscript.

## Estimator comparison figure

Suggested caption:

"Comparison of treatment-effect estimates across the implemented estimators. Bars show point estimates and whiskers show bootstrap confidence intervals. The zero line marks the no-effect reference. Agreement in effect direction across estimators strengthens software-level confidence that the implementation is behaving coherently, while disagreement in magnitude highlights estimator sensitivity to modeling assumptions."

## Balance summary figure

Suggested caption:

"Mean absolute standardized mean differences before and after adjustment for each estimator. Lower values indicate improved covariate balance. This figure is intended as a software-oriented diagnostic summary rather than proof of unconfoundedness."

## Sensitivity curve figure

Suggested caption:

"Additive-bias sensitivity curve for the primary doubly robust estimate. The plotted line shows how the estimated effect changes as hypothetical additive bias increases, with the shaded region indicating the adjusted confidence interval. The intersection with zero provides an explain-away style robustness summary."

## Subgroup effects figure

Suggested caption:

"Subgroup treatment-effect estimates for the selected grouping variable. Bars show subgroup-specific point estimates and whiskers show bootstrap confidence intervals. These results are intended for early heterogeneity review and should not be over-interpreted when subgroup sizes are small."

## Cross-dataset benchmark table

Suggested caption:

"Cross-dataset benchmark summary comparing effect size, interval width, overlap status, and mean absolute balance improvement across estimators. The benchmark is designed for software evaluation and manuscript reporting, not for declaring one estimator universally superior across causal settings."
