# Addendum: Fix Calendar Conflict Visualization Limitations (Issue #193)

**Date:** 2026-02-14
**Parent Feature:** #182 — Calendar Conflict Visualization & Event Picker
**Issue:** #193 — Address limitations of the Calendar Conflict Visualization & Event Picker

## Context

Issue #182 shipped a calendar conflict detection & event picker feature. Production testing revealed several design flaws, primarily because QA only tested 2-event conflict groups. The core issues are: (1) the "Confirm" UX is backwards (should maximize attendance, not minimize it), (2) conflict counts per day are wrong (counts groups instead of edges), (3) group resolution status uses event count instead of edge resolution, and (4) `consecutive_window_days` can't be set to 0.

---

## Changes

### 1. Backend: Fix group resolution status (edge-based)

**File:** `backend/src/services/conflict_service.py`

- **`_derive_group_status`** (line 548-558): Change signature to `(events, edges)`. A group is RESOLVED when every edge has at least one skipped event, PARTIALLY_RESOLVED when some do, UNRESOLVED when none do.
- **`_build_groups`** (line 538): Pass `component_edges.get(root, [])` to `_derive_group_status`.
- **Edge normalization** (line 512): After the union-find loop, normalize each edge so `event_a_guid < event_b_guid` for deterministic ordering.

### 2. Backend: Add 5-event production scenario test

**File:** `backend/tests/integration/test_conflict_endpoints.py` (new test class)

Create `TestFiveEventProductionScenario` matching issue #193's exact test case:
- 2 series, 2 locations (NYC ~2,451mi from LA), 5 events Thu–Sun
- `consecutive_window_days=0`, `travel_buffer_days=3`
- Assert conflict edge counts: Thu=1, Fri=2, Sat=5, Sun=2
- Assert 1 conflict group with all 5 events
- Assert skipping Series 2 (2 events) resolves all conflicts

### 3. Backend: Update existing status derivation tests

**File:** `backend/tests/unit/test_conflict_service.py`

- Update `_derive_group_status` tests to pass edges alongside events
- Add tests: 5 events with 2 skipped where all edges are resolved → RESOLVED
- Add test: partial edge resolution → PARTIALLY_RESOLVED

### 4. Frontend: UX reversal — "Skip" / "Restore" buttons

**File:** `frontend/src/components/events/ConflictResolutionPanel.tsx`

- Replace `onConfirmEvent` prop with `onSkipEvent` + `onRestoreEvent`
- **ConflictEventRow**: Replace "Confirm" button (Check icon) with "Skip" button (SkipForward icon). Add "Restore" button (RotateCcw icon) for skipped events.
- **handleSkipEvent**: sends `[{event_guid, attendance: 'skipped'}]` (single event only)
- **handleRestoreEvent**: sends `[{event_guid, attendance: 'planned'}]`
- Show "Restore" for skipped events regardless of group status (always allow undo)
- Remove `otherGuids` prop from ConflictEventRow (no longer needed)

**File:** `frontend/src/components/events/RadarComparisonDialog.tsx`

- Replace `handleConfirm` with `handleSkip` / `handleRestore`
- **EventDetailCard**: Replace "Confirm" with "Skip", remove `pendingConfirm` two-step guard (skip is easily reversible). Add "Restore" button for skipped events.
- Remove `otherEventCount` prop (no longer needed)

### 5. Frontend: Fix day conflict count (edge-based counting)

**File:** `frontend/src/hooks/useConflicts.ts` — `buildConflictLookups()`

Replace group-per-day counting with edge-per-day counting:
- Build `guid→attendance` and `guid→event_date` lookups from group events
- Iterate edges (not groups). For each edge, determine dates it touches (`Set([dateA, dateB])`)
- An edge is "resolved" if at least one of its events is skipped
- Increment `byDate` counters per touched date

### 6. Frontend: Day-scoped conflict view

**File:** `frontend/src/pages/EventsPage.tsx` — `selectedDayConflicts` (line 441-447)

Replace full-group filtering with day-scoped group construction:
- For each global group, filter edges where at least one event is on the selected day
- Collect only events referenced by those filtered edges
- Recompute day-scoped status from the filtered edges (same edge-based logic as backend)
- Use original `group_id` for resolve requests

**Also:** Change `unresolvedConflictCount` (line 449-451) from counting unresolved groups to counting unresolved edges across all day-scoped groups.

### 7. Frontend: Allow consecutive_window_days = 0

**File:** `frontend/src/components/settings/ConflictRulesSection.tsx` (line 96)

- Change `min: 1` → `min: 0` for `consecutive_window_days`
- Update description: `'Window of days to check for distance conflicts (0 = same-day only)'`

### 8. Frontend: Update component tests

- `ConflictResolutionPanel.test.tsx`: Expect "Skip"/"Restore" instead of "Confirm"
- `RadarComparisonDialog.test.tsx`: Remove two-step confirm tests, add skip/restore tests
- Add `useConflicts.test.ts` tests for edge-based `buildConflictLookups`

---

## Production Test Scenario (from Issue #193)

### Setup
- 5 events, 2 series, 2 locations
- Series 1: 3 events (Thu, Fri, Sat) at NYC, travel_required=True
- Series 2: 2 events (Sat, Sun) at LA, travel_required=True
- Distance NYC↔LA: ~2,451 miles (> 150mi threshold)
- Config: `travel_buffer_days=3`, `consecutive_window_days=0`

### Expected Conflicts Per Day
| Day | Events on Day | Conflict Edges | Events in Day-Conflict Group |
|-----|--------------|----------------|------------------------------|
| Thu | E1/S1 | 1 (E1/S1↔E1/S2 travel buffer) | 2 (E1/S1, E1/S2) |
| Fri | E2/S1 | 2 (E2/S1↔E1/S2, E2/S1↔E2/S2 travel buffer) | 3 (E2/S1, E1/S2, E2/S2) |
| Sat | E3/S1, E1/S2 | 5 (time overlap + distance + 3 travel buffers) | 5 (all) |
| Sun | E2/S2 | 2 (E2/S2↔E2/S1, E2/S2↔E3/S1 travel buffer) | 3 (E2/S2, E2/S1, E3/S1) |

### Saturday Conflicts Detail
1. E3/S1 ↔ E1/S2: Time Overlap (same day, same time)
2. E3/S1 ↔ E1/S2: Distance (>70mi colocation radius, same day with window=0)
3. E1/S1 ↔ E1/S2: Travel Buffer (2 days apart, >150mi, travel required)
4. E2/S1 ↔ E1/S2: Travel Buffer (1 day apart, >150mi, travel required)
5. E3/S1 ↔ E2/S2: Travel Buffer (1 day apart, >150mi, travel required)

### Expected Resolution
- 1 global conflict group containing all 5 events
- Skipping E1/S2 + E2/S2 (Series 2) resolves ALL conflicts
- Result: attend 3 events (Series 1), skip 2 events (Series 2)

---

## Verification

1. **Backend tests:** `venv/bin/python -m pytest backend/tests/unit/test_conflict_service.py backend/tests/integration/test_conflict_endpoints.py -v`
2. **Frontend type check:** `cd frontend && npx tsc --noEmit`
3. **Frontend tests:** `cd frontend && npx vitest run --reporter=verbose`
4. **Manual test:** Create the 5-event scenario in the UI, verify badge counts per day, verify Skip/Restore flow, verify `consecutive_window_days=0` setting
