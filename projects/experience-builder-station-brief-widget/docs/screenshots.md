# Screenshots

Visual review artifacts for the Experience Builder Station Brief Widget.

## Planned Screenshots

### 1. Default Dashboard View
**File**: `assets/widget-default.png`
- Station list panel with filter controls
- Summary cards showing station counts by status
- Widget in its default unfiltered state

### 2. Filtered Station View
**File**: `assets/widget-filtered.png`
- A status or category filter applied
- Filtered station count reflected in summary cards
- Selected station highlighted in the list

### 3. Station Detail Panel
**File**: `assets/widget-detail.png`
- A specific station selected from the list
- Detail panel showing station properties and operational context
- Selection-driven summary content

### 4. Coverage Map Interaction
**File**: `assets/widget-coverage.png`
- Map canvas showing station locations
- Interactive selection behavior between map and panel

### 5. Mobile Responsive View
**File**: `assets/widget-mobile.png`
- Widget rendered at 375px viewport width
- Responsive layout behavior

## How to Capture

1. Start the development server:
```bash
npm run dev
```

2. Open `http://localhost:5173`

3. For consistent automated captures:
```bash
npx playwright screenshot http://localhost:5173 assets/widget-default.png --viewport-size=1280,800
```

## Current Placeholder

The `assets/widget-preview.svg` provides a schematic preview.
