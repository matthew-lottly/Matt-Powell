# Demo Storyboard

Reference asset: `assets/anomaly-preview.svg`

## 1. Frame the use case

Present the repo as the monitoring triage lane for identifying suspicious telemetry behavior and comparing anomaly detectors.

## 2. Explain the inputs

Show the station observation fixture and note that each row represents a timestamped measurement plus a public-safe event label.

## 3. Run the pipeline

Generate `outputs/anomaly_report.json` and highlight the detector leaderboard, ranked events, selected alerts, and station alert counts.

## 4. Explain the extension path

Close by noting that the same structure can grow into rolling-window detectors, seasonality-aware scoring, or model-driven alerts.