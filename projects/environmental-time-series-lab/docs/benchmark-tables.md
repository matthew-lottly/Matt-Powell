# Benchmark Tables

Evaluation context for the environmental time series lab.

## Baseline Comparison Framework

The lab compares these candidate baselines against a trailing hold-out window:

| Baseline | Approach | Best For |
| --- | --- | --- |
| Naive (last value) | Repeat the most recent observation | Stable, slowly-changing series |
| Trailing average | Mean of the most recent N observations | Smoothing out short-term noise |
| Drift model | Linear extrapolation from recent trend | Trending series |
| Seasonal profile | Phase-aligned mean from historical cycles | Series with strong seasonality |

## Evaluation Metrics

Each baseline is scored on the hold-out window using:

- **MAE** (Mean Absolute Error): average magnitude of errors
- **RMSE** (Root Mean Square Error): penalizes larger errors more heavily
- **MAPE** (Mean Absolute Percentage Error): scale-independent error measure

## Expected Baseline Performance

On the built-in sample station data:

| Baseline | MAE | RMSE | Notes |
| --- | --- | --- | --- |
| Naive | Low | Moderate | Good for stable stations |
| Trailing average | Low-Moderate | Low | Smooths noise effectively |
| Drift | Moderate | Moderate | Best for trending series |
| Seasonal profile | Varies | Varies | Best when seasonality is strong |

Exact values depend on station characteristics and window sizes.

## Leaderboard

The lab produces a leaderboard ranking baselines by hold-out MAE for each station. This helps identify which approach works best for each monitoring context without committing to a single model.

## Limitations

- Baselines are intentionally simple — they establish a performance floor, not a ceiling
- The sample dataset covers a limited time range and station set
- Feature profiling (rolling stats, seasonal phase) is descriptive, not predictive
