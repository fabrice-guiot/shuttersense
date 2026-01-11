# Research: Dark Theme Compliance

**Feature Branch**: `009-dark-theme-compliance`
**Date**: 2026-01-10

## Overview

This document captures research findings for implementing dark theme compliance across the Photo Admin frontend. No critical unknowns require clarification - existing design tokens and infrastructure are sufficient.

---

## 1. Cross-Browser Scrollbar Styling

### Decision

Use a dual approach: standard CSS properties for Firefox + WebKit pseudo-elements for Chrome/Safari/Edge, with colors derived from existing design tokens.

### Rationale

- **Standard properties** (`scrollbar-color`, `scrollbar-width`) have 86% global support and work natively in Firefox
- **WebKit pseudo-elements** provide fine-grained control (hover states, border-radius) for Chrome/Safari/Edge
- **CSS custom properties** allow dynamic theming that respects existing design token system
- No additional libraries needed - pure CSS solution

### Implementation Pattern

```css
/* Standard properties (Firefox) */
* {
  scrollbar-color: hsl(var(--muted)) hsl(var(--background));
  scrollbar-width: thin;
}

/* WebKit (Chrome, Safari, Edge) */
*::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

*::-webkit-scrollbar-track {
  background: hsl(var(--background));
}

*::-webkit-scrollbar-thumb {
  background: hsl(var(--muted));
  border-radius: 4px;
  border: 2px solid hsl(var(--background));
  background-clip: padding-box;
}

*::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground));
}

*::-webkit-scrollbar-corner {
  background: hsl(var(--background));
}
```

### Color Mapping

| Scrollbar Part | Design Token | Purpose |
|----------------|--------------|---------|
| Track | `--background` | Matches page background |
| Thumb | `--muted` | Subtle but visible |
| Thumb (hover) | `--muted-foreground` | Brighter on interaction |
| Corner | `--background` | Seamless appearance |

### Browser-Specific Notes

- **Firefox**: Only supports `scrollbar-color` and `scrollbar-width` (no pseudo-elements)
- **WebKit**: Full control via pseudo-elements; standard properties ignored
- **Edge**: Uses WebKit engine, follows Chrome behavior
- **Safari**: Same as Chrome but may have minor rendering differences

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| JavaScript scrollbar library (e.g., SimpleBar) | Over-engineering; CSS-only solution sufficient |
| Custom scrollbar component | Adds complexity; native scrollbar behavior is preferred |
| Hide scrollbars entirely | Poor accessibility; users need scrollbar visibility |

---

## 2. React Error Boundary Implementation

### Decision

Create a class-based ErrorBoundary component with a dark-theme-compatible fallback UI. Implement multiple boundary levels: root (app-wide) and page-level.

### Rationale

- React 18 still requires class components for error boundaries (no hooks support)
- Multiple boundary levels prevent entire app crashes while providing contextual error feedback
- Fallback UI using design tokens ensures consistency with dark theme
- Simple implementation without external libraries (react-error-boundary is optional)

### Implementation Pattern

```typescript
// ErrorBoundary.tsx - Class component (required by React)
class ErrorBoundary extends React.Component<Props, State> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Error caught:', error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} onReset={this.handleReset} />
    }
    return this.props.children
  }
}

// ErrorFallback.tsx - Functional component with dark theme styling
function ErrorFallback({ error, onReset }) {
  return (
    <div className="bg-background text-foreground p-8">
      <div className="bg-card border border-border rounded-lg p-6">
        <AlertTriangle className="text-destructive" />
        <h1 className="text-foreground">Something went wrong</h1>
        <p className="text-muted-foreground">{userFriendlyMessage}</p>
        <Button onClick={onReset}>Try Again</Button>
      </div>
    </div>
  )
}
```

### Boundary Architecture

```
App (Root ErrorBoundary)
  └─ MainLayout
      ├─ Sidebar (independent - continues if main fails)
      └─ Main Content
          └─ Routes (Page-level ErrorBoundary per route)
```

### Error Boundary Limitations

Error boundaries do NOT catch:
- Event handler errors (use try-catch)
- Async code (setTimeout, promises - use .catch())
- Server-side rendering errors
- Errors in the error boundary itself

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| react-error-boundary library | Simple implementation sufficient; avoid dependency |
| Function component with hooks | React requires class components for error boundaries |
| Single root boundary only | Doesn't provide granular error recovery |

---

## 3. 404 Not Found Page

### Decision

Create a dedicated NotFoundPage component that follows dark theme styling and provides clear navigation options.

### Rationale

- Users navigating to invalid routes should see a styled page, not a blank screen
- Consistent with error boundary fallback styling
- Provides clear actions: go home, go back

### Implementation Pattern

```typescript
// NotFoundPage.tsx
function NotFoundPage() {
  return (
    <div className="bg-background text-foreground min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
        <p className="text-foreground mt-4">Page not found</p>
        <p className="text-muted-foreground mt-2">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6 flex gap-4 justify-center">
          <Button onClick={() => navigate(-1)}>Go Back</Button>
          <Button variant="outline" onClick={() => navigate('/')}>Go Home</Button>
        </div>
      </div>
    </div>
  )
}
```

