# Architecture

## Overview

This project models a lightweight anomaly-detection workflow for environmental monitoring telemetry with experiment-style detector comparison.

## Flow

1. Station observations are loaded from checked-in CSV data with labeled events.
2. Per-station baselines are computed from the observed values.
3. Several detectors score each event after a warmup period.
4. Detector performance is compared using precision, recall, and F1.
5. The winning detector is used to export ranked alerts and station summaries.

## Why It Works Publicly

- Demonstrates applied data science without exposing private telemetry.
- Keeps the scoring logic readable and testable in plain Python.
- Leaves a clear extension path toward richer labels, rolling retraining, model-based detectors, and alert orchestration.