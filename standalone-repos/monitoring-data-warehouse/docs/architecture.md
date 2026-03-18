# Architecture

## Overview

The warehouse project turns flat monitoring observations into a small dimensional model with dimensions, a fact table, and downstream marts for station-level and regional reporting.

## Build Flow

1. Load raw CSV data into a staging view.
2. Build `dim_region`, `dim_category`, and `dim_station`.
3. Build `fact_observation` by joining the dimensions to the staged observations.
4. Build `mart_alert_station_daily` as a grouped downstream mart for alert stations.
5. Build `mart_region_status_daily` as a regional status mart for operational coverage review.
6. Run row-count and quality checks to confirm the load is coherent.

## Why It Works As A Portfolio Project

- Shows dimensional modeling instead of only application schemas
- Shows repeatable SQL transformations
- Makes data quality visible as part of the engineering workflow
- Gives a database-engineering lane that is distinct from the API and analytics repos