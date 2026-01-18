# Feature Specification: Distributed Agent Architecture

**Feature Branch**: `021-distributed-agent-architecture`
**Created**: 2026-01-18
**Status**: Draft
**Input**: GitHub Issue #90 - Implement Agent Mode for distributed job execution
**Related PRD**: `docs/prd/021-distributed-agent-architecture.md`

---

## Executive Summary

This feature enables distributed job execution on user-owned hardware instead of centralized cloud infrastructure. Agents are lightweight worker processes that connect to the central server, receive job assignments, execute analysis tools locally, and report results back. This architecture addresses three critical objectives:

1. **Cost Reduction**: Offload compute-intensive operations to user-owned devices
2. **Security/Trust**: Keep sensitive credentials on user-controlled infrastructure
3. **Resource Access**: Enable access to local filesystems, SMB shares, and desktop applications

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Registration and Setup (Priority: P0)

**As** a team administrator, **I want to** register an agent running on my local machine, **so that** jobs can be executed on my own hardware instead of the central server.

**Why this priority**: This is the foundational capability that enables all other agent functionality. Without agent registration, no distributed job execution is possible.

**Independent Test**: Can be fully tested by downloading agent binary, configuring with server URL and registration token, and verifying agent appears in the agent list UI. Delivers the core ability to connect user hardware to the platform.

**Acceptance Scenarios**:

1. **Given** I have access to the Settings page, **When** I click "Generate Registration Token", **Then** a one-time registration token is created and displayed (expires in 24 hours)

2. **Given** I have downloaded the agent binary and have a valid registration token, **When** I run `shuttersense-agent register --server <url> --token <token> --name "My Workstation"`, **Then** the agent registers with the server and receives an API key (shown once)

3. **Given** I have a registered agent running, **When** I view the Agents list in Settings, **Then** I see the agent with its name, hostname, status (online/offline), capabilities, and last heartbeat timestamp

4. **Given** I have a running agent, **When** the agent sends heartbeats every 30 seconds, **Then** the server updates the agent's last_heartbeat and status

5. **Given** an agent has not sent a heartbeat for 90 seconds, **When** the server checks agent status, **Then** the agent is marked as OFFLINE

6. **Given** I have a registered agent in the UI, **When** I click "Delete Agent", **Then** the agent is removed and its API key is revoked

---

### User Story 2 - Local Collection with Agent Binding (Priority: P0)

**As** a photographer, **I want to** analyze my local photo collection via an agent, **so that** I don't need to upload files to the cloud.

**Why this priority**: Local filesystem access is a critical capability that cannot be achieved through server-side execution. This enables photographers to analyze their existing local photo libraries.

**Independent Test**: Can be fully tested by creating a LOCAL collection bound to an agent, running a tool (PhotoStats), and verifying results appear in the web UI. Delivers the core value of analyzing local files without cloud upload.

**Acceptance Scenarios**:

1. **Given** I am creating a new collection, **When** I select type "LOCAL" and enter a local path, **Then** I am required to select an online agent with `local_filesystem` capability

2. **Given** I have created a LOCAL collection bound to Agent A, **When** a PhotoStats job is created for this collection, **Then** the job is routed ONLY to Agent A (not any other capable agent)

3. **Given** Agent A is bound to a LOCAL collection but is offline, **When** a job is created for this collection, **Then** the job queues and waits until Agent A comes online

4. **Given** I view a LOCAL collection in the UI, **When** I look at the collection details, **Then** I can see which agent it is bound to

5. **Given** Agent A has bound collections, **When** I try to delete Agent A, **Then** deletion is blocked with a message explaining bound collections must be migrated or deleted first

6. **Given** the same path `/home/user/Photos` exists on Agent A and Agent B, **When** I create LOCAL collections for each, **Then** two separate collections are created with different content

---

### User Story 3 - Job Distribution and Execution (Priority: P0)

**As** a team user, **I want** jobs to be automatically distributed to capable agents, **so that** analysis runs on the most appropriate hardware without manual intervention.

**Why this priority**: Automatic job distribution is core to the agent architecture. Without this, users would need to manually manage which jobs run where.

**Independent Test**: Can be fully tested by having an online agent, creating a job, and verifying the agent claims and executes the job with results appearing in the web UI.

**Acceptance Scenarios**:

