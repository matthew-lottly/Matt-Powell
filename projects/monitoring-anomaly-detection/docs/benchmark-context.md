# Benchmark Summary

Evaluation context for the monitoring anomaly detection pipeline.

## Detector Comparison

The pipeline compares these anomaly detection approaches:

| Detector | Approach | Strengths | Limitations |
| --- | --- | --- | --- |
| Global threshold | Static percentile cutoff | Simple, interpretable | No temporal context |
| Rolling Z-score | Windowed standard deviation | Captures local trends | Sensitive to window size |
| Robust threshold | Median absolute deviation | Outlier-resistant | Slower on large datasets |
| Delta detector | Rate-of-change scoring | Catches sudden shifts | Noisy with high-frequency data |

## Labeled-Event Evaluation

When labeled events (known anomalies) are available, the pipeline computes:

- **Precision**: fraction of detected anomalies that are real
- **Recall**: fraction of real anomalies that were detected
- **F1 score**: harmonic mean of precision and recall

These metrics are computed per detector and per station to identify which methods work best for each monitoring context.

## Expected Baseline Performance

On the built-in sample dataset:

| Detector | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Global threshold | High | Low | Moderate |
| Rolling Z-score | Moderate | Moderate | Moderate |
| Robust threshold | High | Moderate | Moderate-High |
| Delta detector | Moderate | High | Moderate |

Exact values depend on the threshold configuration and evaluation window.

## When to Use Each Detector

- **Global threshold**: first-pass screening for obvious outliers
- **Rolling Z-score**: stations with seasonal or trending patterns
- **Robust threshold**: stations with noisy or skewed distributions
- **Delta detector**: stations where sudden changes matter more than absolute levels

## Limitations

- The sample dataset is small and synthetic — real performance will differ
- Detector parameters are not tuned to a specific deployment context
- The pipeline does not include time-series decomposition or ML classifiers
