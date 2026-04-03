# Monitoring Data Warehouse

Database-engineering project for modeling, building, and validating a monitoring warehouse from operational station data.

![Warehouse preview](assets/warehouse-preview.svg)

## Review Artifacts

- Example output: [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md)
- Data-flow diagram: [docs/data-flow.md](docs/data-flow.md)

## Snapshot

- Lane: Database engineering
- Domain: Environmental monitoring
- Stack: DuckDB, SQL, Python
- Includes: dimensional model, fact table, alert mart, quality checks, source SLA validation, CI-ready build artifact, model metadata, tests

## Overview

This project represents the database-engineering lane of the portfolio. It starts from raw station observations, builds a small warehouse model with dimensions and facts, and runs validation queries that are closer to platform engineering than notebook analysis.

## What It Demonstrates

- Warehouse-style schema design
- Dimension and fact table modeling
- Repeatable SQL execution against DuckDB
- Data quality checks for operational datasets
- Freshness and completeness SLA validation driven from metadata
- dbt-style model dependency metadata and executable data contracts
- A portfolio lane focused on database structure and reliability

## Why This Project Exists

Warehouse work is often hard to show publicly because the most valuable parts are schema choices, transformation discipline, and data quality controls. This repository isolates those concerns in a small, reviewable build.

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

## Why It Is Useful In A Portfolio

- Shows dimensional modeling instead of only application code
- Demonstrates transform execution and validation from raw data to marts
- Gives a reviewer a clear database-engineering example that is separate from analytics and API work

## Project Structure

```text
monitoring-data-warehouse/
|-- data/
|-- sql/
|-- src/monitoring_data_warehouse/
|   |-- __init__.py
|   `-- builder.py
|-- tests/
|   `-- test_builder.py
|-- pyproject.toml
`-- README.md
```

## Outputs

- A local DuckDB warehouse file
- Row-count and quality-check summary
- A JSON warehouse-build artifact for CI upload and review
- A slowly changing dimension example for station ownership and response tier
- Sample daily alert and regional status marts
- A manifest-backed model catalog and contract check summary

See [docs/model-notes.md](docs/model-notes.md) for the modeling rationale behind the warehouse shape.
See [docs/architecture.md](docs/architecture.md) for the warehouse build flow.
See [docs/model-catalog.md](docs/model-catalog.md) for model dependencies, grains, and contract coverage.
See [docs/postgresql-migration-strategy.md](docs/postgresql-migration-strategy.md) for concrete partitioning and retention notes for a PostgreSQL migration path.
See [docs/schema-diagram.md](docs/schema-diagram.md) for a quick view of the warehouse structure.
See [docs/schema-walkthrough.md](docs/schema-walkthrough.md) for a guided tour of each table and its role in the warehouse.

## Next Steps

- Add source freshness thresholds and late-arriving dimension handling notes
- Generate contract results into a lightweight build artifact for CI review

## Publication

- License: [LICENSE](LICENSE)
- Standalone publishing notes: [PUBLISHING.md](PUBLISHING.md)

## Repository Notes

This copy is intended to be publishable as its own repository. CI is included in [.github/workflows/ci.yml](.github/workflows/ci.yml).