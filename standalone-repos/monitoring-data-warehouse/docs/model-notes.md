# Model Notes

## Purpose

This warehouse exists to show dimensional thinking applied to monitoring data rather than ad hoc query work.

## Model Shape

- `dim_station` captures station identity and stable descriptive attributes
- `dim_station_attribute_history` demonstrates a Type 2 slowly changing dimension for ownership and response-tier changes
- `dim_region` standardizes regional grouping
- `dim_category` standardizes monitoring domains
- `fact_observation` stores observation-level operational events
- `mart_alert_station_daily` gives a compact daily alert aggregate for reporting and downstream consumption
- `mart_region_status_daily` gives a regional daily view of status mix and alert pressure

## Why This Matters In The Portfolio

- Shows database design beyond application CRUD schemas
- Shows repeatable transformation logic in SQL
- Gives a clean bridge between raw operational data and analytical consumption

## Slowly Changing Dimension Example

The warehouse includes `dim_station_attribute_history` as a compact Type 2 history table.

- `station_id` remains the business key
- `effective_from` and `effective_to` define validity windows
- `is_current` marks the current attribute row
- `owner_team` and `response_tier` illustrate how station operations metadata can evolve without overwriting prior state

This keeps the example focused on a pattern a reviewer will recognize immediately, without expanding the repo into a full enterprise warehouse.

## PostgreSQL Retention And Partitioning Notes

The DuckDB build is intentionally compact, but the same model translates cleanly to PostgreSQL with a few operational decisions:

- Partition `fact_observation` by date so routine retention and vacuum work stays bounded.
- Retain raw ingest-stage data for a shorter audit window, such as 30 to 90 days, once warehouse loads are proven repeatable.
- Retain `fact_observation` for a longer operational history, such as 13 to 24 months, so alert and status analysis still has seasonal context.
- Retain derived daily marts longer than raw staging data because they are smaller and more useful for reporting baselines.
- Archive or snapshot partitions before deletion if regulatory or incident-review needs require longer lookback.

The dedicated migration note in `docs/postgresql-migration-strategy.md` turns those choices into a concrete reviewer-facing plan.