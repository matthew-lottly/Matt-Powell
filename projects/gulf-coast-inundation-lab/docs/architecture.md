# Architecture

## Overview

This project is split into two connected layers:

1. Google Earth Engine scripts for Landsat-based inundation mapping.
2. A local Python workflow for summarizing gauge-validation tables after Earth Engine export.

## Earth Engine Flow

1. Build the Gulf Coast study area from WBD features using HUC2 regions `03`, `08`, and `12`.
2. Load multi-decadal Landsat Collection 2 Level 2 imagery.
3. Rename and scale sensor bands into a common optical schema.
4. Mask clouds, shadows, cirrus, snow, and dilated cloud pixels using `QA_PIXEL`.
5. Compute AWEIsh and classify water with a configurable threshold.
6. Aggregate water detections across the image stack to produce inundation-frequency layers.
7. Suppress near-permanent water using JRC occurrence and export observation-support counts.
8. Start from the checked-in ten-gauge validation manifest and upload it to Earth Engine as an AOI feature collection.
9. Export AOI-level inundated-area summaries for downstream gauge validation.

## Local Validation Flow

1. Load a merged CSV containing `gaugeId`, `gaugeName`, `date`, `stageFt`, and `percentInundated`.
2. Group records by gauge.
3. Fit a simple linear relation between stage and inundated area for each gauge.
4. Compute $R^2$ and classify each gauge using article-style thresholds.
5. Export a JSON summary with ranked gauges and portfolio-friendly notes.

## Why This Structure Works

- The remote-sensing logic stays where it belongs: in Earth Engine near the imagery.
- The validation summary is still runnable locally, which keeps the repository demonstrable without requiring live GEE access during review.
- The repo mirrors the original article’s method sequence without pretending every step should live in one runtime.