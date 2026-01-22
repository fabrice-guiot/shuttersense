# Data Model: Distributed Agent Architecture

**Feature**: 021-distributed-agent-architecture
**Created**: 2026-01-18

---

## Entity Overview

| Entity | GUID Prefix | Storage | Description |
|--------|-------------|---------|-------------|
| Agent | `agt_` | Database | Worker process on user hardware |
| AgentRegistrationToken | `art_` | Database | One-time registration token |
| Job | `job_` | Database | Enhanced with agent routing fields |
| Connector | `con_` | Database | Enhanced with credential_location |
| Collection | `col_` | Database | Enhanced with agent binding |
| User | `usr_` | Database | Enhanced: SYSTEM user for agents |

---

## Entity: Agent

A worker process running on user-owned hardware that executes jobs.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `system_user_id` | Integer | FK(users.id), not null | Dedicated SYSTEM user for audit |
| `created_by_user_id` | Integer | FK(users.id), not null | Human who registered agent |
| `name` | String(255) | not null | User-friendly agent name |
| `hostname` | String(255) | nullable | Machine hostname (auto-detected) |
| `os_info` | String(255) | nullable | OS type/version |
| `status` | Enum | not null, default='OFFLINE' | Agent status |
| `error_message` | Text | nullable | Last error if status=ERROR |
| `last_heartbeat` | DateTime | nullable | Last successful heartbeat |
| `capabilities_json` | JSONB | not null, default='[]' | Declared capabilities |
| `connectors_json` | JSONB | not null, default='[]' | Connector GUIDs with local credentials |
| `api_key_hash` | String(255) | not null, unique | SHA-256 hash of API key |
| `api_key_prefix` | String(10) | not null | First 8 chars for identification |
| `version` | String(50) | nullable | Agent software version |
| `binary_checksum` | String(64) | nullable | SHA-256 of agent binary (attestation) |
| `revocation_reason` | Text | nullable | Reason if status=REVOKED |
| `revoked_at` | DateTime | nullable | Timestamp of revocation |
| `created_at` | DateTime | not null, auto-now | Registration timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification |

### Status Enum

```python
class AgentStatus(str, Enum):
    ONLINE = "online"      # Heartbeat within 90 seconds
    OFFLINE = "offline"    # No heartbeat for 90+ seconds
    ERROR = "error"        # Agent reported error state
    REVOKED = "revoked"    # Agent revoked by admin
```

### Capability Format

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

### Indexes

- `ix_agents_team_id` on `team_id`
- `ix_agents_status` on `status`
- `uq_agents_api_key_hash` on `api_key_hash` (unique)

### Relationships

- `team`: ManyToOne → Team
- `system_user`: OneToOne → User (is_system=true)
- `created_by`: ManyToOne → User
- `bound_collections`: OneToMany → Collection
- `assigned_jobs`: OneToMany → Job

### Validation Rules

1. `name` must be 1-255 characters
2. `api_key_hash` must be valid SHA-256 (64 hex chars)
3. `status` must be valid enum value
4. `capabilities_json` must be valid JSON array
5. When `status=REVOKED`, `revocation_reason` required
6. Cannot delete agent with bound collections

---

## Entity: AgentRegistrationToken

One-time token for agent registration.

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `team_id` | Integer | FK(teams.id), not null | Team this token registers for |
| `created_by_user_id` | Integer | FK(users.id), not null | User who created token |
| `token_hash` | String(255) | unique, not null | SHA-256 hash of token |
| `name` | String(100) | nullable | Optional description |
| `is_used` | Boolean | not null, default=false | Whether token has been used |
| `used_by_agent_id` | Integer | FK(agents.id), nullable | Agent that used this token |
| `expires_at` | DateTime | not null | Token expiration (24h default) |
| `created_at` | DateTime | not null, auto-now | Creation timestamp |

### Indexes

- `uq_art_token_hash` on `token_hash` (unique)
- `ix_art_team_expires` on `(team_id, expires_at, is_used)`

### Relationships

