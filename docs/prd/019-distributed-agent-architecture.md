# PRD: Distributed Agent Architecture

**Issue**: TBD
**Status**: Draft
**Created**: 2026-01-14
**Last Updated**: 2026-01-14
**Related Documents**:
- [Domain Model](../domain-model.md) (Section: Agent - Planned Entity)
- [007-remote-photos-completion.md](./007-remote-photos-completion.md) (Current job execution)
- [012-user-tenancy.md](./012-user-tenancy.md) (Team-based multi-tenancy)

---

## Executive Summary

This PRD defines the architecture for distributed Agents in photo-admin, enabling job execution on user-owned hardware instead of centralized cloud infrastructure. Agents are lightweight worker processes that connect to the central server, receive job assignments, execute tools locally, and report results back. This architecture addresses three critical objectives:

1. **Cost Reduction**: Offload compute-intensive operations to user-owned devices
2. **Security/Trust**: Keep sensitive credentials on user-controlled infrastructure
3. **Resource Access**: Enable access to local filesystems, SMB shares, and desktop applications

### Key Design Decisions

1. **Pull-Based Job Assignment**: Agents poll for work (not pushed), enabling NAT traversal and firewall-friendly operation
2. **Explicit Agent Binding for Local Collections**: Local collections are bound to a specific agent at creation time (not capability-based), because the same path may exist on multiple agents with different content
3. **Capability-Based Routing for Connectors**: Jobs for remote storage are matched to agents that have verified access to the connector (via connection testing)
4. **Three Credential Modes**: Connectors support `SERVER` (credentials on server), `AGENT` (credentials only on agent), or `PENDING` (no credentials yet, awaiting agent configuration)
5. **Agent-Driven Capability Acquisition**: Agents discover and report their capabilities by testing connections and detecting installed tools
6. **Credential Locality**: Connector credentials can remain encrypted on the agent's host, never transmitted to the central server
7. **Eventual Consistency**: Results are stored centrally for reporting, but agents can operate offline and sync when connected
8. **Team-Scoped Agents**: Each agent belongs to exactly one team; agents cannot access other teams' data or jobs

---

## Background

### Current Architecture Limitations

The current photo-admin architecture executes all jobs in the backend process:

**Current Job Execution Flow:**
```
API Request (POST /tools/run)
    ↓
JobQueue (in-memory FIFO)
    ↓
asyncio.to_thread() → Tool Execution
    ↓
WebSocket Progress Broadcast
    ↓
Result Storage (PostgreSQL)
```

**Limitations:**

| Limitation | Impact | Severity |
|------------|--------|----------|
| **Single-machine execution** | All jobs compete for server CPU/memory | High |
| **No local file access** | Server cannot access user's local files | Critical |
| **Credentials on server** | Connector secrets stored centrally | Medium |
| **Network-bound storage access** | S3/GCS/SMB accessed from server location | Medium |
| **No desktop app integration** | Cannot invoke Lightroom, DxO, Photoshop | High |
| **Job queue non-persistent** | Queue lost on restart | Medium |
| **No parallelism** | Single job at a time | Medium |

### Strategic Context

As photo-admin moves toward cloud deployment and SaaS offering, the centralized execution model becomes untenable:

1. **Cloud Infrastructure Cost**: Running analysis on large collections requires significant compute
2. **Data Sovereignty**: Enterprise users require credentials never leave their infrastructure
3. **Local Resource Access**: Professional photographers work with local storage, not cloud-only
4. **Desktop Tool Integration**: Workflows involve Adobe Lightroom, DxO PureRAW, Photoshop, etc.

The Agent architecture solves these by moving execution to user-controlled infrastructure while maintaining centralized coordination, result storage, and reporting.

---

## Goals

### Primary Goals

1. **Distributed Execution**: Execute jobs on user-owned agents instead of central server
2. **Credential Security**: Enable credentials to remain on agent hosts, never transmitted to server
3. **Local Resource Access**: Access local filesystems, SMB shares, and network resources from agent location
4. **Job Persistence**: Replace in-memory queue with persistent, distributed job queue
5. **Horizontal Scaling**: Support multiple concurrent agents per team

### Secondary Goals

1. **Desktop Application Integration**: Foundation for invoking local applications (Lightroom, DxO, etc.)
2. **Offline Operation**: Agents can queue results locally when server is unreachable
3. **Agent Monitoring**: Real-time visibility into agent status, capabilities, and performance
4. **Graceful Migration**: Existing functionality continues working during transition

### Non-Goals (v1)

1. **Agent Auto-Updates**: Manual agent installation/updates (defer auto-update to v2)
2. **Agent Clustering**: No agent-to-agent communication (all coordination via server)
3. **Real-Time Streaming**: Progress updates via periodic reporting (not WebSocket from agent)
4. **Credential Vault Integration**: No HashiCorp Vault/AWS Secrets Manager (defer to v2)
5. **Container Orchestration**: No Kubernetes/Docker Swarm integration (simple process model)

---

## Core Concepts and Terminology

### Glossary

| Term | Definition |
|------|------------|
| **Agent** | A worker process running on user-owned hardware that executes jobs |
| **Coordinator** | The central server component that manages job distribution |
| **Job** | A unit of work (tool execution) that can be assigned to an agent |
| **Capability** | A declared ability of an agent (connector access, tool support, etc.) |
| **Heartbeat** | Periodic signal from agent to coordinator indicating availability |
| **Claim** | An agent's request to take ownership of a job |
| **Bound Agent** | The specific agent assigned to a local collection (explicit binding) |
| **Server Connector** | A connector whose credentials are stored on the central server |
| **Agent Connector** | A connector whose credentials are stored only on agent(s) |
| **Pending Connector** | A connector created without credentials, awaiting agent configuration |

### Collection Access Models

Photo-admin supports two distinct access models for collections:

**Model 1: Agent-Bound Local Collections**

Local filesystem collections are explicitly bound to a single agent at creation time. This is necessary because:
- The same path (e.g., `/home/user/Photos`) may exist on multiple agents
- Each agent's path represents completely different photo content
- There is no authentication mechanism to differentiate access

```
┌─────────────────────────────────────────────────────────────────────┐
│  Collection: "Wedding Photos 2026"                                   │
│  type: LOCAL                                                         │
│  location: /home/user/Photos/Wedding2026                             │
│  bound_agent_id: agt_01hgw2bbg... ◄── EXPLICIT BINDING              │
│                                                                      │
│  Jobs for this collection can ONLY execute on Agent Alpha           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │      Agent Alpha          │
                    │  /home/user/Photos/       │
                    │    └── Wedding2026/       │
                    │        ├── IMG_001.jpg    │
                    │        └── IMG_002.jpg    │
                    └───────────────────────────┘
```

**Model 2: Capability-Based Remote Collections**

Connector-based collections (S3, GCS, SMB) use capability-based routing. Multiple agents may have access to the same connector, and jobs route to any capable agent:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Collection: "Cloud Archive"                                         │
│  type: S3                                                            │
│  connector_id: con_aws_prod                                          │
│  bound_agent_id: NULL ◄── NO BINDING (capability-based)             │
│                                                                      │
│  Jobs route to ANY agent with capability "connector:con_aws_prod"   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌─────────────────────┐        ┌─────────────────────┐
        │   Agent Alpha       │        │   Agent Beta        │
        │   has credentials   │        │   has credentials   │
        │   for con_aws_prod  │        │   for con_aws_prod  │
        │                     │        │                     │
        │   ✅ Can execute    │        │   ✅ Can execute    │
        └─────────────────────┘        └─────────────────────┘
```

### Agent Execution Modes

**Mode 1: Server-Side Execution (Current Behavior)**
- Jobs execute in the backend process
- Used when no capable agent is online
- Limited to remote connectors (S3, GCS, remote SMB)
- Credentials decrypted server-side

**Mode 2: Agent-Side Execution (New)**
- Jobs execute on a registered agent
- Required for local collections, local SMB
- Credentials can remain agent-local (never transmitted to server)
- Results reported back to server for storage

### Job Assignment Model

The coordinator uses two different assignment strategies based on collection type:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Coordinator (Server)                             │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Distributed Job Queue                            │ │
│  │                                                                      │ │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐       │ │
│  │  │ Job A           │ │ Job B           │ │ Job C           │       │ │
│  │  │ LOCAL collection│ │ S3 collection   │ │ SMB collection  │       │ │
│  │  │ bound_agent:    │ │ bound_agent:    │ │ bound_agent:    │       │ │
│  │  │   agt_alpha     │ │   NULL          │ │   NULL          │       │ │
│  │  │ required_caps:  │ │ required_caps:  │ │ required_caps:  │       │ │
│  │  │   [tool:*]      │ │   [con_s3_prod] │ │   [con_smb_nas] │       │ │
│  │  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘       │ │
│  └───────────┼───────────────────┼───────────────────┼────────────────┘ │
│              │                   │                   │                   │
│  ┌───────────▼───────────────────▼───────────────────▼────────────────┐ │
│  │                        Job Matcher Logic                            │ │
│  │                                                                      │ │
│  │  if job.bound_agent_id:                                             │ │
│  │      → Route ONLY to bound agent (local collections)                │ │
│  │  else:                                                               │ │
│  │      → Route to ANY agent with matching capabilities (connectors)   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                    │                               │
    ┌───────────────▼──────┐          ┌────────────▼─────────────┐
    │     Agent Alpha      │          │      Agent Beta          │
    │  hostname: workstation│          │  hostname: nas-server    │
    │                       │          │                          │
    │  Bound collections:   │          │  Bound collections:      │
    │    - col_wedding (✓)  │          │    - col_archive (✓)     │
    │                       │          │                          │
    │  Connector access:    │          │  Connector access:       │
    │    - con_s3_prod (✓)  │          │    - con_s3_prod (✓)     │
    │    - con_smb_nas (✓)  │          │    - con_smb_nas (✓)     │
    │                       │          │                          │
    │  Job A → ✅ (bound)   │          │  Job A → ❌ (not bound)  │
    │  Job B → ✅ (capable) │          │  Job B → ✅ (capable)    │
    │  Job C → ✅ (capable) │          │  Job C → ✅ (capable)    │
    └───────────────────────┘          └──────────────────────────┘
```

---

## User Personas

### Primary: Cloud-Conscious Studio Owner (Sam)

- **Current Pain**: Cloud compute costs are unpredictable, scales with usage
- **Desired Outcome**: Run analysis on existing office workstation, pay only for coordination
- **This PRD Delivers**: Agent running on workstation executes all tool jobs locally

