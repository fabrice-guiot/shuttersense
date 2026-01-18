# Developer Quick Start: Distributed Agent Architecture

**Feature**: 021-distributed-agent-architecture
**Created**: 2026-01-18

---

## Overview

This guide helps developers quickly understand and work on the Distributed Agent Architecture feature.

## Key Concepts

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                           SERVER                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │  FastAPI    │  │ PostgreSQL  │  │  WebSocket Handler          │  │
│  │  Backend    │  │  Job Queue  │  │  (Progress Proxy)           │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────────┬──────────────┘  │
│         │                │                        │                  │
│         └────────────────┴────────────────────────┘                  │
│                          │ REST + WebSocket                          │
└──────────────────────────┼───────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Agent   │    │  Agent   │    │  Agent   │
    │ (macOS)  │    │ (Linux)  │    │(Windows) │
    └──────────┘    └──────────┘    └──────────┘
```

### Critical Design Decisions

1. **Agent-Only Execution**: Server NEVER executes jobs. All jobs run on agents.
2. **Pull-Based**: Agents poll for jobs (not pushed).
3. **Dual Routing**: LOCAL collections bound to specific agent; remote collections use capability-based routing.
4. **Hybrid Protocol**: REST for lifecycle, WebSocket for real-time progress.

---

## Getting Started

### 1. Database Migrations

Run migrations to add agent-related tables:

```bash
cd backend
alembic upgrade head
```

New tables:
- `agents` - Agent records with capabilities
- `agent_registration_tokens` - One-time registration tokens

Enhanced tables:
- `jobs` - New fields: `bound_agent_id`, `agent_id`, `scheduled_for`, etc.
- `connectors` - New field: `credential_location`
- `collections` - New fields: `bound_agent_id`, `auto_refresh`, etc.

### 2. Start the Backend

```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

New endpoints available at `/api/agent/v1/*`

### 3. Build and Run Agent (Development)

```bash
cd agent
pip install -e .

# Run in development mode
python -m shuttersense_agent --config ~/.shuttersense/agent-config.yaml
```

---

## Directory Structure

### Backend Additions

```
backend/src/
├── models/
│   ├── agent.py                    # Agent entity
│   └── agent_registration_token.py # Token entity
├── services/
│   ├── agent_service.py            # Agent lifecycle
│   └── job_coordinator_service.py  # Job routing
├── api/agent/
│   ├── routes.py                   # /api/agent/v1/*
│   └── schemas.py                  # Pydantic models
└── ws/
    └── agent_progress.py           # WebSocket handler
```

### Agent Package

```
agent/
├── src/
│   ├── main.py              # Entry point
│   ├── polling_loop.py      # Main job loop
│   ├── job_executor.py      # Tool execution
│   └── config_loader.py     # ApiConfigLoader
├── cli/
│   ├── register.py          # Registration command
│   └── connectors.py        # Credential management
└── tests/
```

---

## Key Files to Understand

| File | Purpose |
|------|---------|
| `backend/src/services/job_coordinator_service.py` | Job claim logic with FOR UPDATE SKIP LOCKED |
| `backend/src/api/agent/routes.py` | Agent API endpoints |
| `agent/src/polling_loop.py` | Agent main loop (heartbeat + job poll) |
| `agent/src/config_loader.py` | ApiConfigLoader for tool configuration |

---

## Testing Locally

### 1. Generate Registration Token

```python
# In backend shell or test
from backend.src.services.agent_service import AgentService

service = AgentService(db_session)
token = service.create_registration_token(
    team_id=1,
    user_id=1,
    name="Dev Agent"
)
print(f"Token: {token.token}")  # art_xxxxx...
```

### 2. Register Agent

```bash
shuttersense-agent register \
  --server http://localhost:8000 \
  --token art_xxxxx... \
  --name "My Dev Machine"
```

### 3. Create Test Job

```python
# In backend shell or test
from backend.src.services.job_coordinator_service import JobCoordinatorService

service = JobCoordinatorService(db_session)
job = service.create_job(
    collection_id=1,
    tool="photostats"
)
print(f"Job created: {job.guid}")
```

### 4. Watch Agent Claim and Execute

Agent logs show:
```
INFO: Claimed job job_01hgw2bbg...
INFO: Executing photostats on /path/to/photos
INFO: Progress: scanning (45%)
INFO: Job completed, uploading results
```

