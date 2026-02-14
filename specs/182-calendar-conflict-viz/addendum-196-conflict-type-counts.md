# Addendum: Show Conflict Types in Compare Events Dialog (Issue #196)

**Date:** 2026-02-14
**Parent Feature:** #182 — Calendar Conflict Visualization & Event Picker
**Issue:** #196 — Show Conflict types in the Event comparison table (Compare Events Dialog)

## Context

The RadarComparisonDialog currently shows a **Rating Dimensions** table (Venue, Organizer, Performers, Logistics, Readiness) summarized by a **Composite** row. While the `ConflictGroup` object already contains typed edges (`time_overlap`, `distance`, `travel_buffer`), these conflict types are not surfaced in the comparison table. Users cannot see *why* events conflict at a glance.

## Change: Add Conflicts Section to Comparison Table

### Frontend-only — no backend changes required

All data is already available in `ConflictGroup.edges`. The change adds a new **Conflicts** section below the Composite row in the dimension breakdown table.

### Table Layout

```
┌─────────────┬──────────────────┬──────────────────┐
│ Dimension   │ Morning Workshop │ Afternoon Meetup  │
├─────────────┼──────────────────┼──────────────────┤
│ Venue       │ 80               │ 50               │
│ Organizer   │ 70               │ 40               │
│ Performers  │ 60               │  0               │
│ Logistics   │ 90               │ 100              │
│ Readiness   │ 100              │ 80               │
│ Composite   │ 80               │ 54               │  ← bold
├─────────────┼──────────────────┼──────────────────┤
│ Conflicts   │                  │                  │  ← section header
│ Time Overlap│ 1                │ 1                │
│ Distance    │ 1                │ —                │
│ Total       │ 2                │ 1                │  ← bold
└─────────────┴──────────────────┴──────────────────┘
```

### Rules

- **Section header**: "Conflicts" label row with top border for visual separation
- **One row per conflict type** that has at least one edge in the group (no empty rows)
- **Cell value**: count of edges where the event is `event_a_guid` or `event_b_guid` for that type; zero shown as `—`
- **Total row**: sum of all conflict edges per event, styled bold
- **Counts do not change when an event is skipped** — all edges are counted regardless of attendance status

### Computation

```typescript
// For each conflict type, count edges involving each event
for (const edge of group.edges) {
  counts[edge.conflict_type][edge.event_a_guid] += 1
  counts[edge.conflict_type][edge.event_b_guid] += 1
}
```

Only conflict types with at least one edge are rendered.

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/components/events/RadarComparisonDialog.tsx` | Add Conflicts section to breakdown table |
| `frontend/src/components/events/__tests__/RadarComparisonDialog.test.tsx` | Tests for conflict type rows, totals, and skip invariance |

## Verification

1. Type check: `cd frontend && npx tsc --noEmit`
2. Unit tests: `npx vitest run src/components/events/__tests__/RadarComparisonDialog.test.tsx`
3. Manual: Planner view → click conflict group connector → verify Conflicts section with correct counts
