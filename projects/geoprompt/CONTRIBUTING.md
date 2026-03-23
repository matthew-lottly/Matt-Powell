# Contributing to GeoPrompt

## Development Setup

```bash
git clone https://github.com/matthew-lottly/Matt-Powell.git
cd projects/geoprompt
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

pip install -e ".[dev,compare,overlay,projection,io,raster]"
```

## Running Tests

```bash
pytest --tb=short -q
```

## Project Structure

```
src/geoprompt/
├── __init__.py          # Public API exports
├── frame.py             # GeoPromptFrame class (400+ spatial tools)
├── geometry.py          # Pure-Python geometry functions
├── equations.py         # Spatial equations (gravity, accessibility, etc.)
├── overlay.py           # Buffer, dissolve, Shapely interop
├── spatial_index.py     # R-tree spatial index
├── io.py                # GeoJSON, CSV, flat-record I/O
└── py.typed             # PEP 561 type marker
```

## Adding a New Tool

1. Add the method to `GeoPromptFrame` in `frame.py`.
2. Follow the naming convention: `tool_name(self, ..., suffix: str = "shortname") -> GeoPromptFrame`.
3. Add at least one test in the appropriate test file.
4. Run the full suite to check for regressions.
5. Update `CHANGELOG.md` with the new tool.

## Conventions

- Tools that add columns use a configurable `suffix` parameter.
- Tools return new `GeoPromptFrame` instances (immutable pattern).
- Tools that return aggregate results (not per-row) return `dict` or `list`.
- Helper functions are module-level and prefixed with `_`.
- Keep zero required dependencies beyond `matplotlib`.

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Make your changes with tests.
3. Run the full test suite.
4. Update the changelog.
5. Submit a PR against `main`.
