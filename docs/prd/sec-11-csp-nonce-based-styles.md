# SEC-11: Nonce-Based CSP for Inline Styles

**Status**: Proposed
**Priority**: Medium
**Origin**: Security Audit Remediation (Phase 3)
**Reference**: [Security Audit Plan](../issues/security-audit-remediation.md#sec-11-remove-csp-unsafe-inline-for-styles)

---

## Problem Statement

The application's Content Security Policy currently uses `style-src 'self' 'unsafe-inline'` to
allow inline styles. While this is standard practice for many SPAs, `unsafe-inline` weakens
the CSP by allowing any injected inline styles to execute, which could be exploited for CSS
injection attacks (e.g., data exfiltration via CSS selectors or UI redressing).

## Investigation Findings

A thorough audit of the frontend codebase identified **25+ component files** that rely on
inline `style={}` attributes. Removing `unsafe-inline` without a replacement mechanism would
break the application. The inline styles fall into these categories:

### 1. Dynamic Color Values (User-Defined)

Category and event colors are user-configurable and applied at runtime:

- `CategoriesTab.tsx` — `style={{ backgroundColor: color }}`
- `CategoryForm.tsx` — Color picker previews
- `EventCard.tsx`, `CategoryBadge.tsx` — Event/category color display
- `LocationForm.tsx`, `OrganizerForm.tsx`, `PerformerForm.tsx` — Directory entity colors

### 2. Charting Library (Recharts)

Recharts uses inline styles extensively for tooltip positioning and theming:

- `TrendChart.tsx` — Tooltip backgrounds, axis fill colors, dot colors

### 3. Dynamic Layout Calculations

Runtime-computed dimensions that cannot be pre-compiled:

- `progress.tsx` — `transform: translateX(-${100 - percentage}%)`
- `JobProgressCard.tsx` — `width: ${percentage}%`
- `FolderTreeNode.tsx` — `paddingLeft: ${indentPx + 8}px`
- `FolderTree.tsx` — Dynamic heights/widths

### 4. Browser Compatibility Fallbacks

Clipboard API fallback for older browsers:

- `guid.ts`, `useClipboard.ts` — Programmatic `style` property assignment on textarea elements

## Proposed Solution: Nonce-Based CSP

Replace `unsafe-inline` with a per-request nonce that authorizes only intentional inline styles.

### Architecture

1. **Server-Side Nonce Generation** — Generate a cryptographically random nonce for each HTTP
   response in the security headers middleware (`backend/src/main.py`).

2. **CSP Header Update** — Replace `style-src 'self' 'unsafe-inline'` with
   `style-src 'self' 'nonce-{random}'`.

3. **HTML Injection** — Inject the nonce into the SPA's `index.html` before serving it,
   adding `nonce="{random}"` to all `<style>` and `<link rel="stylesheet">` tags.

4. **React Nonce Propagation** — Pass the nonce to React via a `<meta>` tag or global
   variable so that runtime style injection (e.g., Recharts, emotion) can include it.

5. **Component Refactoring** — Where feasible, replace inline `style={}` with:
   - CSS custom properties set via `data-*` attributes
   - Dynamic Tailwind classes (e.g., `bg-[${color}]` with safelist)
   - CSS-in-JS solutions that support nonce propagation

### Key Challenges

| Challenge | Complexity | Notes |
|-----------|-----------|-------|
| Recharts nonce support | High | May require custom tooltip renderer or library fork |
| Dynamic user colors | Medium | Can use CSS custom properties (`--category-color`) |
| Progress bar transforms | Low | Can use CSS custom properties |
| Clipboard fallback | Low | Style assignment is on programmatically created elements (may not need CSP) |
| SPA nonce injection | Medium | Need to inject nonce into `index.html` on each request, breaking static file caching |

### Impact on Caching

Nonce-based CSP means each response has a unique nonce, which **prevents CDN/browser caching
of the HTML shell**. This is acceptable since:

- The SPA HTML shell is small (~2KB)
- Static assets (JS, CSS bundles) remain cacheable
- API responses are not affected

## Acceptance Criteria

- [ ] CSP header uses `nonce-{random}` instead of `unsafe-inline` for `style-src`
- [ ] All existing inline styles work with the nonce
- [ ] Recharts tooltips and charts render correctly
- [ ] Dynamic category/event colors display correctly
- [ ] Progress bars animate correctly
- [ ] No CSP violations reported in browser console
- [ ] Frontend tests pass without modification (or with minimal updates)

## Alternatives Considered

### 1. CSS Hashes

Pre-compute SHA-256 hashes of all inline style values and list them in the CSP header.

- **Rejected**: Dynamic values (user colors, percentages) produce infinite hash combinations.

### 2. Shadow DOM Isolation

Move dynamically-styled components into Shadow DOM where CSP doesn't apply.

- **Rejected**: Major architectural change; breaks Tailwind utility class inheritance.

### 3. Accept `unsafe-inline`

Keep the current CSP and mitigate through other means (input sanitization, XSS prevention).

- **Viable fallback**: The application already has strong XSS prevention (React's JSX escaping,
  CSP `script-src 'self'` without unsafe-inline). The risk from `style-src unsafe-inline`
  is lower severity than script injection.

## Dependencies

- None — this is a standalone security improvement
- Should coordinate with any Recharts version upgrades
