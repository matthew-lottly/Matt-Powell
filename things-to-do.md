**Additional Tasks (next 50)**
73. Add localization / i18n support
74. Add unit test coverage target and coverage badge
75. Add CI status badge to `README.md`
76. Implement semantic-release or conventional commits enforcement
# Things To Do

Purpose: a single, organized plan for making the project production-ready, reproducible, and delightful to use. Keep this file as the canonical high-level plan; convert items into GitHub issues for tracking and assignment.

How to use
- Triage: create issues for high/medium/low items and add estimates and owners.
- Work in small PRs: land quick wins first (CI, lint, docs) to increase contributor confidence.
- Track progress: update this document when major areas change and reference issue numbers.

Top priority (first PRs)
- CI & tests: add a GitHub Actions workflow that runs `pytest`, `ruff`/`black`, and `pyright`.
- Fix immediate test failures: run test suite, open issues for failing tests, and fix high-impact failures.
- Pre-commit & formatting: add `.pre-commit-config.yaml` with `ruff`, `black`, and `isort` and run formatting.
- Minimal Docker dev image: provide a reproducible dev environment for contributors.
- Examples & quick demo: ensure `examples/quick_demo.py` runs and produces a visible artifact.

Organized work areas (grouped tasks and next steps)

1) CI, Testing & Quality
- Add `pytest` workflows and smoke tests; add coverage reporting and badge.
- Add `pyright` type checks to CI and fix high-priority type issues.
- Add fuzz testing (`hypothesis`), flakiness tracking, and retry logic for flaky tests.
- Run mutation testing on critical modules to improve test quality (optional, high effort).

2) Developer Experience
- Add `pre-commit` hooks, `ruff`/`black` config, and CI linting; add CI status badges to `README.md`.
- Add contributor onboarding (`CONTRIBUTOR_ONBOARDING.md`) and PR templates.
- Add `CODEOWNERS` for core areas and create `good first issue` examples.

3) Simulation & Sports Engine
- Design a modular sport plugin interface (rules, physics, scoring).
- Build a scenario/presets library (YAML/JSON) and a CLI to run presets.
- Implement baseline scripted agents and a training harness for ML agents.
- Add replay trace format, export, and replay/analysis tools.

Realism & Fidelity Improvements (make simulations match the real world)
- Player physiology and fatigue: model stamina, fatigue accumulation, recovery, and variable performance under fatigue; expose parameters and record telemetry.
- Skill distributions and variability: sample per-player skill profiles from real-world distributions; allow time-varying skill (form, slumps).
- Injury model: probabilistic injury events dependent on load, collisions, fatigue, and field conditions, with recovery timelines.
- Biomechanics constraints: impose realistic movement limits (max speed, acceleration, turning radius) and energy costs per action.
- Perception and reaction delays: add sensory latency, decision delays, and error rates for players and agents.
- Decision noise and bounded rationality: model suboptimal decisions, heuristics, and stochastic choice behavior.
- Environmental effects: model weather, wind, temperature, surface friction, and how they affect ball/actor physics and injury risk.
- Ball/object physics fidelity: improve collision physics, spin, bounce variability, and surface interactions (e.g., wet field).
- Sensor/camera occlusion and noise: simulate partial observability, occlusions, and noisy sensors for agents and replay visuals.
- Referee/umpire behavior: add probabilistic officiating errors, penalty biases, and VAR/review systems where applicable.
- Crowd and home advantage: simulate crowd noise effects on decisions, referee bias, and home travel fatigue effects.
- Tactical formations and team strategies: implement common tactic templates and allow AI to learn/adapt tactics mid-game.
- Substitution and roster rules: enforce substitution windows, timeouts, and manage bench fatigue and strategy.
- Scheduling and travel effects: model travel fatigue, timezone shifts, and congested schedules affecting performance.
- Warm-up and pre-game state: simulate different pre-game prep and their impact on early-game performance and injury risk.
- Equipment variability: model differences in boots, balls, protective gear affecting performance and injury.
- Real-world statistical calibration: fit simulation parameters to real historical distributions (scores, possession, event rates).
- Parameter estimation pipelines: add scripts to estimate parameters from real match logs and telemetry.
- Multi-level stochasticity: add shot/attempt outcome noise at event-level plus longer-term season-level variability.
- Player psychology & momentum: model confidence, morale, and momentum effects after events (scoring, mistakes).
- Team chemistry and lineup effects: model pairwise player interactions, compatibility scores, and cohesion over time.
- Training and skill progression: simulate training sessions, skill learning curves, and long-term development.
- Tactical miscommunication and errors: include mis-passes, misreads, and failed coordinated actions with tunable rates.
- Latent variable modeling & uncertainty: track and expose uncertainty in state estimates and agent beliefs.
- Domain randomization for robustness: randomize environment and perception during training to generalize agents.
- Replay fidelity: include timestamped, high-resolution traces and ability to attach sensor noise and visualization layers.
- Validation harness: assemble real-match benchmarks and unit tests that assert simulation statistics match targets within tolerance.
- Adversarial scenario generation: auto-generate edge-case scenarios to test fragility (e.g., all players congested, extreme weather).
- Ensemble simulation and confidence intervals: run batched Monte Carlo sims and report outcome distributions and CIs.
- Partial observability modes: support full-observation, partial, and replay-only modes for different experiments.
- Human-in-the-loop calibration UI: expose sliders and tools for domain experts to tune realism parameters interactively.
- Explainability hooks: log decision features and rationales for key events to analyze model behavior.
- Performance vs fidelity modes: provide fast, medium, and high-fidelity simulation modes to trade speed vs realism.
- Dataset augmentation & synthetic generation: export synthetic labeled data for training perception models (e.g., tracking).
- Regulatory/rule variants: support league- or tournament-specific rules and experimental rule sets for A/B testing.
- Measurement noise models: add probabilistic noise to recorded metrics (timing, coordinates) to mimic measurement errors.

