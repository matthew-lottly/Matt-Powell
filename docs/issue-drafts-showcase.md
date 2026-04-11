# Showcase Issue Drafts

Use these drafts to open the next round of issues in the seven showcase-priority standalone repositories.

## spatial-data-api

Title: Add richer API examples, rollback notes, and invalid-query coverage

Labels: enhancement, ci, showcase

Summary:
Strengthen the reviewability and operational confidence of `spatial-data-api` by expanding the concrete API examples, documenting rollback guidance, and adding failure-path validation for invalid spatial query parameters.

Why this matters:
This repo is one of the clearest backend and GIS signals in the portfolio. The next quality jump is not a new feature, it is stronger evidence that the API is understandable and safer to operate.

Acceptance criteria:
- Review artifacts include at least one request and response pair beyond the current basic example.
- The runbook includes rollback or recovery guidance for bad deploys or schema-compatible regressions.
- Tests cover at least one invalid bbox or invalid filter scenario.
- README wording stays outcome-focused rather than implementation-heavy.

## environmental-monitoring-api

Title: Improve operational examples, startup validation, and rollback guidance

Labels: enhancement, ci, showcase

Summary:
Upgrade `environmental-monitoring-api` so reviewers can see richer payload examples, clearer operational scenarios, and stronger startup and health-check confidence.

Why this matters:
This repo reads like a production-leaning monitoring service. The highest-value improvement is to make that operational story more concrete and better tested.

Acceptance criteria:
- Add richer example payloads tied to realistic monitoring conditions.
- Add health-check and startup-failure tests.
- Expand the runbook with rollback notes.
- Keep examples aligned with downstream dashboard expectations.

## monitoring-data-warehouse

Title: Add schema walkthrough artifact and strengthen warehouse narrative

Labels: enhancement, showcase

Summary:
Improve `monitoring-data-warehouse` by adding a reviewer-friendly schema walkthrough artifact and tightening the README narrative around the marts, quality checks, and database-engineering value.

Why this matters:
This is one of the best database-engineering signals in the portfolio, but it will read stronger if the core marts and their purpose are explained directly.

Acceptance criteria:
- Add one schema walkthrough artifact that names the most important tables or marts and what they support.
- Tighten the README summary around warehouse outcomes.
- Confirm tracked generated artifacts are not committed.

## qgis-operations-workbench

Title: Add screenshots and analyst workflow guidance

Labels: enhancement, showcase

Summary:
Add visual proof and clearer analyst workflow framing to `qgis-operations-workbench` so it reads as a stronger desktop GIS showcase project.

Why this matters:
Desktop GIS is a core part of the portfolio direction. This repo needs easier visual evaluation and clearer explanation of how an analyst would use the packaged outputs.

Acceptance criteria:
- Add one or more screenshots of the packaged review workspace.
- Add a short analyst workflow note to the README.
- Keep the project framed around repeatable operational GIS packaging.

## open-web-map-operations-dashboard

Title: Add screenshots, accessibility checks, and browser-level flow coverage

Labels: enhancement, ci, showcase

Summary:
Strengthen the public-facing value of `open-web-map-operations-dashboard` by adding visual review assets, accessibility checks, and higher-signal browser-level validation.

Why this matters:
This repo is a showcase frontend. Reviewers should not have to infer the UX quality from code and a render smoke test alone.

Acceptance criteria:
- Add screenshots or a short GIF showing the main dashboard state.
- Add accessibility checks for the main flows.
- Expand beyond render-only smoke coverage into at least one browser-level interaction path.
- Keep the README centered on operational map review value.

## geoprompt

Title: Align CI and sharpen package positioning

Labels: enhancement, ci, showcase

Summary:
Tighten `geoprompt` by aligning CI with current package expectations, cleaning up packaging metadata where needed, and sharpening the README around reusable spatial workflows and outcomes.

Why this matters:
This is the clearest custom package story in the portfolio. It should present as deliberate, stable, and reusable.

Acceptance criteria:
- CI reflects the current package entry points and intended validation path.
- README messaging is outcome-focused and easier for external readers to understand.
- Dependency and packaging metadata are reviewed for looseness or drift.

## environmental-monitoring-analytics

Title: Improve packaging guidance and reporting-value framing

Labels: enhancement, showcase

Summary:
Strengthen `environmental-monitoring-analytics` with clearer packaging and reproducibility guidance, plus better framing around who the reports are for and why they are useful.

Why this matters:
This repo is a strong analytics lane, but the reader should immediately understand the report audience, the operational use case, and how reproducible the pipeline is.

Acceptance criteria:
- Add or tighten packaging and reproducibility guidance.
- Clarify the value and intended audience of the reports in the README.
- Review dependency looseness in `pyproject.toml`.