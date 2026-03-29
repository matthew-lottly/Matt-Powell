# Demo Storyboard

Reference asset: `assets/classification-preview.svg`

## 1. Frame the use case

Introduce the repo as the classification lane for turning station behavior summaries into escalation-ready risk labels.

## 2. Explain the feature vectors

Show the JSON fixture and note that each station snapshot includes recent level, variability, trend, anomaly rate, maintenance lag, and exceedance-day features.

## 3. Run the lab

Generate `outputs/station_risk_report.json` and review the experiment metadata, classifier leaderboard, selected model metrics, and explainable holdout predictions.

## 4. Explain the extension path

Close by noting that the same structure can grow into richer feature engineering, probability calibration, or more formal ML experimentation.