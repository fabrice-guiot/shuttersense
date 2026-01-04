# Research: Remote Photo Collections Completion

**Feature**: 007-remote-photos-completion
**Date**: 2026-01-03
**Status**: Complete

## Overview

This document consolidates research findings for implementing Phases 4-8 of the Remote Photo Collections feature. All technical decisions are documented with rationale and alternatives considered.

---

## Research Task 1: CLI Tool Integration Pattern

**Question**: How should the web backend invoke existing CLI tools (PhotoStats, Photo Pairing, Pipeline Validation) programmatically?

**Decision**: Import and instantiate CLI tool classes directly in Python backend services.

**Rationale**:
- CLI tools are Python modules with well-defined classes (PhotoStats, PhotoPairing, PipelineValidator)
- Classes already support programmatic instantiation with folder_path and config_path parameters
- Direct invocation avoids subprocess overhead and enables progress callback injection
- Results are returned as Python dictionaries, easily stored in JSONB

**Implementation Approach**:
```python
# In tool_service.py
from photo_stats import PhotoStats
from photo_pairing import PhotoPairing
from pipeline_validation import PipelineValidator

class ToolService:
    def run_photostats(self, collection_path: str, progress_callback):
        tool = PhotoStats(collection_path)
        tool.scan_folder()  # Inject progress callback
        return tool.stats  # Return dict for JSONB storage
```

**Alternatives Considered**:
1. **Subprocess execution**: Would require parsing stdout for progress, complex error handling, slower
2. **Message queue (Celery/RQ)**: Overkill for single-user localhost deployment, adds infrastructure complexity
3. **REST API to CLI**: Would duplicate tool logic, unnecessary network overhead

---

## Research Task 2: WebSocket Progress Updates

**Question**: How to implement real-time progress updates during tool execution?

**Decision**: Use FastAPI's native WebSocket support with starlette.websockets.

**Rationale**:
- FastAPI has built-in WebSocket support via starlette
- Existing CORS configuration already handles localhost:3000
- Single connection per tool execution, simple broadcast pattern
- No additional dependencies required

**Implementation Approach**:
```python
# Backend: websocket.py
from fastapi import WebSocket
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # job_id -> connections

    async def broadcast_progress(self, job_id: str, data: dict):
        for connection in self.active_connections.get(job_id, []):
            await connection.send_json(data)

# Frontend: useWebSocket hook
const [socket, setSocket] = useState<WebSocket | null>(null);
useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);
    ws.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        setProgress(progress);
    };
    return () => ws.close();
}, [jobId]);
```

**Alternatives Considered**:
1. **Server-Sent Events (SSE)**: Simpler but one-way; WebSocket allows bidirectional (future: cancel from UI)
2. **Polling**: Higher latency, more server load, poor UX
3. **Socket.IO**: Additional dependency, unnecessary features for this use case

---

## Research Task 3: Collection Statistics Update Strategy

**Question**: When and how should collection statistics (storage_used, file_count, image_count) be updated?

**Decision**: Update statistics transactionally after successful tool completion within the same database transaction as result storage.

**Rationale**:
- Ensures consistency: if result storage fails, statistics remain unchanged
- Clear update logic: PhotoStats → storage/files, Photo Pairing/Pipeline Validation → images
- Existing Collection model already has columns from migration 002
- TopHeader KPIs fetch via existing `/api/collections/stats` endpoint

**Implementation Approach**:
```python
# In tool_service.py
def save_result_and_update_stats(self, db: Session, result: AnalysisResult):
    with db.begin():
        db.add(result)

        # Update collection statistics based on tool type
        collection = db.query(Collection).get(result.collection_id)
        if result.tool == 'photostats':
            collection.storage_used = result.results_json.get('total_size')
            collection.file_count = result.results_json.get('total_files')
        elif result.tool in ('photo_pairing', 'pipeline_validation'):
            collection.image_group_count = result.results_json.get('group_count')
            collection.image_count = result.results_json.get('image_count')

        collection.last_stats_update = datetime.utcnow()
```