### Secondary: Security-Aware Enterprise Admin (Morgan)

- **Current Pain**: Cannot store cloud storage credentials on third-party SaaS
- **Desired Outcome**: Credentials never leave corporate network, only results shared
- **This PRD Delivers**: Local connectors with agent-side credential storage

### Tertiary: Remote Photographer (Alex)

- **Current Pain**: 10TB local photo collection cannot be uploaded to analyze
- **Desired Outcome**: Analyze local files without network transfer
- **This PRD Delivers**: Agent accesses local filesystem, reports only metadata/results

### Quaternary: Workflow Integrator (Taylor)

- **Current Pain**: Cannot trigger DxO PureRAW processing from photo-admin
- **Desired Outcome**: Workflow that includes local application processing
- **This PRD Delivers**: Foundation for desktop app integration (future user story)

---

## User Stories

### User Story 1: Agent Registration and Setup (Priority: P0 - Critical)

**As** a team administrator
**I want to** register an agent running on my local machine
**So that** jobs can be executed on my own hardware

**Acceptance Criteria:**
- Download agent binary or install via package manager
- Configure agent with server URL and registration token
- Agent registers with server, appears in agent list UI
- Agent capabilities auto-detected (local filesystem, installed tools)
- Agent status (online/offline/error) visible in dashboard
- Agent can be named for identification ("Office Workstation", "NAS Server")

**Technical Notes:**
- Registration token generated from UI (one-time use, team-scoped)
- Agent stores API key locally after registration
- Heartbeat interval: 30 seconds
- Agent considered offline after 3 missed heartbeats (90 seconds)

---

### User Story 2: Local Collection with Agent Binding (Priority: P0 - Critical)

**As** a photographer
**I want to** analyze my local photo collection via an agent
**So that** I don't need to upload files to the cloud

**Acceptance Criteria:**
- Create collection pointing to local path (e.g., `/home/user/Photos`)
- **Must select a specific agent** when creating a local collection
- Only online agents with `local_filesystem` capability are shown in selector
- Collection is permanently bound to the selected agent
- Jobs for this collection route **only** to the bound agent
- Agent executes PhotoStats/Photo Pairing locally
- Results appear in web UI same as server-executed jobs
- HTML report generated and stored on server
- If bound agent is offline, jobs queue until agent comes online
- UI clearly shows which agent a local collection is bound to

**Technical Notes:**
- Collection `type=LOCAL` with `location=/absolute/path` and `bound_agent_id`
- Job routing checks `bound_agent_id` first (not capability-based for locals)
- Path uniqueness is scoped to agent (same path on different agents = different collections)
- Agent binding cannot be changed after creation (delete and recreate collection)
- Agent deletion prevented if bound collections exist (or migrate to another agent)

---

### User Story 3: Connector Credential Modes (Priority: P1)

**As** a team administrator
**I want to** choose where connector credentials are stored
**So that** I can balance convenience with security requirements

**Acceptance Criteria:**

**Server Credentials (credential_location=SERVER):**
- Provide credentials when creating connector (current behavior)
- Credentials stored encrypted on server
- Server can execute jobs directly (when no agent required)
- Agents with server-connector capability can also execute
- Agent tests connection to verify access, then reports capability

**Agent-Only Credentials (credential_location=AGENT):**
- Create connector marked as "agent-only" credentials
- Server stores connector metadata but NOT credentials
- Credentials configured via agent CLI (see User Story 3a)
- Only agents with local credentials can execute jobs
- UI shows which agents have credentials for this connector

**Pending Credentials (credential_location=PENDING):**
- Create connector without any credentials
- Connector exists but is not usable until credentials provided
- Agent CLI shows pending connectors for credential configuration
- Once agent configures credentials, connector becomes usable via that agent
- Multiple agents can independently configure credentials

**Technical Notes:**
- Connector model: `credential_location` enum (`SERVER`, `AGENT`, `PENDING`)
- Existing connectors default to `SERVER` for backward compatibility
- `PENDING` enables "tentative activation" workflow (create first, configure later)
- UI badge indicates credential status: "Server", "Agent-only", "Pending"

---

### User Story 3a: Agent Credential Configuration via CLI (Priority: P1)

**As** an agent operator
**I want to** configure connector credentials locally
**So that** credentials never leave my machine

**Acceptance Criteria:**
- Agent CLI command lists connectors awaiting credentials
- CLI prompts for credentials based on connector type schema
- Credentials stored in local encrypted file (agent master key)
- Agent tests connection before confirming credential storage
- On success, agent reports capability to server ("I can access con_xyz")
- Server updates agent's capability list
- If connection test fails, credentials not stored, error displayed

**Agent CLI Workflow:**
```bash
# List connectors needing credentials on this agent
$ photo-admin-agent connectors list --pending

Connectors awaiting credentials:
  con_01hgw2bbg... "AWS Production" (S3) - PENDING
  con_01hgw2bbh... "Office NAS" (SMB) - PENDING

# Configure credentials for a connector
$ photo-admin-agent connectors configure con_01hgw2bbg...

Connector: AWS Production (S3)
AWS Access Key ID: AKIA...
AWS Secret Access Key: ****
Region [us-east-1]:
Endpoint URL (optional):

Testing connection... ✓ Success (42 objects found)
Credentials stored locally.
Capability reported to server.

# Verify agent capabilities
$ photo-admin-agent capabilities

Capabilities:
  - local_filesystem
  - tool:photostats
  - tool:photo_pairing
  - tool:pipeline_validation
  - connector:con_01hgw2bbg... (AWS Production)
```

**Technical Notes:**
- Credentials encrypted with agent-local master key
- Master key derived from user password or hardware key
- Server never receives actual credentials
- Agent capability update via heartbeat or explicit API call

---

### User Story 4: SMB/Network Share via Agent (Priority: P1)

**As** a photographer with NAS storage
**I want to** analyze photos on my local SMB share
**So that** I don't need to copy files to cloud storage

**Acceptance Criteria:**
- Create SMB connector pointing to local network share
- Connector can be configured with agent-local credentials (or PENDING)
- Agent on same network can access SMB share
- Agent tests SMB connection, then reports capability
- Jobs execute locally with low-latency file access
- No SMB traffic traverses the internet

**Technical Notes:**
- SMB connector type already supported
- Agent resolves SMB hostname from its network location
- Agent-local credentials avoid server credential storage
- Progress reporting includes file scan count

---

### User Story 4a: Tool Capability Detection (Priority: P2)

**As** an agent
**I want to** automatically detect and report available tools
**So that** the server knows what jobs I can execute

**Acceptance Criteria:**

**Bundled Tools (v1):**
- Agent includes PhotoStats, Photo Pairing, Pipeline Validation
- All agents report these tool capabilities automatically
- No user configuration required for bundled tools
- Tool versions reported with capabilities

**External Tools (Future - v2):**
- Agent detects installed applications (Lightroom, DxO PureRAW, etc.)
- Detection via well-known paths, registry, or CLI probing
- User can manually declare tool availability
- Agent tests tool execution before reporting capability
- Server tracks which agents can execute which external tools

**Capability Reporting:**
```json
{
  "capabilities": [
    "local_filesystem",
    "tool:photostats:1.2.3",
    "tool:photo_pairing:1.2.3",
    "tool:pipeline_validation:1.2.3",
    "connector:con_01hgw2bbg..."
  ]
}
```

**Technical Notes:**
- In v1, all agents have all bundled tools (same codebase)
- Future tool capabilities will follow same pattern as connector capabilities
- External tool integration requires defining invocation protocol per app
- Tool version tracking enables compatibility checks

---

### User Story 5: Job Queue Visibility and Management (Priority: P1)

**As** a team administrator
**I want to** see all queued and running jobs across agents
**So that** I can monitor workload and troubleshoot issues

**Acceptance Criteria:**
- View all jobs: queued, running, completed, failed
- See which agent is executing each running job
- Cancel queued jobs before execution
- Retry failed jobs with one click
- Filter jobs by collection, tool, agent, status

**Technical Notes:**
- Persistent job queue (Redis or PostgreSQL-backed)
- Job states: PENDING, ASSIGNED, RUNNING, COMPLETED, FAILED, CANCELLED
- Job assignment recorded with agent_guid
- Failed jobs retain error message and stack trace

---

### User Story 6: Agent Health Monitoring (Priority: P2)

**As** a team administrator
**I want to** monitor agent health and resource usage
**So that** I can identify performance bottlenecks

**Acceptance Criteria:**
- View agent status: online, offline, error
- See last heartbeat timestamp
- View current job (if executing)
- View recent job history per agent
- Receive notification when agent goes offline

**Technical Notes:**
- Heartbeat includes: status, current job, CPU/memory (optional)
- Agent offline notification via WebSocket to dashboard
- Agent list sorted by status (online first)

---

### User Story 7: Multi-Agent Job Distribution (Priority: P2)

**As** a studio owner with multiple workstations
**I want to** run agents on multiple machines
**So that** jobs are distributed across available compute

**Acceptance Criteria:**
- Register multiple agents for same team
- Jobs distributed to any capable online agent
- Each agent processes one job at a time (v1)
- Agent selection considers: capabilities match, queue depth, last active
- Load balancing visible in job assignment UI

**Technical Notes:**
- Job assignment algorithm: FIFO with capability filtering
- Tie-breaker: agent with fewest recent jobs (simple load balance)
- No job stealing (agent completes assigned job or fails)
- V2: concurrent job execution per agent

---

### User Story 7a: Automatic Collection Refresh Scheduling (Priority: P2)

**As** a team administrator
**I want to** have collection analysis automatically re-run based on TTL
**So that** KPIs stay fresh without manual intervention

**Acceptance Criteria:**
- Collections have a configurable refresh interval (TTL)
- When a job completes, the next scheduled job is automatically created
- Scheduled jobs appear in the queue with a "scheduled for" timestamp
- Agents only claim jobs when their scheduled time has passed
- UI shows upcoming scheduled jobs separately from ready-to-run jobs
- Users can manually trigger a refresh (creates immediate job, reschedules next)
- Changing TTL updates the next scheduled job's target time
- Deleting a collection cancels any scheduled jobs

