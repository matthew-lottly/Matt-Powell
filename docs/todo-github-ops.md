# GitHub Ops Todo List

These items require GitHub settings, issue management, or automation outside the local working tree.

Now
- Keep `docs/issue-filing-tracker.md` current as new issue waves are added beyond the initial 20.
- Use `scripts/show-next-batch.ps1` and `scripts/mark-issue-filed.ps1` for future filing sessions.
- Review whether the newest standalone repos should keep full CI or a lighter validation path.
- Spot-check Dependabot and CodeQL after their first runs on the newly published repos.

Completed on 2026-04-02
- All 20 initial standalone issues are now filed.
- Baseline triage labels exist across the newly published repos.
- `spatial-data-api`, `gulf-coast-inundation-lab`, `arroyo-flood-forecasting-lab`, `station-risk-classification-lab`, and `strata` are now published as standalone GitHub repos.
- The shared `.github` templates and baseline automation files are present on those newly published repos.

Next
- Decide which repos should keep full CI versus lighter validation.
- Follow `docs/github-automation-policy.md` for the current collaboration-ready template and automation scope.
- Keep future repo-sync passes aligned with the local `projects/` folders so the remotes do not drift.
- Update the tracker immediately after each future GitHub filing session so the queue stays trustworthy.

Later
- Add nightly or long-test workflows only where suites justify them.
- Add project boards or milestones if active collaboration volume warrants them.
- Reassess GitHub automation quarterly rather than enabling everything by default.