### Route Integration

Add catch-all route in App.tsx router configuration:
```typescript
<Route path="*" element={<NotFoundPage />} />
```

---

## 4. Design Token Compliance Audit

### Decision

Search and replace hardcoded colors with design tokens. Focus on badge and alert components.

### Current Status by Component

#### Badge Component (`badge.tsx`)

| Variant | Current Classes | Status | Action |
|---------|-----------------|--------|--------|
| `default` | `bg-primary text-primary-foreground` | ✅ Compliant | None |
| `secondary` | `bg-secondary text-secondary-foreground` | ✅ Compliant | None |
| `destructive` | `bg-destructive text-destructive-foreground` | ✅ Compliant | None (red background already uses tokens) |
| `outline` | `text-foreground` | ✅ Compliant | None |
| `success` | `bg-green-500 text-white` | ❌ Hardcoded | Replace with token-based colors |
| `muted` | `bg-gray-400 text-white` | ❌ Hardcoded | Replace with `bg-muted text-muted-foreground` |
| `info` | `bg-blue-500 text-white` | ❌ Hardcoded | Replace with token-based colors |

**Note**: The `destructive` badge variant (red background for errors) is already correctly using design tokens.

#### Alert Component (`alert.tsx`)

| Variant | Current Classes | Status | Action |
|---------|-----------------|--------|--------|
| `default` | `bg-background text-foreground` | ✅ Compliant | None |
| `destructive` | `border-destructive/50 text-destructive` | ⚠️ Needs review | Add subtle background for visibility |

**Issue**: The destructive alert uses red text on transparent background. In dark mode, this may lack visual impact. Consider adding `bg-destructive/10` for a subtle red tint background.

### Proposed Token Mapping

| Variant | Current (Hardcoded) | Proposed (Token-based) |
|---------|---------------------|------------------------|
| Badge `success` | `bg-green-500 text-white` | `bg-emerald-600 text-white` → define `--success` token |
| Badge `muted` | `bg-gray-400 text-white` | `bg-muted text-muted-foreground` |
| Badge `info` | `bg-blue-500 text-white` | `bg-primary/20 text-primary` |
| Alert `destructive` | `text-destructive` (no bg) | Add `bg-destructive/10` for subtle red background |

### Search Patterns for Audit

```bash
# Find hardcoded hex colors
grep -rn '#[0-9a-fA-F]\{3,6\}' frontend/src/components/

# Find Tailwind color utilities (non-token)
grep -rn 'bg-\(gray\|blue\|green\|red\|yellow\)-' frontend/src/components/
grep -rn 'text-\(white\|black\|gray\|blue\|green\|red\)-' frontend/src/components/
```

---

## 5. WCAG Contrast Requirements

### Decision

Use Lighthouse/axe DevTools for automated contrast verification. All text must meet WCAG 2.1 AA requirements.

### Requirements

| Element Type | Minimum Ratio | Standard |
|--------------|---------------|----------|
| Normal text (<18px, <14px bold) | 4.5:1 | WCAG AA |
| Large text (≥18px, ≥14px bold) | 3:1 | WCAG AA |
| UI components, graphics | 3:1 | WCAG AA |
| Focus indicators | 3:1 | WCAG AA |

### Current Design Token Contrast (Dark Mode)

| Combination | Estimated Ratio | Status |
|-------------|-----------------|--------|
| `foreground` on `background` | ~16:1 | ✅ Pass |
| `muted-foreground` on `background` | ~7:1 | ✅ Pass |
| `primary` on `background` | ~5:1 | ✅ Pass |
| `destructive-foreground` on `destructive` | ~8:1 | ✅ Pass |

### Verification Method

1. Run Lighthouse accessibility audit
2. Check for contrast violations
3. Fix any flagged elements
4. Re-run to confirm

---

## 6. Form Control Styling

### Decision

Verify existing shadcn/ui form components use design tokens. Most should already be compliant based on library defaults.

### Components to Verify

- `input.tsx` - text inputs
- `textarea.tsx` - multiline inputs
- `select.tsx` - dropdown menus
- `checkbox.tsx` - checkboxes
- `form.tsx` - form field wrapper and error messages

### Expected Token Usage

| Element | Background | Text | Border | Focus |
|---------|------------|------|--------|-------|
| Input | `transparent` | `foreground` | `input` | `ring` |
| Select | `popover` | `popover-foreground` | `input` | `ring` |
| Checkbox | `primary` (checked) | `primary-foreground` | `primary` | `ring` |

---

## Summary

| Area | Research Complete | Implementation Ready |
|------|-------------------|---------------------|
| Scrollbar Styling | ✅ | ✅ CSS pattern defined |
| Error Boundary | ✅ | ✅ Component pattern defined |
| 404 Page | ✅ | ✅ Component pattern defined |
| Token Audit | ✅ | ✅ Violations identified |
| Contrast Check | ✅ | ✅ Verification method defined |
| Form Controls | ✅ | ✅ Likely compliant, verify only |

**All research items resolved. Ready for Phase 1 design artifacts.**
