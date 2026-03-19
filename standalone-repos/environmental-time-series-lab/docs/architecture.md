# Architecture

## Overview

This project models a small temporal diagnostics workflow for monitoring histories.

## Flow

1. Station histories are loaded from checked-in JSON fixtures.
2. Each series is split into a calibration segment and a trailing review window.
3. Rolling summaries, first differences, variability, and trend features are computed from the calibration history.
4. Candidate temporal baselines are compared on review-window MAE and ranked in a leaderboard.
5. Station diagnostics and experiment metadata are exported for downstream review.