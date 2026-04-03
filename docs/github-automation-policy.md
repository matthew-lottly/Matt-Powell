# GitHub Automation Policy

Reviewed on 2026-04-02 after the todo-100 execution pass.

## Collaboration-ready repos

These repos are ready for issue templates and PR templates because they are public-facing, already reviewable, and now have enough docs or CI to support outside feedback without creating avoidable triage noise.

- `spatial-data-api`
- `environmental-monitoring-api`
- `monitoring-data-warehouse`
- `qgis-operations-workbench`
- `open-web-map-operations-dashboard`
- `geoprompt`
- `environmental-monitoring-analytics`

## Template decision

Add issue templates and PR templates to the seven collaboration-ready showcase repos above.

Do not add templates yet to the more experimental supporting repos. Those repos still need more stable scope, cleaner validation expectations, or a clearer outside-contribution story.

## Dependabot decision

The narrower initial plan covered only the most collaboration-ready showcase repos. The current published baseline is broader because the newly published repos inherited the shared `.github` automation bundle during repo sync.

Repos currently carrying Dependabot:

- `spatial-data-api`
- `environmental-monitoring-api`
- `open-web-map-operations-dashboard`
- `geoprompt`
- `environmental-monitoring-analytics`
- `gulf-coast-inundation-lab`
- `arroyo-flood-forecasting-lab`
- `station-risk-classification-lab`
- `strata`

Review this broader baseline quarterly and remove Dependabot from repos where the update volume is not earning its maintenance cost.

## Security scanning decision

The narrower initial plan also expanded during the publish pass for the newly created repos.

Repos currently carrying CodeQL:

- `spatial-data-api`
- `environmental-monitoring-api`
- `open-web-map-operations-dashboard`
- `geoprompt`
- `environmental-monitoring-analytics`
- `gulf-coast-inundation-lab`
- `arroyo-flood-forecasting-lab`
- `station-risk-classification-lab`
- `strata`

Keep reviewing whether the research-heavy repos are producing actionable CodeQL signal or just maintenance noise.

## Label baseline

Create these labels manually in GitHub for the collaboration-ready repos:

- `bug`
- `enhancement`
- `ci`
- `maintenance`
- `showcase`

## PR #2 decision

Do not merge PR #2 as one broad branch after stale-thread cleanup.

Preferred path:

1. Resolve the obsolete sports-sim review threads.
2. Post the maintainer cleanup note.
3. Treat the existing PR as historical context.
4. Replace it with smaller follow-up PRs grouped as `hub coordination` and `project review artifacts`.

That keeps the review discussion aligned with the actual repo direction and avoids carrying stale scope into the merge decision.

## Review cadence

Review templates, Dependabot, and CodeQL quarterly.

Keep automation only where it is still producing actionable signal.

Verified on 2026-04-02:

- the newly published repos have active GitHub Actions runs
- Dependabot update PRs are already appearing on those repos