# PostgreSQL Migration Strategy

## Goal

Translate the current DuckDB-first warehouse shape into a PostgreSQL deployment without changing the dimensional model reviewers already see in this repository.

## Recommended Partitioning

### fact_observation

`fact_observation` is the first table to partition because it will grow the fastest and most often be queried by time range.

- Partition key: `observed_at` or a derived `observed_on`
- Default starting point: monthly range partitions
- Switch to daily partitions only if ingestion volume or delete frequency makes monthly partitions too large
- Index each partition on `(station_key, observed_at)` for station drill-downs and on `(region_key, observed_at)` if regional time-slice queries dominate

### Daily marts

`mart_alert_station_daily` and `mart_region_status_daily` can stay as ordinary tables at small scale, but for PostgreSQL they should follow one of two patterns:

- Partition by `observed_on` if the marts are materialized into physical tables during each load
- Use materialized views plus scheduled refresh if the marts remain thin and downstream access is mostly dashboard-oriented

### Dimensions

Keep `dim_station`, `dim_region`, `dim_category`, and `dim_station_attribute_history` unpartitioned.

- They are comparatively small
- They are keyed for lookup joins rather than large date scans
- Partitioning them would add operational complexity without much payoff

## Retention Guidance

### Raw and staging data

- Retain raw landing files and staging copies for 30 to 90 days
- Extend retention when source reliability is poor or replay requirements are high
- Store longer-lived raw archives outside the main PostgreSQL warehouse when possible

### Fact history

- Retain `fact_observation` online for 13 to 24 months as a practical default
- Drop or archive whole partitions rather than running row-by-row deletes
- Keep partition boundaries aligned with the retention window so cleanup is operationally simple

### Derived marts

- Retain daily marts for at least as long as the online fact window
- Consider longer retention for marts because they are compact and useful for baseline comparisons
- Rebuild marts from retained facts when practical instead of preserving every intermediate transform artifact

## Operational Tradeoffs

- Monthly partitions reduce maintenance overhead, but daily partitions make high-volume retention and reprocessing easier
- Materialized marts simplify dashboard reads, but increase refresh orchestration work
- Short raw-data retention keeps PostgreSQL lean, but shifts long-term audit responsibility to cheaper archive storage
- Type 2 history stays easy to manage because attribute history volume is low relative to observations

## Migration Sequence

1. Move the current schema to PostgreSQL without partitioning dimensions.
2. Partition `fact_observation` by month.
3. Load facts and validate row counts against the DuckDB build.
4. Materialize or partition daily marts based on expected dashboard load.
5. Add partition drop/archive jobs once retention expectations are agreed.

This keeps the migration path concrete, production-minded, and aligned with the warehouse model already presented in the repo.