**Example Workflow:**
```
Collection: "Wedding Photos" (TTL: 24 hours)

Day 1, 10:00 AM:
  └─ User creates collection
  └─ System creates Job A (immediate, scheduled_for=NULL)
  └─ Agent claims and executes Job A
  └─ Job A completes at 10:05 AM
  └─ System creates Job B (scheduled_for=Day 2, 10:05 AM)

Day 2, 10:05 AM:
  └─ Job B transitions: SCHEDULED → PENDING
  └─ Agent claims and executes Job B
  └─ Job B completes at 10:08 AM
  └─ System creates Job C (scheduled_for=Day 3, 10:08 AM)

Day 2, 2:00 PM:
  └─ User manually triggers refresh
  └─ System cancels Job C (scheduled)
  └─ System creates Job D (immediate)
  └─ Agent executes Job D
  └─ Job D completes at 2:03 PM
  └─ System creates Job E (scheduled_for=Day 3, 2:03 PM)
```

**Technical Notes:**
- Job model: `scheduled_for` (DateTime, nullable) - NULL means immediate
- Job status: Add `SCHEDULED` status (before `PENDING`)
- Unique constraint: Only one SCHEDULED job per (collection_id, tool)
- Background task: Transition SCHEDULED → PENDING when `scheduled_for <= NOW()`
- Alternative: Filter in claim query (no status transition needed)
- Job completion atomically creates next scheduled job (single transaction)
- Collection deletion cascades to cancel scheduled jobs

---

### User Story 8: Offline Agent Operation (Priority: P3 — Future Version)

> **⚠️ OUT OF SCOPE FOR V1**: This user story describes a future enhancement, not part of the initial agent implementation. It is retained here for long-term vision and planning purposes.

**As** a photographer working in the field
**I want to** run analysis while disconnected from internet
**So that** I can review results when back online

**Acceptance Criteria:**
- Agent can operate with queued local jobs when offline
- Results stored locally until connectivity restored
- Agent syncs completed results on reconnection
- No duplicate job execution during sync
- UI shows "pending sync" status for offline results

**Why This Is Complex (Future Work):**

Offline operation requires significant enhancements beyond the initial agent architecture:

1. **Local Collection Management**: Ability to create or modify collections while offline, requiring local-first data model
2. **Conflict Resolution**: Reconciling local changes with server state when back online (last-write-wins, merge strategies, etc.)
3. **CLI Enhancements**: Extended CLI toolbox for offline workflows (local job creation, result browsing, manual sync triggers)
4. **Sync Protocol**: Robust bi-directional sync with idempotency guarantees
5. **Offline-First UI**: Agent-side result viewer for field use without server connectivity

**Technical Notes (for future reference):**
- Local job queue on agent (SQLite)
- Result upload retry with exponential backoff
- Conflict resolution strategy TBD (server-wins simplest, but limits offline utility)
- Consider CRDT or event-sourcing patterns for true offline-first support

---

## Key Entities

### Agent (New Entity)

**GUID Prefix:** `agt_`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `name` | String(255) | not null | User-friendly agent name |
| `hostname` | String(255) | nullable | Machine hostname (auto-detected) |
| `os_info` | String(255) | nullable | OS type/version |
| `status` | Enum | not null, default='OFFLINE' | `ONLINE`, `OFFLINE`, `ERROR` |
| `error_message` | Text | nullable | Last error if status=ERROR |
| `last_heartbeat` | DateTime | nullable | Last successful heartbeat |
| `capabilities_json` | JSONB | not null, default='[]' | Declared capabilities |
| `connectors_json` | JSONB | not null, default='[]' | Connector GUIDs with local credentials |
| `api_key_hash` | String(255) | not null, unique | SHA-256 hash of API key |
| `api_key_prefix` | String(10) | not null | First 8 chars for identification |
| `version` | String(50) | nullable | Agent software version |
| `created_at` | DateTime | not null | Registration timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification |

**Capability Types (v1):**
```json
{
  "capabilities": [
    "local_filesystem",      // Can access local paths
    "tool:photostats",       // PhotoStats tool installed
    "tool:photo_pairing",    // Photo Pairing tool installed
    "tool:pipeline_validation",  // Pipeline Validation tool
    "connector:smb",         // Can connect to SMB shares
    "connector:s3",          // Can connect to S3 (with local creds)
    "connector:gcs",         // Can connect to GCS (with local creds)
    "app:lightroom",         // Adobe Lightroom available (future)
    "app:dxo_pureraw"        // DxO PureRAW available (future)
  ]
}
```

**Design Notes:**
- `capabilities_json` auto-populated on registration, can be manually adjusted
- `connectors_json` lists connectors for which this agent has local credentials
- API key shown once at registration, stored only as hash
- Version tracking enables compatibility checks

---

### AgentRegistrationToken (New Entity)

**GUID Prefix:** `art_`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `team_id` | Integer | FK(teams.id), not null | Team this token registers for |
| `created_by_user_id` | Integer | FK(users.id), not null | User who created token |
| `token_hash` | String(255) | unique, not null | SHA-256 hash of token |
| `name` | String(100) | nullable | Optional description |
| `is_used` | Boolean | not null, default=false | Whether token has been used |
| `used_by_agent_id` | Integer | FK(agents.id), nullable | Agent that used this token |
| `expires_at` | DateTime | not null | Token expiration |
| `created_at` | DateTime | not null | Creation timestamp |

**Design Notes:**
- One-time use tokens (is_used=true after registration)
- Default expiration: 24 hours
- Token shown once at creation
- Prevents unauthorized agent registration

---

### Job (Enhanced from Current)

**GUID Prefix:** `job_`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `collection_id` | Integer | FK(collections.id), not null | Target collection |
| `tool` | Enum | not null | `photostats`, `photo_pairing`, `pipeline_validation` |
| `pipeline_id` | Integer | FK(pipelines.id), nullable | Pipeline for validation |
| `status` | Enum | not null, default='PENDING' | Job lifecycle state |
| `bound_agent_id` | Integer | FK(agents.id), nullable | Required agent for LOCAL collections |
| `required_capabilities_json` | JSONB | not null | Capabilities needed (for unbound jobs) |
| `agent_id` | Integer | FK(agents.id), nullable | Currently assigned/executing agent |
| `assigned_at` | DateTime | nullable | When job was assigned |
| `started_at` | DateTime | nullable | When execution began |
| `completed_at` | DateTime | nullable | When execution finished |
| `progress_json` | JSONB | nullable | Current progress data |
| `result_id` | Integer | FK(analysis_results.id), nullable | Result after completion |
| `error_message` | Text | nullable | Error details if failed |
| `retry_count` | Integer | not null, default=0 | Number of retry attempts |
| `max_retries` | Integer | not null, default=3 | Maximum retry attempts |
| `priority` | Integer | not null, default=0 | Higher = more urgent |
| `scheduled_for` | DateTime | nullable | Earliest execution time (NULL=immediate) |
| `parent_job_id` | Integer | FK(jobs.id), nullable | Previous job in refresh chain |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification |

**Indexes:**
- Unique partial index: `(collection_id, tool) WHERE status = 'SCHEDULED'` - ensures only one scheduled job per collection/tool

**Job Status State Machine:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLAIMABLE JOBS                                   │
│  ┌───────────┐                              ┌───────────┐                   │
│  │ SCHEDULED │ (scheduled_for <= NOW())     │  PENDING  │◄────────────────┐ │
│  └─────┬─────┘                              └─────┬─────┘                 │ │
│        │                                          │         ▲             │ │
│        │ (cancelled)                              │ (canc.) │ (retry)     │ │
│        ▼                                          ▼         │             │ │
│   CANCELLED                                  CANCELLED      │             │ │
└────────┼──────────────────────────────────────────┼─────────┼─────────────┼─┘
         │                                          │         │             │
         │         ┌────────────────────────────────┘         │             │
         │         │                                          │             │
         ▼         ▼                                          │             │
       ┌─────────────┐  (agent offline)                       │             │
       │  ASSIGNED   │────────────────────────────────────────┘             │
       └──────┬──────┘                                                      │
              │                                                             │
              │ (execution starts)                                          │
              ▼                                                             │
       ┌─────────────┐                                                      │
       │   RUNNING   │                                                      │
       └──────┬──────┘                                                      │
              │                                                             │
     ┌────────┴────────┐                                                    │
     │                 │                                                    │
     ▼                 ▼                                                    │
┌─────────┐      ┌──────────┐                                               │
│ FAILED  │──────│COMPLETED │                                               │
└─────────┘      └────┬─────┘                                               │
                      │                                                     │
                      │ (if auto_refresh && TTL > 0)                        │
                      ▼                                                     │
               Create new SCHEDULED job ────────────────────────────────────┘
               (scheduled_for = completed_at + TTL)
```

**Key Insight: No Background Task Needed**

SCHEDULED jobs transition directly to ASSIGNED when an agent claims them (if `scheduled_for <= NOW()`).
The claim query handles both PENDING and ready-SCHEDULED jobs in a single query—no status transition step required.

**Status Definitions:**
| Status | Description |
|--------|-------------|
| `SCHEDULED` | Waiting for `scheduled_for` time; claimable once time passes |
| `PENDING` | Immediate job, ready to claim (no scheduled time) |
| `ASSIGNED` | Claimed by agent, not yet started |
| `RUNNING` | Agent is actively executing |
| `COMPLETED` | Successfully finished |
| `FAILED` | Execution failed (may retry) |
| `CANCELLED` | Cancelled by user or system |

**Job Creation Logic:**
```python
def create_job(
    collection: Collection,
    tool: str,
    scheduled_for: datetime | None = None,
    parent_job_id: int | None = None
) -> Job:
    """Create job with appropriate routing constraints and scheduling."""

    # Determine initial status based on scheduling
    if scheduled_for and scheduled_for > datetime.utcnow():
        status = JobStatus.SCHEDULED
    else:
        status = JobStatus.PENDING
        scheduled_for = None  # Normalize: immediate jobs have NULL scheduled_for

    job = Job(
        team_id=collection.team_id,
        collection_id=collection.id,
        tool=tool,
        status=status,
        scheduled_for=scheduled_for,
        parent_job_id=parent_job_id
    )

    # LOCAL collections: explicit agent binding (NOT capability-based)
    if collection.type == CollectionType.LOCAL:
        job.bound_agent_id = collection.bound_agent_id
        job.required_capabilities_json = [f"tool:{tool}"]
    else:
        # Remote collections: capability-based routing
        job.bound_agent_id = None
        job.required_capabilities_json = resolve_connector_capabilities(collection)

    return job

def resolve_connector_capabilities(collection: Collection) -> list[str]:
    """Determine capabilities needed for connector-based collection."""
    caps = [f"tool:{collection.tool}"]

    if collection.connector:
        # Require specific connector access
        caps.append(f"connector:{collection.connector.guid}")

    return caps
