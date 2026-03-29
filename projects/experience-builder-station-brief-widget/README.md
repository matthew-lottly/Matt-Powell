# Experience Builder Station Brief Widget

Public-safe TypeScript and React prototype inspired by ArcGIS Experience Builder interaction patterns for station filtering, operational summaries, coverage-map interaction, and selection-driven detail panels.

![Concept preview for the station brief widget prototype](assets/widget-preview.svg)

![Browser screenshot of the station brief widget prototype](assets/widget-live-screenshot.png)

![Interaction storyboard for the station brief widget prototype](assets/widget-interaction-walkthrough.svg)

## Snapshot

- Lane: GIS application development
- Domain: GIS frontend prototype informed by Experience Builder patterns
- Stack: React, TypeScript, Vite, Vitest
- Includes: mock data source records, widget config pattern, coverage-map mock, summary cards, detail panel, tests

## Why This Project Exists

My public portfolio already showed backend, analytics, and database work. This project closes the remaining gap by demonstrating the kind of TypeScript and React interface work that maps closely to Experience Builder-style widget development, while making it explicit that the visuals are conceptual portfolio assets rather than ArcGIS product screenshots.

It is designed to read as the frontend companion to the monitoring API and analytics repos rather than a disconnected UI demo.

## What It Demonstrates

- React and TypeScript component structure for GIS-facing UIs
- Widget-style configuration and data-source-driven rendering
- Local persistence of runtime widget configuration across page reloads
- Station filtering, summary cards, a map-adjacent mock, status multi-filtering, and selection-driven detail panels
- Station detail history modal patterns that map to inspection workflows in GIS apps
- A public-safe way to discuss Experience Builder-inspired architecture without exposing private code

## Project Structure

```text
experience-builder-station-brief-widget/
|-- src/
|   |-- App.tsx
|   |-- main.tsx
|   |-- styles.css
|   `-- widget/
|       |-- mockData.ts
|       |-- StationBriefWidget.tsx
|       |-- transform.ts
|       `-- types.ts
|-- tests/
|   `-- transform.test.ts
|-- assets/
|-- docs/
|-- package.json
|-- tsconfig.json
`-- vite.config.ts
```

## Quick Start

```bash
npm install
npm run dev
```

Run tests:

```bash
npm test
```

Build the demo:

```bash
npm run build
```

## Public Notes

This is not a full ArcGIS Experience Builder export or a screenshot of ArcGIS software. It is a deliberately public-safe prototype that demonstrates component structure, interaction patterns, and data-shaping logic relevant to Experience Builder-style widget work.

The browser screenshot in this README comes from the Vite app in this repository. The SVG assets are conceptual walkthrough graphics used to explain the interaction flow without implying access to ArcGIS product imagery.

The configuration panel now persists key widget settings in browser local storage so a reviewer can see settings survive refresh without requiring a backend. That now includes the multi-select status filter alongside the region and display settings.

The interaction walkthrough asset highlights the main reviewer path: switch the region filter to `West`, keep only alert stations visible, select `Sierra Air Quality Node`, and open the history modal to inspect recent observation notes.

See [docs/architecture.md](docs/architecture.md) for the widget design notes.
See [docs/demo-storyboard.md](docs/demo-storyboard.md) for a short walkthrough script.

## Publication

- License: [LICENSE](LICENSE)
- Standalone publishing notes: [PUBLISHING.md](PUBLISHING.md)
- Local CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Repository Notes

This copy is intended to be publishable as its own repository.