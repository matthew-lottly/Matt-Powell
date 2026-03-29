# Architecture

## Overview

This project models the design boundary between raw spatial data and a publishable PostGIS-backed service.

## Flow

1. Sample features define the layers that should be published.
2. SQL schema assets describe the base table and the indexes required for common spatial queries.
3. Publication views define what gets exposed to downstream service consumers.
4. A Python builder exports a service blueprint artifact that captures collections, endpoints, and publication notes.
5. The same builder can generate seed SQL for a local PostGIS container.

## Why It Works Publicly

- Demonstrates open-stack spatial service thinking without needing a live database.
- Keeps the repo runnable in a normal Python environment.
- Leaves a clear extension path toward PostGIS seeding, FastAPI, PostgREST, or OGC API Features delivery.
