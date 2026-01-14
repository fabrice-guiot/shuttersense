# Research: Mobile Calendar View

**Feature Branch**: `016-mobile-calendar-view`
**Date**: 2026-01-13

## Research Summary

This document captures research findings for implementing a compact mobile calendar view. All technical questions have been resolved through codebase exploration.

---

## 1. Responsive Design Approach

### Decision: Pure CSS with Tailwind Breakpoints

**Rationale**: The codebase already uses Tailwind CSS responsive classes consistently. Using the same approach ensures consistency and avoids introducing new patterns.

**Alternatives Considered**:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Tailwind classes (`sm:`, `md:`) | Consistent with codebase, no JS overhead, SSR-friendly | Requires duplicate markup for complex cases | **Selected** |
| `useMediaQuery` hook + conditional render | More control, dynamic behavior | Adds JS complexity, flash on hydration | Rejected |
| CSS Container Queries | Modern, component-scoped | Limited browser support, not used in codebase | Rejected |

**Evidence**: TopHeader.tsx uses `hidden sm:inline-flex` and `hidden md:flex` patterns. MainLayout.tsx uses `p-4 md:p-6` responsive padding.

---

## 2. Breakpoint Selection

### Decision: 640px (Tailwind `sm:` breakpoint)

**Rationale**: This is the standard Tailwind breakpoint for mobile-to-tablet transition and matches the spec requirement.

**Breakpoint Mapping**:

| Tailwind | Pixels | Use Case |
|----------|--------|----------|
| (default) | < 640px | Mobile: Compact calendar view |
| `sm:` | >= 640px | Tablet/Desktop: Full calendar view |

**Evidence**: The spec explicitly states "screen width < 640px" for compact mode. The existing codebase uses `sm:` as the first responsive breakpoint consistently.

---

## 3. Category Badge Design

### Decision: Icon + Count Badge Component

**Rationale**: The GitHub issue recommends "a badge with the icon of the Event Category and a counter." This matches the existing visual language of category icons used in EventCard.

**Design Details**:

| Element | Value | Rationale |
|---------|-------|-----------|
| Icon size | 12x12px (h-3 w-3) | Smaller than EventCard (h-3.5) for compact cells |
| Count position | Bottom-right overlay | Standard badge pattern |
| Count max | 99+ | Prevents overflow, matches spec edge case |
| Background | Category color at 20% opacity | Consistent with EventCard background pattern |
| Max badges per day | 4 + overflow indicator | Spec edge case: "+N more" for >5 categories |

**Evidence**: EventCard.tsx uses `h-2.5 w-2.5` for compact icons with `${event.category.color}20` background.

---

## 4. Cell Height Optimization

### Decision: Reduce from 100px to 48px on Mobile

**Rationale**: The spec requires "at least 50% smaller height" for compact cells. 48px provides adequate touch target while fitting more content.

**Calculations**:

| Mode | Min Height | Days Visible (320px screen) |
|------|------------|----------------------------|
| Desktop | 100px | ~3.2 rows (partial visibility) |
| Mobile | 48px | ~6.6 rows (full month visible) |

**Touch Target Compliance**: 48px height exceeds iOS/Android minimum (44px).

**Evidence**: Current calendar uses `min-h-[100px]`. The spec success criteria SC-005 requires "at least 50% smaller height."

---

## 5. Click/Tap Behavior

### Decision: Preserve Existing Day Click Handler

**Rationale**: The existing `onDayClick` handler already opens the Day Detail popup. No behavior changes needed.

**Flow Preserved**:
1. Tap day number → Opens Day Detail dialog with event list
2. Tap event in dialog → Opens Event View card
3. Tap Edit in Event View → Opens Event Form dialog

**Evidence**: EventCalendar.tsx lines 147-164 handle day clicks, showing day detail dialog when events exist, or create dialog when empty.

---

## 6. Event Grouping Strategy

### Decision: Group by Category with Count

**Rationale**: The spec requires "category icon badges with event counts for each day in compact mode, grouped by event category."

**Implementation Approach**:

