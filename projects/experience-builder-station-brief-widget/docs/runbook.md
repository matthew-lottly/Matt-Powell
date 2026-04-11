# Runbook

## Purpose

Run the widget prototype locally, verify selection and persistence behavior, and keep it ready for portfolio review.

## Local Startup

```bash
npm install
npm run dev
```

## Verification

- Confirm the hero panel and widget render.
- Toggle status and region filters and verify the detail panel updates.
- Switch between mock and API-backed modes if configured.
- Run `npm test` before merging changes.

## Integration Notes

- Treat the current UI as a public-safe prototype, not a vendor screenshot surrogate.
- Keep the expected API payload shape consistent with the monitoring API projects.

## Release Notes

- Run `npm run build` before publishing.
- Re-check local storage config persistence after settings changes.