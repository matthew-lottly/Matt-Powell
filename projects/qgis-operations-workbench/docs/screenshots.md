# Screenshots

Visual review artifacts for the QGIS Operations Workbench.

## Planned Screenshots

These screenshots should be captured and committed to `assets/` after the GeoPackage output is stable:

### 1. GeoPackage Loaded in QGIS
**File**: `assets/qgis-loaded.png`
- QGIS with the `qgis_review_bundle.gpkg` loaded
- Station review points visible on a base map
- Layers panel showing both feature layers

### 2. Station Status Styling
**File**: `assets/qgis-styled.png`
- Categorized styling applied to station points by status
- Red for alert/critical, yellow for warning, green for healthy
- Legend panel visible

### 3. Inspection Route View
**File**: `assets/qgis-routes.png`
- Inspection routes overlaid on station points
- Route labels visible
- Zoomed to a specific inspection corridor

### 4. Region Bookmark Navigation
**File**: `assets/qgis-bookmarks.png`
- QGIS spatial bookmarks panel showing region bookmarks
- Map zoomed to a bookmarked region
- Station density visible in the bookmarked extent

### 5. Print Layout Preview
**File**: `assets/qgis-layout.png`
- QGIS print layout based on the station_brief_a4 template
- Shows the intended print output format

## How to Capture

1. Generate the GeoPackage:
```bash
python -m qgis_operations_workbench.workbench --export-geopackage
```

2. Open `outputs/qgis_review_bundle.gpkg` in QGIS

3. Apply categorized styling on the `status` field

4. Capture screenshots using the OS screenshot tool or QGIS screenshot export

## Current Placeholder

The `assets/workbench-preview.svg` provides a schematic preview. Replace with actual QGIS screenshots once the GeoPackage workflow is demonstrated end-to-end.
