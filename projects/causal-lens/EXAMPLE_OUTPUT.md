# Example Output

Representative estimator comparison table for a public benchmark run.

```csv
estimator,ate,ci_low,ci_high,balance_max_smd
ipw,2.84,2.11,3.56,0.13
doubly_robust,2.67,2.02,3.28,0.09
matching,2.51,1.88,3.17,0.11
meta_learner,2.73,1.94,3.42,0.15
```

Reviewers should be able to tell which estimator is most stable, whether intervals overlap, and how much covariate imbalance remains.