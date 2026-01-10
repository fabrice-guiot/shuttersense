# Plan: Remove Numeric IDs from API in Favor of GUIDs Only

## Overview

This plan removes numeric `id` fields from all API response schemas, converts foreign key references to use GUIDs, removes backward compatibility logic for numeric IDs, and updates all API endpoints to accept GUIDs only.

Since this is a pre-release (v0.x), we're cleaning up rather than maintaining deprecated backward compatibility.

## Summary of Changes

| Area | Change |
|------|--------|
| Response schemas | Remove `id: int`, keep only `guid: str` |
| Foreign keys | Use `_guid` suffix (e.g., `pipeline_guid`) or nested objects |
| API endpoints | Only accept GUIDs, remove numeric ID support |
| Deprecation warnings | Remove all `X-Deprecation-Warning` logic |
| Tests | Update to use GUIDs exclusively |

---

## Phase 1: Backend Schema Changes

### 1.1 ConnectorResponse
**File:** `backend/src/schemas/collection.py`

- Remove: `id: int`
- Keep: `guid: str` (con_xxx)

### 1.2 CollectionResponse
**File:** `backend/src/schemas/collection.py`

- Remove: `id: int`, `connector_id: Optional[int]`, `pipeline_id: Optional[int]`
- Keep: `guid: str` (col_xxx)
- Add: `pipeline_guid: Optional[str]` (pip_xxx format)
- Note: `connector` nested object provides connector info (with guid)

### 1.3 CollectionCreate/Update
**File:** `backend/src/schemas/collection.py`

- Change: `connector_id: Optional[int]` → `connector_guid: Optional[str]`
- Change: `pipeline_id: Optional[int]` → `pipeline_guid: Optional[str]`

### 1.4 CollectionFilesResponse
**File:** `backend/src/schemas/collection.py`

- Change: `collection_id: int` → `collection_guid: str`

### 1.5 PipelineSummary & PipelineResponse
**File:** `backend/src/schemas/pipelines.py`

- Remove: `id: int`
- Keep: `guid: str` (pip_xxx)

### 1.6 PipelineStatsResponse
**File:** `backend/src/schemas/pipelines.py`

- Change: `default_pipeline_id: Optional[int]` → `default_pipeline_guid: Optional[str]`

### 1.7 DeleteResponse (pipelines & results)
**Files:** `backend/src/schemas/pipelines.py`, `backend/src/schemas/results.py`

- Change: `deleted_id: int` → `deleted_guid: str`

### 1.8 AnalysisResultSummary & AnalysisResultResponse
**File:** `backend/src/schemas/results.py`

- Remove: `id: int`, `collection_id: Optional[int]`, `pipeline_id: Optional[int]`
- Keep: `guid: str` (res_xxx)
- Add: `collection_guid: Optional[str]`, `pipeline_guid: Optional[str]`

### 1.9 ResultsQueryParams
**File:** `backend/src/schemas/results.py`

- Change: `collection_id: Optional[int]` → `collection_guid: Optional[str]`

---

## Phase 2: Backend Service Changes

### 2.1 GuidService
**File:** `backend/src/services/guid.py`

- Update `parse_identifier()` to ONLY accept GUIDs (remove numeric ID support)
- Simplify to return just UUID, not tuple with `is_numeric`

### 2.2 Service Methods
**Files:**
- `backend/src/services/collection_service.py`
- `backend/src/services/connector_service.py`
- `backend/src/services/pipeline_service.py`
- `backend/src/services/result_service.py`

For each service:
- Change `get_by_identifier()` to `get_by_guid()` returning just the entity
- Remove `is_numeric` return value
- Update methods accepting FK IDs to accept GUIDs instead
- Add helper methods to resolve GUIDs to internal IDs when needed

### 2.3 Response Building
- Ensure response objects populate `pipeline_guid`, `collection_guid` from relationships

---

## Phase 3: Backend API Changes

### 3.1 Path Parameters
**Files:**
- `backend/src/api/collections.py`
- `backend/src/api/connectors.py`
- `backend/src/api/pipelines.py`
- `backend/src/api/results.py`

