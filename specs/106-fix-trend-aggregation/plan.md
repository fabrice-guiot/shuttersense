# Implementation Plan: Fix Trend Aggregation for Storage-Optimized Results

**Branch**: `106-fix-trend-aggregation` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/106-fix-trend-aggregation/spec.md`
**Related Issue**: [#105](https://github.com/fabrice-guiot/shuttersense/issues/105)

## Summary

Fix the trend aggregation bug introduced by storage optimization (Issue #92). The current aggregation logic produces incorrect totals when not all collections have results for a given day (because unchanged collections don't generate new results). The fix implements a fill-forward algorithm that:

1. Seeds collection values from the latest result before the trend window starts
2. Fills forward missing values for each collection on each day in the window
3. Tracks which values are actual vs. calculated (filled)
4. Applies consistently across PhotoStats, Photo Pairing, Pipeline Validation, and Trend Summary methods

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, React 18.3.1, Recharts
**Storage**: PostgreSQL 12+ (JSONB columns for analysis results)
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Web application (Docker deployment)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Trend queries complete within existing response time expectations
**Constraints**: Must not modify storage optimization behavior (Issue #92)
**Scale/Scope**: Affects 4 service methods, 3 schema files, frontend chart components

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a backend service fix, not a CLI tool
- [x] **Testing & Quality**: Tests planned for fill-forward logic, seed retrieval, edge cases. pytest configured.
- [x] **User-Centric Design**:
  - For analysis tools: N/A (service layer fix)
  - Are error messages clear and actionable? N/A (no new user-facing errors)
  - Is the implementation simple (YAGNI)? Yes - fill-forward at query time, no new storage
  - Is structured logging included? Will use existing logger
- [x] **Shared Infrastructure**: N/A - No config changes needed
- [x] **Simplicity**: Yes - fill-forward is the simplest approach that preserves storage optimization
- [x] **Global Unique Identifiers (GUIDs)**: No changes to entity identification
- [x] **Multi-Tenancy and Authentication**: All trend queries already filter by team_id via TenantContext
- [x] **Agent-Only Execution**: N/A - Trend service is read-only, not job execution

**Violations/Exceptions**: None. The fix maintains all existing architectural patterns.

## Project Structure

### Documentation (this feature)

```text
specs/106-fix-trend-aggregation/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Schema changes documentation
├── quickstart.md        # Developer quickstart guide
├── contracts/           # API contract updates
│   └── trends-api.md    # Updated API response schemas
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── services/
│   │   └── trend_service.py    # Main fix: fill-forward logic
│   └── schemas/
│       └── trends.py           # Add calculated_count field to aggregated points
└── tests/
    ├── unit/
    │   └── test_trend_service.py    # Unit tests for fill-forward
    └── integration/
        └── test_trend_aggregation.py  # Integration tests

frontend/
├── src/
│   ├── contracts/api/
│   │   └── trends-api.ts       # Add calculated_count to TypeScript types
│   └── components/charts/      # Visual distinction for calculated points
└── tests/                      # Frontend tests if applicable
```

**Structure Decision**: Web application structure (backend + frontend). All changes follow existing patterns.

## Complexity Tracking

No violations - all changes follow existing patterns and maintain simplicity.

---

## Phase 0: Research

See [research.md](./research.md) for detailed findings.

### Key Decisions

1. **Fill-Forward Algorithm**: Implement at query time in service layer (preserves storage optimization)
2. **Seed Query Strategy**: Single query per tool type to get latest result per collection before window
3. **Calculated Count Field**: Add `calculated_count: int` to all aggregated point schemas
4. **Frontend Indication**: Tooltip showing "X of Y collections have actual data for this day"

---

## Phase 1: Design

### 1.1 Data Model Changes

See [data-model.md](./data-model.md) for complete schema documentation.

**Summary**: Add `calculated_count` field to aggregated point schemas:
- `PhotoStatsAggregatedPoint.calculated_count: int = 0`
- `PhotoPairingAggregatedPoint.calculated_count: int = 0`
- `PipelineValidationAggregatedPoint.calculated_count: int = 0`

No database schema changes required.

### 1.2 API Contract Changes

See [contracts/trends-api.md](./contracts/trends-api.md) for updated contracts.

**Summary**: Add `calculated_count` to trend response aggregated points. This is a non-breaking addition.

### 1.3 Backend Implementation Design

#### New Helper Functions

```python
# In trend_service.py

