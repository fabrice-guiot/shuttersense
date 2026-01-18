# Research: Distributed Agent Architecture

**Feature**: 021-distributed-agent-architecture
**Created**: 2026-01-18
**Source**: PRD at `docs/prd/021-distributed-agent-architecture.md`

This document consolidates all research and design decisions from the PRD. All decisions below are pre-validated through extensive PRD analysis.

---

## 1. Architecture Pattern: Pull-Based Job Distribution

**Decision**: Agents poll for work (pull-based) rather than receiving pushed jobs.

**Rationale**:
- NAT traversal and firewall-friendly operation
- Simpler server infrastructure (no need for server-to-agent connections)
- Agents can operate behind corporate firewalls
- Graceful degradation when agents go offline

**Alternatives Considered**:
- Push-based (WebSocket server → agent): Rejected due to firewall/NAT complexity
- Message queue (RabbitMQ, Kafka): Rejected as over-engineering for v1

**PRD Reference**: Section "Key Design Decisions" - Decision #1

---

## 2. Job Assignment Model: Dual Strategy

**Decision**: Use two distinct job assignment strategies based on collection type.

### Strategy A: Explicit Agent Binding (LOCAL collections)
- Local collections are permanently bound to a specific agent at creation
- Jobs route ONLY to the bound agent
- Same path on different agents creates different collections

### Strategy B: Capability-Based Routing (Remote collections)
- Jobs for S3/GCS/SMB route to ANY agent with matching capabilities
- Multiple agents can have credentials for the same connector
- Load balancing across capable agents

**Rationale**:
- Local path `/home/user/Photos` exists with different content on different machines
- No authentication mechanism to differentiate local paths
- Remote storage has intrinsic identity (bucket/container names)

**Alternatives Considered**:
- Unified capability-based for all: Rejected because local paths have no identity
- Agent binding for all: Rejected as overly restrictive for remote storage

**PRD Reference**: Section "Collection Access Models"

---

## 3. Credential Storage: Three-Mode Model

**Decision**: Connectors support three credential locations.

| Mode | Description | Server Stores | Agent Required |
|------|-------------|---------------|----------------|
| `SERVER` | Traditional model | Encrypted credentials | Optional |
| `AGENT` | Security-focused | Only metadata | Yes (with local creds) |
| `PENDING` | Tentative activation | Only metadata | Awaiting configuration |

**Rationale**:
- `SERVER`: Backward compatible, enables server-side execution fallback
- `AGENT`: Enterprise requirement - credentials never leave user infrastructure
- `PENDING`: Allows connector creation before agent is configured

**Note**: Per spec, server-side execution is NOT supported. All jobs require agents.

**PRD Reference**: Section "Connector Credential Modes"

---

## 4. Communication Protocol: Hybrid REST + WebSocket

**Decision**: Use REST for control plane, WebSocket for real-time progress streaming.

| Operation | Protocol | Reason |
|-----------|----------|--------|
| Registration | REST | One-time, stateless |
| Heartbeat | REST | Simple, periodic |
| Job claim | REST | Database transaction required |
| Progress updates | WebSocket | Real-time streaming |
| Job completion | REST | Atomic with result upload |
| Cancellation | WebSocket | Server → agent signal |

**Fallback**: If WebSocket unavailable, progress updates via REST (every 2-5 seconds).

**Rationale**:
- REST simplifies job lifecycle management (database transactions)
- WebSocket enables real-time progress matching server-side UX
- Fallback ensures functionality in restricted networks

**PRD Reference**: Section "Communication Protocol"

---

## 5. Job Queue: PostgreSQL-Based Persistence

**Decision**: Use PostgreSQL for job queue persistence (Redis optional for future scale).

