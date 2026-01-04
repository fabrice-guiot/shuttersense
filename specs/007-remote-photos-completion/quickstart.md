# Quickstart: Remote Photo Collections Completion

**Feature**: 007-remote-photos-completion
**Date**: 2026-01-03

## Overview

This quickstart guide helps developers get started implementing Phases 4-8 of the Remote Photo Collections feature. It covers setup, key implementation patterns, and testing strategies.

---

## Prerequisites

### Existing Infrastructure (from Phases 1-3)

Ensure the following are working before starting:

```bash
# Backend (from backend/ directory)
cd backend
source venv/bin/activate  # or your virtual environment
pip install -r requirements.txt

# Database
export PHOTO_ADMIN_MASTER_KEY="your-32-byte-key"
export DATABASE_URL="postgresql://user:pass@localhost:5432/photo_admin"
alembic upgrade head

# Start backend
uvicorn src.main:app --reload --port 8000

# Frontend (from frontend/ directory)
cd frontend
npm install
npm run dev  # Starts on localhost:3000
```

### Verify Existing Features

```bash
# Collections and connectors should work
curl http://localhost:8000/api/collections
curl http://localhost:8000/api/connectors
curl http://localhost:8000/health
```

---

## Phase 4: Tool Execution (MVP)

### Step 1: Create Analysis Results Model

```bash
# Create migration
cd backend
alembic revision -m "Add analysis_results table"
```

```python
# backend/src/models/analysis_result.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.db.database import Base
import enum

class ResultStatus(enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    tool = Column(String(50), nullable=False)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(ResultStatus), nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    results_json = Column(JSONB, nullable=False)
    report_html = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    files_scanned = Column(Integer, nullable=True)
    issues_found = Column(Integer, nullable=True)

    # Relationships
    collection = relationship("Collection", back_populates="analysis_results")
```

### Step 2: Create Tool Service

```python
# backend/src/services/tool_service.py
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

# Add repo root to import CLI tools
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from photo_stats import PhotoStats
from photo_pairing import PhotoPairing

class ToolService:
    def __init__(self, db: Session, job_queue, websocket_manager):
        self.db = db
        self.job_queue = job_queue
        self.websocket = websocket_manager

    async def run_photostats(self, collection_path: str, job_id: str):
        """Execute PhotoStats and broadcast progress."""
        started_at = datetime.utcnow()

        try:
            tool = PhotoStats(collection_path)

            # Hook into scan for progress updates
            original_scan = tool.scan_folder
            def scan_with_progress():
                # Periodically broadcast progress
                await self.websocket.broadcast(job_id, {
                    "stage": "scanning",
                    "files_scanned": tool.stats.get("total_files", 0)
                })
                return original_scan()

            tool.scan_folder = scan_with_progress
            tool.scan_folder()

            return {
                "status": "COMPLETED",
                "results": tool.stats,
                "report_html": tool.generate_report()  # If available
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error_message": str(e)
            }
```

### Step 3: Create WebSocket Manager

```python
# backend/src/utils/websocket.py
from fastapi import WebSocket
from typing import Dict, Set
import asyncio

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.connections:
            self.connections[job_id] = set()
        self.connections[job_id].add(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.connections:
            self.connections[job_id].discard(websocket)

    async def broadcast(self, job_id: str, data: dict):
        if job_id in self.connections:
            for connection in self.connections[job_id]:
                try:
                    await connection.send_json(data)
                except:
                    pass  # Connection closed
```

### Step 4: Create API Routes

