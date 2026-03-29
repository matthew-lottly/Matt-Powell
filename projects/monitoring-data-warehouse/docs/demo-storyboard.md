# Demo Storyboard

## Intended Audience

- Data engineering and database reviewers
- Software teams that want evidence of modeling discipline

## Narrative Arc

1. Start with the warehouse preview image and explain the dimensional model.
2. Walk through the builder: raw staging data, dimensions, fact table, and alert mart.
3. Emphasize that this repo is about structure, repeatability, and quality checks rather than dashboards.
4. Use the test output or builder summary to show row counts and validation results.

## What Reviewers Should Notice

- Clear separation between raw data, warehouse tables, and marts.
- Thoughtful modeling rather than a single flat table.
- Repeatable SQL and data-quality validation as first-class concerns.

## Strong Screens Or GIF Shots To Capture Later

- The schema and transform SQL side by side
- Builder output with counts and quality checks
- A future ERD or lineage diagram