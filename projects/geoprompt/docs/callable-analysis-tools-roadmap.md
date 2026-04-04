# Callable Analysis Tools Roadmap

## Goal
Provide GeoPandas-like, user-callable analysis tools on top of GeoPrompt so users can run spatial analysis with one-liners and chainable workflows.

## Design Principles
- Keep API pandas/geopandas-like: predictable method names and return types.
- Support both frame methods and functional API.
- Return plain tables/GeoJSON-friendly structures by default.
- Add strong input validation and deterministic outputs.
- Expose fast defaults, with expert knobs optional.

## Proposed API Shape

### Method-style API (primary)
- `GeoPromptFrame.analysis.accessibility(...)`
- `GeoPromptFrame.analysis.catchment(...)`
- `GeoPromptFrame.analysis.gravity_flow(...)`
- `GeoPromptFrame.analysis.suitability(...)`
- `GeoPromptFrame.analysis.hotspot_scan(...)`
- `GeoPromptFrame.analysis.equity_gap(...)`
- `GeoPromptFrame.analysis.network_reliability(...)`
- `GeoPromptFrame.analysis.risk_surface(...)`

### Functional API (secondary)
- `geoprompt.accessibility_analysis(frame, ...)`
- `geoprompt.catchment_analysis(frame, ...)`
- `geoprompt.gravity_flow_analysis(frame, ...)`

## MVP Tool Set (Phase 1)

### 1) Accessibility Analyzer
Purpose: score access from origins to opportunities with selectable decay equations.

Inputs:
- origin geometry
- destination geometry
- optional weights (population, jobs, services)
- decay model and parameters

Outputs:
- per-origin accessibility score
- optional destination contribution breakdown

Core equations:
- `prompt_decay`, `exponential_decay`, `gaussian_decay`
- `accessibility_potential`, `multi_scale_accessibility_score`

### 2) Catchment & Competition Analyzer
Purpose: compute service catchments with overlap and competition.

Inputs:
- demand points/polygons
- service points with capacity
- distance method, thresholds

Outputs:
- assigned catchment per demand unit
- overlap penalty and pressure metrics

Core equations:
- `competitive_influence`, `service_overlap_penalty`, `opportunity_pressure_index`

### 3) Gravity Flow Analyzer
Purpose: model interactions/flows between origins and destinations.

Inputs:
- origin mass, destination mass
- distance matrix or geometry
- beta, offset, decay family

Outputs:
- OD flow table
- normalized flow shares

Core equations:
- `gravity_interaction`, `prompt_interaction`, `harmonic_interaction`

### 4) Suitability Analyzer
Purpose: weighted multi-criteria site suitability scoring.

Inputs:
- criteria fields
- optional weights
- per-criterion transform function

Outputs:
- suitability score
- criterion contribution table

Core equations:
- `composite_suitability_score`, `coverage_equity_score`, `density_similarity`

### 5) Hotspot & Risk Surface Analyzer
Purpose: compute local intensity, vulnerability, and intervention priority.

Inputs:
- metric field(s)
- neighborhood parameters
- optional exposure/sensitivity/adaptive capacity fields

Outputs:
- hotspot score
- risk score
- priority class

Core equations:
- `hotspot_intensity_score`, `climate_vulnerability_index`, `transmission_risk_score`

## GeoPandas-like Usage Examples

```python
from geoprompt import GeoPromptFrame

frame = GeoPromptFrame(features)

access = frame.analysis.accessibility(
    opportunities="jobs",
    demand="population",
    decay="gaussian_decay",
    scale=2.0,
)

flows = frame.analysis.gravity_flow(
    origin_weight="population",
    destination_weight="jobs",
    beta=1.8,
)

suitability = frame.analysis.suitability(
    criteria=["transit_access", "flood_safety", "land_cost"],
    weights=[0.45, 0.35, 0.20],
)
```

## Implementation Plan

### Phase 1: API Surface
- Add `analysis` namespace object on `GeoPromptFrame`.
- Implement 5 MVP tools with stable signatures.
- Keep return objects as list[dict] + helper conversion methods.

### Phase 2: Equation Registry Integration
- Allow `decay="equation_name"` lookups through equation registry.
- Add parameter schema validation per equation.

### Phase 3: Performance
- Reuse spatial index and cached pairwise distances.
- Add chunked mode for large datasets.
- Add benchmark tests and baseline budgets.

### Phase 4: DX and Documentation
- Add notebook examples for each tool.
- Add CLI wrappers:
  - `geoprompt analyze accessibility ...`
  - `geoprompt analyze gravity-flow ...`
  - `geoprompt analyze suitability ...`

## Suggested Immediate Build Order
1. Accessibility Analyzer
2. Gravity Flow Analyzer
3. Suitability Analyzer
4. Catchment & Competition Analyzer
5. Hotspot & Risk Surface Analyzer

## Acceptance Criteria
- Each tool has unit tests and at least one integration test.
- Deterministic output on fixed input.
- Clear argument validation and error messages.
- End-to-end example in docs and CLI parity for MVP tools.