**Alternatives Considered**:
1. **Separate background job**: Adds complexity, potential inconsistency
2. **On-demand calculation**: Slow for large collections, poor KPI responsiveness
3. **Periodic refresh**: Stale data between refreshes, unnecessary complexity

---

## Research Task 4: Pipeline Structure Validation

**Question**: How to validate pipeline graph structure (cycles, orphaned nodes, invalid references)?

**Decision**: Use existing `validate_pipeline_structure()` from `utils/pipeline_processor.py`.

**Rationale**:
- Comprehensive validation already implemented for CLI tool
- Detects cycles via topological sort
- Validates node references and edge consistency
- Returns structured error messages suitable for UI display

**Implementation Approach**:
```python
# In pipeline_service.py
from utils.pipeline_processor import validate_pipeline_structure, load_pipeline_config

def validate_and_save(self, pipeline_data: dict) -> ValidationResult:
    # Convert form data to pipeline config structure
    config = PipelineConfig.from_dict(pipeline_data)

    # Use existing validator
    errors = validate_pipeline_structure(config)
    if errors:
        return ValidationResult(valid=False, errors=errors)

    # Save to database
    # ...
```

**Alternatives Considered**:
1. **New validation library**: Unnecessary duplication of existing functionality
2. **Frontend-only validation**: Backend must be authoritative, frontend can pre-validate
3. **External graph library (networkx)**: Overkill, existing implementation sufficient

---

## Research Task 5: Trend Chart Library

**Question**: Which charting library to use for trend visualization?

**Decision**: Use Recharts (already integrated in frontend dependencies).

**Rationale**:
- Already a dependency: `recharts: 2.15.0` in package.json
- React-native, composable components
- Good TypeScript support
- Supports line charts, area charts, multi-series charts needed for trends
- CSS variable theming compatible with Tailwind

**Implementation Approach**:
```typescript
// TrendChart.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts';

export function TrendChart({ data, metric }) {
    return (
        <LineChart data={data}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey={metric} stroke="var(--chart-1)" />
        </LineChart>
    );
}
```

**Chart Types per Tool**:
- PhotoStats: Line chart (orphaned files over time)
- Photo Pairing: Multi-line chart (camera usage by camera ID)
- Pipeline Validation: Stacked area chart (CONSISTENT/PARTIAL/INCONSISTENT ratios)

**Alternatives Considered**:
1. **Chart.js**: Already used in CLI HTML reports, but not React-native
2. **Nivo**: Good but heavier, not already installed
3. **Victory**: Good TypeScript, but not already installed

---

## Research Task 6: Configuration Conflict Resolution

**Question**: How to handle conflicts when importing YAML configuration?

**Decision**: Session-based conflict resolution with 1-hour expiry.

**Rationale**:
- User initiates import, reviews conflicts, makes decisions
- Session stores pending import with conflict details
- 1-hour expiry prevents stale imports from lingering
- Side-by-side UI shows database value vs YAML value

**Implementation Approach**:
```python
# In config_service.py
class ImportSession:
    id: str
    yaml_config: dict
    conflicts: List[ConfigConflict]
    created_at: datetime
    expires_at: datetime  # created_at + 1 hour

def start_import(self, yaml_content: str) -> ImportSession:
    parsed = yaml.safe_load(yaml_content)
    current = self.get_all_config()

    conflicts = []
    for key, yaml_value in parsed.items():
        if key in current and current[key] != yaml_value:
            conflicts.append(ConfigConflict(
                key=key,
                database_value=current[key],
                yaml_value=yaml_value
            ))

    return ImportSession(conflicts=conflicts, ...)

def resolve_conflict(self, session_id: str, key: str, use_yaml: bool):
    # Apply user's choice
    # ...
```

**Alternatives Considered**:
1. **Auto-merge with YAML precedence**: May overwrite intentional database changes
2. **Auto-merge with database precedence**: Defeats purpose of import
3. **Persistent conflict queue**: Overkill for single-user scenario

---

## Research Task 7: HTML Report Storage

**Question**: How to store and serve HTML reports for historical access?

**Decision**: Store complete HTML in TEXT column alongside JSONB results.

**Rationale**:
- HTML reports are pre-generated by CLI tools
- Storing complete HTML allows offline download
- No need to re-render from JSONB data
- TEXT column handles large reports efficiently
- Download via API endpoint with Content-Disposition header

