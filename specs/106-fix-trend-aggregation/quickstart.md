# Developer Quickstart: Fix Trend Aggregation

**Feature**: 106-fix-trend-aggregation
**Date**: 2026-01-23

## Overview

This guide helps developers get started with implementing the trend aggregation fix.

---

## 1. Understanding the Bug

### The Problem

Storage optimization (Issue #92) stores `NO_CHANGE` results instead of duplicating data when a collection hasn't changed. But when aggregating trends, collections without results for a specific day are simply excluded, causing incorrect totals.

### Example

```
Day 1: Collection A = 5, Collection B = 13 → Aggregate = 18
Day 4: Collection A = 7, Collection B unchanged (no record) → Aggregate = 7 (BUG!)

Should be: Day 4 Aggregate = 7 + 13 = 20
```

### The Fix

Fill forward missing collection values using the last known value for that collection.

---

## 2. Development Setup

### Prerequisites

```bash
# Ensure you're on the feature branch
git checkout 106-fix-trend-aggregation

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies (optional for backend-only work)
cd ../frontend
npm install
```

### Run Tests

```bash
# Backend unit tests
cd backend
python -m pytest tests/unit/test_trend_service.py -v

# Backend integration tests
python -m pytest tests/integration/test_trend_aggregation.py -v

# All backend tests
python -m pytest tests/ -v
```

### Run Development Server

```bash
# Start backend
cd backend
uvicorn src.main:app --reload

# Start frontend (separate terminal)
cd frontend
npm run dev
```

---

## 3. Key Files to Modify

### Backend

| File | Changes |
|------|---------|
| `backend/src/services/trend_service.py` | Add fill-forward logic |
| `backend/src/schemas/trends.py` | Add `calculated_count` field |
| `backend/tests/unit/test_trend_service.py` | Add unit tests |
| `backend/tests/integration/test_trend_aggregation.py` | Add integration tests |

### Frontend

| File | Changes |
|------|---------|
| `frontend/src/contracts/api/trends-api.ts` | Add `calculated_count` type |
| Chart components | Optional: visual distinction for calculated points |

---

## 4. Implementation Checklist

### Phase 1: Backend Core Logic

- [ ] Add `_get_seed_values()` helper method
- [ ] Add `_fill_forward_aggregation()` helper method
- [ ] Update `get_photostats_trends()` aggregated mode
- [ ] Update `get_photo_pairing_trends()` aggregated mode
- [ ] Update `get_pipeline_validation_trends()` aggregated mode
- [ ] Update `get_trend_summary()` for both tools

### Phase 2: Schema Updates

- [ ] Add `calculated_count` to `PhotoStatsAggregatedPoint`
- [ ] Add `calculated_count` to `PhotoPairingAggregatedPoint`
- [ ] Add `calculated_count` to `PipelineValidationAggregatedPoint`

### Phase 3: Testing

- [ ] Unit tests for fill-forward helper
- [ ] Unit tests for seed retrieval
- [ ] Integration test: Issue #105 exact scenario
- [ ] Regression tests: comparison mode unchanged

### Phase 4: Frontend

- [ ] Update TypeScript types
- [ ] Optional: Add tooltip showing calculated vs actual count
- [ ] Optional: Visual styling for calculated points

---

## 5. Testing the Fix

### Manual Testing

1. Create 2 collections
2. Run PhotoStats on both on Day 1
3. Wait (or mock) Day 4, run PhotoStats on only Collection 1
4. Query `/api/trends/photostats` for the date range
5. Verify aggregation includes Collection 2's filled values

### Automated Test Template

```python
def test_issue_105_scenario(self, trend_service, sample_result, sample_collection, test_team):
    """Reproduce exact scenario from Issue #105."""
    with tempfile.TemporaryDirectory() as temp_dir:
        col1 = sample_collection(name="Collection 1", location=f"{temp_dir}/col1")
        col2 = sample_collection(name="Collection 2", location=f"{temp_dir}/col2")

    day1 = datetime(2026, 1, 1, 10, 0, 0)
    day4 = datetime(2026, 1, 4, 10, 0, 0)

    # Day 1: Both collections analyzed
    sample_result(tool="photostats", collection_id=col1.id, completed_at=day1,
                  results_json={"orphaned_images": [], "orphaned_xmp": ["a", "b", "c", "d", "e"]})  # 5
    sample_result(tool="photostats", collection_id=col2.id, completed_at=day1,
                  results_json={"orphaned_images": list(range(13)), "orphaned_xmp": []})  # 13

    # Day 4: Only Collection 1 changes
    sample_result(tool="photostats", collection_id=col1.id, completed_at=day4,
                  results_json={"orphaned_images": [], "orphaned_xmp": list(range(7))})  # 7

    # Query trends
    response = trend_service.get_photostats_trends(
        team_id=test_team.id,
        from_date=day1.date(),
        to_date=day4.date()
    )

    assert response.mode == "aggregated"

    # Find day 1 and day 4 points
    day1_point = next(p for p in response.data_points if str(p.date) == "2026-01-01")
    day4_point = next(p for p in response.data_points if str(p.date) == "2026-01-04")

    # Day 1: 5 + 13 = 18 orphaned files total
    assert day1_point.orphaned_images + day1_point.orphaned_metadata == 18
    assert day1_point.calculated_count == 0  # Both actual

    # Day 4: 7 + 13 = 20 orphaned files total (Col 2 filled forward)
    assert day4_point.orphaned_images + day4_point.orphaned_metadata == 20
    assert day4_point.calculated_count == 1  # Col 2 is filled
```

---

## 6. Debugging Tips

### Verify Seed Values

```python
# In trend_service.py, add logging:
logger.debug(f"Seed values for {tool}: {seed_values}")
```

### Verify Fill-Forward

```python
# In _fill_forward_aggregation, add logging:
for date_key in sorted_dates:
    for collection_id in all_collection_ids:
        if lookup_key in deduplicated:
            logger.debug(f"{date_key} - Col {collection_id}: ACTUAL")
        elif collection_id in last_known:
            logger.debug(f"{date_key} - Col {collection_id}: FILLED from {last_known[collection_id]}")
```

### Check API Response

```bash
# Get trends and inspect calculated_count
curl "http://localhost:8000/api/trends/photostats?from_date=2026-01-01&to_date=2026-01-10" \
  -H "Authorization: Bearer $TOKEN" | jq '.data_points[] | {date, calculated_count}'
```

---

## 7. Common Issues

### Issue: Seed query returns empty

**Symptom**: Collections not being filled forward
**Cause**: `before_date` filter excluding all results
**Fix**: Verify the window start date is after the seed result date

### Issue: calculated_count always 0

**Symptom**: No filled values even with gaps
**Cause**: Collection set not including all expected collections
**Fix**: Check `all_collection_ids` includes collections with seed but no window results

### Issue: Comparison mode affected

**Symptom**: Single-collection mode shows filled data
**Cause**: Fill-forward applied to comparison mode
**Fix**: Only apply fill-forward when `comparison_mode == False`

---

## 8. Related Documentation

- [Specification](./spec.md) - Feature requirements
- [Research](./research.md) - Algorithm design decisions
- [Data Model](./data-model.md) - Schema changes
- [API Contracts](./contracts/trends-api.md) - Response format updates
- [Issue #105](https://github.com/fabrice-guiot/shuttersense/issues/105) - Original bug report
- [Assessment](../../docs/issues/105-trend-aggregation-bug-assessment.md) - Technical analysis
