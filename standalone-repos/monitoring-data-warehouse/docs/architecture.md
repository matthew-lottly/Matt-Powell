# Architecture

## Overview

The warehouse project turns flat monitoring observations into a small dimensional model with dimensions, a fact table, and downstream marts for station-level and regional reporting.

## Build Flow

1. Load raw CSV data into a staging view.
2. Build `dim_region`, `dim_category`, and `dim_station`.
3. Load `dim_station_attribute_history` from a compact station-attribute history source to illustrate a Type 2 dimension pattern.
4. Build `fact_observation` by joining the dimensions to the staged observations.
5. Build `mart_alert_station_daily` as a grouped downstream mart for alert stations.
6. Build `mart_region_status_daily` as a regional status mart for operational coverage review.
7. Run row-count and quality checks to confirm the load is coherent.

## Why It Works As A Portfolio Project

- Shows dimensional modeling instead of only application schemas
- Shows repeatable SQL transformations
- Makes data quality visible as part of the engineering workflow
- Gives a database-engineering lane that is distinct from the API and analytics repos

## PostgreSQL Migration Shape

If this DuckDB-first build moved into PostgreSQL, the simplest production-oriented shape would keep dimensions as standard heap tables and partition the largest time-based tables.

- Partition `fact_observation` by observation date, typically monthly partitions if ingestion stays moderate and daily partitions if volume becomes operationally large.
- Keep `mart_alert_station_daily` and `mart_region_status_daily` either as partitioned tables keyed by `observed_on` or as incrementally refreshed materialized views if downstream query patterns are mostly date-bounded.
- Leave `dim_station_attribute_history` unpartitioned at this scale because its access pattern is keyed by `station_id` and validity windows rather than bulk time scans.

This preserves the model shown in the repo while giving a realistic next step toward PostgreSQL operations.