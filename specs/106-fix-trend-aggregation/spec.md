# Feature Specification: Fix Trend Aggregation for Storage-Optimized Results

**Feature Branch**: `106-fix-trend-aggregation`
**Created**: 2026-01-23
**Status**: Draft
**Input**: User description: "the fix for issue #105, especially taking into account the assessment documented in docs/issues/105-trend-aggregation-bug-assessment.md"
**Related Issue**: [#105](https://github.com/fabrice-guiot/shuttersense/issues/105)

## Problem Statement

The storage optimization feature (Issue #92) introduced a bug in trend aggregation calculations. When a collection's state hasn't changed between analysis runs, a lightweight `NO_CHANGE` result is stored instead of duplicating the full result data. This optimization reduces storage usage but breaks aggregated trend calculations.

The current trend aggregation logic only processes results that exist in the database for each specific day. When not all collections have results for a given day (because unchanged collections don't generate new results), the aggregation produces incorrect totals that show false drops and spikes in trend data.

### Example of Current Bug

Given 2 collections:
- Day 1: Both collections analyzed (Collection 1: KPI=5, Collection 2: KPI=13) → Aggregate: 18
- Day 4: Collection 1 changes (KPI=7), Collection 2 unchanged (no new record)
- Day 9: Query the trend

**Current Behavior (Incorrect):**

| Day | Records Found | Aggregated Sum |
|-----|---------------|----------------|
| 1   | 2 records     | 18             |
| 3   | 1 record      | 5              |
| 4   | 1 record      | 7              |
| 9   | 2 records     | 20             |

Sequence appears as: 18 → 5 → 7 → 20 (false drop on days 3-4)

**Expected Behavior:**

| Day | Collections Included | Aggregated Sum |
|-----|---------------------|----------------|
| 1   | Both                | 18             |
| 3   | Both (Col2 filled)  | 18             |
| 4   | Both (Col2 filled)  | 20             |
| 9   | Both                | 20             |

Sequence should be: 18 → 18 → 20 → 20 (stable until actual change)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Multi-Collection Trend Viewing (Priority: P1)

As a user viewing aggregated trends across multiple collections, I need to see mathematically accurate trend data that correctly represents the combined state of all collections over time, even when some collections haven't changed and therefore have no new results stored.

**Why this priority**: This is the core bug fix. Without accurate aggregation, users receive misleading trend information that could lead to incorrect conclusions about their photo collection health over time.

**Independent Test**: Can be fully tested by running analysis on multiple collections on different days, then viewing the aggregated trend chart and verifying the values are mathematically correct.

**Acceptance Scenarios**:

1. **Given** 2 collections where Collection 1 has results for Day 1 and Day 4, and Collection 2 has results only for Day 1, **When** I view the aggregated trend for Days 1-7, **Then** the aggregation for Day 4 includes Collection 2's last known value (from Day 1) combined with Collection 1's Day 4 value.

2. **Given** 3 collections with staggered result dates across a 14-day period, **When** I view the aggregated trend for that period, **Then** every day in the trend shows the sum of the most recent known value for each collection as of that day.

3. **Given** a collection that has not been analyzed before the trend window starts but has a result from before the window, **When** I view an aggregated trend starting after that result date, **Then** the seed value from before the window is used for days until a new result appears.

---

### User Story 2 - Visual Distinction of Calculated vs. Actual Data Points (Priority: P2)

As a user viewing trend charts, I need to distinguish between actual data points (where all collections have real results) and calculated data points (where some collections' values were filled forward), so I can understand the confidence level of the displayed data.

**Why this priority**: This provides transparency to users about the nature of the data they're viewing. Without it, users might not realize some points are interpolated.

**Independent Test**: Can be tested by examining trend data responses and UI charts to verify that calculated data points are visually distinguished from actual data points.

**Acceptance Scenarios**:

1. **Given** a trend response that includes both actual and filled values, **When** the data is displayed in a chart, **Then** data points with filled values are visually distinguishable (e.g., different styling, tooltip indicator).

2. **Given** a trend response for a date where all collections have actual results, **When** the data is displayed, **Then** that data point is shown as a fully actual data point with no "calculated" indicator.

3. **Given** a trend response for a date where some collections have filled values, **When** I hover over that data point, **Then** I can see information about how many collections had actual vs. calculated values.

---

### User Story 3 - Consistent Behavior Across All Tools (Priority: P1)

As a user, I expect the trend aggregation fix to work consistently across PhotoStats, Photo Pairing, and Pipeline Validation tools, providing accurate aggregated trends regardless of which tool I'm analyzing.

**Why this priority**: The bug exists in all three tool trend methods. A partial fix would be confusing and incomplete.

**Independent Test**: Can be tested by verifying aggregation accuracy independently for each of the three tools.

**Acceptance Scenarios**:

1. **Given** multiple collections with PhotoStats results on different days, **When** I view aggregated PhotoStats trends, **Then** the fill-forward logic correctly aggregates all collections.

2. **Given** multiple collections with Photo Pairing results on different days, **When** I view aggregated Photo Pairing trends, **Then** the fill-forward logic correctly aggregates all collections.

3. **Given** multiple collections with Pipeline Validation results on different days, **When** I view aggregated Pipeline Validation trends, **Then** the fill-forward logic correctly aggregates all collections.

---

### Edge Cases

- **New Collection Added Mid-Window**: A collection created after the trend window starts has no seed value. It should be excluded from aggregation until its first result, then included from that point forward.

- **Collection Never Analyzed Before Window**: If a collection has no result before or during the trend window, it has no seed. Handle like a new collection.

- **Empty Trend Window**: If the trend window has no actual results for any collection, the response should gracefully handle this (return seed values or empty).

- **Very Large Date Ranges**: For multi-year ranges with many collections, the fill-forward computation should remain performant.

- **All Collections Unchanged on a Day**: A day with only `NO_CHANGE` results should still produce correct aggregation using filled values from the previous day.

- **Single Collection Mode (Comparison)**: The fill-forward logic applies only to aggregated mode. Single-collection trends should continue working without fill-forward.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST retrieve the latest result for each collection before the trend window starts (seed values) to establish the baseline state.

- **FR-002**: System MUST fill forward missing collection values for each day in the trend window using the most recent known value for that collection.

- **FR-003**: System MUST track and expose in the response how many collections have actual vs. calculated (filled) values for each data point.

- **FR-004**: System MUST apply the fill-forward logic consistently to `get_photostats_trends()`, `get_photo_pairing_trends()`, `get_pipeline_validation_trends()`, and `get_trend_summary()` methods.

- **FR-005**: System MUST exclude collections from aggregation until they have at least one actual result (either as seed or within the window).

- **FR-006**: System MUST continue supporting single-collection trend queries without applying fill-forward logic (fill-forward applies only to aggregated multi-collection queries).

- **FR-007**: Frontend MUST visually distinguish trend data points that include calculated (filled) values from data points where all collections have actual values.

### Key Entities

- **Seed Value**: The most recent result for a collection before the trend window starts. Used as the initial state when the collection has no result on Day 1 of the window.

- **Filled Value**: A value carried forward from a collection's previous known result when no new result exists for a given day. Marked as "calculated" in the response.

- **Aggregated Point**: A single data point in the trend response representing the combined metrics across all collections for a specific date. Includes count of actual vs. calculated values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Aggregated trend totals for any date equal the sum of the most recent known values for all collections as of that date (mathematical accuracy).

- **SC-002**: 100% of existing trend-related tests pass after the fix (no regression).

- **SC-003**: New tests verify the exact scenario from Issue #105 (2 collections, staggered results, correct sequence 18 → 18 → 20 → 20).

- **SC-004**: Trend queries complete within acceptable response times (no significant performance degradation from fill-forward computation).

- **SC-005**: Users can visually identify which data points include calculated values when viewing trend charts.

## Assumptions

- The storage optimization (Issue #92) behavior remains unchanged; fill-forward happens at query time in the service layer, not in the persistence layer.
- The existing `NO_CHANGE` result type continues to be stored as designed.
- Frontend charting library supports styling individual data points differently (for calculated value indication).
- Performance requirements for large date ranges will be addressed through lazy computation or reasonable API limits if needed during implementation.
