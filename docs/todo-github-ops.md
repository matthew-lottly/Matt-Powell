# GitHub Ops Todo List

These items require GitHub settings, issue management, or automation outside the local working tree.

Now
- Open issues in the correct standalone repos from `docs/standalone-issue-checklists.md`.
- Use `docs/issue-drafts-showcase.md` first for the seven priority repos, then use `docs/issue-drafts-supporting.md` for the rest.
- Follow `docs/issue-filing-queue.md` so the highest-value issues are opened first.
- Track filed issues in `docs/issue-filing-tracker.md`.
- Add triage labels for `bug`, `enhancement`, `ci`, `maintenance`, and `showcase`.
- Resolve stale PR review threads that still reference deleted sports-sim files.

Next
- Decide which repos should keep full CI versus lighter validation.
- Add issue templates and PR templates to the standalone repos that are collaboration-ready.
- Add Dependabot and security scanning only where maintenance commitment is realistic.

Later
- Add nightly or long-test workflows only where suites justify them.
- Add project boards or milestones if active collaboration volume warrants them.
- Reassess GitHub automation quarterly rather than enabling everything by default.