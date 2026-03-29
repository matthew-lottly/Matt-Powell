# Demo Storyboard

## Intended Audience

- Hiring managers who need a quick visual impression
- Senior engineers reviewing backend structure
- GIS or geospatial engineering reviewers looking for applied spatial work

## Narrative Arc

1. Start on the dashboard and frame the project as an operational monitoring service, not just an API toy.
2. Use the status cards and map to show that the service is exposing geospatially meaningful information.
3. Open the alert list and explain how API consumers can triage active issues.
4. Move to Swagger and show typed endpoints, filters, and summaries.
5. End by noting the two deployment modes: local file-backed and PostGIS-backed Docker deployment.

## What Reviewers Should Notice

- There is a user-facing surface, not just backend code.
- The project has operational language: readiness, alerts, summaries, status filtering.
- The repo includes testing, CI, Docker, and database wiring.

## Strong Screens Or GIF Shots To Capture Later

- Dashboard hero with status and metrics visible
- Map with labeled alert station
- Swagger docs showing the typed monitoring endpoints
- Docker containers running with the API and database side by side