**Implementation Approach**:
```python
# AnalysisResult model
class AnalysisResult(Base):
    results_json = Column(JSONB, nullable=False)  # Structured data
    report_html = Column(Text, nullable=True)      # Pre-rendered HTML

# API endpoint
@router.get("/results/{result_id}/report")
async def download_report(result_id: int):
    result = db.query(AnalysisResult).get(result_id)
    return Response(
        content=result.report_html,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=report_{result_id}.html"}
    )
```

**Alternatives Considered**:
1. **File system storage**: Adds complexity, requires cleanup, path management
2. **Re-render on demand**: Slower, may produce different output over time
3. **Compress HTML (gzip)**: Adds complexity, PostgreSQL handles TEXT efficiently

---

## Research Task 8: Database-First Configuration for CLI

**Question**: How to extend PhotoAdminConfig to read from database with YAML fallback?

**Decision**: Add optional database connection parameter; attempt database read first, fall back to YAML on connection failure.

**Rationale**:
- Maintains backward compatibility: CLI works without database
- Web interface benefits from centralized config
- Graceful degradation for CLI users not using web interface
- Single config class maintains consistency

**Implementation Approach**:
```python
# In config_manager.py
class PhotoAdminConfig:
    def __init__(self, config_path=None, database_url=None):
        self.database_url = database_url or os.getenv('PHOTO_ADMIN_DATABASE_URL')
        self._config = None

    @property
    def raw_config(self):
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self):
        if self.database_url:
            try:
                return self._load_from_database()
            except Exception as e:
                logger.warning(f"Database config load failed, falling back to YAML: {e}")
        return self._load_from_yaml()
```

**Alternatives Considered**:
1. **Separate config classes**: Code duplication, maintenance burden
2. **Database-only for web**: Breaks CLI functionality
3. **YAML-only for CLI**: Defeats purpose of unified config management

---

## Research Task 9: Job Queue Persistence

**Question**: Should the in-memory job queue persist to database?

**Decision**: Keep in-memory queue; persist only completed job metadata in AnalysisResult.

**Rationale**:
- Single-user localhost: queue rarely has multiple jobs
- Jobs are transient; only results need persistence
- AnalysisResult provides historical job metadata (tool, duration, status)
- In-memory is simpler, faster, sufficient for scope

**Note**: PRD Open Question #1 resolved - in-memory queue is sufficient.

**Alternatives Considered**:
1. **Full queue persistence**: Overkill for single-user scenario
2. **Redis queue**: External dependency, infrastructure complexity
3. **Database-backed queue**: Adds latency, unnecessary durability

---

## Research Task 10: Rate Limiting Strategy

**Question**: What rate limiting approach for production polish?

**Decision**: Use slowapi middleware with reasonable defaults.

**Rationale**:
- slowapi is FastAPI-compatible (based on flask-limiter)
- Simple decorator-based rate limiting
- In-memory storage sufficient for single-user
- Protects against runaway scripts or misconfigured clients

**Implementation Approach**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/tools/run")
@limiter.limit("10/minute")  # 10 tool executions per minute
async def run_tool():
    # ...
```

**Rate Limits**:
- Tool execution: 10/minute (prevent resource exhaustion)
- API reads: 100/minute (reasonable for single user)
- Config import: 5/minute (prevent accidental spam)

**Alternatives Considered**:
1. **No rate limiting**: Risky even for localhost (runaway scripts)
2. **nginx rate limiting**: Requires additional infrastructure
3. **Token bucket**: More complex, unnecessary for single-user

---

## Summary

All technical decisions align with the project's constitution principles:
- **Simplicity**: In-memory queue, direct tool invocation, existing libraries
- **YAGNI**: No external message queues, no complex persistence
- **Independent CLI Tools**: Database-optional with YAML fallback
- **User-Centric Design**: Real-time WebSocket progress, pre-rendered HTML reports
- **Shared Infrastructure**: Extended PhotoAdminConfig, existing validation logic

No NEEDS CLARIFICATION items remain. Ready for Phase 1 design.