**Implementation**:
```sql
-- Job claim with locking
SELECT * FROM jobs
WHERE status IN ('PENDING', 'SCHEDULED')
  AND (scheduled_for IS NULL OR scheduled_for <= NOW())
  AND team_id = :team_id
  AND required_capabilities_json <@ :agent_capabilities
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

**Rationale**:
- Existing PostgreSQL infrastructure
- ACID guarantees for job state transitions
- `FOR UPDATE SKIP LOCKED` prevents race conditions
- Jobs survive server restart

**Alternatives Considered**:
- Redis-based queue: Deferred (adds infrastructure complexity)
- In-memory queue (current): Rejected (jobs lost on restart)

**PRD Reference**: Section "JobQueue Persistence Model"

---

## 6. Agent Trust: Binary Attestation + Result Signing

**Decision**: Multi-layer trust verification.

### Layer 1: Registration Attestation
- Agent sends binary checksum (self-hash) during registration
- Server validates against release manifest
- Rejects unrecognized/modified binaries

### Layer 2: Result Signing (HMAC)
- Agent receives job-specific signing secret when claiming
- Results include HMAC signature
- Server verifies signature before accepting

### Layer 3: Revocation
- Agents can be revoked (status=REVOKED)
- Revoked agents cannot claim jobs
- In-progress jobs released back to queue

**Rationale**:
- Prevents unauthorized/modified agents from participating
- Ensures result integrity
- Enables response to compromised agents

**PRD Reference**: Section "Agent Trust & Attestation"

---

## 7. Result Ingestion: Chunked Upload Protocol

**Decision**: Large results use chunked upload with integrity verification.

| Content Type | Typical Size | Strategy |
|--------------|--------------|----------|
| Results JSON | 10KB - 500KB | Inline if < 1MB |
| HTML Report | 100KB - 20MB | Always chunked |

**Flow**:
1. Agent sends completion request with size declaration
2. Server responds with upload_id and chunk_size (default 5MB)
3. Agent uploads chunks via PUT `/uploads/{upload_id}/{chunk_index}`
4. Agent finalizes; server verifies SHA-256 checksum
5. Server stores assembled content

**Features**:
- Idempotent chunks (re-upload returns 409)
- Upload sessions expire after 1 hour
- Automatic retry with exponential backoff

**PRD Reference**: Section "Result Ingestion Protocol"

---

## 8. Tool Configuration: ConfigLoader Interface

**Decision**: Abstract configuration source via ConfigLoader interface.

```python
class ConfigLoader(Protocol):
    def get_photo_extensions(self) -> list[str]: ...
    def get_camera_mappings(self) -> dict[str, CameraInfo]: ...
    def get_pipeline(self, guid: str) -> PipelineDefinition: ...
```

**Implementations**:
| Loader | Use Case | Source |
|--------|----------|--------|
| YamlConfigLoader | CLI standalone | Local YAML files |
| DatabaseConfigLoader | Server-side | PostgreSQL via ORM |
| ApiConfigLoader | Agent execution | Server API endpoints |

**New API Endpoints**:
- `GET /api/config/photo-extensions` - Team photo extensions
- `GET /api/config/camera-mappings` - Team camera mappings
- `GET /api/config/processing-methods` - Team processing methods
- `GET /api/pipelines/{guid}` - Complete pipeline definition
- `GET /api/jobs/{guid}/config` - All job configuration (bundled)

**Rationale**:
- Agents don't have database access
- Single interface keeps tool code clean
- Caching reduces API calls

**PRD Reference**: Section "API-Based Tool Configuration"

---

## 9. Scheduled Job Execution: No Background Task

**Decision**: Scheduled jobs claimed inline during agent polling (no background scheduler).

**Implementation**:
```python
def is_ready_to_claim():
    return or_(
        Job.status == JobStatus.PENDING,
        and_(
            Job.status == JobStatus.SCHEDULED,
            Job.scheduled_for <= now
        )
    )
