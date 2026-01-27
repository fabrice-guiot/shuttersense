# Tool Implementation Pattern

**Version:** 1.0.0
**Last Updated:** 2026-01-27
**Status:** Living Document

---

## Overview

This document defines the standard pattern for implementing new analysis tools in ShutterSense. All tools follow a consistent architecture that separates data collection from job lifecycle management.

## Core Principle

**Specialized data endpoints MUST NOT manage job lifecycle.**

The standard completion endpoint (`/api/agent/v1/jobs/{guid}/complete`) is the single source of truth for job status transitions. Specialized endpoints only store domain-specific data.

## Tool Architecture

### Components

1. **Backend Tool Service** - Business logic for tool-specific operations
2. **Agent Tool Executor** - Client-side execution logic
3. **API Endpoints** - RESTful interface for data storage
4. **AnalysisResult Record** - Persistent storage of execution results

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENT EXECUTION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Agent claims job via /api/agent/v1/jobs/claim                       │
│     └── Receives: job_guid, signing_secret, previous_result             │
│                                                                          │
│  2. Agent fetches config via /api/agent/v1/jobs/{guid}/config           │
│     └── Receives: collection/connector info, pipeline, credentials      │
│                                                                          │
│  3. Agent executes tool logic locally                                    │
│     └── Reports progress via /api/agent/v1/jobs/{guid}/progress         │
│                                                                          │
│  4. (Optional) Agent reports intermediate data to specialized endpoint   │
│     └── e.g., /api/agent/v1/jobs/{guid}/inventory/validate             │
│     └── e.g., /api/agent/v1/jobs/{guid}/inventory/folders              │
│     └── NOTE: These endpoints store data but DO NOT complete the job    │
│                                                                          │
│  5. Agent completes job via /api/agent/v1/jobs/{guid}/complete          │
│     └── Sends: results, signature, files_scanned, issues_found          │
│     └── Creates: AnalysisResult record with all metadata                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tool Types

### Collection-Based Tools

Tools that analyze files in a collection:
- `photostats` - File statistics and orphan detection
- `photo_pairing` - Filename pattern analysis
- `pipeline_validation` - Pipeline structure validation
- `collection_test` - Collection accessibility test

**AnalysisResult Links:** `collection_id`, `pipeline_id` (optional)

### Connector-Based Tools

Tools that operate on connector resources:
- `inventory_validate` - Validate inventory configuration accessibility
- `inventory_import` - Import folder structure from inventory

**AnalysisResult Links:** `connector_id`

### Pipeline-Only Tools

Tools that validate pipeline definitions without collections:
- `pipeline_validation` (display_graph mode)

**AnalysisResult Links:** `pipeline_id` only, `collection_id` = NULL

## Implementation Checklist

When implementing a new tool:

### 1. Backend Schema
- [ ] Add tool type to `ToolType` enum in `backend/src/schemas/tools.py`
- [ ] Add mode if needed to `ToolMode` enum
- [ ] Create request/response schemas if tool has specialized endpoints

### 2. Agent Executor
- [ ] Add tool handler in `agent/src/job_executor.py` `_execute_tool()`
- [ ] Create tool class in `agent/src/tools/`
- [ ] Implement progress reporting
- [ ] Ensure standard completion flow is used (no early returns)

### 3. Backend API (if specialized endpoint needed)
- [ ] Create endpoint in `backend/src/api/agent/routes.py`
- [ ] Endpoint MUST NOT modify job status
- [ ] Endpoint stores data and returns success/failure

### 4. Job Coordinator
- [ ] Handle tool in `_create_analysis_result()` if custom FK needed
- [ ] Update `_update_collection_stats_from_results()` if tool updates stats

### 5. Frontend
- [ ] Add tool type to `ToolType` in `frontend/src/contracts/api/results-api.ts`
- [ ] Add label to `TOOL_LABELS` in `ResultsTable.tsx`
- [ ] Update any tool-specific UI components

### 6. Database
- [ ] Create migration if new columns/tables needed
- [ ] Update `AnalysisResult` model if new FK relationship

## Example: Inventory Validate Tool

### Specialized Endpoint (Stores Data Only)

```python
@router.post("/jobs/{job_guid}/inventory/validate")
async def report_inventory_validation(
    job_guid: str,
    data: InventoryValidationRequest,
    ...
):
    # 1. Validate job ownership
    # 2. Update connector validation status
    db.commit()

    # NOTE: DO NOT complete the job here!
    # The agent will call /complete after this

    return InventoryValidationResponse(status=status_str, message=message)
```

### Agent Executor Flow

```python
async def _run_inventory_validate(self, job, config):
    # 1. Execute validation logic
    result = validate_inventory_config(...)

    # 2. Report data to specialized endpoint
    await self._report_inventory_validation_result(...)

    # 3. Return JobResult - will flow to standard completion
    return JobResult(
        success=True,
        results={"success": True, "manifest_count": 5}
    )
```

### Job Coordinator Handling

```python
def _create_analysis_result(self, job, completion_data):
    # Extract connector_id for inventory tools
    connector_id = None
    if job.tool in ("inventory_validate", "inventory_import"):
        progress = job.progress or {}
        connector_id = progress.get("connector_id")

    result = AnalysisResult(
        connector_id=connector_id,  # Set for inventory tools
        ...
    )
```

## Anti-Patterns

### DON'T: Complete Jobs in Specialized Endpoints

```python
# BAD - specialized endpoint completing the job
@router.post("/jobs/{guid}/my-endpoint")
async def report_data(...):
    # ... store data ...
    job.status = JobStatus.COMPLETED  # ❌ WRONG!
    job.completed_at = datetime.utcnow()
    db.commit()
```

### DON'T: Skip Standard Completion in Agent

```python
# BAD - skipping standard completion
if tool == "my_tool":
    await self._report_to_specialized_endpoint(...)
    return  # ❌ WRONG - never reaches complete_job!
```

### DO: Let Data Flow Through Standard Path

```python
# GOOD - specialized endpoint stores data only
@router.post("/jobs/{guid}/my-endpoint")
async def report_data(...):
    # Store domain data
    db.commit()
    return MyResponse(status="success")

# GOOD - agent completes via standard flow
result = await self._execute_tool(job, config)
# ... flows to standard completion ...
await self._api_client.complete_job(job_guid, completion_data)
```

## Benefits of This Pattern

1. **Single Source of Truth** - Job status managed in one place
2. **Consistent Error Handling** - All tools follow same failure path
3. **Audit Trail** - All completions create AnalysisResult records
4. **Extensibility** - New tools plug in without special cases
5. **Testability** - Standardized flow easier to test

## Related Documents

- [Domain Model](domain-model.md) - Entity relationships and AnalysisResult design
- [Agent Architecture](agent-installation.md) - Agent setup and configuration
