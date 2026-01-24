# API Contract Updates: Trend Aggregation Fix

**Feature**: 106-fix-trend-aggregation
**Date**: 2026-01-23

## Overview

This document describes the API contract changes for the trend aggregation fix. All changes are **backward compatible** - adding a new field with a default value.

---

## 1. Affected Endpoints

| Endpoint | Method | Change |
|----------|--------|--------|
| `/api/trends/photostats` | GET | Add `calculated_count` to aggregated points |
| `/api/trends/photo-pairing` | GET | Add `calculated_count` to aggregated points |
| `/api/trends/pipeline-validation` | GET | Add `calculated_count` to aggregated points |
| `/api/trends/summary` | GET | No response change, internal fix only |

---

## 2. Response Schema Changes

### 2.1 PhotoStatsAggregatedPoint

**Endpoint**: `GET /api/trends/photostats` (when `mode = "aggregated"`)

```json
{
  "date": "2026-01-15",
  "orphaned_images": 45,
  "orphaned_metadata": 12,
  "collections_included": 5,
  "no_change_count": 2,
  "has_transition": false,
  "calculated_count": 2  // NEW FIELD
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `calculated_count` | `integer` | `0` | Number of collections with filled (calculated) values. `0` means all collections have actual results for this date. |

### 2.2 PhotoPairingAggregatedPoint

**Endpoint**: `GET /api/trends/photo-pairing` (when `mode = "aggregated"`)

```json
{
  "date": "2026-01-15",
  "group_count": 1250,
  "image_count": 4500,
  "collections_included": 5,
  "no_change_count": 2,
  "has_transition": false,
  "calculated_count": 2  // NEW FIELD
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `calculated_count` | `integer` | `0` | Number of collections with filled (calculated) values. |

### 2.3 PipelineValidationAggregatedPoint

**Endpoint**: `GET /api/trends/pipeline-validation` (when `mode = "aggregated"`)

```json
{
  "date": "2026-01-15",
  "overall_consistency_pct": 92.5,
  "overall_inconsistent_pct": 2.1,
  "black_box_consistency_pct": 95.0,
  "browsable_consistency_pct": 90.0,
  "total_images": 15000,
  "consistent_count": 13875,
  "inconsistent_count": 315,
  "collections_included": 5,
  "no_change_count": 2,
  "has_transition": false,
  "calculated_count": 2  // NEW FIELD
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `calculated_count` | `integer` | `0` | Number of collections with filled (calculated) values. |

---

## 3. Complete Response Examples

### 3.1 PhotoStats Aggregated Response

```json
{
  "mode": "aggregated",
  "data_points": [
    {
      "date": "2026-01-13",
      "orphaned_images": 45,
      "orphaned_metadata": 12,
      "collections_included": 5,
      "no_change_count": 0,
      "has_transition": false,
      "calculated_count": 0
    },
    {
      "date": "2026-01-14",
      "orphaned_images": 45,
      "orphaned_metadata": 12,
      "collections_included": 5,
      "no_change_count": 0,
      "has_transition": false,
      "calculated_count": 3
    },
    {
      "date": "2026-01-15",
      "orphaned_images": 52,
      "orphaned_metadata": 14,
      "collections_included": 5,
      "no_change_count": 1,
      "has_transition": true,
      "calculated_count": 2
    }
  ],
  "collections": []
}
```

**Interpretation**:
- Jan 13: All 5 collections have actual results
- Jan 14: 2 collections have actual results, 3 are filled forward
- Jan 15: 3 collections have actual results (1 is NO_CHANGE), 2 are filled forward

---

## 4. TypeScript Type Updates

### 4.1 Frontend Contract

**File**: `frontend/src/contracts/api/trends-api.ts`

```typescript
/** Aggregated data point for PhotoStats (summed across all collections) */
export interface PhotoStatsAggregatedPoint {
  date: string
  orphaned_images: number | null
  orphaned_metadata: number | null
  collections_included: number
  no_change_count: number
  has_transition: boolean
  /** Number of collections with filled (calculated) values for this date */
  calculated_count: number  // NEW FIELD
}

/** Aggregated data point for Photo Pairing (summed across all collections) */
export interface PhotoPairingAggregatedPoint {
  date: string
  group_count: number | null
  image_count: number | null
  collections_included: number
  no_change_count: number
  has_transition: boolean
  /** Number of collections with filled (calculated) values for this date */
  calculated_count: number  // NEW FIELD
}

/** Aggregated data point for Pipeline Validation */
export interface PipelineValidationAggregatedPoint {
  date: string
  overall_consistency_pct: number | null
  overall_inconsistent_pct: number | null
  black_box_consistency_pct: number | null
  browsable_consistency_pct: number | null
  total_images: number | null
  consistent_count: number | null
  inconsistent_count: number | null
  collections_included: number
  no_change_count: number
  has_transition: boolean
  /** Number of collections with filled (calculated) values for this date */
  calculated_count: number  // NEW FIELD
}
```

---

## 5. OpenAPI Schema Updates

### 5.1 PhotoStatsAggregatedPoint

```yaml
PhotoStatsAggregatedPoint:
  type: object
  required:
    - date
    - collections_included
    - no_change_count
    - has_transition
    - calculated_count
  properties:
    date:
      type: string
      format: date
      description: Date (YYYY-MM-DD)
    orphaned_images:
      type: integer
      nullable: true
      description: Total orphaned images across all collections
    orphaned_metadata:
      type: integer
      nullable: true
      description: Total orphaned metadata files (XMP)
    collections_included:
      type: integer
      minimum: 0
      description: Number of collections with data for this date
    no_change_count:
      type: integer
      minimum: 0
      description: Count of NO_CHANGE results included
    has_transition:
      type: boolean
      description: Whether this date has an Input State transition
    calculated_count:
      type: integer
      minimum: 0
      default: 0
      description: Number of collections with filled (calculated) values
```

---

## 6. Backward Compatibility

### 6.1 Existing Clients

Clients that don't read `calculated_count` will continue to work:
- Field has default value of `0`
- No existing fields are modified
- Response structure unchanged

### 6.2 Upgrade Path

1. Deploy backend with new field
2. Frontend can be updated incrementally to consume `calculated_count`
3. No client-side changes required for basic functionality

---

## 7. Error Responses

No changes to error responses. Existing error handling remains:

```json
{
  "detail": "Invalid query parameters",
  "userMessage": "Please check your filter values"
}
```

---

## 8. Query Parameters

No changes to query parameters. Existing parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `collection_ids` | string | Comma-separated collection IDs |
| `from_date` | date | Start of date range (YYYY-MM-DD) |
| `to_date` | date | End of date range (YYYY-MM-DD) |
| `limit` | integer | Maximum data points (default: 50) |