1. **Given** Agent A is online with capability `tool:photostats`, **When** a PhotoStats job is created, **Then** Agent A can claim the job via polling

2. **Given** a job is assigned to an agent, **When** the agent begins execution, **Then** job status changes from ASSIGNED to RUNNING

3. **Given** a job is running on an agent, **When** the agent streams progress updates via WebSocket, **Then** the frontend receives real-time progress (percentage, files scanned, current file)

4. **Given** a job completes successfully, **When** the agent reports completion, **Then** job status changes to COMPLETED and results are stored

5. **Given** a job fails, **When** the agent reports failure with error message, **Then** job status changes to FAILED and error is recorded

6. **Given** a job fails with retry_count < max_retries, **When** the job is released, **Then** it returns to PENDING status for retry

7. **Given** an agent goes offline while executing a job, **When** 90 seconds pass without heartbeat, **Then** the job is released back to PENDING for reassignment

---

### User Story 4 - Connector Credential Modes (Priority: P1)

**As** a team administrator, **I want to** choose where connector credentials are stored (server vs agent), **so that** I can balance convenience with security requirements.

**Why this priority**: Credential security is critical for enterprise adoption. Some organizations require credentials never leave their infrastructure.

**Independent Test**: Can be fully tested by creating connectors with different credential locations and verifying jobs route appropriately based on credential availability.

**Acceptance Scenarios**:

1. **Given** I am creating a new S3 connector, **When** I choose `credential_location=SERVER` and provide credentials, **Then** credentials are encrypted and stored on the server

2. **Given** I am creating a new S3 connector, **When** I choose `credential_location=AGENT`, **Then** the connector is created without credentials on the server, marked as requiring agent configuration

3. **Given** I am creating a new S3 connector, **When** I choose `credential_location=PENDING`, **Then** the connector is created without any credentials, awaiting agent configuration

4. **Given** a connector has `credential_location=AGENT`, **When** I view the connector in the UI, **Then** I see which agents have configured credentials for it

5. **Given** a connector has `credential_location=AGENT`, **When** a job requires this connector, **Then** only agents with local credentials for this connector can claim the job

6. **Given** a connector has `credential_location=SERVER`, **When** no capable agents are online, **Then** the server can execute the job directly (for remote connectors)

---

### User Story 5 - Agent Credential Configuration via CLI (Priority: P1)

**As** an agent operator, **I want to** configure connector credentials locally via CLI, **so that** credentials never leave my machine.

**Why this priority**: This enables the security-conscious credential workflow where sensitive credentials remain on user-controlled infrastructure.

**Independent Test**: Can be fully tested by running CLI commands to list pending connectors, configure credentials, and verify the agent reports the new capability to the server.

**Acceptance Scenarios**:

1. **Given** I have a running agent, **When** I run `shuttersense-agent connectors list --pending`, **Then** I see all connectors awaiting credentials on this agent

2. **Given** a connector of type S3 is pending, **When** I run `shuttersense-agent connectors configure <connector_guid>`, **Then** I am prompted for AWS Access Key ID, Secret Access Key, and Region

3. **Given** I have entered connector credentials, **When** the agent tests the connection, **Then** it reports success or failure with details

4. **Given** connection test succeeds, **When** credentials are stored, **Then** they are encrypted locally and the agent reports the connector capability to the server

5. **Given** connection test fails, **When** I see the error, **Then** credentials are NOT stored and I can retry

6. **Given** I run `shuttersense-agent capabilities`, **Then** I see all current capabilities including configured connectors

---

### User Story 6 - SMB/Network Share via Agent (Priority: P1)

**As** a photographer with NAS storage, **I want to** analyze photos on my local SMB share via an agent, **so that** I don't need to copy files to cloud storage.

**Why this priority**: Many photographers use NAS devices for local storage. Agent-based SMB access enables analysis without network transfer to the cloud.

**Independent Test**: Can be fully tested by configuring SMB credentials on an agent, creating a collection pointing to the SMB share, and running analysis.

**Acceptance Scenarios**:

1. **Given** I create an SMB connector with `credential_location=AGENT`, **When** I configure credentials on an agent on the same network, **Then** the agent can access the SMB share

2. **Given** an agent has SMB credentials configured, **When** I run a PhotoStats job on an SMB collection, **Then** the agent executes with low-latency local network access

