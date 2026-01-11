# Quickstart: Dark Theme Compliance Verification

**Feature Branch**: `009-dark-theme-compliance`
**Date**: 2026-01-10

This guide provides step-by-step instructions to verify dark theme compliance after implementation.

---

## Prerequisites

- Node.js 18+ installed
- Frontend development server running (`npm run dev` in `frontend/`)
- Modern browser with DevTools (Chrome, Firefox, Safari, or Edge)

---

## 1. Scrollbar Verification

### Visual Check

1. Navigate to a page with scrollable content (e.g., Collections list with many items)
2. Observe the scrollbar appearance:
   - **Track** should be dark (match page background)
   - **Thumb** should be a muted gray color (visible but not bright)
   - **Hover** the thumb - it should brighten slightly

### Cross-Browser Test

| Browser | Expected Behavior |
|---------|-------------------|
| Chrome | Custom styled scrollbar (thin, dark, rounded thumb) |
| Firefox | Thin scrollbar with dark colors (no rounded corners) |
| Safari | Same as Chrome |
| Edge | Same as Chrome |

### Code Verification

```bash
# Verify scrollbar styles exist in globals.css
grep -A 5 "::-webkit-scrollbar" frontend/src/globals.css
grep "scrollbar-color" frontend/src/globals.css
```

---

## 2. Design Token Compliance Check

### Automated Search

Run these commands to find any remaining hardcoded colors:

```bash
# Check for hardcoded hex colors
grep -rn '#[0-9a-fA-F]\{3,6\}' frontend/src/components/ --include="*.tsx"

# Check for Tailwind color utilities (non-token)
grep -rn 'bg-\(gray\|blue\|green\|red\|yellow\|white\|black\)-' frontend/src/components/ --include="*.tsx"
grep -rn 'text-\(gray\|blue\|green\|red\|yellow\|white\|black\)-' frontend/src/components/ --include="*.tsx"

# Exclude: text-white in badges (if intentionally retained with proper contrast)
```

### Expected Results

- Zero matches for hardcoded hex colors in component files
- Zero matches for non-token Tailwind color classes
- All colors should use tokens: `bg-background`, `text-foreground`, `bg-primary`, etc.

---

## 3. Accessibility Contrast Audit

### Lighthouse Audit

1. Open Chrome DevTools (F12)
2. Go to **Lighthouse** tab
3. Select **Accessibility** category only
4. Click **Analyze page load**
5. Review results for contrast issues

### Expected Results

- Accessibility score ≥ 90
- Zero "Contrast" issues flagged
- All text meets WCAG AA (4.5:1 for normal, 3:1 for large)

### Manual Spot Check

Use Chrome DevTools color picker to verify contrast:

1. Inspect any text element
2. Click the color swatch in Styles panel
3. Check the "Contrast ratio" shown
4. Should show ✓ for AA compliance

---

## 4. Error State Verification

### Backend Unavailable Test

1. Stop the backend server
2. Refresh the frontend
3. Verify:
   - Error message is visible (not blank page)
   - Text is readable (light text on dark background)
   - Message is user-friendly (no stack traces)
   - "Try Again" or "Retry" option is available

### 404 Page Test

1. Navigate to a non-existent URL (e.g., `/nonexistent-page`)
2. Verify:
   - 404 page displays (not blank)
   - Dark theme styling is consistent
   - Navigation options present (Go Home, Go Back)

### Error Boundary Test (Development)

1. Intentionally break a component (add `throw new Error('test')`)
2. Verify:
   - Fallback UI displays (not white screen)
   - Error message is styled with dark theme
   - "Try Again" button works to reset

---

## 5. Form Styling Verification

### Visual Check

1. Navigate to Create Collection or Create Connector form
2. Verify each form element:

| Element | Expected Styling |
|---------|------------------|
| Text inputs | Dark background, light text, visible border |
| Dropdowns | Dark popover background when open |
| Labels | Light text (`foreground` color) |
| Error messages | Red/destructive color, readable text |
| Buttons | Primary button is blue, outline button has border |

### Focus State Check

1. Tab through form fields with keyboard
2. Verify each field shows a visible focus ring
3. Focus ring should be blue (`ring` token)

---

## 6. Badge Component Verification

### Visual Check

1. Find pages with status badges (Collections, Connectors)
2. Verify badge variants:

| Variant | Expected |
|---------|----------|
| Success (Live) | Green background, white text |
| Destructive (Error) | Red background, light text |
| Muted (Inactive) | Gray background, readable text |
| Info (Archived) | Blue-ish background, readable text |
| Secondary (Type labels) | Muted background, readable text |

### Contrast Check

All badge text should meet 4.5:1 contrast ratio against badge background.

---

## 7. Full Page Dark Theme Audit

### Pages to Check

- [ ] Dashboard/Home
- [ ] Collections List
- [ ] Collection Detail
- [ ] Connectors List
- [ ] Connector Detail
- [ ] Create/Edit Forms
- [ ] Settings (if exists)
- [ ] 404 Page
- [ ] Error States

### Checklist Per Page

- [ ] No bright white backgrounds visible
- [ ] All text is readable
- [ ] Scrollbars match dark theme
- [ ] Buttons and links are visible
- [ ] Focus states are visible
- [ ] Error messages are styled

---

## Quick Commands Reference

```bash
# Start frontend dev server
cd frontend && npm run dev

# Run frontend tests
cd frontend && npm test

# Build for production (catches type errors)
cd frontend && npm run build

# Check for hardcoded colors
grep -rn '#[0-9a-fA-F]\{3,6\}' frontend/src/components/
```

---

## Success Criteria Summary

| Criterion | Verification Method | Pass |
|-----------|---------------------|------|
| SC-001: Zero hardcoded colors | Grep search | [ ] |
| SC-002: Dark scrollbars | Visual inspection (4 browsers) | [ ] |
| SC-003: WCAG AA contrast | Lighthouse audit | [ ] |
| SC-004: Visible focus states | Keyboard navigation | [ ] |
| SC-005: Design system docs updated | File review | [ ] |
| SC-006: No blank error pages | Error simulation | [ ] |
| SC-007: Error contrast OK | Accessibility audit | [ ] |
| SC-008: No technical errors shown | Error simulation | [ ] |

---

*Complete all checks before marking feature as done.*
