# Contributing to STRATA

Thank you for your interest in contributing to STRATA.

## Development Setup

```bash
git clone https://github.com/matthew-lottly/strata.git
cd strata
pip install -e ".[dev]"
pytest tests/ -v
```

## Running Tests

```bash
pytest tests/ -v
```

## Running the Benchmark

```bash
python scripts/run_benchmark.py
```

## Code Style

- Follow PEP 8 conventions.
- Use type annotations for public API functions.
- Keep modules focused: one responsibility per file.

## Pull Requests

1. Fork the repository and create a feature branch.
2. Make your changes and add or update tests as needed.
3. Run the full test suite and confirm all tests pass.
4. Submit a pull request with a clear description of the change.

## Reporting Issues

Open an issue at https://github.com/matthew-lottly/strata/issues with:
- A clear description of the problem or feature request.
- Steps to reproduce (for bugs).
- Expected vs. actual behavior.