3. **Given** an SMB share is only accessible from certain networks, **When** I configure the connector as agent-only, **Then** only agents on the correct network with credentials can execute jobs

---

### User Story 7 - Job Queue Visibility and Management (Priority: P1)

**As** a team administrator, **I want to** see all queued and running jobs across agents, **so that** I can monitor workload and troubleshoot issues.

**Why this priority**: Visibility into job state is essential for operational management and troubleshooting.

**Independent Test**: Can be fully tested by creating multiple jobs, viewing the job queue UI, and performing management actions (cancel, retry).

**Acceptance Scenarios**:

1. **Given** I am on the Jobs page, **When** I view the job list, **Then** I see all jobs with status (PENDING, SCHEDULED, ASSIGNED, RUNNING, COMPLETED, FAILED, CANCELLED)

2. **Given** a job is running, **When** I view job details, **Then** I see which agent is executing it

3. **Given** a job is PENDING, **When** I click "Cancel", **Then** the job status changes to CANCELLED

4. **Given** a job has FAILED, **When** I click "Retry", **Then** a new job is created in PENDING status

5. **Given** I am viewing the job list, **When** I apply filters (collection, tool, agent, status), **Then** the list is filtered accordingly

---

### User Story 8 - Agent Health Monitoring (Priority: P2)

**As** a team administrator, **I want to** monitor agent health and resource usage, **so that** I can identify performance bottlenecks.

**Why this priority**: Monitoring enables proactive management but is not required for core functionality.

**Independent Test**: Can be fully tested by viewing the agent dashboard and verifying real-time status updates.

**Acceptance Scenarios**:

1. **Given** I am viewing the Agents list, **When** an agent's status changes (online/offline/error), **Then** the UI updates in real-time

2. **Given** I view an agent's details, **When** the agent is executing a job, **Then** I see the current job information

3. **Given** I view an agent's details, **When** I look at history, **Then** I see recent job history for that agent

4. **Given** an agent goes offline, **When** I am on the dashboard, **Then** I receive a notification

---

### User Story 9 - Multi-Agent Job Distribution (Priority: P2)

**As** a studio owner with multiple workstations, **I want to** run agents on multiple machines, **so that** jobs are distributed across available compute.

**Why this priority**: Load distribution improves throughput but single-agent scenarios work first.

**Independent Test**: Can be fully tested by registering multiple agents, creating multiple jobs, and verifying distribution.

**Acceptance Scenarios**:

1. **Given** I have registered 3 agents for my team, **When** I view the Agents list, **Then** I see all 3 agents with their individual statuses

2. **Given** 3 agents are online with the same capabilities, **When** multiple jobs are created, **Then** jobs are distributed across agents (one job per agent at a time in v1)

3. **Given** multiple agents can execute a job, **When** an agent claims it, **Then** the agent with fewest recent jobs is preferred (simple load balancing)

---

### User Story 10 - Automatic Collection Refresh Scheduling (Priority: P2)

**As** a team administrator, **I want** collection analysis to automatically re-run based on a configurable TTL, **so that** KPIs stay fresh without manual intervention.

**Why this priority**: Automated refresh improves user experience but manual refresh works initially.

**Independent Test**: Can be fully tested by setting a collection TTL, waiting for initial job completion, and verifying the next job is automatically scheduled.

**Acceptance Scenarios**:

1. **Given** a collection has `auto_refresh=true` and `refresh_interval_hours=24`, **When** a job completes, **Then** the next job is automatically scheduled for 24 hours later

2. **Given** a scheduled job exists, **When** the `scheduled_for` time passes, **Then** agents can claim the job (no background task needed)

3. **Given** a scheduled job exists for tomorrow, **When** I manually trigger a refresh, **Then** the scheduled job is cancelled and an immediate job runs

4. **Given** I view scheduled jobs, **Then** I see them in a separate "Upcoming" section with countdown to execution

5. **Given** I delete a collection, **When** it has a scheduled job, **Then** the scheduled job is automatically cancelled

---

### Edge Cases

- **Agent goes offline mid-job**: Job is released back to PENDING after 90 seconds without heartbeat. If bound agent, job waits for that agent. If capability-based, any capable agent can claim.

- **Multiple agents claim same job**: Database locking (FOR UPDATE SKIP LOCKED) prevents race conditions. Only one agent gets the job.

