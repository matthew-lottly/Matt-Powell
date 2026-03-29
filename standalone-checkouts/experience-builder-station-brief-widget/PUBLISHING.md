# Publishing Guide

## Recommended Standalone Repository Name

- experience-builder-station-brief-widget

## Recommended Description

- React and TypeScript GIS widget prototype inspired by ArcGIS Experience Builder patterns for station summaries, filtering, and selection-driven detail panels.

## Suggested Topics

- react
- typescript
- arcgis
- experience-builder
- gis
- frontend
- geospatial-ui

## Split Steps

1. Create a new empty repository named `experience-builder-station-brief-widget`.
2. Initialize git in this folder.
3. Add the remote origin for the new repository.
4. Push the contents of this folder to the new repository.
5. Use [assets/widget-preview.svg](assets/widget-preview.svg) as the initial visual preview.
6. Reference [docs/architecture.md](docs/architecture.md) and [docs/demo-storyboard.md](docs/demo-storyboard.md) from the README when polishing the public pitch.

## Local Publish Commands

```powershell
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/<your-username>/experience-builder-station-brief-widget.git
git push -u origin main
```

## First Public Polish Pass

- Add one browser screenshot from the live Vite app alongside the SVG preview and caption it as a prototype capture from this repository
- Add a short GIF showing region filtering and marker selection
- Link this repository back to the API repo as the frontend-facing companion project