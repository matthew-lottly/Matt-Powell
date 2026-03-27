# STRATA — Work Items Backlog

20 prioritized tasks for completing the project toward publication-ready status.

---

## Critical Path (Paper Blockers)

### 1. Fix CQR output path bug in benchmark script
The `run_benchmark.py` saves `cqr_quantile_losses_seed{n}.json` to a relative path, but background terminals start in `D:\GitHub` not the project dir. Need to use absolute paths or `os.path.dirname(__file__)` to resolve output directory.
**Status:** Not started | **Effort:** Small

### 2. Run real-data benchmark (ACTIVSg200)
Create a separate benchmark script (or extend `run_benchmark.py`) that runs all 9 calibrators on the real ACTIVSg200 graph across 20 seeds. Currently only validated with single-seed pipeline test. Need full comparison table for the paper's Section 5.6.
**Status:** Not started | **Effort:** Medium

### 3. Fill in paper results placeholders
The rough draft in `paper/strata-paper.md` has `[TABLE: Insert ...]` and `[FIGURE: Insert ...]` placeholders. After benchmarks complete, insert actual numbers, compile key result tables, and reference generated PNGs.
**Status:** Blocked on benchmarks | **Effort:** Medium

### 4. Generate publication-quality figures
Current benchmark PNGs use matplotlib defaults. Need: consistent color palette, proper axis labels with units, legend placement, font size appropriate for two-column format, vector PDF output for camera-ready submission.
**Status:** Not started | **Effort:** Medium

### 5. Improve telecom coverage on real data
Telecom coverage was 0.85 on ACTIVSg200 (below 0.90 target). Investigate whether `floor_sigma`, `LearnableLambda`, or `AttentionCalibrator` can close this gap. If not, document as a known limitation.
**Status:** Not started | **Effort:** Medium

---

## Code Quality & Robustness

### 6. Add larger graph stress tests
Current tests use default config (~450 nodes). Add tests with 1000+ nodes to verify scaling behavior and catch memory/performance issues before paper benchmarks on larger datasets.
**Status:** Not started | **Effort:** Small

### 7. Add type annotations throughout codebase
Several modules (conformal.py, experiment.py, advanced_calibrators.py) use untyped function signatures. Add proper type hints for all public APIs to improve readability for reviewers checking the repo.
**Status:** Not started | **Effort:** Medium

### 8. Profile and optimize hot paths
The 20-seed benchmark takes significant time on CPU. Profile `train_model()` and `calibrate_with_propagation()` to identify optimization opportunities (e.g., vectorized neighbor aggregation instead of loops).
**Status:** Not started | **Effort:** Medium

### 9. Add integration test for full benchmark pipeline
Create a test that runs a mini version of `run_benchmark.py` (2 seeds, saving to a temp dir) to catch output-path bugs and format issues before full runs.
**Status:** Not started | **Effort:** Small

### 10. Validate conformal guarantees formally
Add a dedicated test suite that checks coverage guarantees hold across 100+ seeds for each calibrator, with statistical tests that the empirical coverage rate is consistent with the theoretical bound.
**Status:** Not started | **Effort:** Medium

---

## Dataset & Evaluation

### 11. Source a real multi-utility dataset
ACTIVSg200 has real power data but synthetic water/telecom layers. Research available multi-utility infrastructure datasets (e.g., OpenStreetMap utilities, EPANET water networks, FCC telecom data) to build a truly heterogeneous real-world benchmark.
**Status:** Not started | **Effort:** Large

### 12. Add IEEE 118-bus and 300-bus test cases
Expand real data support beyond ACTIVSg200. The MATPOWER parser already handles the format — add `load_ieee118()` and `load_ieee300()` for multi-dataset evaluation.
**Status:** Not started | **Effort:** Small

### 13. Ablation study: number of GNN layers
The paper claims 3 layers is optimal but doesn't prove it. Run ablation with 1, 2, 3, 4, 5 layers across 20 seeds, measuring coverage and width. Reference Li et al. [64] oversmoothing analysis.
**Status:** Not started | **Effort:** Medium

### 14. Ablation study: feature dimensionality
Test with feature_dim ∈ {4, 8, 16, 32} to characterize sensitivity to input representation richness.
**Status:** Not started | **Effort:** Small

---

## Paper Completion

### 15. Write supplementary materials
Create a supplementary document with: all benchmark tables, per-seed results, diagnostic report outputs, hyperparameter sensitivity details, and proof sketches for coverage guarantees.
**Status:** Not started | **Effort:** Large

### 16. Create BibTeX file from REFERENCES.md
Convert the 66 references in `REFERENCES.md` to a proper `references.bib` BibTeX file for LaTeX/Overleaf compilation.
**Status:** Not started | **Effort:** Small

### 17. Convert paper draft to LaTeX
Transfer `paper/strata-paper.md` to a LaTeX template (e.g., NeurIPS, AAAI, or IEEE format) with proper typesetting, equation numbering, and figure/table floats.
**Status:** Not started | **Effort:** Medium

### 18. Write reproducibility appendix
Document exact environment (Python version, package versions, hardware specs), random seed list, runtime measurements, and instructions for reproducing all results from scratch.
**Status:** Not started | **Effort:** Small

---

## Infrastructure & Release

### 19. Set up CI/CD pipeline
Add GitHub Actions workflow: run all 73 tests on push, lint with ruff/flake8, type-check with pyright. Ensure repo stays green before paper submission.
**Status:** Not started | **Effort:** Medium

### 20. Prepare public release
Clean up README.md for the `strata` GitHub repo: add installation instructions, quick-start example, badge links, and citation block (once paper is submitted). Ensure all outputs/ and paper/ remain gitignored until publication.
**Status:** Not started | **Effort:** Medium
