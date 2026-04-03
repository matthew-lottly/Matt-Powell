# Screenshots

Visual review artifacts for the Open Web Map Operations Dashboard.

## Planned Screenshots

These screenshots should be captured and committed to `assets/` after significant UI changes:

### 1. Full Dashboard View
**File**: `assets/dashboard-full.png`
- Shows the complete dashboard with map, filter panel, and station summary
- MapLibre map centered on the default data extent with station markers visible
- All filters in their default (unfiltered) state

### 2. Filtered Status View
**File**: `assets/dashboard-filtered.png`
- Region filter set to a specific region
- Status filter set to "alert" or "critical"
- Map zoomed to the filtered area with highlighted stations

### 3. Station Detail View
**File**: `assets/station-detail.png`
- A specific station selected on the map
- Detail panel showing station properties and recent observations
- Map centered on the selected station

### 4. Mobile Responsive View
**File**: `assets/dashboard-mobile.png`
- Dashboard rendered at 375px viewport width
- Shows the responsive layout behavior

## How to Capture

1. Start the development server:
```bash
npm run dev
```

2. Open in a browser at `http://localhost:5173`

3. Use the browser's device toolbar for responsive views

4. For consistent screenshots, use Playwright or Puppeteer:
```bash
npx playwright screenshot http://localhost:5173 assets/dashboard-full.png --viewport-size=1280,800
```

## Current Placeholder

The `assets/dashboard-preview.svg` provides a schematic preview. Replace with actual screenshots once the UI is stable enough for long-lived captures.
