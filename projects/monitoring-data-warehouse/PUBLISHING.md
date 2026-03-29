# Publishing Guide

## Recommended Standalone Repository Name

- monitoring-data-warehouse

## Recommended Description

- Warehouse-style modeling and validation project for monitoring observations, dimensions, facts, and alert marts.

## Suggested Topics

- data-warehouse
- sql
- duckdb
- dimensional-modeling
- data-engineering
- environmental-monitoring

## Split Steps

1. Create a new empty repository named `monitoring-data-warehouse`.
2. Initialize git in this folder.
3. Add the remote origin for the new repository.
4. Push the contents of this folder to the new repository.
5. Add [assets/warehouse-preview.svg](assets/warehouse-preview.svg) near the top of the README.
6. Reference [docs/model-notes.md](docs/model-notes.md) for the modeling rationale.

## Local Publish Commands

```powershell
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/<your-username>/monitoring-data-warehouse.git
git push -u origin main
```

## First Public Polish Pass

- Add an ERD or dbt-style DAG diagram
- Add a section explaining migration from DuckDB to PostgreSQL or Snowflake
- Add row-count and quality-check output examples to the README