Implementation notes:
- Prioritize features by ROI: start with player fatigue, skill distributions, and ball physics, then add perception and referee behavior.
- Use real-world logs (if available) to fit and validate distributions; bootstrap with literature values when data is missing.
- Keep parameters configurable and instrumented so experiments can record which realism settings were used.
- Add unit tests and statistical checks to prevent regressions in the simulated distributions.

4) UI/UX & Frontend
- Scaffold `web/` (React + Vite) and add a minimal demo page that plays a recorded trace.
- Design wireframes for core flows: create scenario, run, watch replay, analyze results.
- Add accessibility, keyboard navigation, theming, and mobile responsiveness.
- Add Storybook, unit tests for components, and visual regression tests.

5) Data, Experiments & Reproducibility
- Add small example datasets and `DATA_README.md` describing schema and provenance.
- Add reproducible experiment runner, seed control, and model serialization/versioning.
- Add experiment tracking (MLflow) and data versioning guidance (DVC/git-lfs).

6) Observability & Operations
- Instrument services with Prometheus metrics and expose `/metrics`.
- Add Grafana dashboard templates and basic alerting for benchmarks and regressions.
- Integrate optional error reporting (Sentry) and structured JSON logging.

7) Security, Licensing & Compliance
- Enable Dependabot, add `bandit` static analysis in CI, and run `safety` scans.
- Add container scanning (Trivy) to CI and license compliance checks.
- Draft privacy policy and telemetry opt-in/out documentation for demos.

8) Packaging, Releases & Deployment
- Verify `pyproject.toml`, add build/release workflow, and enable automated changelog generation.
- Provide Docker manifests, Helm/Kubernetes examples, and a simple demo deployment script.

9) Community & Roadmap
- Create `ROADMAP.md` with milestones, owners, and rough dates.
- Create a GitHub Project board and issue templates; categorize backlog into Releases.
- Schedule a public demo and collect feedback; maintain weekly maintenance checklist.

Next immediate actions (recommended)
1. Add `.github/workflows/ci.yml` with `pytest`, `ruff`/`black`, and `pyright` (minimal configuration).
2. Add `.pre-commit-config.yaml` and run formatters across the repo.
3. Ensure `examples/quick_demo.py` runs and add a test that executes it in CI.

Reference: this plan was generated after scanning the repo on 2026-03-29 and consolidating discovered TODOs and review notes. Convert items to issues and assign owners to begin execution.