- Change `{identifier}` to `{guid}` in route paths
- Remove dual-mode parsing logic
- Remove all deprecation warning header additions

### 3.2 Action Endpoints
Update to accept GUID:
- `/collections/{guid}/test`
- `/collections/{guid}/refresh`
- `/connectors/{guid}/test`
- `/pipelines/{guid}/activate`, `deactivate`, `set-default`, etc.

### 3.3 Query Parameters
- Change `collection_id` query param to `collection_guid`

---

## Phase 4: Frontend Changes

### 4.1 Type Definitions
**Files:**
- `frontend/src/contracts/api/collection-api.ts`
- `frontend/src/contracts/api/connector-api.ts`
- `frontend/src/contracts/api/pipelines-api.ts`
- `frontend/src/contracts/api/results-api.ts`

Remove `id: number` from all entity types, update FK fields to use `_guid` suffix.

### 4.2 Service Functions
**Files:**
- `frontend/src/services/collections.ts`
- `frontend/src/services/connectors.ts`
- `frontend/src/services/pipelines.ts`
- `frontend/src/services/results.ts`

Change all function signatures from `number | string` to `string` (GUID only).

### 4.3 Request Schemas
Update create/update request interfaces to use `connector_guid`, `pipeline_guid`.

### 4.4 Hooks & Pages
Update to use `.guid` instead of `.id` for all entity references.

---

## Phase 5: Test Updates

### 5.1 Backend Tests
**Files to update:**
- `backend/tests/unit/test_api_guids.py` - Remove numeric ID tests
- `backend/tests/unit/test_api_*.py` - Use GUIDs in URLs
- `backend/tests/unit/test_*_service.py` - Update service method calls
- `backend/tests/integration/*.py` - Update all ID references

### 5.2 Frontend Tests
**Files to update:**
- `frontend/tests/mocks/handlers.ts` - Major refactor for GUID-only
- `frontend/tests/hooks/*.test.ts` - Use `.guid` not `.id`
- `frontend/tests/components/*.test.tsx` - Update mock data

---

## Implementation Order

1. Backend schemas (all at once)
2. Backend services
3. Backend API endpoints
4. Backend tests (verify backend works)
5. Frontend types and services
6. Frontend hooks and pages
7. Frontend tests (verify frontend works)

---

## Verification

After implementation, verify:

1. **Backend unit tests pass:**
   ```bash
   python -m pytest backend/tests/unit -v
   ```

2. **Backend integration tests pass:**
   ```bash
   python -m pytest backend/tests/integration -v
   ```

3. **Frontend tests pass:**
   ```bash
   cd frontend && npm test -- --run
   ```

4. **Manual API verification:**
   - Create entities and verify responses contain `guid` but no `id`
   - Verify FK fields use `_guid` suffix
   - Verify endpoints reject numeric IDs with 400/404 errors
   - Verify nested objects (like connector in collection) contain guid

---

## Key Files Summary

### Backend Schemas:
- `backend/src/schemas/collection.py`
- `backend/src/schemas/pipelines.py`
- `backend/src/schemas/results.py`

### Backend Services:
- `backend/src/services/guid.py`
- `backend/src/services/collection_service.py`
- `backend/src/services/connector_service.py`
- `backend/src/services/pipeline_service.py`
- `backend/src/services/result_service.py`

### Backend API:
- `backend/src/api/collections.py`
- `backend/src/api/connectors.py`
- `backend/src/api/pipelines.py`
- `backend/src/api/results.py`

### Frontend Types:
- `frontend/src/contracts/api/collection-api.ts`
- `frontend/src/contracts/api/connector-api.ts`
- `frontend/src/contracts/api/pipelines-api.ts`
- `frontend/src/contracts/api/results-api.ts`

### Frontend Services:
- `frontend/src/services/collections.ts`
- `frontend/src/services/connectors.ts`
- `frontend/src/services/pipelines.ts`
- `frontend/src/services/results.ts`
