# Publishing Notes

This project is intended to live as a standalone Python package under `projects/causal-lens` and later as its own public repository.

## Release Checklist

1. Run the test suite (`pytest tests/ -v`).
2. Build the package (`python -m build`).
3. Validate distribution metadata (`twine check dist/*`).
4. Tag the release after the package and docs are in sync.
5. Verify CITATION.cff version matches pyproject.toml version.

## Journal Targets

### 1. JORS (Primary Verified Option)

**Journal of Open Research Software** — concise software metapaper describing the software, where to find it, and why it is useful.

**Verified Submission Characteristics:**
- Public software under an open license in a public repository or repository deposit.
- Concise software paper using the journal template.
- Persistent identifier and clear software availability information.
- Concise manuscript rather than a full methods-statistics article.
- APC applies unless waived.

**Why it fits CausalLens:**
- The package already has a strong software-architecture story, clear validation evidence, and public benchmark coverage.
- The current contribution is better framed as reusable research software than as a new statistical method.
- The manuscript can stay focused on implementation, validation, and reuse potential.

**Current Status:**
- [x] Tests exist and pass.
- [x] Installation instructions in README.
- [x] CONTRIBUTING.md present.
- [x] MIT LICENSE present.
- [x] CITATION.cff present and updated.
- [x] Literature review documents the gap.
- [x] CI workflow (GitHub Actions) present.
- [x] Replication scripts present under `replications/`.
- [ ] Standalone public repo with stable release identity.
- [ ] Manuscript draft aligned to JORS software-paper structure.

### 2. JSS (Stretch Option)

**Journal of Statistical Software** — longer software-statistics article with strong replication expectations.

**Verified Submission Characteristics:**
- PDF manuscript in JSS style.
- Source code for the software.
- Replication materials for all manuscript results, preferably a standalone replication script.
- GPL-2, GPL-3, or GPL-compatible software license for the published code path.
- No author fees.

**Why it is harder right now:**
- CausalLens has the code breadth and replication direction, but not yet the full article depth JSS usually rewards.
- The paper would need a more formal estimator-by-estimator exposition, replication bundle, and tighter article narrative.

**Current Status:**
- [ ] Full JSS-style manuscript.
- [ ] JSS-grade replication bundle with expected outputs and article-linked tables.
- [ ] Explicit GPL-compatibility note for the publication path.

### 3. SoftwareX (Candidate Option)

**SoftwareX** remains a plausible fit because the package has a strong reproducibility and engineering story.

**Current note:**
- Direct author-guide retrieval was blocked during this session, so SoftwareX-specific checklist items should be verified manually before committing to that route.
- The manuscript draft started here is still usable as a base for a SoftwareX submission.

## Novelty Thesis

CausalLens is a unified, diagnostics-first Python package integrating causal estimation across six identification strategies — observational adjustment, difference-in-differences (including staggered adoption), instrumental variables, regression discontinuity, and bunching — with a common diagnostic-carrying result-object API and Cinelli-Hazlett omitted-variable bias sensitivity analysis. No existing Python package spans this design space with integrated diagnostics.

This is a software-architecture and workflow claim, not a new-methods claim.

## Pre-Submission Blockers

1. **Standalone public repo.** The package should exist as its own public repository with a stable release identity and clean issue tracker.
2. **Venue-specific manuscript formatting.** Pick the target venue before finalizing references, section headings, and front matter.
3. **Replication packaging.** The current scripts are a good base, but the submission bundle still needs expected outputs and figure/table mapping into the manuscript.
4. **Claim audit.** Keep all prose on the integration/workflow/software-validation axis rather than new-method claims.
