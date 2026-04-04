# Showcase Issue Bodies

Copy the sections below directly into GitHub issues in the matching standalone repositories.

## spatial-data-api

Title: Add richer API examples, rollback notes, and invalid-query coverage

Labels: enhancement, ci, showcase

Body:

Summary
Strengthen the reviewability and operational confidence of `spatial-data-api` by expanding the concrete API examples, documenting rollback guidance, and adding failure-path validation for invalid spatial query parameters.

Why this matters
This repo is one of the clearest backend and GIS signals in the portfolio. The next quality jump is not a new feature. It is stronger evidence that the API is understandable, stable, and safer to operate.

Requested changes
- Add at least one richer request and response example to the review artifacts.
- Add rollback or recovery guidance to the runbook.
- Add tests for at least one invalid bbox or invalid filter scenario.
- Keep README wording outcome-focused rather than implementation-heavy.

Definition of done
- A reviewer can see realistic request and response examples without running the service.
- The runbook contains rollback guidance.
- Failure-path validation exists for invalid spatial queries.

## environmental-monitoring-api

Title: Improve operational examples, startup validation, and rollback guidance

Labels: enhancement, ci, showcase

Body:

Summary
Upgrade `environmental-monitoring-api` so reviewers can see richer payload examples, clearer operational scenarios, and stronger startup and health-check confidence.

Why this matters
This repo reads like a production-leaning monitoring service. The highest-value improvement is to make that operational story more concrete and better tested.

Requested changes
- Add richer example payloads tied to realistic monitoring conditions.
- Add health-check and startup-failure tests.
- Expand the runbook with rollback notes.
- Keep examples aligned with downstream dashboard expectations.

Definition of done
- The API docs and review artifacts show realistic operational payloads.
- Startup and health-check behavior are validated.
- The runbook includes rollback guidance.

## monitoring-data-warehouse

Title: Add schema walkthrough artifact and strengthen warehouse narrative

Labels: enhancement, showcase

Body:

Summary
Improve `monitoring-data-warehouse` by adding a reviewer-friendly schema walkthrough artifact and tightening the README narrative around the marts, quality checks, and database-engineering value.

Why this matters
This is one of the best database-engineering signals in the portfolio, but it will read stronger if the core marts and their purpose are explained directly.

Requested changes
- Add one schema walkthrough artifact that names the most important tables or marts and what they support.
- Tighten the README summary around warehouse outcomes.
- Confirm tracked generated artifacts are not committed.

Definition of done
- The repo includes a reviewer-friendly schema walkthrough.
- The README explains the warehouse value more directly.
- Generated artifact hygiene is confirmed.

## qgis-operations-workbench

Title: Add screenshots and analyst workflow guidance

Labels: enhancement, showcase

Body:

Summary
Add visual proof and clearer analyst workflow framing to `qgis-operations-workbench` so it reads as a stronger desktop GIS showcase project.

Why this matters
Desktop GIS is a core part of the portfolio direction. This repo needs easier visual evaluation and clearer explanation of how an analyst would use the packaged outputs.

Requested changes
- Add one or more screenshots of the packaged review workspace.
- Add a short analyst workflow note to the README.
- Keep the project framed around repeatable operational GIS packaging.

Definition of done
- Visual evidence exists for the review workspace.
- The README includes a concise analyst workflow explanation.

## open-web-map-operations-dashboard

Title: Add screenshots, accessibility checks, and browser-level flow coverage

Labels: enhancement, ci, showcase

Body:

Summary
Strengthen the public-facing value of `open-web-map-operations-dashboard` by adding visual review assets, accessibility checks, and higher-signal browser-level validation.

Why this matters
This repo is a showcase frontend. Reviewers should not have to infer the UX quality from code and a render smoke test alone.

Requested changes
- Add screenshots or a short GIF showing the main dashboard state.
- Add accessibility checks for the main flows.
- Expand beyond render-only smoke coverage into at least one browser-level interaction path.
- Keep the README centered on operational map review value.

Definition of done
- Visual proof exists in the repo.
- Accessibility checks are present.
- At least one browser-level interaction path is validated.

## geoprompt

Title: Align CI and sharpen package positioning

Labels: enhancement, ci, showcase

Body:

Summary
Tighten `geoprompt` by aligning CI with current package expectations, cleaning up packaging metadata where needed, and sharpening the README around reusable spatial workflows and outcomes.

Why this matters
This is the clearest custom package story in the portfolio. It should present as deliberate, stable, and reusable.

Requested changes
- Align CI with current package entry points and intended validation.
- Sharpen README messaging around reusable workflows and outcomes.
- Review dependency and packaging metadata for looseness or drift.

Definition of done
- CI and packaging match the current package design.
- README positioning is clearer to outside readers.

## environmental-monitoring-analytics

Title: Improve packaging guidance and reporting-value framing

Labels: enhancement, showcase

Body:

Summary
Strengthen `environmental-monitoring-analytics` with clearer packaging and reproducibility guidance, plus better framing around who the reports are for and why they are useful.

Why this matters
This repo is a strong analytics lane, but the reader should immediately understand the report audience, the operational use case, and how reproducible the pipeline is.

Requested changes
- Add or tighten packaging and reproducibility guidance.
- Clarify the value and intended audience of the reports in the README.
- Review dependency looseness in `pyproject.toml`.

Definition of done
- Packaging and reproducibility guidance are explicit.
- README makes the report audience and value obvious.