- **Agent binary checksum mismatch**: Registration fails if binary doesn't match known release manifest. Prevents modified/malicious agents.

- **Large result upload fails**: Chunked upload protocol with retry and resumption. Upload sessions expire after 1 hour.

- **WebSocket connection fails**: Agent automatically falls back to REST-based progress updates (every 2-5 seconds).

- **Credentials exposed in logs**: Agent-local credentials never transmitted to server. Only capability is reported ("I can access connector X").

- **Collection deleted while job running**: Job continues but result storage fails gracefully. Job marked COMPLETED with warning.

- **Team A agent tries to access Team B job**: Rejected. All job queries are team-scoped. Cross-team access returns 404.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Agent Management (FR-100)

- **FR-100.1**: System MUST allow team administrators to generate registration tokens from Settings UI (team-scoped)
- **FR-100.2**: Registration tokens MUST expire after 24 hours or single use (whichever comes first)
- **FR-100.3**: Agent MUST receive an API key upon successful registration (shown once, stored as hash on server)
- **FR-100.4**: Agent MUST send heartbeat every 30 seconds to maintain online status
- **FR-100.5**: System MUST mark agent as OFFLINE after 90 seconds without heartbeat
- **FR-100.6**: UI MUST display agent list with status, capabilities, last heartbeat, and current job
- **FR-100.7**: System MUST allow deletion of agents (revokes API key, reassigns queued jobs)
- **FR-100.8**: Users MUST be able to rename agents from the UI

#### Job Distribution (FR-200)

- **FR-200.1**: Jobs MUST persist to database (not in-memory queue)
- **FR-200.2**: Jobs MUST include `required_capabilities_json` array for routing
- **FR-200.3**: Agent MUST claim jobs via polling (POST /jobs/claim)
- **FR-200.4**: Job MUST be assigned to first capable agent that claims it (database locking)
- **FR-200.5**: Server MAY execute job if no capable agent online (for server connectors only)
- **FR-200.6**: Job MUST be reassigned if agent goes offline mid-execution
- **FR-200.7**: Failed jobs MUST retry up to max_retries (default: 3)
- **FR-200.8**: Job history MUST be retained for 90 days (configurable)

#### Connector Credential Modes (FR-300)

- **FR-300.1**: Connector MUST have `credential_location` enum (`SERVER`, `AGENT`, `PENDING`)
- **FR-300.2**: `SERVER` mode: Credentials stored encrypted on server (current behavior)
- **FR-300.3**: `AGENT` mode: Credentials stored only on agent(s), NOT on server
- **FR-300.4**: `PENDING` mode: Connector created without credentials (awaiting agent configuration)
- **FR-300.5**: Agent CLI MUST list PENDING/AGENT connectors for credential configuration
- **FR-300.6**: Agent MUST test connection before storing credentials locally
- **FR-300.7**: Agent MUST report connector capability to server after successful connection test
- **FR-300.8**: Jobs requiring agent-only connectors MUST only route to capable agents
- **FR-300.9**: UI MUST indicate credential status: "Server", "Agent-only", "Pending"
- **FR-300.10**: UI MUST show which agents have credentials for each connector

#### Local Collection Support (FR-400)

- **FR-400.1**: Collection `type=LOCAL` MUST create local filesystem collection
- **FR-400.2**: Local collections MUST require explicit agent binding at creation
- **FR-400.3**: UI MUST enforce agent selection for LOCAL collection type
- **FR-400.4**: Jobs for LOCAL collections MUST route ONLY to bound agent (not capability-based)
- **FR-400.5**: Same path on different agents MUST create different collections
- **FR-400.6**: Local collection jobs MUST NOT execute on server
- **FR-400.7**: UI MUST clearly show bound agent for each local collection
- **FR-400.8**: Agent deletion MUST be blocked if bound collections exist
- **FR-400.9**: If bound agent is offline, jobs MUST queue until agent comes online

#### Tool Capability Reporting (FR-450)

- **FR-450.1**: All agents MUST report bundled tool capabilities automatically
- **FR-450.2**: Tool capabilities MUST include version information
- **FR-450.3**: Agent heartbeat MUST include current capabilities
- **FR-450.4**: Server MUST track which agents can execute which tools

#### Scheduled Job Execution (FR-460)

