# Portfolio Todo 100

This is the expanded 100-item backlog for the Matt Powell portfolio hub and the linked standalone repositories.

How to use it
- `Hub` items belong in this repository.
- `Standalone` items belong in the matching project repository.
- `GitHub` items belong in repository settings, issues, labels, PR cleanup, or hosted automation.
- Items marked with ~~strikethrough~~ have been completed.

## Hub

1. ~~Keep `README.md`, `things-to-do.md`, `ROADMAP.md`, and `docs/portfolio-matrix.md` aligned.~~
2. Re-review the featured repository list for ordering and public impact.
3. Tighten the root profile summary so it stays outcome-focused.
4. Keep the showcase-priority section current with the strongest seven repositories.
5. Add a short note when a repo enters or leaves the showcase set.
6. ~~Refresh the portfolio matrix after every major project improvement pass.~~
7. Add a clearer maturity note when a repo moves from reviewable to operational prototype.
8. ~~Keep `docs/todo-hub.md`, `docs/todo-showcase.md`, `docs/todo-standalone-repos.md`, and `docs/todo-github-ops.md` synchronized.~~
9. Periodically trim planning docs that are no longer earning their place in the root README.
10. ~~Keep `CHANGELOG.md` current for major portfolio-level coordination changes.~~
11. Revisit whether the quick access list should be shorter and more opinionated.
12. Add a hub-level note for repositories that are intentionally documentation-first.
13. Add a hub-level note for repositories that justify heavier CI investment.
14. ~~Review whether every local planning doc still reflects the current portfolio direction.~~
15. Add a small release-history section for portfolio showcase changes.
16. Keep the contributor onboarding doc aligned with current repo workflow.
17. Tighten merge guidance for future broad cleanup branches.
18. Add a recurring process to review the public front page quarterly.
19. ~~Re-check the portfolio matrix against the local workspace after major repo additions or removals.~~
20. Keep the issue submission pack aligned with the issue tracker.

## Showcase Repos

21. ~~Add richer request and response examples to `spatial-data-api`.~~
22. ~~Add rollback guidance to `spatial-data-api`.~~
23. ~~Add invalid-query tests to `spatial-data-api`.~~
24. ~~Add richer payload examples to `environmental-monitoring-api`.~~
25. ~~Add startup and health-check validation to `environmental-monitoring-api`.~~
26. ~~Add rollback notes to `environmental-monitoring-api`.~~
27. ~~Add a schema walkthrough artifact to `monitoring-data-warehouse`.~~
28. ~~Tighten the README narrative in `monitoring-data-warehouse`.~~
29. Audit tracked generated artifacts in `monitoring-data-warehouse`.
30. Add screenshots for `qgis-operations-workbench`.
31. ~~Add an analyst workflow note to `qgis-operations-workbench`.~~
32. ~~Add packaging guidance in `qgis-operations-workbench`.~~
33. Add screenshots or a GIF for `open-web-map-operations-dashboard`.
34. Add browser-level interaction tests to `open-web-map-operations-dashboard`.
35. ~~Add accessibility checks to `open-web-map-operations-dashboard`.~~
36. ~~Align CI with current package expectations in `geoprompt`.~~
37. Tighten public package framing in `geoprompt`.
38. ~~Audit dependency looseness in `geoprompt`.~~
39. ~~Tighten packaging guidance in `environmental-monitoring-analytics`.~~
40. Improve report-audience framing in `environmental-monitoring-analytics`.

## Supporting Repos