```

**Auto-Refresh Flow**:
1. Job completes successfully
2. If collection has TTL configured, create next SCHEDULED job
3. `scheduled_for` = completion time + TTL
4. SCHEDULED jobs claimed when time passes (no status transition)

**Unique Constraint**: One SCHEDULED job per (collection_id, tool)

**Rationale**:
- Simpler than background scheduler
- Zero latency (job claimable immediately when time passes)
- Reduces infrastructure complexity

**PRD Reference**: Section "User Story 7a" and Job entity details

---

## 10. Agent Binary Distribution

**Decision**: Cross-platform Python-based agent packaged with PyInstaller.

| Platform | Package Format | Requirements |
|----------|---------------|--------------|
| macOS 12+ | DMG installer | Code-signed (future) |
| Windows 10+ | MSI installer | Code-signed (future) |
| Ubuntu 20.04+ | AppImage or deb | Checksum verified |

**Bundle Contents**:
- Agent core (polling, execution, reporting)
- PhotoStats tool
- Photo Pairing tool
- Pipeline Validation tool
- Local credential store

**Rationale**:
- Python for cross-platform consistency
- PyInstaller creates standalone executables
- No Python installation required for users
- Binary < 50MB target

**PRD Reference**: Section "Phase 3: Agent Binary"

---

## 11. Performance Targets (from NFR)

| Metric | Target | Notes |
|--------|--------|-------|
| Job claim latency | < 100ms | Excluding network |
| Concurrent agents/team | 100+ | PostgreSQL can handle |
| Job throughput | 1000 jobs/minute | With FOR UPDATE SKIP LOCKED |
| Heartbeat processing | < 50ms | Simple update |
| Agent poll interval | 5-10 seconds | Configurable |
| WebSocket progress latency | < 200ms | Agent → frontend |
| Concurrent WebSocket connections | 100+ per server | Async handlers |

**PRD Reference**: Section "NFR-100: Performance"

---

## 12. Security Requirements (from NFR)

| Requirement | Implementation |
|-------------|----------------|
| API key storage | SHA-256 hashed |
| Registration tokens | Single-use, 24-hour expiry |
| Transport security | HTTPS required |
| Credential isolation | Agent-local, never transmitted |
| Result validation | Schema + security checks |
| Rate limiting | 60 heartbeats/min, 120 claims/min |

**PRD Reference**: Section "NFR-300: Security"

---

## 13. Agent Auditability: SYSTEM User Pattern

**Decision**: Each agent creates a dedicated SYSTEM user for audit trail (consistent with API token pattern).

**Implementation** (from spec):
- On registration, create SYSTEM user with `full_name = "Agent: {agent name}"`
- Agent record stores `system_user_id` and `created_by_user_id`
- Records created by agent (AnalysisResult) use SYSTEM user for `created_by`
- Agent rename updates SYSTEM user's `full_name`
- SYSTEM user NOT deleted when agent deleted (preserves audit history)

**Rationale**:
- Consistent with existing API token SYSTEM user pattern
- Complete audit trail for agent-created records
- Distinguishes agent actions from human actions

**PRD Reference**: Spec update (not in original PRD)

---

## 14. Header Agent Pool Status (UI)

**Decision**: Display agent status in top header with real-time badge.

**Badge States**:
| Condition | Color | Content |
|-----------|-------|---------|
| All agents offline / no agents | Red | "Offline" |
| Agents idle (no jobs running) | Blue | Count of idle agents |
| At least one job running | Green | Count of running jobs |

**Implementation**:
- Icon between notification bell and user card
- Updates via WebSocket without page refresh
- Clicking icon navigates to Agent List (exclusive entry point)
- No sidebar menu entry or Settings tab for agents

**PRD Reference**: Spec update (not in original PRD)

---

## 15. Entity GUID Prefixes

| Entity | Prefix | Notes |
|--------|--------|-------|
| Agent | `agt_` | Worker process |
| AgentRegistrationToken | `art_` | One-time token |
| Job | `job_` | Enhanced with agent fields |

**PRD Reference**: Section "Key Entities"

---

## 16. Agent-Only Execution (Architectural Constraint)

**Decision**: Server NEVER executes jobs directly. All jobs require agents.

**Implications**:
- No server-side fallback
- Jobs queue indefinitely until agent available
- UI must clearly communicate agent requirement
- Foundation for future async processing

**Rationale**:
- Pre-first-release implementation (no backward compatibility needed)
- Cost reduction (user hardware vs cloud)
- Security (credentials on user infrastructure)
- Access to local resources

**PRD Reference**: Spec update (explicit override of PRD's fallback option)

---

## Summary of Key Technical Decisions

1. **Pull-based polling** (5-second interval, 30-second heartbeat)
2. **Dual job routing** (binding for LOCAL, capabilities for remote)
3. **Three credential modes** (SERVER, AGENT, PENDING)
4. **Hybrid REST + WebSocket** (REST for lifecycle, WS for progress)
5. **PostgreSQL job queue** (FOR UPDATE SKIP LOCKED)
6. **Binary attestation + HMAC** (trust verification)
7. **Chunked uploads** (5MB chunks, SHA-256 verification)
8. **ConfigLoader interface** (YAML, Database, API implementations)
9. **Inline scheduled execution** (no background scheduler)
10. **PyInstaller packaging** (cross-platform binaries)
11. **SYSTEM user per agent** (audit trail)
12. **Header status badge** (real-time agent pool visibility)
13. **Agent-only execution** (no server fallback)

All decisions documented in PRD have been validated and consolidated above.
