# Addendum: Normalize DimensionMicroBar Segment Sizes (Issue #208)

**Date:** 2026-02-14
**Parent Feature:** #182 — Calendar Conflict Visualization & Event Picker
**Issue:** #208 — Normalize DimensionMicroBar Segment Sizes

## Context

The `DimensionMicroBar` in the Planner view previously sized each dimension segment proportionally to raw score values. This meant adding or removing a dimension's score shifted **all** segments — making cross-event comparison impossible. For example, `venue_quality=80` rendered as 27.6% in one event and 26.7% in another simply because a different dimension changed.

## Change: Weight-Based Fixed Segments

Each dimension now gets a **fixed-width segment** proportional to its configured scoring weight. Within that segment, the colored fill shows the actual score (0–100) and the remaining space renders as `bg-muted`.

### Before (proportional to raw scores)

```
[venue 27.6%][org 20.7%][perf 17.2%][log 17.2%][ready 17.2%]
```

Segment widths changed whenever any score changed.

### After (fixed by weight config)

```
[venue ██████░░ 20%][org ████░░░░ 20%][perf ██░░░░░░ 20%][log ████░░░░ 20%][ready ██████░░ 20%]
```

- Outer segment width = `(weight / totalWeight) * 100%` — fixed per weight configuration
- Inner fill width = score clamped to `[0%, 100%]` — shows actual performance
- Tooltip updated to: `"Venue: 80 (20% weight)"`

### Edge Cases

- **No weights prop**: falls back to equal weights of 20 each
- **Total weight = 0**: falls back to equal weights
- **Score > 100 or < 0**: clamped to `[0%, 100%]`
- **Weights loading**: renders with equal-weight fallback; re-renders when weights arrive

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/components/events/DimensionMicroBar.tsx` | Replace proportional sizing with nested weight-based segments; add `weights?: ScoringWeightsResponse` prop |
| `frontend/src/components/events/TimelineEventMarker.tsx` | Add `scoringWeights` prop, pass to `DimensionMicroBar` |
| `frontend/src/components/events/TimelinePlanner.tsx` | Add `scoringWeights` prop, pass to both `TimelineEventMarker` render sites |
| `frontend/src/pages/EventsPage.tsx` | Fetch weights via `useScoringWeights()`, pass to `TimelinePlanner` |
| `frontend/src/components/events/__tests__/DimensionMicroBar.test.tsx` | Rewrite tests for nested structure (12 tests) |

## Not Changed

- **Backend** — no API or model changes; existing `useScoringWeights()` hook and `ScoringWeightsResponse` type reused as-is
- **EventRadarChart** — radar chart already uses its own rendering; unaffected
- **Scoring weights configuration** — same keys and semantics
- **Mobile behavior** — micro-bar remains `hidden sm:flex`