- `team`: ManyToOne → Team
- `created_by`: ManyToOne → User
- `used_by_agent`: OneToOne → Agent (nullable)

### Validation Rules

1. Token can only be used once (`is_used=false` required for registration)
2. Token must not be expired (`expires_at > NOW()`)
3. Token expiration default: 24 hours from creation

---

## Entity: Job (Enhanced)

Unit of work for tool execution. Enhanced with agent routing and scheduling fields.

### New/Modified Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `bound_agent_id` | Integer | FK(agents.id), nullable | Required agent for LOCAL collections |
| `required_capabilities_json` | JSONB | not null, default='[]' | Capabilities needed (for unbound jobs) |
| `agent_id` | Integer | FK(agents.id), nullable | Currently assigned/executing agent |
| `assigned_at` | DateTime | nullable | When job was assigned |
| `started_at` | DateTime | nullable | When execution began |
| `progress_json` | JSONB | nullable | Current progress data |
| `scheduled_for` | DateTime | nullable | Earliest execution time (NULL=immediate) |
| `parent_job_id` | Integer | FK(jobs.id), nullable | Previous job in refresh chain |
| `signing_secret_hash` | String(64) | nullable | For HMAC result verification |

### Status Enum (Enhanced)

```python
class JobStatus(str, Enum):
    SCHEDULED = "scheduled"  # Waiting for scheduled_for time
    PENDING = "pending"      # Immediate job, ready to claim
    ASSIGNED = "assigned"    # Claimed by agent, not yet started
    RUNNING = "running"      # Agent actively executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Execution failed (may retry)
    CANCELLED = "cancelled"  # Cancelled by user or system
```

### Indexes

- `ix_jobs_claimable` on `(team_id, status, scheduled_for)` WHERE status IN ('PENDING', 'SCHEDULED')
- `uq_jobs_scheduled_per_collection` partial unique on `(collection_id, tool)` WHERE status='SCHEDULED'

### State Machine

```
SCHEDULED ──(scheduled_for <= NOW)──> ASSIGNED
    │                                    │
    │ (cancelled)                        │ (agent offline)
    ▼                                    ▼
CANCELLED                            PENDING
                                        │
                                        ▼
                                    ASSIGNED
                                        │
                                        │ (execution starts)
                                        ▼
                                     RUNNING
                                        │
                               ┌────────┴────────┐
                               │                 │
                               ▼                 ▼
                            FAILED ─(retry)─> PENDING
                               │
                               ▼
                           COMPLETED ─(auto-refresh)─> SCHEDULED
```

### Progress JSON Format

```json
{
  "stage": "scanning",
  "percentage": 45,
  "files_scanned": 1234,
  "total_files": 2741,
  "current_file": "IMG_1234.jpg",
  "message": "Scanning files..."
}
```

---

## Entity: Connector (Enhanced)

New field for credential storage location.

### New Field

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `credential_location` | Enum | not null, default='SERVER' | Where credentials are stored |

### Credential Location Enum

```python
class CredentialLocation(str, Enum):
    SERVER = "server"    # Encrypted on server (current behavior)
    AGENT = "agent"      # Only on agent(s), NOT on server
    PENDING = "pending"  # No credentials yet, awaiting config
```

### Semantic Differences

| Mode | Server Has Creds | Agent Has Creds | Can Execute |
|------|-----------------|-----------------|-------------|
| SERVER | Yes (encrypted) | Optional | Any capable agent |
| AGENT | No | Required | Only agents with local creds |
| PENDING | No | No | Cannot execute yet |

### Migration

- Existing connectors default to `SERVER`
- No data migration needed (column addition with default)

---

## Entity: Collection (Enhanced)

New fields for agent binding and auto-refresh.

### New Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `bound_agent_id` | Integer | FK(agents.id), nullable | Agent for LOCAL collections |
| `auto_refresh` | Boolean | not null, default=true | Enable auto-refresh scheduling |
| `refresh_interval_hours` | Integer | nullable | Hours between refreshes (TTL) |
| `last_refresh_at` | DateTime | nullable | Last completed refresh |
| `next_refresh_at` | DateTime | nullable | Computed: next scheduled time |

