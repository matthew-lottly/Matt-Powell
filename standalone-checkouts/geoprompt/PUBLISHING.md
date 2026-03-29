# Publishing Guide

## Recommended Standalone Repository Name

- geoprompt

## Recommended Description

- Custom Python spatial analysis package with GeoPandas-style frame workflows and reusable GeoPrompt equations.

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
5. Preserve the GitHub Actions workflow in `.github/workflows/geoprompt-ci.yml` so validation follows the package.
6. Reference [docs/architecture.md](docs/architecture.md) and [docs/demo-storyboard.md](docs/demo-storyboard.md) from the README when polishing the public pitch.

## Release Checklist

1. Run `pytest`.
2. Run `geoprompt-demo`.
3. Run `geoprompt-compare`.
4. Run `python -m build`.
5. Run `python -m twine check dist/*`.
6. Review `outputs/geoprompt_comparison_report.json` and confirm all summary flags are `true`.
7. Confirm the PyPI Trusted Publisher is linked to `.github/workflows/publish-pypi.yml` in the `geoprompt` GitHub repository.
8. Push a version tag such as `v0.1.0` to trigger the publish workflow, or run the workflow manually from GitHub Actions.

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

1. Ensure the Trusted Publisher entry in PyPI points at the `matthew-lottly/geoprompt` repository.
2. Set the workflow file to `.github/workflows/publish-pypi.yml`.
3. Leave the environment name empty unless you explicitly add an environment requirement to the workflow.
4. Push a tag such as `v0.1.6`.
5. Watch the `Publish To PyPI` workflow in GitHub Actions.

Example tag commands:

```bash
git tag v0.1.6
git push origin v0.1.6
```

## First Public Polish Pass

- Add richer geometry behavior beyond the current point, line, polygon, dissolve, and first overlay support
- Add dataframe adapters or pandas interop where it helps the API
- Expand the GeoPrompt equation family with more operators once the first API settles
- Add larger real-world benchmark corpora alongside the current checked-in fixtures