- **FR-460.1**: Jobs MUST support `scheduled_for` field (DateTime, nullable)
- **FR-460.2**: Jobs with future `scheduled_for` MUST have status `SCHEDULED`
- **FR-460.3**: Claim query MUST include SCHEDULED jobs where `scheduled_for <= NOW()`
- **FR-460.4**: SCHEDULED jobs MUST transition directly to ASSIGNED when claimed
- **FR-460.5**: System MUST enforce unique constraint: one SCHEDULED job per (collection, tool)
- **FR-460.6**: Job completion MUST auto-create next SCHEDULED job if TTL configured
- **FR-460.7**: Next scheduled time MUST equal completion time + collection TTL
- **FR-460.8**: Manual refresh MUST cancel existing SCHEDULED job and run immediately
- **FR-460.9**: Collection TTL change MUST update existing SCHEDULED job's time
- **FR-460.10**: Collection deletion MUST cascade to cancel SCHEDULED jobs

#### Real-Time Progress Streaming (FR-500)

- **FR-500.1**: Agent MUST establish WebSocket connection to stream progress in real-time
- **FR-500.2**: Progress updates MUST include: stage, percentage, files processed, current file, message
- **FR-500.3**: Server MUST proxy agent WebSocket to frontend WebSocket channels
- **FR-500.4**: Frontend MUST receive real-time updates same as server-executed jobs
- **FR-500.5**: Server MUST be able to send cancellation request to agent via WebSocket
- **FR-500.6**: Agent MUST respond to WebSocket ping/pong for connection health
- **FR-500.7**: System MUST fall back to REST progress updates if WebSocket unavailable
- **FR-500.8**: REST fallback MUST update every 2-5 seconds

#### Job Completion and Results (FR-510)

- **FR-510.1**: Agent MUST report completion via REST with results JSON and HTML report
- **FR-510.2**: Results MUST be stored in existing AnalysisResult table
- **FR-510.3**: Collection statistics MUST be updated on job completion
- **FR-510.4**: Job completion MUST trigger WebSocket notification to frontend
- **FR-510.5**: WebSocket connection MUST be closed after completion REST call

#### Agent Trust and Attestation (FR-520)

- **FR-520.1**: Agent MUST send binary checksum (self-hash) during registration
- **FR-520.2**: Server MUST maintain release manifest with checksums per version/platform
- **FR-520.3**: Registration MUST fail if binary checksum doesn't match known release
- **FR-520.4**: Agent MUST receive job-specific signing secret when claiming a job
- **FR-520.5**: Results MUST include HMAC signature computed with signing secret
- **FR-520.6**: Server MUST verify HMAC signature before accepting results
- **FR-520.7**: Agents MUST be revocable (status=REVOKED), preventing job claims
- **FR-520.8**: Revoked agent's in-progress jobs MUST be released back to queue

#### Result Ingestion Protocol (FR-530)

- **FR-530.1**: Results JSON < 1MB MUST be submitted inline with completion request
- **FR-530.2**: Results JSON >= 1MB MUST use chunked upload protocol
- **FR-530.3**: HTML reports MUST always use chunked upload (typically > 100KB)
- **FR-530.4**: Server MUST specify chunk size (default 5MB, max 10MB)
- **FR-530.5**: Chunks MUST be uploaded via PUT to `/uploads/{upload_id}/{chunk_index}`
- **FR-530.6**: Upload finalization MUST verify SHA-256 checksum
- **FR-530.7**: Upload sessions MUST expire after 1 hour of inactivity
- **FR-530.8**: Chunks MUST be idempotent (re-upload same chunk returns 409)
- **FR-530.9**: Results JSON MUST be validated against tool-specific JSON schema
- **FR-530.10**: HTML reports MUST be validated for structure and security (no external scripts)
- **FR-530.11**: Invalid results MUST be rejected with detailed error message
- **FR-530.12**: HTML report MUST contain generator meta tag identifying ShutterSense

#### API-Based Tool Configuration (FR-540)

