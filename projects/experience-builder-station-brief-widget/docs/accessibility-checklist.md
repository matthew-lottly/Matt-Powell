# Accessibility Checklist

Accessibility requirements for the Experience Builder Station Brief Widget.

## Keyboard Navigation

- [ ] All interactive controls reachable via Tab
- [ ] Station list navigable with arrow keys
- [ ] Filter controls keyboard-accessible
- [ ] Focus order follows visual layout
- [ ] Detail panel dismissable with Escape

## Screen Reader Support

- [ ] Widget has a descriptive `aria-label`
- [ ] Station list uses appropriate ARIA roles (`listbox`, `option`)
- [ ] Filter controls have associated labels
- [ ] Status changes announced via `aria-live` regions
- [ ] Summary cards have meaningful text alternatives

## Color and Contrast

- [ ] Text meets WCAG AA contrast (4.5:1 normal, 3:1 large)
- [ ] Status indicators use text or icon in addition to color
- [ ] Focus indicators visible against all backgrounds

## Semantic HTML

- [ ] Heading hierarchy correct (no skipped levels)
- [ ] Interactive elements use `<button>` not `<div>` with click handlers
- [ ] Data lists use semantic list elements

## Testing

1. **Axe DevTools**: Browser extension scan
2. **Keyboard**: Full tab-through test without mouse
3. **Screen reader**: NVDA or VoiceOver navigation test
