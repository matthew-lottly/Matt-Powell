# Contributing to 3D-VP-LCP

## Scope

3D-VP-LCP is a research-stage Python framework for 3-D landscape connectivity analysis using LiDAR point clouds. Contributions that improve the core pipeline, add validated extensions, or strengthen test coverage are welcome.

## Setup

```bash
git clone <repo-url>
cd 3d-vp-lcp
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate
pip install -e ".[dev,viz]"
python -m vp_lcp.scripts.generate_sample_data
pytest -q
```

## Pull requests

- Open an issue before starting large changes.
- Keep PRs focused on a single concern.
- Include or update tests for any new functionality.
- Run `ruff check src/ tests/` and `pytest` before submitting.

## Reporting issues

File a GitHub issue with a clear description, expected vs. actual behaviour, and steps to reproduce.
