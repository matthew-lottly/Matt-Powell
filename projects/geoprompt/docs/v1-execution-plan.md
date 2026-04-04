# Geoprompt V1 Execution Plan

## Phase 1: Trust and Contracts (Weeks 1-2)

- Publish guarantees and approximation policy.
- Enforce deterministic ordering and tie-breakers in all ranked outputs.
- Expand regression suites for edge cases and schema compatibility.
- Success criteria:
  - 0 flaky tests across three consecutive CI runs
  - 100% of CLI analysis outputs include manifest metadata

## Phase 2: Performance and Scale (Weeks 3-4)

- Add benchmark regression gates to CI.
- Profile pairwise workflows at 25, 100, 250, and 1k sample scales.
- Optimize high-cost operations with cache reuse and early exits.
- Success criteria:
  - Benchmark gate active in CI
  - No benchmark operation over threshold on baseline dataset

## Phase 3: Interop and Production CLI (Weeks 5-6)

- Add robust batch/pipeline CLI support and resumable artifacts.
- Expand metadata/provenance for all written outputs.
- Improve IO interoperability and strict CRS/unit checks.
- Success criteria:
  - End-to-end CLI pipeline run reproducible from manifest only
  - Roundtrip validation for primary IO formats

## Phase 4: V1 Readiness (Weeks 7-8)

- Freeze stable API surface and mark experimental modules explicitly.
- Prepare migration notes, deprecation window policy, and release checklist.
- Finalize docs around guarantees, troubleshooting, and performance tuning.
- Success criteria:
  - Public v1 checklist complete
  - Release candidate tagged with green CI matrix