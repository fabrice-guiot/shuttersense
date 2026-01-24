# Data Model: Fix Trend Aggregation for Storage-Optimized Results

**Feature**: 106-fix-trend-aggregation
**Date**: 2026-01-23

## Overview

This document describes the schema changes required to support the fill-forward aggregation fix. The changes are minimal - only Pydantic response schemas are updated. No database schema changes are required.

---

## 1. Database Schema

### No Changes Required

The fix operates entirely at the query/service layer. The existing `AnalysisResult` model and its storage optimization (Issue #92) remain unchanged:

| Column | Type | Description |
|--------|------|-------------|
| `status` | `ResultStatus` | Includes `NO_CHANGE` for optimized storage |
| `no_change_copy` | `Boolean` | True when result is a lightweight copy |
| `results_json` | `JSONB` | Full metrics (populated even for NO_CHANGE) |

---

## 2. Pydantic Schema Changes

### 2.1 PhotoStatsAggregatedPoint

**Location**: `backend/src/schemas/trends.py`

**Change**: Add `calculated_count` field

```python
class PhotoStatsAggregatedPoint(BaseModel):
    """
    Aggregated data point for PhotoStats trend chart.
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    orphaned_images: Optional[int] = Field(None, description="Total orphaned images across all collections")
    orphaned_metadata: Optional[int] = Field(None, description="Total orphaned metadata files (XMP)")
    collections_included: int = Field(0, ge=0, description="Number of collections with data for this date")
    no_change_count: int = Field(0, ge=0, description="Count of NO_CHANGE results included")
    has_transition: bool = Field(False, description="Whether this date has an Input State transition")
    # NEW FIELD
    calculated_count: int = Field(
        0,
        ge=0,
        description="Number of collections with filled (calculated) values for this date. "
                    "0 means all collections have actual results."
    )
```

### 2.2 PhotoPairingAggregatedPoint

**Location**: `backend/src/schemas/trends.py`

**Change**: Add `calculated_count` field

```python
class PhotoPairingAggregatedPoint(BaseModel):
    """
    Aggregated data point for Photo Pairing trend chart.
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    group_count: Optional[int] = Field(None, description="Total image groups across all collections")
    image_count: Optional[int] = Field(None, description="Total images across all collections")
    collections_included: int = Field(0, ge=0, description="Number of collections with data for this date")
    no_change_count: int = Field(0, ge=0, description="Count of NO_CHANGE results included")
    has_transition: bool = Field(False, description="Whether this date has an Input State transition")
    # NEW FIELD
    calculated_count: int = Field(
        0,
        ge=0,
        description="Number of collections with filled (calculated) values for this date. "
                    "0 means all collections have actual results."
    )
```

### 2.3 PipelineValidationAggregatedPoint

**Location**: `backend/src/schemas/trends.py`

**Change**: Add `calculated_count` field

```python
class PipelineValidationAggregatedPoint(BaseModel):
    """
    Aggregated data point for Pipeline Validation trend chart.
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    overall_consistency_pct: Optional[float] = Field(None, description="Overall consistency %")
    overall_inconsistent_pct: Optional[float] = Field(None, description="Overall inconsistent %")
    black_box_consistency_pct: Optional[float] = Field(None, description="Black Box Archive consistency %")
    browsable_consistency_pct: Optional[float] = Field(None, description="Browsable Archive consistency %")
    total_images: Optional[int] = Field(None, description="Total images validated")
    consistent_count: Optional[int] = Field(None, description="Total CONSISTENT count")
    inconsistent_count: Optional[int] = Field(None, description="Total INCONSISTENT count")
    collections_included: int = Field(0, ge=0, description="Number of collections with data for this date")
    no_change_count: int = Field(0, ge=0, description="Count of NO_CHANGE results included")
    has_transition: bool = Field(False, description="Whether this date has an Input State transition")
    # NEW FIELD
    calculated_count: int = Field(
        0,
        ge=0,
        description="Number of collections with filled (calculated) values for this date. "
                    "0 means all collections have actual results."
    )
```

---

## 3. Semantic Meaning

### 3.1 Field Interpretation

| Field | Meaning |
|-------|---------|
| `collections_included` | Total number of collections contributing to this data point |
| `calculated_count` | How many of those collections used filled (carried forward) values |
| Actual count | `collections_included - calculated_count` = collections with actual results |

### 3.2 Example

For a trend window with 5 collections:

| Date | Collections with Results | Collections Filled | Interpretation |
|------|-------------------------|-------------------|----------------|
| 2026-01-15 | 5 | 0 | All collections have actual data |
| 2026-01-16 | 3 | 2 | 3 actual, 2 carried forward |
| 2026-01-17 | 1 | 4 | 1 actual, 4 carried forward |
| 2026-01-18 | 0 | 5 | All data is carried forward |

### 3.3 UI Representation

The frontend can display:
- **Tooltip**: "3 of 5 collections have actual data for this day"
- **Visual Indicator**: Points with `calculated_count > 0` can be styled differently (lighter color, different marker)

---

## 4. Backward Compatibility

### 4.1 API Compatibility

The change is **backward compatible**:
- New field has default value (`calculated_count: int = 0`)
- Existing clients that don't read this field will continue to work
- No existing fields are modified or removed

### 4.2 Frontend Compatibility

Frontend changes are optional for initial deployment:
- Charts will work without consuming `calculated_count`
- Enhanced display can be added incrementally

---

## 5. Validation Rules

| Field | Rule | Rationale |
|-------|------|-----------|
| `calculated_count >= 0` | Non-negative | Cannot have negative filled values |
| `calculated_count <= collections_included` | Bounded | Cannot fill more than total collections |

Note: The second rule is implicit and ensured by the algorithm, not enforced by schema validation.

---

## 6. Related Entities

### 6.1 Existing Entities (Unchanged)

| Entity | Relevance |
|--------|-----------|
| `AnalysisResult` | Source of trend data, NO_CHANGE status used |
| `Collection` | Identified by collection_id in aggregation |
| `ResultStatus` | Enum with COMPLETED, NO_CHANGE values |

### 6.2 Conceptual Entities (Service Layer Only)

| Concept | Description |
|---------|-------------|
| Seed Value | Latest result before trend window per collection |
| Filled Value | Value carried forward from previous day |
| Actual Value | Value from an actual AnalysisResult for that day |
