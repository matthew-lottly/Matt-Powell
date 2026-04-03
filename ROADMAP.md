# Roadmap

This roadmap turns the current portfolio review into the next 40 concrete actions.

How to use it
- `Hub` means work that belongs in this portfolio repository.
- `Standalone` means work that belongs in the matching project repository.
- `GitHub` means repo settings, issue setup, labels, boards, or hosted automation outside the working tree.

Priority now

1. Finalize the portfolio operating docs and keep them current. Scope: Hub. Status: done.
2. Maintain a project matrix with maturity, review artifacts, smoke coverage, and CI state. Scope: Hub. Status: done.
3. Pick the 5 to 7 showcase projects and mark them as the priority lane. Scope: Hub. Status: done.
4. Add a maturity rubric and apply it consistently across the portfolio. Scope: Hub. Status: done.
5. Open issues in the standalone repos for every missing smoke test, runbook, or CI gap. Scope: GitHub and Standalone. Status: ready.
6. Review PR #2 against `main` and split anything that should land separately. Scope: Hub. Status: ready.
7. Remove tracked cache artifacts permanently from affected standalone repos. Scope: Standalone. Status: done.
8. Standardize README ordering across every standalone project. Scope: Standalone. Status: done.
9. Add a root-level changelog note summarizing the recent portfolio hardening pass. Scope: Hub. Status: done.
10. Decide which repos are documentation-first versus CI-enforced. Scope: Hub and GitHub. Status: done.
11. Add a root task runner for common portfolio checks. Scope: Hub. Status: done.
12. Add root issue labels and triage conventions for cross-repo work. Scope: GitHub. Status: ready.

Next

13. Audit every `pyproject.toml` for dependency sprawl and version looseness. Scope: Standalone. Status: done.
14. Tighten Python version support per standalone repo. Scope: Standalone. Status: done.
15. Add CI only where the project is mature enough to justify the maintenance cost. Scope: Standalone and GitHub. Status: done.
16. Add coverage reporting only to showcase repos, not across the whole portfolio. Scope: Standalone and GitHub. Status: ready.
17. Add request and response validation tests to every API repo. Scope: Standalone. Status: done.
18. Add startup, health-check, and failure-path tests to service repos. Scope: Standalone. Status: done.
19. Add environment example files to each service repo. Scope: Standalone. Status: ready.
20. Standardize Docker health checks, ports, and startup docs across service repos. Scope: Standalone. Status: ready.
21. Add rollback guidance to all service runbooks. Scope: Standalone. Status: done.
22. Add sample API requests and expected responses to service review artifacts. Scope: Standalone. Status: done.
23. Add visual review assets for the frontend repos. Scope: Standalone. Status: blocked on capturing assets.
24. Expand frontend smoke tests into browser-level flows. Scope: Standalone. Status: ready.
25. Add accessibility checks for frontend repos. Scope: Standalone. Status: done.
26. Strengthen repo summaries so they explain outcomes, not only ingredients. Scope: Standalone. Status: ready.

Later

27. Add benchmark or comparison tables to the most research-heavy repos. Scope: Standalone. Status: done.
28. Add PR and issue hygiene across the standalone repos, not just the hub. Scope: GitHub. Status: ready.
29. Audit licenses, citations, and publication metadata for public-facing repos. Scope: Standalone. Status: ready.
30. Add a merge checklist for major backlog branches. Scope: Hub. Status: done.
31. Add `ruff` and formatting baselines where they are still missing. Scope: Standalone. Status: done.
32. Add stronger type checking to the most operational repos first. Scope: Standalone. Status: ready.
33. Add portfolio screenshots or GIFs only for showcase projects. Scope: Standalone. Status: blocked on captured media.
34. Add issue templates to each standalone repo as needed. Scope: GitHub and Standalone. Status: ready.
35. Add contributor guides to the standalone repos that are ready for outside collaboration. Scope: Standalone. Status: ready.
36. Add a weekly maintenance checklist for public portfolio upkeep. Scope: Hub. Status: done.
37. Add Dependabot and security scanning only where ongoing maintenance is realistic. Scope: GitHub and Standalone. Status: ready.
38. Add nightly or long-test workflows only to repos with meaningful long-running suites. Scope: Standalone and GitHub. Status: ready.
39. Add deploy guides or Helm manifests only where there is a real deployment target. Scope: Standalone. Status: ready.
40. Re-review the showcase set quarterly and demote low-signal repos from the public front page. Scope: Hub. Status: ready.

Maturity rubric
- `Reviewable`: someone can evaluate the project from README, example output, and docs without running it.
- `Operational prototype`: the project also has runbook-level startup or operational guidance.
- `Showcase candidate`: reviewable, validated, and strong enough to represent the portfolio publicly.

Immediate recommendation
1. Mark the showcase set.
2. Open GitHub issues for the `ready` standalone tasks.
3. Keep this repo focused on portfolio presentation and coordination instead of absorbing project source work.

Showcase priority set
- `spatial-data-api`
- `environmental-monitoring-api`
- `monitoring-data-warehouse`
- `qgis-operations-workbench`
- `open-web-map-operations-dashboard`
- `geoprompt`
- `environmental-monitoring-analytics`