41. ~~Add CI to `causal-lens`.~~
42. Tighten benchmark framing in `causal-lens`.
43. Add screenshots or a GIF to `experience-builder-station-brief-widget`.
44. Add browser-level tests to `experience-builder-station-brief-widget`.
45. ~~Add accessibility checks to `experience-builder-station-brief-widget`.~~
46. ~~Add rollback guidance to `postgis-service-blueprint`.~~
47. ~~Add deployment-oriented examples to `postgis-service-blueprint`.~~
48. Add main-path smoke coverage to `gulf-coast-inundation-lab`.
49. ~~Improve evaluation artifact clarity in `gulf-coast-inundation-lab`.~~
50. ~~Add benchmark context to `monitoring-anomaly-detection`.~~
51. Tighten model-evaluation framing in `monitoring-anomaly-detection`.
52. ~~Add benchmark tables to `environmental-time-series-lab`.~~
53. Tighten evaluation framing in `environmental-time-series-lab`.
54. ~~Add benchmark summaries to `arroyo-flood-forecasting-lab`.~~
55. Tighten README outcome framing in `arroyo-flood-forecasting-lab`.
56. ~~Add benchmark evidence to `raster-monitoring-pipeline`.~~
57. Tighten evaluation narrative in `raster-monitoring-pipeline`.
58. ~~Add clearer holdout metrics to `station-forecasting-workbench`.~~
59. Strengthen selection narrative in `station-forecasting-workbench`.
60. ~~Add classification evaluation evidence to `station-risk-classification-lab`.~~
61. Tighten explainability framing in `station-risk-classification-lab`.
62. ~~Add clearer deployment guidance to `strata`.~~
63. Tighten uncertainty-story framing in `strata`.
64. ~~Add deployment assumptions to `tsuan`.~~
65. Tighten benchmark framing in `tsuan`.

## Cross-Repo Engineering

66. ~~Remove tracked cache artifacts from any remaining standalone repositories.~~
67. ~~Standardize README ordering across the full project set.~~
68. Normalize maturity wording across all standalone READMEs.
69. ~~Audit every `pyproject.toml` for dependency sprawl.~~
70. ~~Tighten Python version support declarations where they are too loose.~~
71. Add CI only where maintenance value exceeds maintenance cost.
72. Add coverage reporting only to showcase repos that justify it.
73. ~~Add request and response validation tests across API repos.~~
74. ~~Add startup, health-check, and failure-path tests across service repos.~~
75. ~~Add environment example files to service repos.~~
76. Standardize Docker health checks, ports, and startup docs across service repos.
77. ~~Add rollback guidance to all service runbooks.~~
78. ~~Add sample requests and expected responses to service review artifacts.~~
79. ~~Add benchmark or comparison tables to research-heavy repos.~~
80. ~~Add `ruff` and formatting baselines where missing.~~
81. Add stronger type checking to the most operational repos first.
82. Add contributor guides to standalone repos that are ready for outside collaboration.
83. Audit licenses, citations, and publication metadata in public-facing repos.
84. ~~Add deploy guides only where a real deployment target exists.~~
85. Revisit whether each repo should stay documentation-first or move toward heavier validation.

## GitHub Ops

> Items 86-100 require GitHub write access (issue creation, label management, PR comments). These must be completed via the GitHub web UI or CLI.

86. Open the first 20 standalone issues from the existing submission pack.
87. Update `docs/issue-filing-tracker.md` with real URLs as issues are opened.
88. Use `scripts/mark-issue-filed.ps1` after each filing session.
89. Keep `docs/issue-opening-batches.md` aligned with the tracker and submission files.
90. Add triage labels to repositories that are missing `bug`, `enhancement`, `ci`, `maintenance`, and `showcase`.
91. ~~Decide which standalone repos need issue templates and PR templates.~~
92. ~~Add issue templates to collaboration-ready standalone repos.~~
93. ~~Add PR templates to collaboration-ready standalone repos.~~
94. ~~Add Dependabot only where maintenance commitment is realistic.~~
95. ~~Add security scanning only where false-positive and upkeep cost are acceptable.~~
96. Resolve the stale sports-sim threads on PR #2.
97. Post the PR #2 maintainer closeout comment.
98. ~~Decide whether PR #2 should merge as-is or be replaced with smaller follow-up PRs.~~
99. Re-check the active PR discussion after stale-thread cleanup so it matches current scope.
100. ~~Review GitHub automation quarterly instead of enabling everything by default.~~