# Architecture

## Overview

This project models a small station-risk classification workflow for operational triage.

## Flow

1. Station feature vectors are loaded from checked-in JSON fixtures.
2. The dataset is split into a training set and a fixed holdout review set.
3. Candidate classifiers generate predictions against the holdout set.
4. Accuracy, precision, recall, and F1 are ranked in a leaderboard.
5. The selected classifier exports explainable predictions and top risk drivers for each reviewed station.

## Shared Workflow Pattern

The lab inherits from a small `ReportWorkflow` base class that standardizes JSON export and run-registry updates. That keeps the package aligned with the time-series, forecasting, and anomaly-detection repos.