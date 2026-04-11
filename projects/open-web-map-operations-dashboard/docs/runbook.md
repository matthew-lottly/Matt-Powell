# Runbook

## Purpose

Run the dashboard locally, verify layer rendering, and confirm it stays aligned with the expected service payloads.

## Local Startup

```bash
npm install
npm run dev
```

## Verification

- Confirm the map loads and the dashboard heading renders.
- Change region and status filters and verify layer counts update.
- Run `npm test` before merging UI changes.
- Run `npm run build` before publishing.

## Data Source Notes

- Current local mode uses checked-in sample data.
- Keep the client response assumptions aligned with the paired API projects.

## Release Notes

- Re-check map styling and filter behavior after dependency upgrades.
- Validate build output on both desktop and smaller viewport sizes.