```

**Job Claim Logic (with Inline Scheduling):**

Scheduled jobs are claimed directly during agent polling—no background task needed. The claim query includes jobs that are either PENDING or SCHEDULED with a past `scheduled_for` time:

```python
from sqlalchemy import or_, and_

def is_ready_to_claim():
    """Filter for jobs ready to be claimed by an agent."""
    now = datetime.utcnow()
    return or_(
        Job.status == JobStatus.PENDING,
        and_(
            Job.status == JobStatus.SCHEDULED,
            Job.scheduled_for <= now
        )
    )

def claim_job(agent: Agent) -> Job | None:
    """Find and assign a job this agent can execute.

    Jobs become claimable when:
    - Status is PENDING (immediate jobs), OR
    - Status is SCHEDULED and scheduled_for time has passed
    """
    # Priority 1: Jobs explicitly bound to this agent
    job = db.query(Job).filter(
        is_ready_to_claim(),
        Job.team_id == agent.team_id,
        Job.bound_agent_id == agent.id
    ).order_by(Job.priority.desc(), Job.created_at.asc()
    ).with_for_update(skip_locked=True).first()

    if job:
        return assign_job(job, agent)

    # Priority 2: Unbound jobs matching agent capabilities
    job = db.query(Job).filter(
        is_ready_to_claim(),
        Job.team_id == agent.team_id,
        Job.bound_agent_id.is_(None),
        Job.required_capabilities_json.contained_by(agent.capabilities_json)
    ).order_by(Job.priority.desc(), Job.created_at.asc()
    ).with_for_update(skip_locked=True).first()

    if job:
        return assign_job(job, agent)

    return None


def assign_job(job: Job, agent: Agent) -> Job:
    """Assign job to agent, transitioning from PENDING/SCHEDULED to ASSIGNED."""
    job.status = JobStatus.ASSIGNED
    job.assigned_agent_id = agent.id
    job.assigned_at = datetime.utcnow()
    db.commit()
    return job
```

**Why No Background Task:**

The pull-based polling model eliminates the need for a background process to transition job statuses:

| Approach | Complexity | Latency | Resource Usage |
|----------|------------|---------|----------------|
| Background task | Higher (extra process, scheduler) | Up to polling interval (30-60s) | Constant DB polling |
| Inline in claim query | Lower (single query) | Zero (instant on poll) | On-demand only |

The SCHEDULED status remains useful for:
- UI display: Show "upcoming" vs "ready" jobs
- Cancellation: User can cancel a scheduled job before it runs
- History: Track when job was originally scheduled vs when claimed

**Job Completion with Auto-Scheduling:**
```python
def complete_job(job: Job, status: JobStatus, result: AnalysisResult | None) -> None:
    """Complete job and optionally schedule next refresh."""
    job.status = status
    job.completed_at = datetime.utcnow()

    if result:
        job.result_id = result.id

    # Auto-schedule next job if collection has TTL configured
    if status == JobStatus.COMPLETED:
        collection = job.collection
        if collection.auto_refresh and collection.refresh_interval_hours:
            # Calculate next scheduled time
            next_run = job.completed_at + timedelta(hours=collection.refresh_interval_hours)

            # Cancel any existing scheduled job for this collection/tool
            existing = db.query(Job).filter(
                Job.collection_id == job.collection_id,
                Job.tool == job.tool,
                Job.status == JobStatus.SCHEDULED
            ).first()

            if existing:
                existing.status = JobStatus.CANCELLED

            # Create next scheduled job
            next_job = create_job(
                collection=collection,
                tool=job.tool,
                scheduled_for=next_run,
                parent_job_id=job.id
            )
            db.add(next_job)

            logger.info(
                f"Scheduled next {job.tool} job for collection {collection.guid} "
                f"at {next_run.isoformat()}"
            )

    db.commit()
```

---

### Connector (Enhanced)

**Additions to existing Connector model:**

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `credential_location` | Enum | not null, default='SERVER' | `SERVER`, `AGENT`, or `PENDING` |

**Credential Location Semantics:**

| Mode | Credentials On Server | Credentials On Agent | Server Execution | Agent Execution |
|------|----------------------|---------------------|------------------|-----------------|
| `SERVER` | ✅ Encrypted | Optional (via test) | ✅ Yes | ✅ If capable |
| `AGENT` | ❌ None | ✅ Required | ❌ No | ✅ If has creds |
| `PENDING` | ❌ None | ❌ Not yet | ❌ No | ❌ Not yet |

**Workflow for Each Mode:**

1. **SERVER** (default, current behavior):
   - User provides credentials when creating connector
   - Server can execute jobs directly
   - Agents can also access if they test connection successfully

2. **AGENT** (security-focused):
   - User creates connector without credentials on server
   - User configures credentials via agent CLI
   - Only agents with local credentials can execute jobs

3. **PENDING** (tentative activation):
   - User creates connector with just metadata (type, name, bucket/path)
   - Connector is "inactive" until an agent configures credentials
   - Agent operator discovers pending connector via CLI
   - After agent configures credentials and tests connection, connector becomes usable

**Migration:** Existing connectors default to `SERVER` for backward compatibility.

---

### Collection (Enhanced)

**Additions to existing Collection model:**

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `bound_agent_id` | Integer | FK(agents.id), nullable | Agent bound to LOCAL collections |
| `auto_refresh` | Boolean | not null, default=true | Enable automatic refresh scheduling |
| `refresh_interval_hours` | Integer | nullable | Hours between automatic refreshes (TTL) |
| `last_refresh_at` | DateTime | nullable | Timestamp of last completed refresh |
| `next_refresh_at` | DateTime | nullable | Computed: next scheduled refresh time |

**Binding Rules:**

| Collection Type | bound_agent_id | Job Routing |
|-----------------|----------------|-------------|
| `LOCAL` | Required (not null) | Only bound agent can execute |
| `S3` | NULL | Any agent with connector capability |
| `GCS` | NULL | Any agent with connector capability |
| `SMB` | NULL (usually) | Any agent with connector capability |

**Auto-Refresh Configuration:**

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_refresh` | true | Whether to auto-schedule next job on completion |
| `refresh_interval_hours` | 24 | Time between refreshes (NULL = no auto-refresh) |

**Common TTL Values:**
- Real-time monitoring: 1 hour
- Daily reports: 24 hours
- Weekly summaries: 168 hours (7 days)
- Archive collections: NULL (manual only)

**Design Notes:**
- `bound_agent_id` is **required** for LOCAL collections, **optional** for others
- SMB collections may optionally bind to specific agent (network locality)
- UI enforces: LOCAL collection form requires agent selection
- Deleting an agent with bound collections requires migration or fails
- `next_refresh_at` is denormalized for efficient dashboard queries
- Collection deletion cascades to cancel any SCHEDULED jobs

**Validation Rules:**
```python
def validate_collection(collection: CollectionCreate) -> None:
    if collection.type == CollectionType.LOCAL:
        if not collection.bound_agent_id:
            raise ValidationError("Local collections require an agent binding")
    # Remote collections must have either connector or bound_agent
    if collection.type in (CollectionType.S3, CollectionType.GCS):
        if not collection.connector_id:
            raise ValidationError("Remote collections require a connector")

def on_collection_delete(collection: Collection) -> None:
    """Cancel scheduled jobs when collection is deleted."""
    db.query(Job).filter(
        Job.collection_id == collection.id,
        Job.status == JobStatus.SCHEDULED
    ).update({Job.status: JobStatus.CANCELLED})
```

---

### JobQueue Persistence Model

Rather than in-memory queue, jobs are persisted to database:

**Queue Query Pattern:**
```sql
-- Find next job for an agent with given capabilities
SELECT * FROM jobs
WHERE status = 'PENDING'
  AND team_id = :team_id
  AND required_capabilities_json <@ :agent_capabilities  -- JSONB containment
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;  -- Prevent race conditions
```

**Alternative: Redis-Based Queue**

For higher throughput, Redis can serve as the job queue:

```python
# Redis queue structure
KEYS:
  "jobs:{team_id}:pending"     # Sorted set: (score=priority, member=job_guid)
  "jobs:{team_id}:assigned"    # Hash: {job_guid: agent_guid}
  "jobs:{job_guid}:data"       # Hash: job attributes
  "agents:{team_id}:heartbeats" # Hash: {agent_guid: last_heartbeat}
```

**Recommendation:** Start with PostgreSQL-backed queue (simpler), migrate to Redis if throughput requires.

---

## Communication Protocol

The agent-server communication uses a **hybrid protocol**:
- **REST API**: Registration, heartbeat, job claiming, job completion
- **WebSocket**: Real-time progress streaming during job execution

This hybrid approach maintains the real-time progress visibility users expect while keeping job discovery simple and firewall-friendly.

### Protocol Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Lifecycle                                 │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐  │
│  │ Registration │    │  Idle Loop   │    │      Job Execution           │  │
│  │   (REST)     │───>│   (REST)     │───>│                              │  │
│  │              │    │              │    │  1. Claim job (REST)         │  │
│  │ POST /register│    │ POST /heartbeat│    │  2. Open WebSocket          │  │
│  │              │    │ POST /jobs/claim│    │  3. Stream progress (WS)    │  │
│  │              │    │              │    │  4. Complete job (REST)      │  │
│  │              │    │              │    │  5. Close WebSocket          │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────────┘  │
│                             ▲                          │                     │
│                             └──────────────────────────┘                     │
│                                  (return to idle)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent ↔ Coordinator REST API

**Base URL:** `{server_url}/api/agent/v1`

**Authentication:** `Authorization: Bearer agt_key_xxxxx`

#### Registration

```http
POST /api/agent/v1/register
Content-Type: application/json

{
  "registration_token": "art_xxxxx...",
  "name": "Office Workstation",
  "hostname": "ws-001.local",
  "os_info": "Ubuntu 22.04 LTS",
  "version": "1.0.0",
  "capabilities": ["local_filesystem", "tool:photostats", "tool:photo_pairing"],
  "connectors": []  // Connector GUIDs with local credentials
}

Response:
{
  "agent_guid": "agt_01hgw2bbg...",
  "api_key": "agt_key_xxxxx...",  // Shown once, store securely
  "server_version": "1.5.0"
}
```

#### Heartbeat

```http
POST /api/agent/v1/heartbeat
Authorization: Bearer agt_key_xxxxx

{
  "status": "ONLINE",
  "current_job_guid": "job_01hgw2bbg..." | null,
  "metrics": {  // Optional
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "disk_free_gb": 120.5
  }
}

Response:
{
  "acknowledged": true,
  "server_time": "2026-01-14T12:00:00Z"
}
```

