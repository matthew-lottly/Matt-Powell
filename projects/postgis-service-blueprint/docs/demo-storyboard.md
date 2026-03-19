# Demo Storyboard

Reference asset: `assets/service-preview.svg`

## 1. Frame the use case

Show the project as the planning layer between spatial source data and a publishable PostGIS service.

## 2. Walk through the SQL

Point out that the repository includes base-table SQL and publication views, so reviewers can see what would be stored versus what would be exposed.

## 3. Run the blueprint builder

Generate `outputs/postgis_service_blueprint.json` and show the collections, endpoint patterns, and publication notes.

Then rerun with `--export-seed-sql` and point out that the same repo can generate `outputs/sample_seed.sql` for a local PostGIS container.

## 4. Explain delivery options

Use the exported artifact to explain how the same collections could later be delivered by FastAPI, PostgREST, or an OGC API Features gateway.