```typescript
// Pseudocode for grouping
const groupEventsByCategory = (events: Event[]) => {
  const grouped = new Map<string, { category: Category; count: number }>()
  events.forEach(event => {
    const key = event.category?.guid || 'uncategorized'
    const existing = grouped.get(key)
    if (existing) {
      existing.count++
    } else {
      grouped.set(key, { category: event.category, count: 1 })
    }
  })
  return Array.from(grouped.values())
}
```

**Evidence**: Events already have `category` property with `icon` and `color` fields. EventCard.tsx accesses these at lines 60-63.

---

## 7. Accessibility Requirements

### Decision: Extend Existing ARIA Patterns

**Rationale**: EventCalendar already has comprehensive accessibility. Compact mode must maintain these standards.

**Requirements**:

| Feature | Current Implementation | Compact Mode |
|---------|----------------------|--------------|
| Screen reader | `role="gridcell"` with aria-label | Preserve with updated label |
| Keyboard nav | Arrow keys, Enter/Space | Preserve unchanged |
| Focus visible | Ring indicator | Preserve unchanged |
| Touch target | 100px cells | 48px (still exceeds 44px minimum) |

**Enhanced ARIA Label** for compact mode:
```
"January 15: 2 concerts, 1 sports event"
```

**Evidence**: EventCalendar.tsx lines 200-250 implement full keyboard navigation. Line 265+ implements ARIA attributes.

---

## 8. Testing Strategy

### Decision: Extend Existing Test Patterns + New Hook Tests

**Rationale**: The codebase has established patterns for component and hook testing. Follow these patterns for new code.

**Test Categories**:

| Test Type | File | Coverage |
|-----------|------|----------|
| Unit | `CategoryBadge.test.tsx` | Icon rendering, count display, overflow handling |
| Unit | `CompactCalendarCell.test.tsx` | Badge composition, click handler, ARIA |
| Unit | `useMediaQuery.test.ts` | Hook state, SSR handling |
| Integration | `EventCalendar.test.tsx` | Responsive layout switching |

**Mock Requirements**:
- `window.matchMedia` - already mocked in `tests/setup.ts`
- Enhance mock to support dynamic `matches` value for responsive tests

**Evidence**: `tests/setup.ts` lines 33-46 mock `matchMedia`. `tests/hooks/useSidebarCollapse.test.ts` shows hook testing pattern.

---

## 9. Performance Considerations

### Decision: CSS-Only Responsive, No JavaScript Layout Switching

**Rationale**: CSS media queries are more performant than JS-based viewport detection for layout changes.

**Performance Targets**:

| Metric | Target | Approach |
|--------|--------|----------|
| Layout switch | <16ms (1 frame) | CSS media queries |
| Re-render on resize | None | Pure CSS, no state changes |
| Memory | No increase | No additional event listeners |

**Evidence**: TopHeader.tsx uses `hidden md:flex` for responsive content without JS state.

---

## 10. Existing Code to Modify

### Files Requiring Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `EventCalendar.tsx` | Modify | Add responsive classes, conditional compact cell rendering |
| `EventCard.tsx` | None | Already supports compact mode |
| `EventsPage.tsx` | Minor | Verify dialog mobile behavior (likely no changes) |

### New Files

| File | Purpose |
|------|---------|
| `CategoryBadge.tsx` | Icon + count badge component |
| `CompactCalendarCell.tsx` | Mobile day cell with badges |
| `useMediaQuery.ts` | Optional: viewport hook for JS-based logic |

---

## Conclusion

All research questions have been resolved. The implementation will:

1. Use Tailwind CSS responsive classes (`sm:` breakpoint at 640px)
2. Create CategoryBadge component for icon + count display
3. Create CompactCalendarCell component for mobile day rendering
4. Reduce cell height to 48px on mobile (52% reduction)
5. Preserve existing click handlers and dialog flows
6. Group events by category for badge display
7. Maintain full accessibility compliance
8. Follow existing test patterns with enhanced matchMedia mock

No external research or API investigation needed - all patterns exist in the codebase.
