# Publishing Notes

This project lives as a standalone Python package under `projects/strata` and as its own public repository.

## Recommended Standalone Repository Name

- strata

## Recommended Description

- Conformal prediction framework for heterogeneous graph neural networks with topology-aware uncertainty quantification on coupled infrastructure systems.

## Suggested Topics

- python
- conformal-prediction
- graph-neural-networks
- uncertainty-quantification
- infrastructure-resilience
- heterogeneous-graphs
- spatial-analysis
- machine-learning

## Split Steps

1. Create a new empty repository named `strata` (done: https://github.com/matthew-lottly/strata).
2. Copy this project folder into the new repository root.
3. Preserve `src/`, `tests/`, `scripts/`, `docs/`, `data/`, `outputs/`, and `pyproject.toml`.
4. Preserve `paper/` and `REFERENCES.md` for the publication draft.
5. Keep the README pointing at the correct repository URL.
6. Reference the JMLR submission folder at `paper/submission_jmlr/` when preparing for publication.

## Release Checklist

1. Run `pytest tests/ -v` and confirm all tests pass.
2. Run the benchmark: `python scripts/run_benchmark.py`.
3. Confirm outputs in `outputs/` are regenerated and consistent.
4. Review `CHANGELOG.md` and verify the release section covers all changes.
5. Build the package: `python -m build`.
6. Validate distribution metadata: `python -m twine check dist/*`.
7. Verify `CITATION.cff` version matches `pyproject.toml` version.
8. Confirm `README.md` and package metadata point at the intended repository path.

## PyPI Commands

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

## Repository URLs

- Monorepo path: `projects/strata` in `matthew-lottly/Matt-Powell`
- Standalone repo: https://github.com/matthew-lottly/strata
- Standalone checkout: `standalone-checkouts/strata/`
