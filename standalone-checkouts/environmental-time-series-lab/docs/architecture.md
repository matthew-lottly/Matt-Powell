# Architecture

## Overview

This project models a small temporal diagnostics workflow for monitoring histories.

## Flow

1. Station histories are loaded from checked-in JSON fixtures.
2. Each series is split into a calibration segment and a trailing review window.
3. Rolling summaries, first differences, variability, and trend features are computed from the calibration history.
4. A seasonal fingerprint is built by averaging repeating phases across a configurable season length.
5. A lightweight change-point candidate is identified by the strongest mean shift across valid splits.
6. Candidate temporal baselines, including a seasonal-naive option, are compared on review-window MAE and ranked in a leaderboard.
7. Station diagnostics and experiment metadata are exported for downstream review.

## Shared Workflow Pattern

The lab inherits from a small `ReportWorkflow` base class that standardizes JSON export and run-registry updates. That keeps the project object-oriented while preserving the same thin functional API used by the CLI and tests.