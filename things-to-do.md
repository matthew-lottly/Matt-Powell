# Things To Do

Purpose: keep one current, portfolio-level execution plan for the Matt Powell hub repository.

Scope rules
- This repository is the portfolio hub, not the home of the standalone project source trees.
- Changes to application code, project CI, packaging, deployment, or tests should be made in the matching standalone repository under `matthew-lottly`.
- Changes to planning, portfolio positioning, review guidance, and contributor workflow belong here.

Current portfolio baseline
- Review artifacts exist for all tracked projects via `EXAMPLE_OUTPUT.md`.
- Data-flow docs exist for all tracked projects via `docs/data-flow.md`.
- Runbooks exist for the current service-style projects.
- Smoke or OpenAPI coverage now exists for most tracked projects.
- The portfolio branch has already removed the old sports-sim work and cleaned its stale references.

Use this file
1. Update repo-level progress here.
2. Open standalone-repo issues from the roadmap items in `ROADMAP.md`.
3. Keep `docs/portfolio-matrix.md` aligned with the real current state.
4. Use `docs/todo-100.md` when you want the full expanded backlog instead of the shorter operational summary.

Done recently
- Added example output artifacts across the project portfolio.
- Added per-project data-flow diagrams.
- Added service runbooks where operational review mattered.
- Added smoke and OpenAPI tests across the active project set.
- Normalized README review-artifact placement.

Now
- Keep the portfolio hub docs current and accurate.
- Convert roadmap items into issues in the correct standalone repositories.
- Prioritize the showcase projects before spreading effort across the full set.
- Use the scoped todo lists in `docs/` so repo-hub work, standalone-repo work, and GitHub-setting work do not get mixed together.

Current repo-level deliverables
- [x] Portfolio roadmap: `ROADMAP.md`
- [x] Portfolio status matrix: `docs/portfolio-matrix.md`
- [x] Scoped todo lists: `docs/todo-hub.md`, `docs/todo-standalone-repos.md`, `docs/todo-github-ops.md`
- [x] Weekly maintenance checklist: `docs/weekly-maintenance-checklist.md`
- [x] Merge checklist: `docs/merge-checklist.md`
- [x] Root changelog: `CHANGELOG.md`
- [x] Portfolio checks script: `scripts/portfolio-checks.ps1`
- [x] Contributor onboarding: `CONTRIBUTOR_ONBOARDING.md`
- [x] Issue templates for bug, feature, and CI follow-up work.
- [x] Pull request template.
- [x] `CODEOWNERS` baseline for the portfolio hub.

Next execution rule
- When a roadmap item requires source-code work, open or link the issue in the target standalone repository and do not implement it in this portfolio hub by mistake.