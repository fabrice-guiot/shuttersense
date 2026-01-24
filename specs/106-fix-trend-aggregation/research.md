# Research: Fix Trend Aggregation for Storage-Optimized Results

**Feature**: 106-fix-trend-aggregation
**Date**: 2026-01-23

## Overview

This document captures research findings for implementing the fill-forward algorithm to fix trend aggregation bugs introduced by the storage optimization (Issue #92).

---

## 1. Current Implementation Analysis

### 1.1 Storage Optimization Background (Issue #92)

The storage optimization stores a `NO_CHANGE` result instead of duplicating full result data when a collection's state hasn't changed. This is implemented in `AnalysisResult` with:

- `status = ResultStatus.NO_CHANGE` - Indicates this is a lightweight record
- `no_change_copy = True` - Flag for UI/API to identify filled records
- `results_json` - Still contains the full metrics (copied from previous result)

**Key Insight**: The `NO_CHANGE` results DO contain the full metric data. The bug is not about missing data, but about WHEN results are created. Collections that don't change don't get new results at all for those days.

### 1.2 Current Aggregation Logic (Buggy)

Location: `backend/src/services/trend_service.py`

The current aggregation in each of the four methods follows this pattern:

```python
# 1. Deduplicate: keep last result per Collection + Day
deduplicated = _deduplicate_results_by_day(results, key_func)

# 2. Aggregate only what exists (BUG: missing collections are excluded)
aggregated_by_date: Dict[str, Dict[str, Any]] = {}
for (date_key, collection_id), result in deduplicated.items():
    if date_key not in aggregated_by_date:
        aggregated_by_date[date_key] = { ... }
    # Aggregate this result into the date's totals
    agg = aggregated_by_date[date_key]
    agg['some_metric'] += extract_metric(result)
```

**The Bug**: When Collection B has no result for Day 4 (because it was unchanged), the aggregation for Day 4 only includes Collection A's value, causing a false drop.

### 1.3 Affected Methods

| Method | Lines | Tool | Dedup Key |
|--------|-------|------|-----------|
| `get_photostats_trends()` | 334-407 | photostats | (date, collection_id) |
| `get_photo_pairing_trends()` | 522-588 | photo_pairing | (date, collection_id) |
| `get_pipeline_validation_trends()` | 728-849 | pipeline_validation | (date, collection_id, pipeline_id, version) |
| `get_trend_summary()` | 1199-1283 | All tools | Same as above per tool |

---

## 2. Solution Design Decisions

### 2.1 Fill-Forward Algorithm Location

**Decision**: Implement fill-forward in the service layer at query time.

**Rationale**:
- Preserves storage optimization (no additional DB writes)
- Mathematically correct (carrying forward = unchanged state = same value)
- Transparent (can mark calculated values for UI)
- Performance acceptable (bounded queries)

**Alternatives Rejected**:

| Alternative | Why Rejected |
|-------------|--------------|
| Store daily snapshots | Defeats storage optimization purpose |
| SQL window functions (LAG) | Complex, hard to maintain, doesn't handle gaps well |
| Materialized views | Stale data, maintenance complexity, same logic needed |

### 2.2 Seed Value Strategy

**Decision**: Single query per tool to get latest result per collection before window.

**Implementation**:
```python
def _get_seed_values(self, tool, team_id, collection_ids, before_date, metric_extractor):
    # Use DISTINCT ON (collection_id) with ORDER BY completed_at DESC
    # to get exactly one result per collection (the latest before window)
    query = self.db.query(AnalysisResult).filter(
        AnalysisResult.tool == tool,
        AnalysisResult.team_id == team_id,
        AnalysisResult.collection_id.in_(collection_ids),
        AnalysisResult.completed_at < datetime.combine(before_date, datetime.min.time()),
        AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE])
    ).order_by(
        AnalysisResult.collection_id,
        desc(AnalysisResult.completed_at)
    ).distinct(AnalysisResult.collection_id)

    return {r.collection_id: metric_extractor(r) for r in query.all()}
```

**Note**: PostgreSQL supports `DISTINCT ON`. For SQLite (tests), we can fallback to subquery approach.

### 2.3 Collection Set Identification

**Decision**: The set of collections to aggregate is determined by:

1. **If `collection_ids` filter provided**: Use those collections
2. **If no filter (aggregated mode)**: Use all collections that have at least one result (seed OR in window)

**Rationale**: This matches user expectations - if a collection exists and has been analyzed, it should be included in aggregation.

### 2.4 Calculated Count Field

**Decision**: Add `calculated_count: int = 0` to aggregated point schemas.

**Semantics**:
- `calculated_count = 0`: All collections have actual results for this date
- `calculated_count > 0`: This many collections used filled (carried forward) values

**Frontend Usage**:
- Tooltip: "12 of 15 collections have actual data" (when calculated_count = 3)
- Optional: Visual styling (lighter opacity, different marker) for points with calculated_count > 0

### 2.5 Edge Case Handling

| Edge Case | Handling |
|-----------|----------|
| New collection added mid-window | Excluded until first result appears, then included |
| Collection never analyzed before window | No seed available, excluded from aggregation |
| All collections unchanged on a day | Only NO_CHANGE results exist, fill forward all values |
| Empty window (no results at all) | Return empty data points as before (null values) |
| Single collection mode (comparison) | No fill-forward needed - existing behavior correct |

---

## 3. Implementation Approach

### 3.1 Refactoring Strategy

Instead of duplicating fill-forward logic in each method, create reusable helpers:

1. **`_get_seed_values()`**: Query seed state before window
2. **`_fill_forward_aggregation()`**: Core fill-forward algorithm
3. **Tool-specific extractors**: Functions to extract metrics from results

### 3.2 Fill-Forward Algorithm Pseudocode

```python
def _fill_forward_aggregation(
    deduplicated,      # {(date, dedup_key): result}
    seed_values,       # {collection_id: {metrics}}
    all_collection_ids,  # Set of all collections to include
    sorted_dates,      # List of dates in window
    metric_extractor,  # result -> {metrics}
    aggregator         # (agg_dict, metrics) -> updates agg_dict
):
    # Track last known value for each collection
    last_known = dict(seed_values)  # Start with seeds

    aggregated_by_date = {}

    for date_key in sorted_dates:
        # Initialize daily aggregate
        daily_agg = {'collections_included': 0, 'calculated_count': 0, ...}

        for collection_id in all_collection_ids:
            lookup_key = (date_key, collection_id)  # Simplified, may vary by tool

            if lookup_key in deduplicated:
                # Actual result exists
                result = deduplicated[lookup_key]
                metrics = metric_extractor(result)
                last_known[collection_id] = metrics
                aggregator(daily_agg, metrics)
                daily_agg['collections_included'] += 1
            elif collection_id in last_known:
                # Fill forward from last known value
                metrics = last_known[collection_id]
                aggregator(daily_agg, metrics)
                daily_agg['collections_included'] += 1
                daily_agg['calculated_count'] += 1
            # else: collection has no history yet, skip

        aggregated_by_date[date_key] = daily_agg

    return aggregated_by_date
```

### 3.3 Pipeline Validation Complexity

Pipeline Validation uses a compound dedup key: `(date, collection_id, pipeline_id, version)`.

**Decision**: For aggregation purposes, we still aggregate per collection per day. If a collection has multiple pipeline results on the same day, they're all included. The fill-forward applies at the collection level, not the pipeline level.

---

## 4. Testing Strategy

### 4.1 Unit Tests

| Test Case | Description |
|-----------|-------------|
| `test_fill_forward_with_gaps` | Collection A has results Day 1, 4; Collection B has result Day 1 only. Verify Day 2, 3, 4 aggregation is correct. |
| `test_seed_retrieval` | Verify seed query returns correct "before window" result per collection. |
| `test_new_collection_mid_window` | Collection added Day 3. Verify it's excluded Days 1-2, included from Day 3. |
| `test_all_no_change_day` | Day where all results are NO_CHANGE. Verify fill-forward works. |
| `test_single_collection_mode` | Comparison mode (1-5 collections). Verify no fill-forward applied. |
| `test_calculated_count_accuracy` | Verify calculated_count matches number of filled values. |

### 4.2 Integration Tests

| Test Case | Description |
|-----------|-------------|
| `test_issue_105_scenario` | Exact example from issue: 2 collections, staggered results. Verify sequence 18→18→20→20. |
| `test_multi_day_gap` | Collection unchanged for 7+ days while others change. Verify correct aggregation throughout. |
| `test_boundary_conditions` | First/last day of window edge cases. |

### 4.3 Regression Tests

| Test Case | Description |
|-----------|-------------|
| `test_existing_photostats_aggregated` | Verify existing aggregated mode still works. |
| `test_existing_comparison_mode` | Verify comparison mode unchanged. |
| `test_date_range_filtering` | Verify date filters work with fill-forward. |

---

## 5. Performance Analysis

### 5.1 Additional Query Cost

**Seed Query**: One additional query per tool per request.

```sql
SELECT DISTINCT ON (collection_id) *
FROM analysis_results
WHERE tool = 'photostats'
  AND team_id = :team_id
  AND collection_id IN (:collection_ids)
  AND completed_at < :window_start
ORDER BY collection_id, completed_at DESC
```

**Estimated Cost**: < 10ms for typical collection counts (< 100 collections).

### 5.2 Fill-Forward Loop Cost

**Complexity**: O(days × collections)

For typical cases:
- 30-day window × 20 collections = 600 iterations
- 365-day window × 100 collections = 36,500 iterations

**Estimated Cost**: < 5ms for typical cases, < 50ms for large windows.

### 5.3 Total Impact

Expected additional latency: 10-50ms for typical requests. Acceptable for trend queries which are already not real-time.

---

## 6. Schema Changes Summary

### 6.1 Backend (Pydantic Schemas)

```python
# backend/src/schemas/trends.py

class PhotoStatsAggregatedPoint(BaseModel):
    # ... existing fields ...
    calculated_count: int = Field(0, ge=0, description="Number of collections with filled (calculated) values")

class PhotoPairingAggregatedPoint(BaseModel):
    # ... existing fields ...
    calculated_count: int = Field(0, ge=0, description="Number of collections with filled (calculated) values")

class PipelineValidationAggregatedPoint(BaseModel):
    # ... existing fields ...
    calculated_count: int = Field(0, ge=0, description="Number of collections with filled (calculated) values")
```

### 6.2 Frontend (TypeScript Types)

```typescript
// frontend/src/contracts/api/trends-api.ts

export interface PhotoStatsAggregatedPoint {
  // ... existing fields ...
  /** Number of collections with filled (calculated) values for this date */
  calculated_count: number
}

// Similar for PhotoPairingAggregatedPoint, PipelineValidationAggregatedPoint
```

### 6.3 Database

**No database schema changes required.** The fix is purely at the query/service layer.

---

## 7. Conclusion

The fill-forward algorithm is the correct solution for this bug:

1. **Preserves storage optimization** - No changes to how results are stored
2. **Mathematically correct** - Unchanged state = same value = carry forward
3. **Transparent** - calculated_count field allows UI to distinguish actual vs. filled
4. **Performant** - Bounded additional queries, acceptable latency increase
5. **Maintainable** - Shared helper functions reduce code duplication
