# Geoprompt 0.1.8 Release Notes

## Highlights

- Expanded equation-powered analysis tooling with 10 new callable maps.
- Added a new 40-equation extension set with dedicated tests.
- Strengthened validation with open-source parity checks and full CLI matrix coverage.
- Cleaned generated artifacts from version control and tightened output hygiene.
- Refreshed docs with clearer markdown graphs and updated release guidance.

## New Analysis Tools

- `drought_stress_map(...)`
- `heat_island_map(...)`
- `school_access_map(...)`
- `healthcare_access_map(...)`
- `food_desert_map(...)`
- `digital_divide_map(...)`
- `wildfire_risk_map(...)`
- `emergency_response_map(...)`
- `infrastructure_lifecycle_map(...)`
- `adaptive_capacity_map(...)`

## Equation Expansion

- Added 40 new equations for resilience, risk, access, equity, performance, uncertainty, and lifecycle scoring.
- New catalog: [equations-extended-catalog.md](equations-extended-catalog.md)

## Validation and Correctness

- Equations: `pytest tests/test_equations.py tests/test_new_equations.py`
- Tools: `pytest tests/test_analysis_tools.py tests/test_tools_open_source_parity.py`
- CLI matrix: `pytest tests/test_cli.py`
- Full suite: `pytest`
- Open-source comparison: `python -m geoprompt.compare --output-dir outputs`

## Documentation and Cleanup

- Updated system and data-flow graphs in:
  - [architecture.md](architecture.md)
  - [data-flow.md](data-flow.md)
  - [../README.md](../README.md)
- Removed stale generated files from tracking and ignored runtime output artifacts.

## Versioning

- Package version updated to `0.1.8` in `pyproject.toml`.
- CLI runtime version marker updated to `0.1.8` in `src/geoprompt/demo.py`.
