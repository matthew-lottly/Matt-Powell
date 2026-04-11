# Schema Walkthrough

A guided tour of the monitoring data warehouse schema, showing how raw station observations become dimensional tables, fact records, and analyst-ready marts.

## Source Data

The warehouse starts with two flat CSV files:

| File | Purpose | Key Columns |
| --- | --- | --- |
| `data/station_readings.csv` | Observation feed | `station_id`, `station_name`, `category`, `region`, `observed_at`, `status`, `alert_score`, `reading_value` |
| `data/station_attribute_history.csv` | SCD-2 ownership history | `station_id`, `owner_team`, `response_tier`, `effective_from`, `effective_to`, `is_current` |

These are loaded into staging views (`staging_readings` and `staging_station_attribute_history`) before the warehouse build.

## Dimension Tables

### dim_station

One row per monitored station. Derives from distinct station identifiers in the reading feed.

| Column | Type | Purpose |
| --- | --- | --- |
| `station_key` | INTEGER PK | Surrogate key |
| `station_id` | TEXT | Natural key from the source |
| `station_name` | TEXT | Display name |
| `region` | TEXT | Geographic region |
| `category` | TEXT | Monitoring domain (hydrology, air quality, water quality) |

### dim_station_attribute_history

Slowly changing dimension (Type 2) tracking ownership and response tier changes over time.

| Column | Type | Purpose |
| --- | --- | --- |
| `station_history_key` | INTEGER PK | Surrogate key |
| `station_id` | TEXT | Natural key |
| `owner_team` | TEXT | Current or historical owner |
| `response_tier` | TEXT | Service level (standard, priority, critical) |
| `effective_from` | TEXT | Period start date |
| `effective_to` | TEXT | Period end date (NULL for current) |
| `is_current` | BOOLEAN | Whether this row is the active record |

### dim_region

One row per geographic region.

| Column | Type | Purpose |
| --- | --- | --- |
| `region_key` | INTEGER PK | Surrogate key |
| `region_name` | TEXT | Region label |

### dim_category

One row per monitoring category.

| Column | Type | Purpose |
| --- | --- | --- |
| `category_key` | INTEGER PK | Surrogate key |
| `category_name` | TEXT | Category label |

## Fact Table

### fact_observation

One row per station observation. Foreign keys point into the dimension tables.

| Column | Type | Purpose |
| --- | --- | --- |
| `observation_id` | INTEGER PK | Surrogate key |
| `station_key` | INTEGER FK | Links to dim_station |
| `region_key` | INTEGER FK | Links to dim_region |
| `category_key` | INTEGER FK | Links to dim_category |
| `observed_at` | TEXT | ISO timestamp |
| `status` | TEXT | Observation status (normal, alert, offline) |
| `alert_score` | DOUBLE | Severity score |
| `reading_value` | DOUBLE | Raw measurement |

## Mart Tables

### mart_alert_station_daily

One row per station per day. Aggregates alert counts and maximum severity for daily operations review.

| Column | Type | Purpose |
| --- | --- | --- |
| `observation_date` | TEXT | Date (from observed_at) |
| `station_id` | TEXT | Station identifier |
| `station_name` | TEXT | Display name |
| `region_name` | TEXT | Region |
| `category_name` | TEXT | Monitoring category |
| `alert_count` | INTEGER | Number of alert observations |
| `max_alert_score` | DOUBLE | Peak severity for the day |

### mart_region_status_daily

One row per region per status per day. Drives regional dashboard cards and trend charts.

| Column | Type | Purpose |
| --- | --- | --- |
| `observation_date` | TEXT | Date |
| `region_name` | TEXT | Region |
| `status` | TEXT | Observation status |
| `observation_count` | INTEGER | Count of observations |
| `avg_alert_score` | DOUBLE | Average severity |
| `max_alert_score` | DOUBLE | Peak severity |

## Build Flow

```text
station_readings.csv ──┐
                        ├──► staging views ──► schema.sql ──► transforms.sql ──► warehouse tables
station_attribute_history.csv ─┘
```

1. **Staging**: CSV files loaded as DuckDB views
2. **Schema**: Dimension and fact tables created by `sql/schema.sql`
3. **Transforms**: Population and aggregation logic in `sql/transforms.sql`
4. **Artifact**: Build summary written to `artifacts/warehouse-build-summary.json`

## Quality Controls

The build emits quality checks including:

- Null surrogate key detection in `fact_observation`
- Alert record counts
- Contract checks from `metadata/warehouse_models.yml`
- Source freshness SLA validation
- Field completeness validation

## Example Queries

Station alert history for the last 7 days:

```sql
SELECT station_id, station_name, observation_date, alert_count, max_alert_score
FROM mart_alert_station_daily
WHERE alert_count > 0
ORDER BY observation_date DESC, max_alert_score DESC
LIMIT 20;
```

Regional alert trend:

```sql
SELECT observation_date, region_name, SUM(observation_count) AS total, ROUND(AVG(avg_alert_score), 3) AS avg_severity
FROM mart_region_status_daily
WHERE status = 'alert'
GROUP BY observation_date, region_name
ORDER BY observation_date DESC;
```
