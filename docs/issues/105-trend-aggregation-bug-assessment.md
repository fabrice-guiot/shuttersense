# Issue #105: Trend Calculations Incorrect Due to Optimized Storage

## Assessment Summary

**Status**: Bug Confirmed
**Severity**: High
**Root Cause**: Storage optimization (Issue #92) breaks aggregated trend calculations
**Proposed Solution**: Correct and recommended

---

## Problem Analysis

### Context

Issue #92 introduced storage optimization for analysis results. When a collection's state hasn't changed between runs, a lightweight `NO_CHANGE` result is stored instead of duplicating the full result data. This optimization significantly reduces storage usage but has an unintended side effect on trend aggregation.

### The Bug

The current trend aggregation logic in `TrendService` (located at `backend/src/services/trend_service.py`) performs aggregation based solely on results that exist in the database for each specific day. When not all collections have results for a given day (because unchanged collections don't generate new results), the aggregation produces incorrect totals.

### Example from Issue (Validated)

Given:
- 2 collections
- Day 1: Both collections analyzed (Collection 1: KPI=5, Collection 2: KPI=13)
- Day 4: Collection 1 changes (KPI=7), Collection 2 unchanged (no new record)
- Day 9: Query the trend

**Current Behavior (Incorrect):**
| Day | Records Found | Aggregated Sum |
|-----|--------------|----------------|
| 1   | 2 (Col1=5, Col2=13) | 18 |
| 3   | 1 (Col1 "no change" preservation) | 5 |
| 4   | 1 (Col1 inflection) | 7 |
| 9   | 2 (latest for both) | 20 |

The sequence appears as: 18 → 5 → 7 → 20 (shows a false drop on days 3-4)

**Expected Behavior:**
| Day | Records + Filled Values | Aggregated Sum |
|-----|------------------------|----------------|
| 1   | Col1=5, Col2=13 | 18 |
| 3   | Col1=5, Col2=13 (filled) | 18 |
| 4   | Col1=7, Col2=13 (filled) | 20 |
| 9   | Col1=7, Col2=13 | 20 |

The sequence should be: 18 → 18 → 20 → 20 (stable until actual change)

### Code Location

The bug manifests in the aggregated mode sections of:
- `get_photostats_trends()` - lines 334-407
- `get_photo_pairing_trends()` - lines 522-588
- `get_pipeline_validation_trends()` - lines 728-849
- `get_trend_summary()` - lines 1199-1283

The aggregation loop (example from PhotoStats):
```python
for (date_key, collection_id), result in deduplicated.items():
    # Only processes results that EXIST in deduplicated
    # Missing collections for this date are simply not included
    if date_key not in aggregated_by_date:
        aggregated_by_date[date_key] = { ... }
    agg = aggregated_by_date[date_key]
    agg['orphaned_images'] += orphaned_images_count  # Missing collections = missing values
```

---

## Proposed Solution Assessment

### Issue Author's Proposal

The algorithm proposed in Issue #105 is:

1. **Seed Phase**: Query the latest result for each collection BEFORE the time window starts (the "seed state")
2. **Query Phase**: Fetch all results within the time window per collection
3. **Fill Phase**: Loop through each day in the window:
   - Day 1: If a collection has no result, use its seed value
   - Subsequent days: If a collection has no result, carry forward from its last known value
   - Mark all filled values as "calculated values"
4. **Aggregate Phase**: Perform aggregation on the filled dataset (all days now have values for all collections)

### Assessment: Correct and Recommended

This algorithm is the right approach for the following reasons:

1. **Preserves storage optimization**: The database remains optimized; filling happens in the service layer at query time
2. **Mathematically correct**: Carrying forward the last known value is semantically accurate (unchanged state = same value)
3. **Transparent to users**: Marking "calculated values" allows the UI to distinguish interpolated vs. actual data points
4. **Performance acceptable**: Extra queries are bounded (one seed query per tool, data is already partially loaded)

---

## Implementation Recommendations

### 1. Create a Utility Function

```python
def _fill_forward_aggregation(
    deduplicated: Dict[Tuple[str, Any], AnalysisResult],
    seed_values: Dict[int, Dict[str, Any]],  # collection_id -> metric values
    all_collections: Set[int],
    date_range: List[str],
    metric_extractor: Callable[[AnalysisResult], Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Fill forward missing collection values for accurate aggregation.

    Returns:
        Dict mapping date -> {
            'aggregated_values': {...},
            'collections_included': int,
            'calculated_count': int,  # How many values were filled
            ...
        }
    """
```

### 2. Add Seed Query Method

```python
def _get_seed_values(
    self,
    tool: str,
    team_id: int,
    collection_ids: List[int],
    before_date: date
) -> Dict[int, Dict[str, Any]]:
    """
    Get the latest result for each collection before the window starts.
    This provides the "seed state" for fill-forward logic.
    """
```

### 3. Modify Response Schemas

Add to aggregated point schemas (e.g., `PhotoStatsAggregatedPoint`):

```python
class PhotoStatsAggregatedPoint(BaseModel):
    # Existing fields...
    calculated_count: int = 0  # Number of collections with filled (not actual) values
```

### 4. Frontend Display

- Use `calculated_count > 0` to show visual indicator (e.g., dashed line segments, lighter color, or tooltip)
- Consider showing "X of Y collections have actual data for this day"

---

## Edge Cases to Handle

### 1. New Collection Added Mid-Window

A collection created after the window start has no seed value. Options:
- **Option A (Recommended)**: Exclude from aggregation until its first result, then include
- **Option B**: Use zero/null as seed (could skew aggregation downward)

### 2. Collection Deleted During Window

Results may still exist for deleted collections. Options:
- **Option A (Recommended)**: Include historical data (it's still valid historical state)
- **Option B**: Exclude deleted collections entirely

### 3. Empty Seed (Collection Never Analyzed Before Window)

If no result exists before the window, the collection has no seed. Handle like "new collection."

### 4. Very Large Date Ranges

For multi-year ranges with many collections, the fill-forward loop could be expensive. Consider:
- Lazy computation (only fill dates that will be displayed)
- Limit maximum date range in API
- Cache seed values per request

---

## Alternative Approaches Considered (Not Recommended)

### Alternative 1: Store Daily Snapshots

Store a snapshot of all collection states daily, regardless of changes.

**Pros**: Simple queries, always accurate
**Cons**: Defeats storage optimization purpose; exponential storage growth

### Alternative 2: SQL Window Functions

Use `LAG()` with `PARTITION BY collection_id ORDER BY date` to fill forward in SQL.

**Pros**: Database handles filling
**Cons**:
- Complex SQL, hard to maintain
- Doesn't handle gaps spanning multiple days well
- Still needs application logic for seed values before window

### Alternative 3: Materialized Views

Pre-compute aggregated trends in a materialized view, refreshed periodically.

**Pros**: Fast queries
**Cons**:
- Stale data between refreshes
- Additional storage overhead
- Maintenance complexity
- Doesn't solve the fundamental fill-forward problem without same logic

---

## Testing Strategy

### Unit Tests

1. **Test fill-forward with gaps**: Multiple days without data for one collection
2. **Test seed retrieval**: Verify correct "before window" result is found
3. **Test new collection**: Added mid-window, verify correct aggregation
4. **Test all collections unchanged**: Day with only NO_CHANGE results
5. **Test single collection mode**: Should not use fill-forward (comparison mode)

### Integration Tests

1. **Scenario from Issue #105**: Exact example with 2 collections, verify sequence
2. **Multi-day gap**: Collection unchanged for 7+ days while others change
3. **Boundary conditions**: First/last day of window edge cases

---

## Conclusion

Issue #105 correctly identifies a critical bug introduced by the storage optimization in Issue #92. The proposed fill-forward algorithm is the appropriate solution. Implementation should:

1. Add seed value retrieval for the "before window" state
2. Implement fill-forward logic in the service layer
3. Track and expose "calculated" vs. "actual" values in the response
4. Handle edge cases for new/deleted collections
5. Update frontend to visually distinguish interpolated data

The fix maintains the storage optimization benefits while ensuring trend aggregations are mathematically accurate.
