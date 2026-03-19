# Monitoring Data Warehouse

Database-engineering project for modeling, building, and validating a monitoring warehouse from operational station data.

![Warehouse preview](assets/warehouse-preview.svg)

## Overview

This project represents the database-engineering lane of the portfolio. It starts from raw station observations, builds a small warehouse model with dimensions and facts, and runs validation queries that are closer to platform engineering than analytics notebooks.

## What It Demonstrates

- Warehouse-style schema design
- Dimension and fact table modeling
- Repeatable SQL execution against DuckDB
- Data quality checks for operational datasets
- dbt-style model dependency metadata and executable data contracts
- A portfolio lane focused on database structure and reliability

## Warehouse Model

- `dim_station`
- `dim_station_attribute_history`
- `dim_region`
- `dim_category`
- `fact_observation`
- `mart_alert_station_daily`
- `mart_region_status_daily`

## Quick Start

```bash
pip install -e .[dev]
python -m monitoring_data_warehouse.builder
```

## Outputs

- A local DuckDB warehouse file
- Row-count and quality-check summary
- A slowly changing dimension example for station ownership and response tier
- Sample daily alert and regional status marts
- A manifest-backed model catalog and contract check summary

See [docs/model-notes.md](docs/model-notes.md) for the modeling rationale behind the warehouse shape.
See [docs/architecture.md](docs/architecture.md) for the warehouse build flow.
See [docs/model-catalog.md](docs/model-catalog.md) for model dependencies, grains, and contract coverage.
See [docs/postgresql-migration-strategy.md](docs/postgresql-migration-strategy.md) for concrete partitioning and retention notes for a PostgreSQL migration path.
See [docs/schema-diagram.md](docs/schema-diagram.md) for a quick view of the warehouse structure.

## Next Steps

- Add source freshness thresholds and late-arriving dimension handling notes
- Generate contract results into a lightweight build artifact for CI review

## Publication

See [PUBLISHING.md](PUBLISHING.md) for the standalone repository plan.