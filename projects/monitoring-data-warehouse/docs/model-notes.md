# Model Notes

## Purpose

This warehouse exists to show dimensional thinking applied to monitoring data rather than ad hoc query work.

## Model Shape

- `dim_station` captures station identity and stable descriptive attributes
- `dim_region` standardizes regional grouping
- `dim_category` standardizes monitoring domains
- `fact_observation` stores observation-level operational events
- `mart_alert_station_daily` gives a compact daily alert aggregate for reporting and downstream consumption
- `mart_region_status_daily` gives a regional daily view of status mix and alert pressure

## Why This Matters In The Portfolio

- Shows database design beyond application CRUD schemas
- Shows repeatable transformation logic in SQL
- Gives a clean bridge between raw operational data and analytical consumption