#### Job Polling (Claim)

```http
POST /api/agent/v1/jobs/claim
Authorization: Bearer agt_key_xxxxx

{
  "capabilities": ["local_filesystem", "tool:photostats"]  // Current capabilities
}

Response (job available):
{
  "job": {
    "guid": "job_01hgw2bbg...",
    "tool": "photostats",
    "collection": {
      "guid": "col_01hgw2bbg...",
      "name": "Wedding Photos 2026",
      "type": "LOCAL",
      "location": "/home/user/Photos/Wedding2026"
    },
    "pipeline": null,
    "parameters": {},
    "websocket_url": "/ws/agent/jobs/job_01hgw2bbg.../progress"
  }
}

Response (no job):
{
  "job": null
}
```

#### Job Completion

```http
POST /api/agent/v1/jobs/{job_guid}/complete
Authorization: Bearer agt_key_xxxxx
Content-Type: multipart/form-data

{
  "status": "COMPLETED" | "FAILED",
  "results_json": {...},  // Tool output
  "report_html": "...",   // Generated HTML report
  "error_message": null | "Error details...",
  "metrics": {
    "duration_seconds": 123.4,
    "files_processed": 5678
  }
}

Response:
{
  "result_guid": "res_01hgw2bbg...",
  "acknowledged": true
}
```

#### Connector Credentials (Agent-Local Setup)

```http
GET /api/agent/v1/connectors/{connector_guid}/metadata
Authorization: Bearer agt_key_xxxxx

Response:
{
  "guid": "con_01hgw2bbg...",
  "name": "My S3 Bucket",
  "type": "S3",
  "credential_location": "AGENT",
  "credential_schema": {
    "type": "object",
    "properties": {
      "aws_access_key_id": {"type": "string"},
      "aws_secret_access_key": {"type": "string"},
      "region": {"type": "string"},
      "endpoint_url": {"type": "string", "optional": true}
    }
  }
}
```

---

### Agent → Server WebSocket (Progress Streaming)

When an agent claims a job, it establishes a WebSocket connection to stream real-time progress updates. The server proxies these updates to connected frontend clients, maintaining the existing real-time UX.

**WebSocket URL:** `wss://{server_url}/ws/agent/jobs/{job_guid}/progress`

**Authentication:** Query parameter `?token=agt_key_xxxxx`

#### Connection Flow

```
Agent                          Server                         Frontend
  │                              │                               │
  │ 1. POST /jobs/claim          │                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ 2. Job assigned              │                               │
  │<─────────────────────────────│                               │
  │                              │                               │
  │ 3. Connect WebSocket         │                               │
  │   /ws/agent/jobs/{id}/progress                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ 4. Connection accepted       │                               │
  │<─────────────────────────────│                               │
  │                              │                               │
  │ 5. Send progress update      │                               │
  │─────────────────────────────>│ 6. Proxy to frontend WS      │
  │                              │──────────────────────────────>│
  │                              │                               │
  │ 7. Send progress update      │                               │
  │─────────────────────────────>│ 8. Proxy to frontend WS      │
  │                              │──────────────────────────────>│
  │                              │                               │
  │         ... (continuous progress streaming) ...              │
  │                              │                               │
  │ 9. Close WebSocket           │                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ 10. POST /jobs/{id}/complete │                               │
  │─────────────────────────────>│ 11. Broadcast completion     │
  │                              │──────────────────────────────>│
```

#### WebSocket Message Format (Agent → Server)

**Progress Update:**
```json
{
  "type": "progress",
  "timestamp": "2026-01-14T12:00:05.123Z",
  "data": {
    "stage": "scanning",
    "percentage": 45,
    "files_scanned": 1234,
    "total_files": 2741,
    "current_file": "IMG_1234.jpg",
    "message": "Scanning files..."
  }
}
```

**Stage Transition:**
```json
{
  "type": "stage",
  "timestamp": "2026-01-14T12:01:00.000Z",
  "data": {
    "previous_stage": "scanning",
    "current_stage": "analyzing",
    "message": "Analyzing 2741 files..."
  }
}
```

**Error (Non-Fatal):**
```json
{
  "type": "warning",
  "timestamp": "2026-01-14T12:01:30.000Z",
  "data": {
    "message": "Could not read EXIF from IMG_5678.jpg",
    "file": "IMG_5678.jpg"
  }
}
```

#### WebSocket Message Format (Server → Agent)

**Cancellation Request:**
```json
{
  "type": "cancel",
  "timestamp": "2026-01-14T12:02:00.000Z",
  "reason": "User requested cancellation"
}
```

**Heartbeat (Keep-Alive):**
```json
{
  "type": "ping",
  "timestamp": "2026-01-14T12:02:30.000Z"
}
```

Agent responds with:
```json
{
  "type": "pong",
  "timestamp": "2026-01-14T12:02:30.050Z"
}
```

#### Server-Side WebSocket Proxy

The server acts as a proxy between agent WebSocket and frontend WebSocket:

```python
# Server-side WebSocket handler (pseudocode)

class AgentProgressWebSocket:
    """Handles WebSocket connection from agent for progress streaming."""

    async def on_connect(self, websocket, job_guid: str, agent_key: str):
        # Validate agent authentication
        agent = await validate_agent_key(agent_key)
        if not agent:
            await websocket.close(code=4001, reason="Invalid agent key")
            return

        # Validate job ownership
        job = await get_job(job_guid)
        if job.agent_id != agent.id:
            await websocket.close(code=4003, reason="Job not assigned to this agent")
            return

        # Register this WebSocket for the job
        self.agent_sockets[job_guid] = websocket

        # Update job status to RUNNING
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()

    async def on_message(self, websocket, message: dict):
        job_guid = self.get_job_guid(websocket)

        if message["type"] == "progress":
            # Update job progress in database
            await update_job_progress(job_guid, message["data"])

            # Proxy to all frontend WebSocket clients watching this job
            await broadcast_to_frontend(
                channel=f"/ws/jobs/{job_guid}",
                message={
                    "type": "job_progress",
                    "job_guid": job_guid,
                    "progress": message["data"]
                }
            )

            # Also broadcast to global job feed
            await broadcast_to_frontend(
                channel="/ws/jobs/all",
                message={
                    "type": "job_progress",
                    "job_guid": job_guid,
                    "progress": message["data"]
                }
            )

        elif message["type"] == "pong":
            # Update agent heartbeat
            await touch_agent_heartbeat(job_guid)

    async def on_disconnect(self, websocket):
        job_guid = self.get_job_guid(websocket)
        del self.agent_sockets[job_guid]
        # Job completion handled via REST endpoint
```

#### Fallback: REST Progress Updates

If WebSocket connection fails (firewall, proxy issues), the agent falls back to REST-based progress updates:

```http
POST /api/agent/v1/jobs/{job_guid}/progress
Authorization: Bearer agt_key_xxxxx

{
  "stage": "scanning",
  "percentage": 45,
  "files_scanned": 1234,
  "message": "Scanning files..."
}

Response:
{
  "acknowledged": true,
  "cancelled": false  // Agent should abort if true
}
```

**Fallback Behavior:**
- Agent attempts WebSocket connection first
- If connection fails after 3 retries, switch to REST polling
- REST progress updates sent every 2-5 seconds
- Slightly degraded UX (less smooth progress) but functional

---

### Agent Main Loop

```python
async def agent_main_loop():
    while running:
        # 1. Send heartbeat (REST)
        await send_heartbeat()

        # 2. Check for job (if idle)
        if not current_job:
            job = await claim_job()
            if job:
                asyncio.create_task(execute_job_with_websocket(job))

        # 3. Wait before next poll
        await asyncio.sleep(POLL_INTERVAL)

async def execute_job_with_websocket(job: Job):
    """Execute job with WebSocket progress streaming."""
    global current_job
    current_job = job

    # 1. Establish WebSocket connection for progress
    ws = await connect_progress_websocket(job.websocket_url)
    use_websocket = ws is not None

    if not use_websocket:
        logger.warning("WebSocket unavailable, falling back to REST progress")

    try:
        # 2. Execute tool with progress callback
        result = await tool_executor.run(
            tool=job.tool,
            collection=job.collection,
            progress_callback=lambda p: report_progress(ws, job.guid, p, use_websocket)
        )

        # 3. Report completion (REST)
        await complete_job(job.guid, "COMPLETED", result)

    except CancelledException:
        await complete_job(job.guid, "CANCELLED", None)

    except Exception as e:
        await complete_job(job.guid, "FAILED", None, error=str(e))

    finally:
        # 4. Close WebSocket
        if ws:
            await ws.close()
        current_job = None

async def report_progress(ws, job_guid: str, progress: dict, use_websocket: bool):
    """Report progress via WebSocket or REST fallback."""
    if use_websocket and ws and ws.open:
        await ws.send(json.dumps({
            "type": "progress",
            "timestamp": datetime.utcnow().isoformat(),
            "data": progress
        }))
    else:
        # Fallback to REST (rate-limited to every 2 seconds)
        await rest_progress_update(job_guid, progress)

POLL_INTERVAL = 5  # seconds when idle
HEARTBEAT_INTERVAL = 30  # seconds
WS_RECONNECT_ATTEMPTS = 3
```

**Backoff on Errors:**
- Network error: exponential backoff (5s, 10s, 20s, 40s, max 60s)
- Authentication error: log and exit (requires manual intervention)
- Server 5xx: exponential backoff with jitter
- WebSocket disconnect during job: attempt reconnect, fall back to REST if fails

---

## Security Model