- **Accessibility & responsiveness**: ensure keyboard navigation, ARIA labels, screen-reader compatibility, and mobile-friendly layouts.
- **Onboarding & tutorials**: interactive walkthroughs and sample scenarios to demonstrate realistic behavior.
- **E2E testing**: add Playwright/Cypress flows that exercise the UI across common tasks.

**Next Steps (short)**
1. Create GitHub issues for each high-priority item (CI, tests, linting, docs).  
2. Add a minimal GitHub Actions workflow that runs `pytest`, `ruff`/`black`, and `pyright`.  
3. Convert one notebook tutorial into a runnable script and confirm in CI.  

---
_Generated by repository scan on 2026-03-29. For a deeper audit, run `rg TODO|FIXME` locally and review subproject review documents._

**Expanded Task List (50 more actionable items)**
**Expanded details (actionable next steps for each task)**
1. Scan codebase for existing TODOs and issues: run `rg TODO|FIXME` across repo, compile results, and link to issues.
2. Create `things-to-do.md` with prioritized tasks: maintain this file and commit changes for transparency.
3. Prioritize tasks and open issues for tracking: convert top-priority items into GitHub issues with labels and estimates.
4. Implement quick wins: CI, tests, linting, formatting: scaffold minimal CI workflow and fix immediate lint/type errors.
5. Improve docs, examples, and tutorials: audit `README.md`, `examples/`, and notebooks; ensure runnable examples.
6. Set up packaging, releases, and dependency management: verify `pyproject.toml`, add `build`/`twine` steps and release workflow.
7. Add performance profiling and benchmarks: add `benchmarks/`, microbenchmarks, and a CI benchmark job.
8. Plan data & reproducibility (datasets, seeds, Docker): list datasets, add seed control, and publish reproducible Docker image.
9. Audit security and dependencies: run `safety`, `bandit`, and enable Dependabot; triage results.
10. Create roadmap + milestones for major features: produce a roadmap.md with milestones, owners, and rough timelines.
11. Design per-sport simulation modules (rules, physics, parameters): define interface and example implementation for one sport.
12. Build scenario library and presets for each sport: create YAML/JSON presets for common game states and edge cases.
13. UI/UX: wireframes & interaction flows: sketch flows for scenario creation, playback, and analysis; collect feedback.
14. Frontend: responsive UI, accessibility, theming: choose stack, theming tokens, and baseline accessibility checks.
15. Visualization: realtime playback, charts, and heatmaps: prototype playback canvas and timeline controls.
16. Agent/AI players: baseline bots and training harness: implement scripted agents and a simple RL training loop harness.
17. Replay recording, export, and analytics tools: define trace format, exporter, and small analytics CLI.
18. Config and tuning UI (difficulty, realism sliders): implement a control panel component for runtime parameter changes.
19. Telemetry, logging, metrics, and monitoring: pick metrics library, instrument key components, and add dashboards.
20. End-to-end tests for UI and API: add Playwright/Cypress tests that exercise main flows end-to-end.
21. Cross-project coordination: monorepo split decision: document pros/cons and propose split criteria.
22. Create issue templates and a project board: add `.github/ISSUE_TEMPLATE` and a GitHub Project board with columns.
23. Create issue templates for bug/feature/CI: write concise templates with reproduction steps and expected outcomes.
24. Setup GitHub project board: create board, add top-priority issues, and invite maintainers.
25. Add pre-commit hooks configuration: add `.pre-commit-config.yaml` with `ruff`, `black`, and `isort` hooks.
26. Add `ruff`/`black` config and formatting checks: add configs and run formatters across the codebase.
27. Add `pyright` type-check configuration in CI: enable pyright job and fix initial type errors incrementally.
28. Add a `pytest` CI workflow with smoke tests: create GitHub Action that runs tests on push/PR and reports failures.
29. Triage and fix failing tests in `tests/`: run test suite locally, open issues for failing tests, and fix regressions.
30. Add unit tests for core modules under `src/`: aim for testable small functions and add fixtures for mocks.
31. Add integration test harness and CI job: build integration fixtures and a CI job to run longer tests nightly.
32. Create a lightweight Docker development image: base on Python slim, install dev deps, and document usage.
33. Add `docker-compose` for local service orchestration: provide compose with API, Redis, and optional DB for development.
34. Provide a small example dataset with README: include minimal CSV/JSON to run quick demos and tests.
35. Implement reusable data loader utilities: centralize parsing/validation and provide caching options.
36. Document data schema, provenance, and licenses: add `DATA_README.md` describing fields, sources, and licensing.
37. Implement config management with TOML/YAML presets: central `Config` loader with environment overrides.
38. Standardize logging format and examples: adopt structured logging format and include examples in README.
39. Add structured JSON logging support: use `python-json-logger` or similar and expose env var to toggle.
40. Add a metrics endpoint for services (Prometheus): instrument app and expose `/metrics`.
41. Add Prometheus metrics + basic dashboards: add recording rules and example Grafana dashboards.
42. Provide Grafana dashboard templates for core metrics: export JSON dashboards into `ops/grafana/`.
43. Integrate error reporting (Sentry or equivalent): add optional Sentry integration with DSN env var.
44. Add benchmark scripts and a CI benchmark job: store baseline numbers and fail if regressions exceed threshold.
45. Add profiling examples and a profiling guide: include `profiling.md` showing `pyinstrument` or `cProfile` usage.
46. Profile and optimize identified hotspots: run profilers, add micro-optimizations, and document changes.
47. Add caching (Redis) for heavy computations: abstract cache layer and provide config for TTLs.
48. Add model serialization and versioning strategy: use versioned artifacts, e.g., `models/v1/...` with manifest files.
49. Create model evaluation and metrics suite: define metrics, implement evaluation runner, and store results.
50. Add reproducible experiment runner (scripts): CLI to run experiments with fixed seeds and save artifacts.
51. Add experiment logging (MLflow or similar): log parameters, artifacts, and metrics to an experiment tracking server.
52. Add data versioning (DVC or git-lfs): choose approach and add minimal config for large file handling.
53. Add a CLI entrypoint with subcommands (`click`): provide `simulate`, `train`, `evaluate`, and `export` subcommands.
54. Support config-driven runs and presets: allow running by preset name or config file path.
55. Add user preferences storage and persistence: persist UI preferences in localStorage or server-side profiles.
56. Add API authentication (OAuth/JWT): secure endpoints and provide token-based auth for API clients.
57. Add authorization and permissions tests: define roles and write tests to validate access controls.
58. Add rate limiting and throttling for API: protect endpoints with per-IP or per-key rate limits.
59. Add OpenAPI (Swagger) docs for endpoints: auto-generate and publish docs for the API surface.
60. Create a client SDK for the API: auto-generate or hand-author a lightweight Python client.
61. Scaffold a frontend app (React + Vite): create `web/` directory, initialize Vite, and add basic routes.
62. Implement responsive UI and theming in frontend: add CSS variables, dark/light themes, and responsive breakpoints.
63. Conduct an accessibility audit and fixes: run `axe` and fix high-severity accessibility issues.
64. Add keyboard shortcuts and power-user flows: implement common shortcuts and allow customization.
65. Improve visualization: animated playback & overlays: implement performant canvas/SVG playback and overlay layers.
66. Add export formats (CSV/JSON) for results and traces: provide exporter CLI and frontend export buttons.
67. Add replay sharing and permalink/export URL support: store trace artifacts and serve permalinks for sharing.
68. Convert key notebooks into runnable scripts: create `scripts/` versions and add tests to validate outputs.
69. Produce short tutorial GIFs and walkthrough videos: record core flows and store in `docs/media/`.
70. Add contributor guide, PR templates, and labels: include `CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md`.
71. Add a `CODEOWNERS` file for critical paths: specify owners for `src/`, `dashboard/`, and CI.
72. Add automated changelog generation and release workflow: configure `release-drafter` or `semantic-release`.
73. Add localization / i18n support: internationalize strings and add gettext or i18next integration.
74. Add unit test coverage target and coverage badge: set target (e.g., 80%) and add badge to `README.md`.
75. Add CI status badge to `README.md`: add status images for CI workflows and coverage.
76. Implement semantic-release or conventional commits enforcement: enforce commit message conventions via CI.
77. Add static security analysis (bandit) to CI: run Bandit and fail on critical issues.
78. Enable Dependabot or scheduled dependency update workflow: configure for major/minor/patch updates.
79. Implement test flakiness tracking and reruns: track flaky tests and enable limited reruns in CI.
80. Add fuzz testing for parsers and config loaders: use `hypothesis` to fuzz config parsing code.
81. Run mutation testing for critical modules: use `mutmut`/`cosmic-ray` to evaluate test quality.
82. Add feature flags / toggle system: implement simple flags with rollout controls for experiments.
83. Design plugin architecture for sport modules: define plugin discovery (entry points) and isolation rules.
84. Create SDK examples for Python and JavaScript: publish short examples demonstrating common tasks.
85. Add WebSocket API for realtime simulation updates: implement channels and broadcast strategy.
86. Add mobile-responsive demo page: craft a demo page optimized for phone-sized screens.
87. Implement offline playback and caching support: cache traces for offline playback in browser or app.
88. Add curated sample datasets for multiple sports: gather representative samples and document usage.
89. Add connectors for CSV/JSON/API data ingestion: provide easy adapters and docs for common formats.
90. Add database migrations and migration docs: introduce `alembic`/`django-migrations` and add docs.
91. Implement data sanitization and validation routines: central validators and schema checks (pydantic).
92. Document telemetry opt-in/out and privacy settings: clarify what is collected and how to opt-out.
93. Add a privacy policy template and guidance: draft a privacy policy for demos and hosted services.
94. Add scheduled nightly CI runs for long tests: configure a cron job for long-running integration tests.
95. Pin dependencies for reproducible builds: use lockfiles and record exact versions for deployments.
96. Add container image scanning (Trivy) to CI: scan built images and fail on critical vulnerabilities.
97. Add license compliance checks and scanning: ensure third-party licenses are compatible and documented.
98. Implement API rate-limiting test cases: write tests that exercise throttling and fallback behavior.
99. Add load testing scripts (Locust) and jobs: create locustfiles and CI jobs for smoke load tests.
100. Draft high-availability deployment guide: recommend multi-AZ deployments, autoscaling, and backups.
101. Add Kubernetes manifests or Helm charts: provide example manifests for deployments and services.
102. Add cloud staging deployment in CI: create a workflow to deploy to a staging environment after merge.
103. Configure docs hosting (GitHub Pages or ReadTheDocs): publish Sphinx/mkdocs site from `docs/`.
104. Create a one-shot demo deployment script: script that builds and deploys a demo to cloud provider.
105. Add performance regression tests and alerts: compare benchmarks and open issues for regressions.
106. Experiment with GPU acceleration for heavy tasks: prototype faster compute paths using CUDA/Numba.
107. Add unit tests for frontend components: use Jest/React Testing Library to assert component behavior.
108. Add Storybook for UI component previews: scaffold Storybook and document components and states.
109. Create a design system with tokens and components: centralize color, spacing, and typography tokens.
110. Add frontend linting (`eslint`, `stylelint`) in CI: add configs and fail CI on lint errors.
111. Add accessibility unit tests (axe) to CI: integrate `jest-axe` or Playwright accessibility checks.
112. Implement keyboard-only interaction flows: ensure all main flows can be used without a mouse.
113. Add visual regression tests for UI (Percy/Chromatic): capture baseline screenshots and assert no regressions.
114. Add a user feedback collection flow in-app: simple modal or feedback form that stores responses.
115. Create a roadmap file with milestones and rough dates: add `ROADMAP.md` and assign owners.
116. Create a weekly maintenance checklist for repo owners: include dependency updates, triage, and PR reviews.
117. Add a `CONTRIBUTOR_ONBOARDING.md` with setup steps: step-by-step dev setup and common troubleshooting.
118. Host a public demo session to gather user feedback: record a live demo and capture attendee feedback.
119. Add benchmarking dashboards for CI results: upload benchmark artifacts and render dashboards from CI data.
120. Schedule automated dependency upgrade runs: ensure updates are batched and tested before merge.
121. Add automated issue triage (bots) to label/prioritize: use Probot or actions to auto-label new issues.
122. Create `good first issue` examples and label: craft small, well-scoped tasks with setup and acceptance criteria.
