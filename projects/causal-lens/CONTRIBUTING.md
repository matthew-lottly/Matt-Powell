# Contributing to CausalLens

Thank you for your interest in contributing to CausalLens.

## Getting Started

1. Fork this repository and clone your fork.
2. Create a virtual environment and install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

3. Run tests to verify your setup:

```bash
pytest tests/ -v
```

## Development Workflow

1. Create a branch for your change: `git checkout -b feature/my-change`
2. Make your edits. Keep changes focused on a single concern.
3. Add or update tests for any new or changed functionality.
4. Run `pytest tests/ -v` and ensure all tests pass.
5. Commit with a descriptive message and open a pull request.

## What We Welcome

- Bug fixes with a test that reproduces the issue.
- New estimators or diagnostics with tests and documentation.
- Benchmark additions on publicly available causal inference datasets.
- Documentation improvements and typo fixes.

## Code Style

- Type annotations on all public function signatures.
- Keep dependencies minimal — new external packages need justification.
- Follow the existing module structure: estimators in `estimators.py`, diagnostics in `diagnostics.py`, result dataclasses in `results.py`.

## Reporting Issues

Open a GitHub issue with:
- A minimal reproducible example.
- Expected vs actual behavior.
- Python version and OS.

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
