# Publishing Guide

## Recommended Standalone Repository Name

- geoprompt

## Recommended Description

- Pure-Python spatial analysis toolkit with GeoJSON-native geometries and GeoPandas-style frame workflows.

## Suggested Topics

- python
- gis
- geospatial
- spatial-analysis
- package
- developer-tools

## Split Steps

1. Create a new empty repository named `geoprompt`.
2. Copy this project folder into the new repository root.
3. Preserve `data/`, `src/`, `tests/`, `docs/`, and `pyproject.toml`.
4. Keep the committed pressure plot in `assets/neighborhood-pressure-review-live.png` and regenerate it with `geoprompt-demo` if the package behavior changes.
5. Keep the README image pointing at the raw GitHub URL so the PyPI long description renders the demo image correctly.
6. Preserve the GitHub Actions workflows in `.github/workflows/geoprompt-ci.yml` and `.github/workflows/publish-pypi.yml` so validation and publishing follow the package.
7. Reference [docs/architecture.md](docs/architecture.md) and [docs/demo-storyboard.md](docs/demo-storyboard.md) from the README when polishing the public pitch.

## Release Checklist

1. Run `pytest`.
2. Run `geoprompt-demo`.
3. Run `geoprompt-compare`.
4. Confirm the tool count in `README.md` matches `docs/tool-inventory.json`.
5. Confirm the test count in `README.md`, `docs/tool-methodology.md`, and `docs/tool-inventory.json` matches the current suite result.
6. Review `CHANGELOG.md` and verify the release section covers all new tools and behavior changes.
7. Run optional integration and performance gates locally before release:
	- `GEOPROMPT_RUN_GEO_IO=1 python -m pytest tests/test_geoprompt.py::test_geospatial_integration_parquet_round_trip`
	- `GEOPROMPT_RUN_BENCHMARKS=1 python -m pytest tests/test_benchmark_regression.py`
8. Confirm the `optional-gated` job in `.github/workflows/geoprompt-ci.yml` is passing in GitHub Actions.
9. Run `python -m build`.
10. Run `python -m twine check dist/*`.
11. Review `outputs/geoprompt_comparison_report.json` and confirm all summary flags are `true`.
12. Confirm the PyPI Trusted Publisher is linked to the correct repository and workflow:
	- monorepo: `matthew-lottly/Matt-Powell` with workflow `.github/workflows/publish-pypi.yml`
	- standalone repo: `matthew-lottly/geoprompt` with workflow `.github/workflows/publish-pypi.yml`
13. If the PyPI publisher entry expects an environment, set it to `pypi` so the OIDC claim matches the workflow.
14. Confirm `pyproject.toml` has the intended release version and that `README.md` still uses the raw GitHub image URL.
15. Push a version tag such as `geoprompt-v0.1.7` to trigger the monorepo publish workflow, or run the workflow manually from GitHub Actions.

## PyPI Commands

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

## GitHub Actions Publish Flow

The standalone repository includes `.github/workflows/publish-pypi.yml`.

Use this flow when PyPI Trusted Publishing is connected to GitHub:

1. Ensure the Trusted Publisher entry in PyPI points at the repository that is actually running the workflow.
2. Set the workflow file to `.github/workflows/publish-pypi.yml`.
3. Set the environment name to `pypi` when using the current workflow.
4. Push a tag such as `geoprompt-v0.1.7`.
5. Watch the `Publish To PyPI` workflow in GitHub Actions.

Example tag commands:

```bash
git tag geoprompt-v0.1.7
git push origin geoprompt-v0.1.7
```

## First Public Polish Pass

- Add richer geometry behavior beyond the current point, line, polygon, dissolve, and first overlay support
- Add dataframe adapters or pandas interop where it helps the API
- Expand the GeoPrompt equation family with more operators once the first API settles
- Add larger real-world benchmark corpora alongside the current checked-in fixtures