- **FR-540.1**: ConfigLoader interface MUST abstract configuration source
- **FR-540.2**: YamlConfigLoader MUST implement interface for CLI usage
- **FR-540.3**: DatabaseConfigLoader MUST implement interface for server-side execution
- **FR-540.4**: ApiConfigLoader MUST implement interface for agent execution
- **FR-540.5**: `/api/config/photo-extensions` MUST return team photo extensions
- **FR-540.6**: `/api/config/camera-mappings` MUST return team camera mappings
- **FR-540.7**: `/api/config/processing-methods` MUST return team processing methods
- **FR-540.8**: `/api/pipelines/{guid}` MUST return complete pipeline definition
- **FR-540.9**: `/api/jobs/{guid}/config` MUST return all config needed for job execution
- **FR-540.10**: ApiConfigLoader MUST cache team settings (5-minute TTL)
- **FR-540.11**: Tools MUST accept ConfigLoader parameter instead of assuming config source
- **FR-540.12**: Implementation MUST be backward compatible with existing CLI and server usage

---

### Key Entities

- **Agent**: A worker process running on user-owned hardware that executes jobs. Key attributes: guid, name, hostname, status (ONLINE/OFFLINE/ERROR/REVOKED), capabilities (array of strings), last_heartbeat, team_id. GUID prefix: `agt_`

- **AgentRegistrationToken**: One-time token for agent registration. Key attributes: token_hash, team_id, created_by_user_id, is_used, expires_at. GUID prefix: `art_`

- **Job** (enhanced): Unit of work for tool execution. New attributes: bound_agent_id (for LOCAL collections), required_capabilities_json, agent_id (assigned agent), scheduled_for (for auto-refresh), parent_job_id (refresh chain), signing_secret_hash. GUID prefix: `job_`

- **Connector** (enhanced): New attribute `credential_location` enum (SERVER, AGENT, PENDING)

- **Collection** (enhanced): New attributes: bound_agent_id (for LOCAL type), auto_refresh, refresh_interval_hours

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can register an agent and have it appear online in the UI within 60 seconds of starting the agent
- **SC-002**: Local collection jobs execute on the bound agent with results appearing in the web UI within the expected tool execution time
- **SC-003**: Progress updates appear in real-time in the frontend during agent job execution (latency < 500ms)
- **SC-004**: System supports at least 100 concurrent agents per team without degradation
- **SC-005**: Job claim latency is under 200ms (excluding network round-trip)
- **SC-006**: Agent reconnects automatically after network failure within 30 seconds
- **SC-007**: Failed jobs are automatically reassigned within 2 minutes of agent going offline
- **SC-008**: 100% of agent-only connector credentials remain on agent hardware (never transmitted to server)
- **SC-009**: Users can complete agent registration and first job execution within 10 minutes following documentation
- **SC-010**: System handles 1000 jobs per hour throughput with persistent queue

---

## Assumptions

The following reasonable assumptions have been made based on the PRD and industry standards:

1. **Agent Distribution**: Agent binaries will be provided for macOS 12+, Windows 10+, and Ubuntu 20.04+ as stated in the PRD
2. **Database**: PostgreSQL will be used for job queue persistence initially (Redis optional for future scale)
3. **Encryption**: Agent local credentials will use Fernet encryption (same as server-side)
4. **Polling Interval**: Agent poll interval of 5 seconds, heartbeat every 30 seconds
5. **Retry Policy**: Default max_retries of 3 with exponential backoff
6. **Token Expiry**: Registration tokens expire in 24 hours
7. **Agent Single-Job**: V1 agents execute one job at a time (concurrent execution deferred to v2)
8. **Tool Bundling**: All three tools (PhotoStats, Photo Pairing, Pipeline Validation) are bundled with the agent
9. **Backward Compatibility**: Server-side execution continues for existing remote connectors without agents

---

## Non-Goals (Out of Scope for v1)

Based on the PRD, the following are explicitly out of scope:

1. **Agent Auto-Updates**: Manual agent installation/updates only (auto-update deferred to v2)
2. **Agent Clustering**: No agent-to-agent communication (all coordination via server)
3. **Offline Operation**: Agents cannot queue/execute jobs while disconnected from server
4. **Credential Vault Integration**: No HashiCorp Vault/AWS Secrets Manager integration
5. **Container Orchestration**: No Kubernetes/Docker Swarm integration (simple process model)
6. **Desktop Application Integration**: Foundation laid but Lightroom/DxO/Photoshop integration deferred
7. **Concurrent Jobs per Agent**: V1 is single-job; multiple concurrent jobs deferred to v2
