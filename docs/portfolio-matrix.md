# Portfolio Matrix

This table is the current snapshot of the tracked local project set.

Showcase priority set
- `spatial-data-api`
- `environmental-monitoring-api`
- `monitoring-data-warehouse`
- `qgis-operations-workbench`
- `open-web-map-operations-dashboard`
- `geoprompt`
- `environmental-monitoring-analytics`

| Project | Lane | Priority | Maturity | Example | Data Flow | Runbook | Smoke | CI | Next Move |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| arroyo-flood-forecasting-lab | Data Science | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Benchmark summary added. Next: tighten README outcome framing. |
| causal-lens | Data Science | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | CI added. Next: refine public framing around outcomes. |
| environmental-monitoring-analytics | Analytics | Showcase | Reviewable | Yes | Yes | No | Yes | Yes | Packaging guide added. Next: add larger snapshot fixtures. |
| environmental-monitoring-api | Backend + GIS | Showcase | Operational prototype | Yes | Yes | Yes | Yes | Yes | API examples and rollback guide added. Health-check tests added. |
| environmental-time-series-lab | Data Science | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Benchmark tables added. Next: tighten evaluation framing. |
| experience-builder-station-brief-widget | GIS Frontend | Supporting | Operational prototype | Yes | Yes | Yes | Yes | Yes | Live screenshot and browser-level tests added. Next: expand interaction coverage beyond the primary selection flow. |
| geoprompt | Package Design | Showcase | Reviewable | Yes | Yes | No | Yes | Yes | CI aligned. Ruff baseline added. Next: tighten public package framing. |
| gulf-coast-inundation-lab | Remote Sensing | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Evaluation artifact and smoke coverage added. Next: add a short runbook for the Earth Engine handoff. |
| monitoring-anomaly-detection | Data Science | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Benchmark context added. Next: strengthen evaluation narrative. |
| monitoring-data-warehouse | Database Engineering | Showcase | Reviewable | Yes | Yes | No | Yes | Yes | Schema walkthrough added. README tightened. Next: audit generated artifacts. |
| open-web-map-operations-dashboard | Web Mapping | Showcase | Operational prototype | Yes | Yes | Yes | Yes | Yes | Live screenshot and browser-level tests added. Next: extend interaction coverage into additional review paths. |
| postgis-service-blueprint | Spatial Services | Supporting | Operational prototype | Yes | Yes | Yes | Yes | Yes | Rollback guide and deployment examples added. |
| qgis-operations-workbench | Desktop GIS | Showcase | Reviewable | Yes | Yes | No | Yes | Yes | Analyst workflow, packaging guide, and a generated review preview asset added. Next: capture fuller desktop screenshots from a live QGIS session. |
| raster-monitoring-pipeline | Raster Analysis | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Benchmark evidence added. Next: tighten evaluation narrative. |
| spatial-data-api | Backend + GIS | Showcase | Operational prototype | Yes | Yes | Yes | Yes | Yes | API examples, rollback guide, and validation tests added. |
| station-forecasting-workbench | Data Science | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Holdout metrics doc added. Next: strengthen selection narrative. |
| station-risk-classification-lab | Data Science | Supporting | Reviewable | Yes | Yes | No | Yes | Yes | Classification evaluation evidence added. Next: tighten explainability framing. |
| strata | Data Science | Supporting | Operational prototype | Yes | Yes | Yes | Yes | Yes | Deployment guide added. Next: tighten uncertainty-story framing. |
| tsuan | Data Science | Supporting | Operational prototype | Yes | Yes | Yes | Yes | Yes | Deployment assumptions added. Next: tighten benchmark framing. |
| 3d-vp-lcp | Remote Sensing / Ecology | New | Research prototype | Yes | Yes | No | Yes | No | Initial scaffold with full pipeline, sample data, tutorial notebook, and 12 passing tests. Next: add circuit-theory extension and real LiDAR validation. |

Notes
- This matrix reflects the local workspace state, not a GitHub inventory API.
- `CI` means a project-local workflow file is present in the checkout.
- `Smoke` means the project currently has a lightweight smoke-style test or OpenAPI verification path.