```python
# backend/src/api/tools.py
from fastapi import APIRouter, Depends, WebSocket, BackgroundTasks
from src.services.tool_service import ToolService
from src.utils.job_queue import get_job_queue, create_job_id, AnalysisJob, JobStatus

router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.post("/run")
async def run_tool(
    request: ToolRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    queue: JobQueue = Depends(get_job_queue)
):
    # Check for existing job
    existing = queue.find_active_job(request.collection_id, request.tool)
    if existing:
        return {"conflict": True, "job_id": existing.id, "position": queue.get_position(existing.id)}

    # Create and enqueue job
    job = AnalysisJob(
        id=create_job_id(),
        collection_id=request.collection_id,
        tool=request.tool,
        pipeline_id=request.pipeline_id,
        status=JobStatus.QUEUED,
        created_at=datetime.utcnow()
    )
    position = queue.enqueue(job)

    # Schedule background execution
    background_tasks.add_task(execute_job, job.id)

    return {"job_id": job.id, "position": position}

@router.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    manager = get_websocket_manager()
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except:
        manager.disconnect(job_id, websocket)
```

### Step 5: Frontend Hook

```typescript
// frontend/src/hooks/useTools.ts
import { useState, useEffect } from 'react'
import { api } from '../services/api'

export function useJobProgress(jobId: string | null) {
    const [progress, setProgress] = useState<ProgressData | null>(null)
    const [connected, setConnected] = useState(false)

    useEffect(() => {
        if (!jobId) return

        const ws = new WebSocket(`ws://localhost:8000/api/tools/ws/jobs/${jobId}`)

        ws.onopen = () => setConnected(true)
        ws.onclose = () => setConnected(false)
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            setProgress(data)
        }

        return () => ws.close()
    }, [jobId])

    return { progress, connected }
}

export function useTools() {
    const [loading, setLoading] = useState(false)

    const runTool = async (collectionId: number, tool: string, pipelineId?: number) => {
        setLoading(true)
        try {
            const response = await api.post('/api/tools/run', {
                collection_id: collectionId,
                tool,
                pipeline_id: pipelineId
            })
            return response.data
        } finally {
            setLoading(false)
        }
    }

    return { runTool, loading }
}
```

---

## Testing Patterns

### Backend Tests

```python
# backend/tests/unit/test_tool_service.py
import pytest
from unittest.mock import Mock, patch
from src.services.tool_service import ToolService

@pytest.fixture
def tool_service(test_db_session):
    return ToolService(
        db=test_db_session,
        job_queue=Mock(),
        websocket_manager=Mock()
    )

def test_run_photostats_success(tool_service, tmp_path):
    # Create test files
    (tmp_path / "IMG_0001.dng").touch()
    (tmp_path / "IMG_0001.xmp").touch()

    with patch('photo_stats.PhotoStats') as MockPhotoStats:
        mock_instance = MockPhotoStats.return_value
        mock_instance.stats = {"total_files": 2}

        result = tool_service.run_photostats(str(tmp_path), "test-job-id")

        assert result["status"] == "COMPLETED"
        assert "results" in result
```

### Frontend Tests

```typescript
// frontend/tests/hooks/useTools.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { useTools } from '../../src/hooks/useTools'
import { server } from '../mocks/server'
import { rest } from 'msw'

describe('useTools', () => {
    it('runs a tool and returns job info', async () => {
        server.use(
            rest.post('/api/tools/run', (req, res, ctx) => {
                return res(ctx.json({ job_id: 'test-123', position: 1 }))
            })
        )

        const { result } = renderHook(() => useTools())

        const response = await result.current.runTool(1, 'photostats')

        expect(response.job_id).toBe('test-123')
        expect(response.position).toBe(1)
    })
})
```

---

## Phase 5: Pipeline Management

### Key Implementation Pattern

Use existing `utils/pipeline_processor.py` for validation:

```python
# backend/src/services/pipeline_service.py
from utils.pipeline_processor import validate_pipeline_structure, PipelineConfig

