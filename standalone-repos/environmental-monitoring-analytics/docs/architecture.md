# Architecture

## Overview

The analytics project is intentionally simple: a lightweight reporting pipeline around DuckDB and a flat observation dataset.

## Flow

1. Load the CSV observation file into an in-memory DuckDB view.
2. Run SQL queries for alert counts, alert rate, regional pressure, and latest alerts.
3. Format the results into a markdown operations brief and an HTML summary.

## Key Design Choice

The project is SQL-first and output-oriented. It is meant to show concise analytical thinking rather than notebook exploration.

## Why It Works As A Portfolio Project

- Small enough to review quickly
- Demonstrates DuckDB and SQL fluency
- Produces concrete markdown and HTML artifacts instead of abstract code only
- Complements the API and warehouse projects as a downstream analytics lane