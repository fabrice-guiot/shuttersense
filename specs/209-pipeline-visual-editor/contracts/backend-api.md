# Backend API Contracts: Pipeline Visual Graph Editor

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-15

## Modified Schemas

### PipelineNode (Extended)

**File**: `backend/src/schemas/pipelines.py`

```python
class NodePosition(BaseModel):
    """Canvas position for visual graph editor."""
    x: float = Field(..., description="X coordinate on canvas")
    y: float = Field(..., description="Y coordinate on canvas")

class PipelineNode(BaseModel):
    """A node in the pipeline graph."""
    id: str = Field(..., min_length=1, max_length=100)
    type: NodeType = Field(...)
    properties: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[NodePosition] = Field(
        None,
        description="Canvas position for visual editor. Omitted for pre-existing pipelines."
    )
```

**Impact**:
- `PipelineCreateRequest.nodes` now accepts optional `position` per node
- `PipelineUpdateRequest.nodes` now accepts optional `position` per node
- `PipelineResponse.nodes` now includes `position` when saved
- YAML export includes `position` when present; import handles absence
- Pipeline validation (`_validate_structure`) ignores `position` field
- Pipeline history snapshots automatically include position data

## Existing Endpoints (No Signature Changes)

All existing pipeline endpoints continue to work unchanged. The `position` field is optional and backward-compatible:

| Method | Path | Change |
|--------|------|--------|
| `POST /api/pipelines` | Create | Accepts optional `position` per node |
| `PUT /api/pipelines/{guid}` | Update | Accepts optional `position` per node |
| `GET /api/pipelines/{guid}` | Get | Returns `position` if saved |
| `GET /api/pipelines/{guid}/versions/{version}` | Get version | Returns `position` from snapshot |
| `GET /api/pipelines/{guid}/export` | Export YAML | Includes `position` when present |
| `POST /api/pipelines/import` | Import YAML | Handles `position` presence/absence |

## New Endpoint (Phase 3)

### GET /api/pipelines/{guid}/flow-analytics

Returns per-node and per-edge flow statistics derived from pipeline validation analysis results.

**File**: `backend/src/api/pipelines.py`

**Request**:
```
GET /api/pipelines/{guid}/flow-analytics?result_guid={optional}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `guid` | path | Yes | Pipeline GUID (`pip_...`) |
| `result_guid` | query | No | Specific analysis result GUID (`res_...`). If omitted, uses most recent completed pipeline_validation result. |

**Response (200)**:
```json
{
  "pipeline_guid": "pip_01hgw2bbg0000000000000001",
  "pipeline_version": 3,
  "result_guid": "res_01hgw2bbg0000000000000005",
  "result_created_at": "2026-02-15T10:30:00Z",
  "total_records": 1500,
  "nodes": [
    {
      "node_id": "capture_1",
      "record_count": 1500,
      "percentage": 100.0
    },
    {
      "node_id": "file_raw",
      "record_count": 1450,
      "percentage": 96.67
    }
  ],
  "edges": [
    {
      "from_node": "capture_1",
      "to_node": "file_raw",
      "record_count": 1450,
      "percentage": 96.67
    }
  ]
}
```

**Response Schemas**:
```python
class NodeFlowStats(BaseModel):
    node_id: str = Field(..., description="Pipeline node ID")
    record_count: int = Field(..., ge=0, description="Records that reached this node")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total records")

class EdgeFlowStats(BaseModel):
    from_node: str = Field(..., description="Source node ID")
    to_node: str = Field(..., description="Target node ID")
    record_count: int = Field(..., ge=0, description="Records that traversed this edge")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of upstream node's records")

class PipelineFlowAnalyticsResponse(BaseModel):
    pipeline_guid: str
    pipeline_version: int
    result_guid: str
    result_created_at: datetime
    total_records: int = Field(..., ge=0)
    nodes: List[NodeFlowStats]
    edges: List[EdgeFlowStats]
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| 400 | Invalid GUID format |
| 404 | Pipeline not found, or no pipeline_validation results exist for this pipeline |
| 404 | Specified `result_guid` not found or not a pipeline_validation result |

**Authentication**: Required (`require_auth` + `get_tenant_context`)
**Tenant Isolation**: Pipeline and results filtered by `team_id`

**Service Method**:
```python
def get_flow_analytics(
    self,
    pipeline_id: int,
    team_id: int,
    result_guid: Optional[str] = None
) -> PipelineFlowAnalyticsResponse:
    """
    Extract flow analytics from pipeline_validation analysis results.

    1. Find the target AnalysisResult:
       - If result_guid provided: look up that specific result
       - Otherwise: find most recent COMPLETED result where tool='pipeline_validation'
         and pipeline_id matches
    2. Extract path_stats from results_json
       - If path_stats is absent, return 404 (pre-Phase 3 result)
    3. Derive per-edge counts by summing image_count across all paths
       that include each edge (consecutive node pairs in each path)
    4. Derive per-node counts by summing image_count across all paths
       that include each node
    5. Calculate percentages relative to Capture node record count
    6. Return structured response with derived nodes[] and edges[]
    """
```

**Data flow**: The agent stores `path_stats` (paths + image counts) in `results_json`. The endpoint aggregates these into the `nodes[]` and `edges[]` arrays in the response. This keeps the stored data compact and path-aware, while the API returns the per-edge/per-node format that the frontend needs for visualization.

## Pipeline Validation Ignore Rule

**File**: `backend/src/services/pipeline_service.py`

The `_validate_structure()` method must strip the `position` field before validation to ensure position data does not interfere with structural validation:

```python
# In _validate_structure():
# Position is visual-only metadata, not part of pipeline structure
# The existing validation already only checks id, type, properties
# No code change needed — validation does not reference position
```

Since the existing validation only checks `id`, `type`, and `properties` fields explicitly, the `position` field is naturally ignored. No code change required.