class PipelineService:
    def validate_and_save(self, pipeline_data: dict) -> tuple[bool, list]:
        """Validate pipeline structure and save if valid."""
        config = PipelineConfig.from_dict(pipeline_data)
        errors = validate_pipeline_structure(config)

        if errors:
            return False, errors

        # Save to database
        pipeline = Pipeline(
            name=pipeline_data["name"],
            nodes_json=pipeline_data["nodes"],
            edges_json=pipeline_data["edges"],
            is_valid=True
        )
        self.db.add(pipeline)
        self.db.commit()

        return True, []
```

---

## Phase 6: Trend Analysis

### JSONB Query Pattern

```python
# backend/src/services/trend_service.py
from sqlalchemy import func

class TrendService:
    def get_photostats_trends(self, collection_ids: list, from_date, to_date):
        """Extract trend data from JSONB results."""
        query = self.db.query(
            AnalysisResult.collection_id,
            AnalysisResult.created_at,
            AnalysisResult.results_json['orphaned_images'].label('orphaned_images'),
            AnalysisResult.results_json['total_files'].astext.cast(Integer).label('total_files')
        ).filter(
            AnalysisResult.tool == 'photostats',
            AnalysisResult.status == ResultStatus.COMPLETED,
            AnalysisResult.collection_id.in_(collection_ids)
        )

        if from_date:
            query = query.filter(AnalysisResult.created_at >= from_date)
        if to_date:
            query = query.filter(AnalysisResult.created_at <= to_date)

        return query.order_by(AnalysisResult.created_at).all()
```

---

## Phase 7: Configuration Migration

### Database-First Config Pattern

```python
# utils/config_manager.py (enhanced)
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class PhotoAdminConfig:
    def __init__(self, config_path=None, database_url=None):
        self.database_url = database_url or os.getenv('PHOTO_ADMIN_DATABASE_URL')
        self.config_path = config_path
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
                logger.warning(f"Database config load failed: {e}. Falling back to YAML.")

        return self._load_from_yaml()

    def _load_from_database(self):
        """Load configuration from database."""
        engine = create_engine(self.database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            from backend.src.models.configuration import Configuration

            configs = session.query(Configuration).all()
            result = {}

            for config in configs:
                if config.category not in result:
                    result[config.category] = {}
                result[config.category][config.key] = config.value_json

            return self._transform_db_to_yaml_format(result)
        finally:
            session.close()
```

---

## Common Patterns

### TopHeader KPI Integration

All new pages must use the TopHeader KPI pattern:

```typescript
// frontend/src/pages/ToolsPage.tsx
import { useHeaderStats } from '../contexts/HeaderStatsContext'
import { useResultStats } from '../hooks/useResults'

export function ToolsPage() {
    const { stats, loading } = useResultStats()
    const { setStats } = useHeaderStats()

    useEffect(() => {
        if (stats) {
            setStats([
                { label: 'Total Runs', value: stats.total_results },
                { label: 'Last Run', value: formatDate(stats.last_run) },
            ])
        }
        return () => setStats([])  // Clear on unmount
    }, [stats, setStats])

    return (
        // Page content
    )
}
```

### Form Validation with react-hook-form + Zod

```typescript
// frontend/src/components/pipelines/PipelineFormEditor.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const pipelineSchema = z.object({
    name: z.string().min(1).max(255),
    description: z.string().optional(),
    nodes: z.array(nodeSchema).min(1),
    edges: z.array(edgeSchema),
})

export function PipelineFormEditor({ onSubmit }) {
    const form = useForm({
        resolver: zodResolver(pipelineSchema),
        defaultValues: { name: '', nodes: [], edges: [] }
    })

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
                {/* Form fields */}
            </form>
        </Form>
    )
}
```

---

## Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=src --cov-report=term-missing

# Target: >80% coverage

# Frontend tests
cd frontend
npm run test

# Target: >75% coverage
```

---

## Next Steps

After completing this quickstart:

1. Run `/speckit.tasks` to generate the detailed task breakdown
2. Start with Phase 4 (MVP) tasks
3. Follow the testing patterns for each new component
4. Ensure KPI integration on all new pages
