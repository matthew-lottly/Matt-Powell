# PR #2 Split Review

Reviewed against `main` on 2026-04-02.

## Scope Summary

- The branch currently spans 248 changed files versus `main`.
- The branch now contains valid portfolio-hub work, valid local `projects/` workspace improvements, and historical sports-sim changes that have since been removed from the working tree but still appear in the PR timeline and diff history.

## Main Findings

1. The branch is broader than one clean merge unit.
2. The portfolio-hub documentation work is coherent and mergeable together.
3. The per-project review artifacts, data-flow docs, runbooks, and smoke tests are coherent as a second merge unit if you intend to keep local `projects/` content in this repo history.
4. The old sports-sim review comments are now stale because they point at deleted files that no longer belong in the repository direction.

## Recommended Split

### Merge Unit A

Portfolio-hub coordination and presentation work:
- `README.md`
- `things-to-do.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `CONTRIBUTOR_ONBOARDING.md`
- `.github/` templates and ownership files
- `docs/portfolio-matrix.md`
- `docs/todo-*.md`
- `docs/merge-checklist.md`
- `docs/weekly-maintenance-checklist.md`
- `scripts/portfolio-checks.ps1`

### Merge Unit B

Project-review hardening work under `projects/`:
- `EXAMPLE_OUTPUT.md` additions
- `docs/data-flow.md` additions
- service `docs/runbook.md` additions
- README review-artifact links
- new smoke or OpenAPI tests

### Explicitly Exclude or Treat As Historical Cleanup

- deleted sports-sim content
- old sports-sim CI, Docker, and test-review threads
- any stale PR conversation tied to removed sports-sim files

## Manual GitHub Follow-Up

1. The unresolved review threads on deleted sports-sim files have been resolved as obsolete.
2. The maintainer closeout comment has been posted.
3. Treat PR #2 as historical cleanup context, not as the preferred merge vehicle.
4. Use smaller follow-up PRs for mergeable work instead of landing the full historical branch as one unit.

## Merge Recommendation

- Decided path: do not merge PR #2 as one unit. Use it as historical review context, then land smaller follow-up PRs for hub coordination work and project-review hardening.
- Temporary fallback: if PR #2 stays open for reference, discuss the branch as `hub planning` plus `project review artifacts` and do not treat the stale sports-sim review history as active feedback.