### Credential Security Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                         CENTRAL SERVER                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Connector: "AWS Production"                                      │ │
│  │  type: S3                                                         │ │
│  │  credential_location: AGENT                                       │ │
│  │  credentials: NULL (not stored)                                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  Job Queue: "Analyze AWS Photos"                                      │
│  required_capabilities: ["connector:con_aws_prod"]                    │
│                         ↓                                              │
│  Only agents with local credentials for this connector can claim     │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│        Agent Alpha           │    │        Agent Beta            │
│  ~/.photo-admin/             │    │  ~/.photo-admin/             │
│    credentials.enc           │    │    credentials.enc           │
│    ┌──────────────────────┐  │    │    (no AWS credentials)      │
│    │ con_aws_prod:        │  │    │                              │
│    │   aws_access_key_id  │  │    │  ❌ Cannot claim this job   │
│    │   aws_secret_key     │  │    │                              │
│    └──────────────────────┘  │    └──────────────────────────────┘
│  ✅ Can claim and execute    │
└──────────────────────────────┘
```

### Authentication Layers

1. **Agent Registration**: One-time token (team-scoped, expires in 24h)
2. **Agent API Key**: Long-lived key (hashed storage, shown once)
3. **Job Claims**: Only agents matching required_capabilities can claim
4. **Connector Access**: Agent-local credentials decrypted only on agent

### Threat Model

| Threat | Mitigation |
|--------|------------|
| Unauthorized agent registration | One-time registration tokens, team-scoped |
| Agent API key theft | Key rotation, IP allowlisting (v2) |
| Job injection | Jobs created only via authenticated API |
| Cross-team data access | team_id enforced on all queries |
| Man-in-the-middle | HTTPS required, certificate pinning (optional) |
| Credential exfiltration | Agent-local storage, never transmitted |
| Malicious agent results | Result validation, anomaly detection (v2) |

### Agent Security Requirements

**Agent Binary:**
- Code-signed binary (macOS/Windows)
- Checksum verification (Linux)
- No auto-update without explicit user action (v1)

**Local Credential Storage:**
```
~/.photo-admin/
├── config.yaml          # Agent configuration
├── credentials.enc      # Encrypted connector credentials
├── agent_key.enc        # Encrypted API key
└── local_queue.db       # SQLite for offline operation
```

**Encryption:**
- Local master key derived from user password or machine key
- Fernet encryption (same as server-side)
- Key never transmitted to server

---

## Technical Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CENTRAL SERVER                                 │
│                                                                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐  │
│  │   FastAPI Backend   │  │   PostgreSQL DB    │  │  Redis (Optional) │  │
│  │                      │  │                    │  │                   │  │
│  │  /api/agent/v1/*    │  │  - agents          │  │  - job queue     │  │
│  │  /api/jobs/*        │  │  - jobs            │  │  - heartbeats    │  │
│  │  /api/connectors/*  │  │  - connectors      │  │  - pub/sub       │  │
│  │                      │  │  - results         │  │                   │  │
│  └─────────┬───────────┘  └────────────────────┘  └──────────────────┘  │
│            │                                                              │
│  ┌─────────▼────────────────────────────────────────────────────────┐   │
│  │                    Agent Coordinator Service                       │   │
│  │  - Agent registration and authentication                          │   │
│  │  - Job routing and assignment                                     │   │
│  │  - Heartbeat monitoring                                           │   │
│  │  - Result collection                                              │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ HTTPS REST API
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   Agent (macOS)   │    │  Agent (Windows)  │    │   Agent (Linux)   │
│                   │    │                   │    │                   │
│  ┌─────────────┐  │    │  ┌─────────────┐  │    │  ┌─────────────┐  │
│  │ Agent Core  │  │    │  │ Agent Core  │  │    │  │ Agent Core  │  │
│  │ - Polling   │  │    │  │ - Polling   │  │    │  │ - Polling   │  │
│  │ - Execution │  │    │  │ - Execution │  │    │  │ - Execution │  │
│  │ - Reporting │  │    │  │ - Reporting │  │    │  │ - Reporting │  │
│  └─────────────┘  │    │  └─────────────┘  │    │  └─────────────┘  │
│                   │    │                   │    │                   │
│  ┌─────────────┐  │    │  ┌─────────────┐  │    │  ┌─────────────┐  │
│  │ Tool Bundle │  │    │  │ Tool Bundle │  │    │  │ Tool Bundle │  │
│  │ - PhotoStats│  │    │  │ - PhotoStats│  │    │  │ - PhotoStats│  │
│  │ - Pairing   │  │    │  │ - Pairing   │  │    │  │ - Pairing   │  │
│  │ - Pipeline  │  │    │  │ - Pipeline  │  │    │  │ - Pipeline  │  │
│  └─────────────┘  │    │  └─────────────┘  │    │  └─────────────┘  │
│                   │    │                   │    │                   │
│  ┌─────────────┐  │    │  ┌─────────────┐  │    │  ┌─────────────┐  │
│  │ Local Store │  │    │  │ Local Store │  │    │  │ Local Store │  │
│  │ - Creds.enc │  │    │  │ - Creds.enc │  │    │  │ - Creds.enc │  │
│  │ - Offline Q │  │    │  │ - Offline Q │  │    │  │ - Offline Q │  │
│  └─────────────┘  │    │  └─────────────┘  │    │  └─────────────┘  │
└───────────────────┘    └───────────────────┘    └───────────────────┘
```

### Agent Architecture

```python
# Pseudocode for agent structure

class PhotoAdminAgent:
    """Main agent process."""

    def __init__(self, config_path: Path):
        self.config = AgentConfig.load(config_path)
        self.api_client = AgentAPIClient(self.config.server_url, self.config.api_key)
        self.tool_executor = ToolExecutor()
        self.credential_store = LocalCredentialStore(self.config.credentials_path)
        self.current_job: Job | None = None

    async def run(self):
        """Main event loop."""
        logger.info(f"Agent {self.config.name} starting...")

        while self.running:
            try:
                # Send heartbeat
                await self.send_heartbeat()

                # Try to claim a job if idle
                if not self.current_job:
                    job = await self.api_client.claim_job(self.get_capabilities())
                    if job:
                        asyncio.create_task(self.execute_job(job))

                await asyncio.sleep(self.config.poll_interval)

            except NetworkError as e:
                logger.warning(f"Network error: {e}, backing off...")
                await self.backoff()

    def get_capabilities(self) -> list[str]:
        """Return current capabilities including local connector access."""
        caps = ["local_filesystem"]
        caps.extend(self.tool_executor.available_tools())
        caps.extend(self.credential_store.available_connectors())
        return caps

    async def execute_job(self, job: Job):
        """Execute a job and report results."""
        self.current_job = job

        try:
            # Get credentials if needed
            creds = await self.resolve_credentials(job)

            # Execute tool
            result = await self.tool_executor.run(
                tool=job.tool,
                collection=job.collection,
                credentials=creds,
                progress_callback=lambda p: self.report_progress(job.guid, p)
            )

            # Report completion
            await self.api_client.complete_job(
                job_guid=job.guid,
                status="COMPLETED",
                results=result.to_json(),
                report_html=result.generate_html()
            )

        except Exception as e:
            await self.api_client.complete_job(
                job_guid=job.guid,
                status="FAILED",
                error_message=str(e)
            )

        finally:
            self.current_job = None
```

### Server-Side Components

```python
# New services for agent coordination

class AgentService:
    """Manages agent lifecycle."""

    def register_agent(self, token: str, agent_data: AgentRegisterRequest) -> Agent:
        """Register new agent using registration token."""
        # Validate token
        reg_token = self.validate_registration_token(token)

        # Create agent
        agent = Agent(
            team_id=reg_token.team_id,
            name=agent_data.name,
            hostname=agent_data.hostname,
            capabilities_json=agent_data.capabilities,
            api_key_hash=hash_api_key(api_key := generate_api_key()),
            status=AgentStatus.ONLINE
        )

        # Mark token as used
        reg_token.is_used = True
        reg_token.used_by_agent_id = agent.id

        return agent, api_key  # api_key shown once

    def process_heartbeat(self, agent_guid: str, heartbeat: HeartbeatRequest) -> None:
        """Update agent status from heartbeat."""
        agent = self.get_agent(agent_guid)
        agent.status = heartbeat.status
        agent.last_heartbeat = datetime.utcnow()
        # Optionally store metrics

class JobCoordinatorService:
    """Manages distributed job queue."""

    def create_job(self, collection: Collection, tool: str) -> Job:
        """Create job with required capabilities."""
        job = Job(
            team_id=collection.team_id,
            collection_id=collection.id,
            tool=tool,
            required_capabilities_json=self.resolve_capabilities(collection),
            status=JobStatus.PENDING
        )
        return job

    def claim_job(self, agent: Agent) -> Job | None:
        """Assign next matching job to agent."""
        # Find job where required_capabilities ⊆ agent.capabilities
        job = self.db.query(Job).filter(
            Job.status == JobStatus.PENDING,
            Job.team_id == agent.team_id,
            Job.required_capabilities_json.contained_by(agent.capabilities_json)
        ).with_for_update(skip_locked=True).first()

        if job:
            job.status = JobStatus.ASSIGNED
            job.agent_id = agent.id
            job.assigned_at = datetime.utcnow()

        return job

    def complete_job(self, job_guid: str, result: JobCompletionRequest) -> AnalysisResult:
        """Process job completion from agent."""
        job = self.get_job(job_guid)
        job.status = JobStatus.COMPLETED if result.status == "COMPLETED" else JobStatus.FAILED
        job.completed_at = datetime.utcnow()

        if result.status == "COMPLETED":
            # Store analysis result
            analysis_result = AnalysisResult(
                collection_id=job.collection_id,
                tool=job.tool,
                results_json=result.results_json,
                report_html=result.report_html
            )
            job.result_id = analysis_result.id

            # Update collection statistics
            self.update_collection_stats(job.collection, result.results_json)

        return analysis_result
```

---

## Migration Strategy

### Phase 1: Foundation (No Breaking Changes)

1. **Database Schema**: Add Agent, AgentRegistrationToken, Job tables
2. **Agent API Endpoints**: `/api/agent/v1/*` (new routes, no conflict)
3. **Job Persistence**: Migrate in-memory queue to database-backed queue
4. **Server-Side Execution**: Continue working as-is (fallback)

**Backward Compatibility:** Existing installations continue working unchanged.

### Phase 2: Agent Introduction

1. **Agent Binary**: Release cross-platform agent (macOS, Windows, Linux)
2. **Registration UI**: Add agent management to Settings
3. **Job Routing**: Jobs prefer agents when capable, fallback to server
4. **Documentation**: Agent installation and configuration guide

**Transition:** Users can optionally install agents; server execution remains default.

### Phase 3: Credential Locality

1. **Connector Enhancement**: Add `credential_location` field
2. **Agent Credential UI**: Configure local credentials per agent
3. **Job Routing Update**: Require agent for agent-local connectors
4. **Migration Tool**: Option to migrate existing connectors to agent-local

**Security Win:** Enterprise users can migrate credentials off server.

### Phase 4: Local Collections (Full Value)

1. **Local Collection Type**: Enable `type=LOCAL` with agent requirement
2. **SMB via Agent**: SMB connectors default to agent-local
3. **Performance Optimization**: Parallel job execution (v2)
4. **Desktop App Foundation**: Capability detection for installed apps

---

## Requirements

### Functional Requirements

#### FR-100: Agent Management

