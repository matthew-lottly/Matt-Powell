# Architecture

## Overview

This project models a small forecasting workflow for station-level monitoring histories.

## Flow

1. Station histories are loaded from checked-in JSON fixtures.
2. Each series is split into training and holdout segments.
3. A trailing-average baseline forecast is generated.
4. Holdout error and next-step projections are exported for review.