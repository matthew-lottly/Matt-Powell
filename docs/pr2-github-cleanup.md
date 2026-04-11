# PR #2 GitHub Cleanup

This note turns the active PR cleanup into an explicit manual checklist for GitHub.

Reviewed from fresh PR metadata on 2026-04-02.

## Current stale review threads

These unresolved review comments still point at deleted sports-sim files and should be resolved as obsolete:

1. `sports-sim/web/src/pages/TuneDashboard.tsx`
2. `sports-sim/pytest.ini`
3. `sports-sim/.github/workflows/ci.yml` for dev dependency installation
4. `sports-sim/.github/workflows/ci.yml` for ignored failures with `|| true`
5. `sports-sim/scripts/Dockerfile.tune_dashboard`
6. `sports-sim/Dockerfile`
7. `sports-sim/tests/test_sim_checkpoint_cache.py` for redundant `asyncio` import
8. `sports-sim/tests/test_sim_checkpoint_cache.py` for duplicate module import path

## GitHub cleanup steps

1. Open PR #2.
2. Resolve each sports-sim review thread as obsolete.
3. Add one maintainer comment explaining that sports-sim was removed and those review threads no longer apply to the current repository direction.
4. Re-check the Files changed tab to confirm the remaining discussion matches the current hub and project-review scope.
5. Prefer replacing PR #2 with smaller follow-up PRs after stale-thread cleanup instead of merging the full historical branch as one unit.

## Suggested maintainer comment

`Sports-sim was removed from this repository after these review comments were created. The unresolved review threads on deleted sports-sim files are obsolete and do not reflect the current branch scope, which is now portfolio-hub coordination work plus project-review artifacts for the tracked local projects.`

## Merge gate after cleanup

- No unresolved sports-sim review threads remain.
- The PR description reflects current scope.
- Merge discussion distinguishes hub planning work from project-review hardening work.
- The current CI failure is understood as unrelated workspace-wide test collection noise, not unresolved sports-sim review feedback.