- **FR-100.1**: Create registration token from Settings UI (team-scoped)
- **FR-100.2**: Registration token expires after 24 hours or single use
- **FR-100.3**: Agent registers with token, receives API key (shown once)
- **FR-100.4**: Agent status updates via heartbeat (30-second interval)
- **FR-100.5**: Agent marked offline after 90 seconds without heartbeat
- **FR-100.6**: View agent list with status, capabilities, last heartbeat
- **FR-100.7**: Delete agent (revokes API key, reassigns queued jobs)
- **FR-100.8**: Rename agent from UI

#### FR-200: Job Distribution

- **FR-200.1**: Jobs persist to database (not in-memory)
- **FR-200.2**: Jobs include `required_capabilities_json` array
- **FR-200.3**: Agent claims job via poll (POST /jobs/claim)
- **FR-200.4**: Job assigned to first capable agent that claims it
- **FR-200.5**: Server executes job if no capable agent online (for server connectors)
- **FR-200.6**: Job reassigned if agent goes offline mid-execution
- **FR-200.7**: Failed jobs retry up to max_retries (default: 3)
- **FR-200.8**: Job history retained for 90 days (configurable)

#### FR-300: Connector Credential Modes

- **FR-300.1**: Connector has `credential_location` enum (`SERVER` | `AGENT` | `PENDING`)
- **FR-300.2**: `SERVER`: Credentials stored encrypted on server (current behavior)
- **FR-300.3**: `AGENT`: Credentials stored only on agent(s), NOT on server
- **FR-300.4**: `PENDING`: Connector created without credentials (tentative activation)
- **FR-300.5**: Agent CLI lists PENDING/AGENT connectors for credential configuration
- **FR-300.6**: Agent tests connection before storing credentials locally
- **FR-300.7**: Agent reports connector capability to server after successful test
- **FR-300.8**: Jobs requiring agent-only connectors only route to capable agents
- **FR-300.9**: UI indicates credential status: "Server", "Agent-only", "Pending"
- **FR-300.10**: UI shows which agents have credentials for each connector

#### FR-400: Local Collection Support (Agent Binding)

- **FR-400.1**: Collection `type=LOCAL` creates local filesystem collection
- **FR-400.2**: Local collections REQUIRE explicit agent binding at creation
- **FR-400.3**: UI enforces agent selection for LOCAL collection type
- **FR-400.4**: Jobs for LOCAL collections route ONLY to bound agent (not capability-based)
- **FR-400.5**: Same path on different agents creates different collections
- **FR-400.6**: Local collection jobs cannot execute on server
- **FR-400.7**: UI clearly shows bound agent for each local collection
- **FR-400.8**: Agent deletion blocked if bound collections exist (or require migration)
- **FR-400.9**: If bound agent is offline, jobs queue until agent comes online

#### FR-450: Tool Capability Reporting

- **FR-450.1**: All agents report bundled tool capabilities automatically
- **FR-450.2**: Tool capabilities include version information
- **FR-450.3**: Agent heartbeat includes current capabilities
- **FR-450.4**: Server tracks which agents can execute which tools
- **FR-450.5**: (Future) Agent detects and reports external tool availability

#### FR-460: Scheduled Job Execution

- **FR-460.1**: Jobs support `scheduled_for` field (DateTime, nullable)
- **FR-460.2**: Jobs with future `scheduled_for` have status `SCHEDULED`
- **FR-460.3**: Claim query includes SCHEDULED jobs where `scheduled_for <= NOW()` (no background task)
- **FR-460.4**: SCHEDULED jobs transition directly to ASSIGNED when claimed (not via PENDING)
- **FR-460.5**: Unique constraint ensures one SCHEDULED job per (collection, tool)
- **FR-460.6**: Job completion auto-creates next SCHEDULED job if TTL configured
- **FR-460.7**: Next scheduled time = completion time + collection TTL
- **FR-460.8**: Manual refresh cancels existing SCHEDULED job, runs immediately
- **FR-460.9**: Collection TTL change updates existing SCHEDULED job's time
- **FR-460.10**: Collection deletion cascades to cancel SCHEDULED jobs
- **FR-460.11**: UI displays scheduled jobs with countdown to execution
- **FR-460.12**: Job history links via `parent_job_id` for refresh chain visibility

#### FR-500: Real-Time Progress Streaming

- **FR-500.1**: Agent establishes WebSocket connection to stream progress in real-time
- **FR-500.2**: Progress updates include: stage, percentage, files processed, current file, message
- **FR-500.3**: Server proxies agent WebSocket to frontend WebSocket channels
- **FR-500.4**: Frontend receives real-time updates same as server-executed jobs
- **FR-500.5**: Server can send cancellation request to agent via WebSocket
- **FR-500.6**: Agent responds to WebSocket ping/pong for connection health
- **FR-500.7**: Fallback to REST progress updates if WebSocket unavailable
- **FR-500.8**: REST fallback updates every 2-5 seconds (graceful degradation)

#### FR-510: Job Completion and Results

- **FR-510.1**: Agent reports completion via REST with results JSON and HTML report
- **FR-510.2**: Results stored in existing AnalysisResult table
- **FR-510.3**: Collection statistics updated on job completion
- **FR-510.4**: Job completion triggers WebSocket notification to frontend
- **FR-510.5**: WebSocket connection closed after completion REST call

---

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: Job claim latency < 100ms (excluding network)
- **NFR-100.2**: Support 100+ concurrent agents per team
- **NFR-100.3**: Job queue throughput: 1000 jobs/minute
- **NFR-100.4**: Heartbeat processing < 50ms
- **NFR-100.5**: Agent polling interval: 5-10 seconds (configurable)
- **NFR-100.6**: WebSocket progress latency < 200ms (agent → frontend)
- **NFR-100.7**: Support 100+ concurrent WebSocket connections per server
- **NFR-100.8**: WebSocket message throughput: 10 messages/second per job

#### NFR-200: Reliability

- **NFR-200.1**: Jobs survive server restart (persistent queue)
- **NFR-200.2**: Agent reconnects automatically after network failure
- **NFR-200.3**: Failed jobs retry with exponential backoff
- **NFR-200.4**: Orphaned jobs (agent offline) reassigned within 2 minutes
- **NFR-200.5**: Results survive agent restart (completion is atomic)
- **NFR-200.6**: WebSocket auto-reconnect on disconnect (3 attempts)
- **NFR-200.7**: Graceful fallback to REST if WebSocket unavailable
- **NFR-200.8**: WebSocket ping/pong keepalive every 30 seconds

#### NFR-300: Security

- **NFR-300.1**: Agent API keys hashed with SHA-256
- **NFR-300.2**: Registration tokens single-use, expire in 24 hours
- **NFR-300.3**: All agent communication over HTTPS
- **NFR-300.4**: Agent-local credentials never transmitted to server
- **NFR-300.5**: Job results validated before storage (prevent injection)
- **NFR-300.6**: Rate limiting: 60 heartbeats/minute, 120 job claims/minute

#### NFR-400: Observability

- **NFR-400.1**: Agent status visible in real-time dashboard
- **NFR-400.2**: Job assignment logged with agent_guid
- **NFR-400.3**: Failed jobs include error message and stack trace
- **NFR-400.4**: Agent heartbeat history retained for 7 days
- **NFR-400.5**: Metrics endpoint for agent count, job throughput (future)

#### NFR-500: Compatibility

- **NFR-500.1**: Agent supports macOS 12+, Windows 10+, Ubuntu 20.04+
- **NFR-500.2**: Agent binary < 50MB (including tool bundle)
- **NFR-500.3**: Agent runs without administrator/root privileges
- **NFR-500.4**: Existing server-side execution continues working

---

## Implementation Plan

### Phase 1: Database Foundation (Priority: P0)

**Duration**: 2-3 weeks

**Tasks:**

1. **Database Schema**
   - Agent model with GuidMixin
   - AgentRegistrationToken model
   - Job model (enhanced from in-memory)
   - Connector enhancement (credential_location)
   - Database migrations

2. **Job Persistence**
   - JobRepository with database queries
   - Replace in-memory JobQueue
   - Job state machine implementation
   - Failed job retry logic

3. **Testing**
   - Unit tests for models
   - Integration tests for job persistence
   - Migration tests

**Checkpoint**: Jobs persist to database, existing functionality unchanged

---

### Phase 2: Agent Coordinator (Priority: P0)

**Duration**: 2-3 weeks

**Tasks:**

1. **Agent API Endpoints**
   - POST /api/agent/v1/register
   - POST /api/agent/v1/heartbeat
   - POST /api/agent/v1/jobs/claim
   - POST /api/agent/v1/jobs/{guid}/progress
   - POST /api/agent/v1/jobs/{guid}/complete

2. **Agent Service**
   - Registration with token validation
   - Heartbeat processing
   - Offline detection (background task)
   - API key authentication middleware

3. **Job Coordinator**
   - Capability-based job matching
   - Job claim with locking
   - Job reassignment on agent offline

4. **Testing**
   - API endpoint tests
   - Service unit tests
   - Concurrency tests (job claiming)

**Checkpoint**: Server can coordinate agents (agent binary not yet built)

---

### Phase 3: Agent Binary (Priority: P0)

**Duration**: 3-4 weeks

**Tasks:**

1. **Agent Core**
   - Python-based agent application
   - Configuration management
   - API client for coordinator
   - Main polling loop
   - Graceful shutdown

2. **Tool Execution**
   - PhotoStats integration
   - Photo Pairing integration
   - Pipeline Validation integration
   - Progress callback mechanism
   - HTML report generation

3. **Local Credential Store**
   - Encrypted credential file
   - Fernet encryption (matching server)
   - Credential CRUD commands
   - Connector capability reporting

4. **Packaging**
   - PyInstaller for binary
   - macOS: DMG installer
   - Windows: MSI installer
   - Linux: AppImage or deb/rpm

5. **Testing**
   - Unit tests for agent components
   - Integration tests with mock server
   - End-to-end tests

**Checkpoint**: Functional agent binary for all platforms

---

### Phase 4: Agent Management UI (Priority: P1)

**Duration**: 2 weeks

**Tasks:**

1. **Settings > Agents Tab**
   - Agent list with status indicators
   - Registration token generation
   - Agent details view
   - Delete agent action

2. **Job Queue UI Enhancement**
   - Agent column in job list
   - Agent filter
   - Job reassignment UI
   - Retry failed job button

3. **Connector Enhancement**
   - Credential location selector
   - Agent-local indicator
   - Which agents have credentials

4. **Testing**
   - Frontend component tests
   - E2E tests for agent management