### Binding Rules

| Collection Type | bound_agent_id | Job Routing |
|-----------------|----------------|-------------|
| LOCAL | Required (not null) | Only bound agent |
| S3 | NULL | Any capable agent |
| GCS | NULL | Any capable agent |
| SMB | NULL (usually) | Any capable agent |

### Validation Rules

1. If `type=LOCAL`, `bound_agent_id` is required
2. If `auto_refresh=true` and `refresh_interval_hours` is set, scheduling is enabled
3. `refresh_interval_hours` must be >= 1 if set
4. Cannot delete bound agent if collections exist

---

## Entity: User (Enhanced for Agents)

Agents create dedicated SYSTEM users for audit trail.

### SYSTEM User for Agents

When an agent is registered:
1. Create new User with `is_system=true`
2. Set `full_name = "Agent: {agent_name}"`
3. Store `user.id` as `agent.system_user_id`

### Audit Trail

| Action | created_by / updated_by |
|--------|------------------------|
| Agent creates AnalysisResult | Agent's SYSTEM user |
| Agent updates Job progress | Agent's SYSTEM user |
| Human registers Agent | Human user (agent.created_by_user_id) |
| Agent renamed | Agent's SYSTEM user full_name updated |

### Lifecycle

- Agent deletion: SYSTEM user NOT deleted (preserves audit history)
- Agent rename: SYSTEM user `full_name` updated to match

---

## Relationships Diagram

```
┌─────────────┐      ┌─────────────────────────┐      ┌──────────────┐
│    Team     │      │         Agent           │      │     User     │
├─────────────┤      ├─────────────────────────┤      ├──────────────┤
│ id          │◄────▶│ team_id                 │      │ id           │
│ ...         │      │ system_user_id          │─────▶│ is_system    │
└─────────────┘      │ created_by_user_id      │─────▶│ full_name    │
       ▲             │ ...                     │      │ ...          │
       │             └────────────┬────────────┘      └──────────────┘
       │                          │
       │                          │ bound_agent_id
       │                          ▼
       │             ┌─────────────────────────┐
       │             │       Collection        │
       └─────────────│ team_id                 │
                     │ bound_agent_id          │
                     │ auto_refresh            │
                     │ ...                     │
                     └────────────┬────────────┘
                                  │
                                  │ collection_id
                                  ▼
                     ┌─────────────────────────┐
                     │          Job            │
                     ├─────────────────────────┤
                     │ team_id                 │
                     │ collection_id           │
                     │ bound_agent_id          │──┐
                     │ agent_id                │──┼──▶ Agent
                     │ required_capabilities   │  │
                     │ scheduled_for           │  │
                     │ parent_job_id           │──┘ (self-ref)
                     │ ...                     │
                     └─────────────────────────┘

┌─────────────────────────┐      ┌─────────────────────────┐
│ AgentRegistrationToken  │      │       Connector         │
├─────────────────────────┤      ├─────────────────────────┤
│ team_id                 │      │ credential_location     │
│ created_by_user_id      │      │ ...                     │
│ used_by_agent_id        │─────▶│                         │
│ ...                     │      └─────────────────────────┘
└─────────────────────────┘
```

---

## Database Migrations

### Migration 1: Create Agent Tables

```sql
-- agents table
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    external_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    system_user_id INTEGER NOT NULL REFERENCES users(id),
    created_by_user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    hostname VARCHAR(255),
    os_info VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'offline',
    error_message TEXT,
    last_heartbeat TIMESTAMP,
    capabilities_json JSONB NOT NULL DEFAULT '[]',
    connectors_json JSONB NOT NULL DEFAULT '[]',
    api_key_hash VARCHAR(255) NOT NULL UNIQUE,
    api_key_prefix VARCHAR(10) NOT NULL,
    version VARCHAR(50),
    binary_checksum VARCHAR(64),
    revocation_reason TEXT,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_agents_team_id ON agents(team_id);
CREATE INDEX ix_agents_status ON agents(status);

-- agent_registration_tokens table
CREATE TABLE agent_registration_tokens (
    id SERIAL PRIMARY KEY,
    external_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    created_by_user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100),
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    used_by_agent_id INTEGER REFERENCES agents(id),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_art_team_expires ON agent_registration_tokens(team_id, expires_at, is_used);
```

