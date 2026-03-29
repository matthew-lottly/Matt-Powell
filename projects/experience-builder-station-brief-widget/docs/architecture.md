# Architecture

## Overview

This project models the shape of a map-centric widget inspired by Experience Builder patterns without depending on private framework exports or employer configuration.

## Flow

1. Mock station records simulate the kind of selection-capable records a widget would receive from a data source.
2. A widget config object provides title, subtitle, default region, and display behavior.
3. Transform helpers filter records, derive summaries, and provide display-ready region options.
4. The widget component renders summary cards, a selection list, and a detail panel.

## Why It Works Publicly

- Demonstrates TypeScript and React patterns relevant to GIS frontend and Experience Builder-adjacent work.
- Shows selection-driven GIS interface design without requiring private services.
- Keeps the code reviewable and runnable in a normal frontend toolchain.