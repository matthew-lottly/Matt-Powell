# Sports-Sim Roadmap

> Living document — updated as priorities shift.

## Current State

Sports-sim is a multi-sport simulation engine with:
- 11 sports (soccer, basketball, baseball, football, hockey, tennis, golf, cricket, boxing, MMA, racing)
- FastAPI REST + WebSocket API
- React + TypeScript + Vite frontend
- Per-sport roster data (NHL, NBA, NFL, MLB, MLS, EPL, and more)
- Realism modules: fatigue, injuries, weather, momentum, travel, surface, referee, substitutions
- Caching layer (Redis-capable), auth scaffolding, Docker setup

---

## v0.9 — Foundation (Current)

- [x] 11 sport plugins with realistic event generation
- [x] Rich WebSocket stream with per-sport state (down/distance, bases, power play, etc.)
- [x] Event metadata in stream payload
- [x] Score progression chart (SVG)
- [x] Post-game summary panel with per-sport stats
- [x] Event log filtering by category
- [x] Roster validation module
- [x] Connecting/error states in UI
- [x] Container health checks and non-root user
- [x] Statistical calibration tests
- [x] CI pipeline: lint, typecheck, test, frontend build

## v1.0 — Production Ready

### Backend
- [ ] Full API authentication (JWT-based, role enforcement)
- [x] Rate limiting on API endpoints
- [x] OpenAPI schema validation and auto-generated docs
- [ ] Redis caching for simulation results
- [x] Replay trace format and export (JSON/CSV)
- [x] Monte Carlo batch simulation endpoint
- [ ] Parameter estimation from real match data
- [x] Age curves and progression model for player development

### Frontend
- [x] Replay/playback controls (pause, rewind, speed)
- [x] Heatmap visualization for spatial events
- [x] Player card modals with stats and attributes
- [x] Keyboard shortcuts for power users
- [x] Accessibility audit (ARIA, screen reader, contrast)
- [ ] Storybook component library
- [ ] Component unit tests (React Testing Library)
- [ ] Visual regression tests
- [x] Dark/light theme toggle
- [x] Export game results (PDF, CSV)

### Data & Rosters
- [x] Coach profile system with tactical tendencies
- [x] Venue calibration from real-world data
- [x] League-specific rule enforcement (OT formats, substitution limits)
- [ ] CSV roster ingestion pipeline (activate `roster_ingest.py`)
- [ ] Position enum (replace free-form strings)
- [ ] Real depth charts for NBA, NFL, MLB

### Infrastructure
- [ ] Kubernetes/Helm deployment templates
- [x] Prometheus metrics endpoint
- [ ] Grafana dashboard templates
- [ ] Staging deployment workflow
- [ ] Load testing scripts (Locust)
- [x] Container image scanning (Trivy)
- [x] Dependency update automation (Dependabot)

## v1.1 — Intelligence

- [ ] Baseline scripted AI agents for each sport
- [ ] RL training harness for agent optimization
- [ ] Explainability hooks (decision logs per event)
- [ ] Tactical formation system (soccer, football)
- [ ] Player chemistry and lineup interaction model
- [ ] Season simulation mode
- [ ] Trade and draft evaluation tools

## v2.0 — Platform

- [ ] Multi-user lobby and concurrent simulations
- [ ] Real-time multiplayer control (live coaching)
- [ ] API client SDK (Python + JavaScript)
- [ ] Plugin architecture for custom sports
- [ ] Marketplace for community presets/formations
- [ ] Mobile app (React Native or PWA)

---

_Last updated by repository audit. Convert items to GitHub Issues for tracking._
