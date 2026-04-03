# Accessibility Checklist

Accessibility requirements and validation steps for the Open Web Map Operations Dashboard.

## Keyboard Navigation

- [ ] All interactive controls (filters, buttons, map controls) are reachable via Tab key
- [ ] Focus order follows visual layout: header → filters → map → side panel
- [ ] Map zoom and pan are accessible via keyboard (arrow keys, +/- keys)
- [ ] Selected station details can be dismissed with Escape
- [ ] Focus trap does not occur in the map canvas

## Screen Reader Support

- [ ] Page has a descriptive `<title>` element
- [ ] All images and icons have meaningful `alt` text or `aria-label`
- [ ] Filter controls have associated `<label>` elements
- [ ] Status counts use `aria-live="polite"` so updates are announced
- [ ] Map canvas has `role="application"` with an `aria-label`
- [ ] Station popups are announced when opened

## Color and Contrast

- [ ] Text meets WCAG AA contrast ratio (4.5:1 for normal text, 3:1 for large text)
- [ ] Status indicators (healthy, warning, critical) do not rely on color alone — use icons or text labels
- [ ] Map markers use shape or size in addition to color for status differentiation
- [ ] Focus indicators are visible against the map background

## HTML Semantics

- [ ] Page uses semantic elements: `<header>`, `<nav>`, `<main>`, `<aside>`
- [ ] Heading hierarchy is correct (`h1` → `h2` → `h3`, no skipped levels)
- [ ] Filter controls use `<fieldset>` and `<legend>` where grouped
- [ ] Data tables use `<th>` with `scope` attributes

## Map Accessibility

- [ ] MapLibre canvas has `aria-label="Operations map"`
- [ ] Non-visual summary of visible stations is available for screen readers
- [ ] Zoom level is communicated to assistive technology
- [ ] Station selection triggers a focus move to the detail panel

## Responsive Design

- [ ] Dashboard is usable at 320px viewport width
- [ ] Touch targets are at least 44×44px on mobile
- [ ] Map controls do not overlap filters on small screens

## Testing Tools

Run these checks regularly:

1. **Axe DevTools**: Browser extension for automated WCAG scanning
2. **Lighthouse**: Chrome DevTools audit for accessibility score
3. **Manual keyboard test**: Tab through the full interface without a mouse
4. **Screen reader test**: Use NVDA (Windows) or VoiceOver (Mac) to navigate
5. **Color contrast checker**: Use the WebAIM contrast checker for each status color

## CI Integration

Add `axe-core` to the test suite for automated accessibility regression checks:

```bash
npm install --save-dev @axe-core/react
```

Then add accessibility assertions to component tests:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

test('dashboard has no accessibility violations', async () => {
  const { container } = render(<App />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```