### Migration 2: Enhance Jobs Table

```sql
ALTER TABLE jobs
    ADD COLUMN bound_agent_id INTEGER REFERENCES agents(id),
    ADD COLUMN required_capabilities_json JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN agent_id INTEGER REFERENCES agents(id),
    ADD COLUMN assigned_at TIMESTAMP,
    ADD COLUMN started_at TIMESTAMP,
    ADD COLUMN progress_json JSONB,
    ADD COLUMN scheduled_for TIMESTAMP,
    ADD COLUMN parent_job_id INTEGER REFERENCES jobs(id),
    ADD COLUMN signing_secret_hash VARCHAR(64);

-- Add SCHEDULED status to enum (if using enum type)
-- Or update check constraint if using VARCHAR

-- Partial unique index for scheduled jobs
CREATE UNIQUE INDEX uq_jobs_scheduled_per_collection
    ON jobs(collection_id, tool)
    WHERE status = 'scheduled';

-- Index for claimable jobs
CREATE INDEX ix_jobs_claimable
    ON jobs(team_id, status, scheduled_for)
    WHERE status IN ('pending', 'scheduled');
```

### Migration 3: Enhance Connectors Table

```sql
ALTER TABLE connectors
    ADD COLUMN credential_location VARCHAR(20) NOT NULL DEFAULT 'server';

-- Default existing connectors to 'server'
UPDATE connectors SET credential_location = 'server' WHERE credential_location IS NULL;
```

### Migration 4: Enhance Collections Table

```sql
ALTER TABLE collections
    ADD COLUMN bound_agent_id INTEGER REFERENCES agents(id),
    ADD COLUMN auto_refresh BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN refresh_interval_hours INTEGER,
    ADD COLUMN last_refresh_at TIMESTAMP,
    ADD COLUMN next_refresh_at TIMESTAMP;

-- Add constraint: LOCAL collections require bound_agent_id
-- (Enforced in application layer, not database constraint)
```

---

## Query Patterns

### Claim Job Query

```sql
-- Find next claimable job for an agent
SELECT * FROM jobs
WHERE (
    status = 'pending'
    OR (status = 'scheduled' AND scheduled_for <= NOW())
)
AND team_id = :team_id
AND (
    bound_agent_id = :agent_id  -- Bound jobs first
    OR (
        bound_agent_id IS NULL
        AND required_capabilities_json <@ :agent_capabilities
    )
)
ORDER BY
    CASE WHEN bound_agent_id = :agent_id THEN 0 ELSE 1 END,  -- Bound first
    priority DESC,
    created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

### Agent Pool Status Query

```sql
-- Get agent pool status for header badge
SELECT
    COUNT(*) FILTER (WHERE status = 'online') AS online_count,
    COUNT(*) FILTER (WHERE status = 'online' AND
        NOT EXISTS (SELECT 1 FROM jobs WHERE jobs.agent_id = agents.id AND jobs.status = 'running')
    ) AS idle_count,
    (SELECT COUNT(*) FROM jobs WHERE status = 'running') AS running_jobs_count
FROM agents
WHERE team_id = :team_id;
```

### Auto-Schedule Next Job

```sql
-- Create scheduled job after completion (in transaction)
INSERT INTO jobs (
    team_id, collection_id, tool, status, scheduled_for, parent_job_id,
    required_capabilities_json, bound_agent_id
)
SELECT
    :team_id, :collection_id, :tool, 'scheduled',
    :completed_at + (refresh_interval_hours * INTERVAL '1 hour'),
    :completed_job_id, :required_capabilities, :bound_agent_id
FROM collections
WHERE id = :collection_id
  AND auto_refresh = TRUE
  AND refresh_interval_hours IS NOT NULL;
```
