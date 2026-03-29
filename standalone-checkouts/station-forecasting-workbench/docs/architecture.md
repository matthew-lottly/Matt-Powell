# Architecture

## Overview

This project models a lightweight forecasting workbench for station-level monitoring histories with experiment-style evaluation.

## Flow

1. Station histories are loaded from checked-in JSON fixtures.
2. Each series is split into training, validation, and test segments.
3. A feature profile is built from recent level, volatility, momentum, and slope.
4. Several candidate forecasts are generated and scored on the validation window.
5. The best-performing model is re-evaluated on the test window and used for forward projection.
6. Experiment metadata is exported with run label, split sizes, and model-win summary.