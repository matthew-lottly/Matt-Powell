# Publishing Notes

This project is intended to live as a standalone Python package under `projects/causal-lens` and later as its own public repository.

## Release Checklist

1. Run the test suite (`pytest tests/ -v`).
2. Build the package (`python -m build`).
3. Validate distribution metadata (`twine check dist/*`).
4. Tag the release after the package and docs are in sync.
5. Verify CITATION.cff version matches pyproject.toml version.

## Journal Targets

### 1. JOSS (Primary Target)

**Journal of Open Source Software** — short software-paper format (1–2 pages of prose plus auto-generated metadata).

**Pre-Submission Requirements:**
- Public repository with at least 6 months of iterative development history visible in commits/issues/PRs.
- Automated tests (CI via GitHub Actions).
- Clear installation instructions and example usage.
- `CITATION.cff` with correct version, abstract, and keywords.
- Statement of need explaining what gap the software fills.
- Community guidelines (CONTRIBUTING.md).
- License file (MIT is acceptable).
- AI usage disclosure if applicable.

**Current Status:**
- [x] Tests exist and pass.
- [x] Installation instructions in README.
- [x] CONTRIBUTING.md present.
- [x] MIT LICENSE present.
- [x] CITATION.cff present and updated.
- [x] Literature review documents the gap.
- [x] CI workflow (GitHub Actions) — added at `.github/workflows/tests.yml`.
- [x] Replication scripts — `replications/` directory with Lalonde, NHEFS, simulation, and cross-design scripts.
- [ ] Standalone public repo with 6-month history — planned.
- [ ] JOSS paper markdown (`paper.md`) — not yet drafted.

### 2. JSS (Secondary Target)

**Journal of Statistical Software** — longer software-statistics article with replication materials.

**Additional Requirements Beyond JOSS:**
- Full manuscript (typically 20–40 pages) documenting each estimator with examples.
- Replication bundle with scripts, data, and expected outputs.
- Code published alongside the article must use GPL-2, GPL-3, or GPL-compatible license. Current MIT license is compatible but needs verification.
- LaTeX manuscript following JSS style.

**Current Status:**
- [ ] Full manuscript — not started.
- [ ] Replication bundle — scripts exist in `replications/`; need JSS-style packaging with expected outputs.
- [ ] GPL licensing decision — MIT is GPL-compatible but confirm.

### 3. SoftwareX (Backup)

**SoftwareX** — shorter format emphasizing software engineering and reproducibility.

**Status:** Not actively pursued. Viable fallback if JOSS review identifies scope concerns.

## Novelty Thesis

CausalLens is a unified, diagnostics-first Python package integrating causal estimation across six identification strategies — observational adjustment, difference-in-differences (including staggered adoption), instrumental variables, regression discontinuity, and bunching — with a common diagnostic-carrying result-object API and Cinelli-Hazlett omitted-variable bias sensitivity analysis. No existing Python package spans this design space with integrated diagnostics.

This is a software-architecture and workflow claim, not a new-methods claim.

## Pre-Submission Blockers

1. **CI workflow.** Add GitHub Actions running the test suite on push/PR.
2. **Public development history.** Standalone repo must be public with visible iterative development for 6+ months before JOSS submission.
3. **JOSS paper.md.** Draft the short paper with Statement of Need, Summary, and References.
4. **Claim audit.** All markdown files must use integration/workflow language, not priority claims.
