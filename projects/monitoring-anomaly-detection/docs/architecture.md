# Architecture

## Overview

This project models a lightweight anomaly-detection workflow for environmental monitoring telemetry.

## Flow

1. Station observations are loaded from checked-in CSV data.
2. Per-station baselines are computed from the observed values.
3. Observations are scored by normalized deviation from their station baseline.
4. High-scoring events are exported as a ranked anomaly report.

## Why It Works Publicly

- Demonstrates applied data science without exposing private telemetry.
- Keeps the scoring logic readable and testable in plain Python.
- Leaves a clear extension path toward rolling windows, model-based detectors, and alert orchestration.