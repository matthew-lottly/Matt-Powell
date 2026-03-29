# Architecture

## Overview

This project recreates a flood-forecasting workflow around a real public South Texas river-stage series used as an Arroyo-style analog.

## Flow

1. A checked-in hourly USGS-derived stage fixture is loaded from JSON.
2. A discrete wavelet transform denoises the observed stage signal.
3. Autocorrelation and partial-autocorrelation summaries describe the dominant lags.
4. Candidate autoregressive orders are fit on both the raw and denoised series.
5. The final holdout window is forecast and scored with PMSE.
6. Residual variance from the best-performing model drives Monte Carlo forecast scenarios.
7. A chart pack is exported for reviewer-friendly hydrograph, lag, PMSE, and scenario visualization.
8. A cross-site comparison summary checks whether denoising helps more on a noisier public gauge.

## Why It Works Publicly

- The checked-in data comes from a real public USGS gage-height feed rather than a synthetic placeholder.
- The workflow preserves the core method story from the original study without depending on MATLAB.
- The chosen station is a reproducible South Texas analog, which is more honest and portable than implying access to a non-public Arroyo feed.
- The output is reviewable by hiring managers who want to see applied forecasting structure, not just a notebook.