# GitHub Ops Todo List

These items require GitHub settings, issue management, or automation outside the local working tree.

Now
- Open issues in the correct standalone repos from `docs/standalone-issue-checklists.md`.
- Use `docs/issue-drafts-showcase.md` first for the seven priority repos, then use `docs/issue-drafts-supporting.md` for the rest.
- Follow `docs/issue-filing-queue.md` so the highest-value issues are opened first.
- Track filing status, owner, and issue URLs in `docs/issue-filing-tracker.md`.
- Use `docs/issue-opening-batches.md` to open issues in manageable waves.
- Use `scripts/show-next-batch.ps1` and `scripts/mark-issue-filed.ps1` during filing sessions.
- Add triage labels for `bug`, `enhancement`, `ci`, `maintenance`, and `showcase`.
- Remaining blockers: `spatial-data-api`, `gulf-coast-inundation-lab`, `arroyo-flood-forecasting-lab`, `station-risk-classification-lab`, and `strata` are not currently accessible as standalone GitHub repos, so their issue filing and repo-level automation cannot be completed yet.

Next
- Decide which repos should keep full CI versus lighter validation.
- Follow `docs/github-automation-policy.md` for the current collaboration-ready template and automation scope.
- Mirror the new templates and automation files from `projects/` into the published standalone repos during the next repo-sync pass.
- Update the tracker immediately after each GitHub filing session so the queue stays trustworthy.

Later
- Add nightly or long-test workflows only where suites justify them.
- Add project boards or milestones if active collaboration volume warrants them.
- Reassess GitHub automation quarterly rather than enabling everything by default.