**Checkpoint**: Full agent management from web UI

---

### Phase 5: Local Collections (Priority: P1)

**Duration**: 2 weeks

**Tasks:**

1. **Local Collection Type**
   - Collection type=LOCAL in backend
   - Path validation on agent
   - Agent requirement enforcement
   - Frontend collection form update

2. **SMB via Agent**
   - SMB default to agent-local credentials
   - Agent SMB access testing
   - Documentation update

3. **E2E Testing**
   - Local collection workflow
   - SMB collection via agent
   - Multi-agent scenarios

**Checkpoint**: Local and SMB collections work via agents

---

### Phase 6: Polish and Documentation (Priority: P1)

**Duration**: 2 weeks

**Tasks:**

1. **Documentation**
   - Agent installation guide (per platform)
   - Agent configuration reference
   - Troubleshooting guide
   - Architecture documentation

2. **Security Hardening**
   - Penetration testing
   - Rate limiting tuning
   - Audit logging verification

3. **Performance Optimization**
   - Connection pooling
   - Batch heartbeat processing
   - Redis evaluation (if needed)

4. **CLAUDE.md Update**
   - Agent architecture section
   - New API endpoints
   - Configuration reference

**Checkpoint**: Production-ready agent system

---

## Risks and Mitigation

### Risk 1: Agent Adoption Friction

- **Impact**: High - Users may not install agents, limiting value
- **Probability**: Medium
- **Mitigation**: One-click installers, minimal configuration, clear documentation, server fallback for remote connectors

### Risk 2: Network Reliability

- **Impact**: Medium - Agents in unreliable networks may disconnect frequently
- **Probability**: Medium
- **Mitigation**: Automatic reconnection, exponential backoff, offline job queue, idempotent operations

### Risk 3: Job Queue Race Conditions

- **Impact**: High - Duplicate job execution wastes resources
- **Probability**: Low (with proper locking)
- **Mitigation**: Database-level locking (FOR UPDATE SKIP LOCKED), idempotent job completion, deduplication checks

### Risk 4: Agent Security Vulnerabilities

- **Impact**: Critical - Compromised agent could access sensitive data
- **Probability**: Low (with security review)
- **Mitigation**: API key rotation, capability-based access, audit logging, code signing, no auto-update without verification

### Risk 5: Cross-Platform Compatibility

- **Impact**: Medium - Agent may not work consistently across OS
- **Probability**: Medium
- **Mitigation**: Extensive platform testing, CI/CD for all platforms, user feedback loop, Python for portability

### Risk 6: Backward Compatibility

- **Impact**: High - Breaking existing installations
- **Probability**: Low (with careful migration)
- **Mitigation**: Server-side execution continues as fallback, gradual migration path, feature flags

---

## Open Questions

1. **Job Queue Backend**: PostgreSQL-only or Redis for scale? (Recommendation: Start PostgreSQL, add Redis if needed)

2. **Agent Auto-Update**: Should agents auto-update, or require manual update? (Security vs convenience)

3. **Concurrent Jobs per Agent**: V1 single job, V2 concurrent - what's the limit? (CPU cores, memory?)

4. **Agent Impersonation Prevention**: How to prevent fake agents from claiming jobs? (Registration token + API key sufficient?)

5. **Result Size Limits**: Maximum results JSON and HTML report size? (10MB? 50MB?)

6. **Offline Job Creation**: Should agents be able to create jobs while offline? (Complexity vs value)

7. **Agent Grouping**: Should agents be organizable into groups/pools? (Defer to v2?)

8. **Desktop App Protocol**: How will agents invoke Lightroom, DxO, etc.? (CLI, AppleScript, COM?)

---

## Testing Strategy

### Unit Tests

- AgentService: registration, heartbeat, offline detection
- JobCoordinatorService: capability matching, job claiming, completion
- Agent Core: polling, execution, reporting
- LocalCredentialStore: encryption, CRUD, validation

### Integration Tests

- Full registration flow (token → agent → API key)
- Job lifecycle (create → claim → execute → complete)
- Multi-agent job distribution
- Agent offline → job reassignment
- Agent-local credential access

### End-to-End Tests

- Install agent on fresh machine
- Register with server via UI-generated token
- Create local collection
- Run PhotoStats via agent
- View results in web UI

### Security Tests

- Unauthorized agent registration attempt
- Cross-team job access attempt
- API key brute force protection
- Credential exfiltration attempt

### Performance Tests

- 100 concurrent agents
- 1000 jobs/minute throughput
- Agent reconnection under load
- Job queue under high contention

---

## Future Enhancements (Post-v1)

### v2.0: Agent Auto-Update

- Secure update channel
- Rollback capability
- Version compatibility matrix
- Zero-downtime updates

### v2.1: Desktop Application Integration

- Adobe Lightroom Classic plugin
- DxO PureRAW CLI wrapper
- Capture One integration
- Photoshop scripting

### v2.2: Agent Clustering

- Agent-to-agent communication
- Local job distribution
- Shared file cache
- Leader election

### v2.3: Advanced Job Scheduling

- Scheduled jobs (cron-like)
- Job dependencies (DAG)
- Priority queues
- Resource reservations

### v2.4: Credential Vault Integration

- HashiCorp Vault support
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

---

## Dependencies

### External Dependencies

- **Python 3.10+**: Agent runtime
- **PyInstaller**: Binary packaging
- **PostgreSQL 12+**: Job persistence
- **Redis (optional)**: High-throughput queue

### Internal Dependencies

- **Team/User entities**: Multi-tenancy (from 012-user-tenancy.md)
- **Existing tool implementations**: PhotoStats, Photo Pairing, Pipeline Validation
- **Jinja2 templates**: HTML report generation
- **GuidMixin pattern**: Entity identification

---

## Appendix

### A. Agent Configuration File

```yaml
# ~/.photo-admin/config.yaml
server:
  url: https://photo-admin.example.com
  verify_ssl: true

agent:
  name: "Office Workstation"
  poll_interval: 5  # seconds
  heartbeat_interval: 30  # seconds

capabilities:
  # Auto-detected, can be overridden
  - local_filesystem
  - tool:photostats
  - tool:photo_pairing
  - tool:pipeline_validation

logging:
  level: INFO
  file: ~/.photo-admin/agent.log
```

### B. Agent CLI Commands

```bash
# Install and register
photo-admin-agent register \
  --server https://photo-admin.example.com \
  --token art_xxxxx... \
  --name "Office Workstation"

# Start agent (foreground)
photo-admin-agent start

# Start agent (background service)
photo-admin-agent start --daemon

# Stop agent
photo-admin-agent stop

# Check status
photo-admin-agent status

# Configure local credentials
photo-admin-agent credentials add con_xxxxx \
  --aws-access-key-id AKIAIOSFODNN7EXAMPLE \
  --aws-secret-access-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# List local credentials
photo-admin-agent credentials list

# Remove local credentials
photo-admin-agent credentials remove con_xxxxx

# View logs
photo-admin-agent logs --tail 100
```

### C. API Key Format

```
agt_key_[32 random bytes base64url encoded]

Example: agt_key_xK9mN2pQrStUvWxYz01234567890ABCDEFghij
```

### D. Related Issues/PRDs

| Document | Relevance |
|----------|-----------|
| [012-user-tenancy.md](./012-user-tenancy.md) | Team-scoped agents, authentication |
| [007-remote-photos-completion.md](./007-remote-photos-completion.md) | Current job execution, result storage |
| [004-remote-photos-persistence.md](./004-remote-photos-persistence.md) | Connector architecture, tool integration |
| [Domain Model](../domain-model.md) | Agent entity specification |

---

## Revision History

- **2026-01-14 (v1.3)**: Added scheduled job execution for automatic collection refresh
  - **Scheduled Jobs**: Jobs can specify `scheduled_for` datetime for deferred execution
    - SCHEDULED status for jobs waiting for their time
    - Agents claim SCHEDULED jobs directly when `scheduled_for <= NOW()`
    - No background task needed—leverages existing agent polling
  - **Auto-Refresh**: Collections can configure automatic refresh scheduling
    - `auto_refresh` flag and `refresh_interval_hours` (TTL) settings
    - Job completion atomically creates next SCHEDULED job
    - Manual refresh cancels scheduled job and runs immediately
  - **Job Chaining**: `parent_job_id` links refresh jobs for history visibility
  - **Simplicity**: Inline claim query approach eliminates need for cron or background scheduler
  - Added Collection model enhancements (auto_refresh, refresh_interval_hours, etc.)
  - Added functional requirements (FR-460)

- **2026-01-14 (v1.2)**: Added WebSocket-based real-time progress streaming
  - **Hybrid Communication Protocol**: REST for control plane, WebSocket for data plane
    - Agent establishes WebSocket connection when claiming a job
    - Real-time progress streaming during job execution
    - Server proxies agent updates to frontend WebSocket channels
    - Maintains existing real-time UX for users
  - **WebSocket Message Protocol**: Defined message types and formats
    - Progress updates with stage, percentage, files, current file
    - Cancellation requests from server to agent
    - Ping/pong keepalive mechanism
  - **Graceful Fallback**: REST progress updates if WebSocket unavailable
    - Automatic fallback after 3 WebSocket connection failures
    - Slightly degraded but functional progress reporting
  - Updated functional requirements (FR-500, FR-510)
  - Added WebSocket performance requirements (NFR-100.6-8, NFR-200.6-8)

- **2026-01-14 (v1.1)**: Refined routing model and credential modes
  - **Local Collections**: Changed from capability-based to explicit agent binding
    - Local collections now require agent selection at creation time
    - Same path on different agents represents different collections
    - Jobs route ONLY to bound agent (not any capable agent)
  - **Connector Credential Modes**: Expanded from 2 to 3 modes
    - Added `PENDING` mode for tentative activation without credentials
    - Agent CLI workflow for discovering and configuring pending connectors
    - Agent tests connection before reporting capability to server
  - **Tool Capability Reporting**: Clarified capability detection model
    - Bundled tools auto-detected (all agents have same tools in v1)
    - Foundation for future external tool detection (Lightroom, DxO, etc.)
  - Added Collection model enhancements (bound_agent_id)
  - Updated Job routing logic to prioritize bound agents

- **2026-01-14 (v1.0)**: Initial draft
  - Defined core Agent architecture and concepts
  - Specified agent registration and lifecycle
  - Designed distributed job queue with capability routing
  - Detailed credential locality security model
  - Outlined communication protocol (REST API)
  - Created 6-phase implementation plan
  - Identified risks and mitigation strategies
