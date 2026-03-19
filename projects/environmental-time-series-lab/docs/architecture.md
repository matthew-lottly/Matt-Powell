# Architecture

## Overview

This project models a small time-series analysis workflow for monitoring histories.

## Flow

1. Station histories are loaded from checked-in JSON fixtures.
2. Rolling means are computed for each time series.
3. A simple trend value is estimated from first-to-last observations.
4. Station summaries are exported for downstream review.