# Publishing Guide

## Recommended Standalone Repository Name

- environmental-monitoring-analytics

## Recommended Description

- DuckDB analytics project for generating monitoring operations briefs and alert-oriented reporting.

## Suggested Topics

- duckdb
- analytics
- sql
- environmental-monitoring
- data-reporting
- python

## Split Steps

1. Create a new empty repository named `environmental-monitoring-analytics`.
2. Initialize git in this folder.
3. Add the remote origin for the new repository.
4. Push the contents of this folder to the new repository.
5. Add the sample output from [docs/sample-operations-brief.md](docs/sample-operations-brief.md) to the README or docs.
6. Use [assets/report-preview.svg](assets/report-preview.svg) as the initial visual preview.

## Local Publish Commands

```powershell
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/<your-username>/environmental-monitoring-analytics.git
git push -u origin main
```

## First Public Polish Pass

- Add one chart or exported HTML artifact
- Show the generated brief directly in the README
- Add notes about how this project complements the API repo