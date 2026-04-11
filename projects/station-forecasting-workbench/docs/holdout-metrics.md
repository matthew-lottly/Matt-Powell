# Holdout Metrics

Evaluation evidence for the station forecasting workbench.

## Evaluation Design

The workbench uses a three-way split for rigorous model comparison:

| Split | Purpose | Used For |
| --- | --- | --- |
| Training | Fit candidate models | Parameter estimation |
| Validation | Select the best model | Model ranking and selection |
| Test | Final performance report | Unbiased performance estimate |

This prevents information leakage: the test set is never used for model selection.

## Candidate Models

| Model | Approach | Complexity |
| --- | --- | --- |
| Naive (last value) | Repeat the most recent observation | Simplest baseline |
| Trailing average | Mean of recent N values | Low |
| Drift | Linear extrapolation from recent trend | Low |
| Linear regression | Feature-based linear fit | Moderate |

## Metrics

- **MAE** (Mean Absolute Error): average error magnitude
- **RMSE** (Root Mean Square Error): penalizes large errors
- **Skill score**: improvement over the naive baseline

## Expected Results Pattern

On the built-in station data:

- The naive baseline provides a simple error floor
- Trailing average often wins for stable stations
- Drift wins when there is a clear trend
- Linear regression wins when feature profiles add predictive value

The leaderboard reports validation MAE for model selection and test MAE for the final reported performance.

## Limitations

- Models are intentionally simple — they demonstrate evaluation discipline, not state-of-the-art forecasting
- Feature profiles are descriptive summaries, not engineered predictive features
- The sample dataset is small; real station data would provide more discriminating comparisons
