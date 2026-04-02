# GitHub Ops Todo List

These items require GitHub settings, issue management, or automation outside the local working tree.

Now
- Open issues in the correct standalone repos for the gaps listed in `docs/portfolio-matrix.md`.
- Add triage labels for `bug`, `enhancement`, `ci`, `maintenance`, and `showcase`.
- Review whether PR #2 should be split before merge.

Next
- Decide which repos should keep full CI versus lighter validation.
- Add issue templates and PR templates to the standalone repos that are collaboration-ready.
- Add Dependabot and security scanning only where maintenance commitment is realistic.

Later
- Add nightly or long-test workflows only where suites justify them.
- Add project boards or milestones if active collaboration volume warrants them.
- Reassess GitHub automation quarterly rather than enabling everything by default.