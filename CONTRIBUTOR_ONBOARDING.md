# Contributor Onboarding

This repository is the portfolio hub for Matt Powell's public project set.

What belongs here
- Portfolio positioning and repo-level planning docs.
- Cross-project status tracking.
- Public-facing links, roadmap notes, and contributor workflow templates.

What does not belong here
- Standalone project source trees as committed portfolio content.
- Project-specific CI logic that should live in each standalone repository.
- Feature work for a specific project unless the matching standalone repo is the target.

How to work in this repo
1. Confirm whether the change belongs in the hub or in a standalone repo.
2. If the change is project-specific, open or link the issue in the correct standalone repository.
3. Keep the roadmap, matrix, and README links current when project status changes.
4. Prefer small PRs that change planning, docs, or cross-project coordination in one focused pass.

Recommended workflow
1. Read `README.md`, `things-to-do.md`, `ROADMAP.md`, and `docs/portfolio-matrix.md`.
2. Check whether the target project is a showcase priority or a lower-priority reviewable project.
3. Update the matrix when adding artifacts, runbooks, CI, or smoke coverage.
4. If you add a new portfolio-level process, document it here or in `things-to-do.md`.

Contribution guardrails
- Do not move standalone project source into this hub repo.
- Do not add generated caches, `node_modules`, or other local artifacts.
- Keep repo-level docs accurate, concise, and specific.
- When a task depends on GitHub settings, document the required manual follow-up clearly in the PR.