def _get_seed_values(
    self,
    tool: str,
    team_id: int,
    collection_ids: List[int],
    before_date: date,
    metric_extractor: Callable[[AnalysisResult], Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    """
    Get the latest result for each collection before the window starts.
    This provides the "seed state" for fill-forward logic.

    Args:
        tool: Tool type (photostats, photo_pairing, pipeline_validation)
        team_id: Team ID for tenant isolation
        collection_ids: List of collection IDs to seed
        before_date: Date before which to find the latest result
        metric_extractor: Function to extract metric dict from result

    Returns:
        Dict mapping collection_id -> metric values dict
    """

def _fill_forward_aggregation(
    self,
    deduplicated: Dict[Tuple[str, Any], AnalysisResult],
    seed_values: Dict[int, Dict[str, Any]],
    all_collection_ids: Set[int],
    sorted_dates: List[str],
    metric_extractor: Callable[[AnalysisResult], Dict[str, Any]],
    aggregator: Callable[[Dict[str, Any], Dict[str, Any]], None]
) -> Dict[str, Dict[str, Any]]:
    """
    Fill forward missing collection values for accurate aggregation.

    Args:
        deduplicated: Dict of (date_key, collection_id) -> result
        seed_values: Dict of collection_id -> seed metric values
        all_collection_ids: Set of all collection IDs to include
        sorted_dates: List of dates in the window (sorted ascending)
        metric_extractor: Function to extract metrics from result
        aggregator: Function to aggregate metrics into daily totals

    Returns:
        Dict mapping date -> {
            'aggregated_values': {...},
            'collections_included': int,
            'calculated_count': int,
            ...
        }
    """
```

#### Method Updates

Each of the four affected methods follows this pattern:

1. **Before aggregation loop**: Query seed values for all collections
2. **Build collection set**: Identify all collections that should participate
3. **Replace aggregation loop**: Use `_fill_forward_aggregation()` helper
4. **Update response**: Include `calculated_count` in each data point

### 1.4 Frontend Implementation Design

#### TypeScript Type Updates

```typescript
// In trends-api.ts, add to all aggregated point types:
export interface PhotoStatsAggregatedPoint {
  // ... existing fields ...
  /** Number of collections with filled (calculated) values for this date */
  calculated_count: number
}
```

#### Visual Distinction

- Chart tooltip shows: "X of Y collections have actual data" when `calculated_count > 0`
- Optional: Different point styling (lighter opacity, dashed segment) for calculated points

### 1.5 Quickstart Guide

See [quickstart.md](./quickstart.md) for developer setup and testing instructions.

---

## Phase 2: Tasks

*Generated via `/speckit.tasks` command - not part of this plan document.*

---

## Implementation Notes

### Edge Cases Handled

1. **New Collection Added Mid-Window**: Excluded until first result, then included
2. **Collection Never Analyzed**: No seed, excluded from aggregation
3. **All Collections Unchanged on a Day**: Fill forward from previous values
4. **Empty Trend Window**: Return empty/null data points as before
5. **Single Collection Mode**: No fill-forward needed (comparison mode)

### Performance Considerations

- Seed query is bounded: one query per tool per request
- Fill-forward loop is O(days × collections) - acceptable for typical windows
- No additional database storage required

### Testing Strategy

1. **Unit Tests**: Fill-forward helper function with various scenarios
2. **Integration Tests**: Exact Issue #105 scenario (2 collections, staggered results)
3. **Regression Tests**: Verify existing behavior for single-collection mode
