# Model Catalog

This catalog mirrors a small dbt-style model manifest for the public warehouse example.

## Sources

- `staging_readings`: raw station observations loaded from the CSV extract
- `staging_station_attribute_history`: owner-team and response-tier history for the Type 2 example

## Models

### dim_station

- Grain: one row per `station_id`
- Depends on: `staging_readings`
- Purpose: canonical station dimension for fact joins and mart labeling

### dim_station_attribute_history

- Grain: one row per `station_id` and `effective_from`
- Depends on: `staging_station_attribute_history`
- Purpose: tracks owner-team and response-tier changes across time

### dim_region

- Grain: one row per `region_name`
- Depends on: `staging_readings`
- Purpose: region reference table for reporting

### dim_category

- Grain: one row per `category_name`
- Depends on: `staging_readings`
- Purpose: category reference table for reporting

### fact_observation

- Grain: one row per station observation
- Depends on: `dim_station`, `dim_region`, `dim_category`, `staging_readings`
- Purpose: atomic warehouse fact table used by the marts and contract checks

### mart_alert_station_daily

- Grain: one row per `station_id` and `observation_date` when alerts occur
- Depends on: `fact_observation`, `dim_station`, `dim_region`, `dim_category`
- Purpose: operational alert rollup for escalation reviews

### mart_region_status_daily

- Grain: one row per `region_name`, `status`, and `observation_date`
- Depends on: `fact_observation`, `dim_region`
- Purpose: quick regional operating summary mart

## Data Contracts

The manifest-backed build validates a small contract suite after loading the warehouse:

- unique keys for station, region, and category dimensions
- at most one current row per station in the attribute history dimension
- non-null foreign keys and valid status values in the fact table
- positive alert counts and valid status values in the marts