---

## Common Tasks

### Add New Agent Capability

1. Define capability string format:
   ```python
   # Format: {type}:{name}:{version}
   capability = "tool:new_tool:1.0.0"
   ```

2. Update capability detection in agent:
   ```python
   # agent/src/capabilities.py
   def detect_capabilities() -> list[str]:
       caps = ["local_filesystem"]
       caps.extend(detect_tools())
       caps.extend(detect_connectors())
       return caps
   ```

3. Update job routing to match:
   ```python
   # backend/src/services/job_coordinator_service.py
   job.required_capabilities_json = [f"tool:{tool}"]
   ```

### Add New Agent API Endpoint

1. Add route in `backend/src/api/agent/routes.py`:
   ```python
   @router.post("/new-endpoint")
   async def new_endpoint(
       request: NewRequest,
       agent: Agent = Depends(get_current_agent)
   ):
       ...
   ```

2. Add Pydantic schema in `backend/src/api/agent/schemas.py`

3. Update OpenAPI spec in `specs/021-distributed-agent-architecture/contracts/agent-api.yaml`

### Handle Agent Offline

When agent misses heartbeat for 90+ seconds:

1. Background task marks agent OFFLINE:
   ```python
   # backend/src/tasks/agent_monitor.py
   def check_agent_heartbeats():
       cutoff = datetime.utcnow() - timedelta(seconds=90)
       offline_agents = db.query(Agent).filter(
           Agent.status == AgentStatus.ONLINE,
           Agent.last_heartbeat < cutoff
       ).all()

       for agent in offline_agents:
           agent.status = AgentStatus.OFFLINE
           release_agent_jobs(agent.id)
   ```

2. In-progress jobs released back to PENDING:
   ```python
   def release_agent_jobs(agent_id: int):
       db.query(Job).filter(
           Job.agent_id == agent_id,
           Job.status.in_([JobStatus.ASSIGNED, JobStatus.RUNNING])
       ).update({
           Job.status: JobStatus.PENDING,
           Job.agent_id: None
       })
   ```

---

## Testing

### Unit Tests

```bash
# Backend
cd backend
pytest tests/unit/test_agent_service.py -v
pytest tests/unit/test_job_coordinator.py -v

# Agent
cd agent
pytest tests/unit/ -v
```

### Integration Tests

```bash
# Backend API
cd backend
pytest tests/integration/test_agent_api.py -v

# Agent with mock server
cd agent
pytest tests/integration/test_agent_registration.py -v
```

### E2E Test

```bash
# Start server
cd backend && uvicorn src.main:app &

# Start agent
cd agent && python -m shuttersense_agent &

# Run E2E
pytest tests/e2e/test_job_execution.py -v
```

---

## Debugging

### Agent Debug Mode

```bash
# Enable verbose logging
export SHUTTERSENSE_LOG_LEVEL=DEBUG
shuttersense-agent start
```

### Server-Side Agent Logs

```python
# In routes.py
import structlog
logger = structlog.get_logger()

@router.post("/heartbeat")
async def heartbeat(request: HeartbeatRequest, agent: Agent):
    logger.info("agent_heartbeat", agent_guid=agent.guid, status=request.status)
```

### WebSocket Debugging

```python
# In ws/agent_progress.py
async def on_message(self, websocket, message: dict):
    logger.debug("ws_message", job_guid=self.job_guid, type=message["type"])
```

---

## References

| Document | Location |
|----------|----------|
| Feature Spec | `specs/021-distributed-agent-architecture/spec.md` |
| Research | `specs/021-distributed-agent-architecture/research.md` |
| Data Model | `specs/021-distributed-agent-architecture/data-model.md` |
| Agent API | `specs/021-distributed-agent-architecture/contracts/agent-api.yaml` |
| WebSocket Protocol | `specs/021-distributed-agent-architecture/contracts/websocket-protocol.md` |
| PRD | `docs/prd/021-distributed-agent-architecture.md` |

---

## Common Pitfalls

1. **Forgetting team_id filtering**: All agent queries MUST filter by team_id
2. **Not using FOR UPDATE SKIP LOCKED**: Race conditions in job claiming
3. **Hardcoding capabilities**: Use capability detection, not hardcoded lists
4. **Ignoring WebSocket fallback**: Always support REST progress updates
5. **Not creating SYSTEM user**: Agent registration must create audit user
