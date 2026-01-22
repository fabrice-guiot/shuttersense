# PRD: Remove CLI Tool Direct Usage

**Issue**: #93
**Status**: Draft
**Created**: 2026-01-22
**Last Updated**: 2026-01-22 (v1.2)
**Related Documents**:
- [021-distributed-agent-architecture.md](./021-distributed-agent-architecture.md) (Agent architecture)
- [Domain Model](../domain-model.md) (Entity definitions)

---

## Executive Summary

This PRD proposes consolidating all tool execution through the Agent interface, eliminating direct CLI tool invocation. Currently, ShutterSense provides two ways to run analysis tools: (1) direct CLI execution via standalone Python scripts, and (2) agent-based execution via the web application. This dual approach creates maintenance overhead, inconsistent user experiences, and prevents the full benefits of the distributed agent architecture.

### Current State

**Dual Execution Paths:**
- **CLI Tools**: `photo_stats.py`, `photo_pairing.py`, `pipeline_validation.py` run as standalone scripts
- **Agent Execution**: Jobs queued via web UI, claimed and executed by registered agents

**Pain Points:**
- CLI tools bypass tenant isolation, job tracking, and result persistence
- Configuration split between YAML files (CLI) and API parameters (agents)
- No way to test local collections before creating them on the server
- Users must manually manage CLI tool execution and HTML reports
- Duplicate code paths for the same analysis logic

### What This PRD Delivers

1. **Agent CLI Commands**: New agent subcommands for testing collections and running tools locally
2. **Collection Creation via Agent**: Agents can create Collections on the server after successful local validation
3. **Unified Tool Execution**: All analysis runs through the agent, ensuring consistent tracking and results
4. **CLI Tool Removal**: Complete removal of standalone CLI tools and updated project constitution for agent-only architecture

---

## Background

### Problem Statement

The ShutterSense architecture evolved from standalone CLI tools to a distributed agent system. However, the original CLI tools remain as a parallel execution path, creating several issues:

| Issue | Impact | Severity |
|-------|--------|----------|
| **No result persistence** | CLI results stored as local HTML files only | High |
| **No tenant isolation** | CLI tools have no concept of teams or users | High |
| **No job tracking** | Cannot monitor CLI tool execution status | Medium |
| **Configuration fragmentation** | YAML files vs API parameters | Medium |
| **No pre-validation** | Cannot test a collection path before creating it on server | Medium |
| **Maintenance burden** | Two code paths for same functionality | Medium |

### Strategic Context

With the distributed agent architecture (PRD-021) now implemented, agents are the canonical way to execute tools. The CLI tools served their purpose during early development but now create technical debt:

1. **Agent Architecture Benefits Lost**: CLI execution bypasses job queuing, progress tracking, result storage
2. **User Confusion**: Two ways to do the same thing with different capabilities
3. **Testing Gap**: No way to validate a local path works before creating a Collection

The solution is to enhance the agent CLI to support all workflows previously served by standalone tools, then remove the standalone tools entirely before production deployment.

### Current Architecture

**Standalone CLI Tools:**
```
User Terminal → python3 photo_stats.py /photos → Local HTML Report
```

**Agent-Based Execution:**
```
Web UI → Server (Job Queue) → Agent (Poll & Execute) → Server (Store Results)
```

**Proposed Agent-Only Architecture:**
```
Agent CLI → Test/Run Locally → (Optional) Create Collection on Server
     ↓
Agent Daemon → Poll Server → Execute Jobs → Report Results
```

---

## Goals

### Primary Goals

1. **Agent Test Command**: Enable testing a local path with analysis tools before creating a Collection
2. **Agent Collection Creation**: Allow agents to create Collections on the server from validated local paths
3. **Unified Execution**: Route all tool execution through agent infrastructure
4. **Graceful Deprecation**: Provide clear migration path from CLI tools to agent commands

### Secondary Goals

1. **Local-Only Mode**: Support running tools locally without server connection (offline mode)
2. **Bulk Collection Setup**: Test and create multiple Collections in one workflow
3. **Configuration Migration**: Convert YAML configs to API-compatible format
4. **Progress Visibility**: Show tool progress even in CLI mode

### Non-Goals (v1)

1. **GUI for Agent**: No desktop application; agent remains CLI-based
2. **Auto-Discovery**: No automatic detection of photo folders (manual path specification)
3. **Remote Collection Testing**: Focus on local collections; remote collections tested via existing connector test flow
4. **Backward Compatibility**: Pre-release product; no need to maintain CLI tool compatibility

---

## User Personas

### Primary: Power User Migrating from CLI (Alex)

- **Current Workflow**: Runs `python3 photo_stats.py /photos` directly
- **Pain Point**: Results not visible in web UI, no job history
- **Desired Outcome**: Same command-line workflow but with server integration
- **This PRD Delivers**: `shuttersense-agent test /photos --tool photostats`

### Secondary: New User Setting Up Collections (Morgan)

- **Current Workflow**: Creates Collection in web UI, hopes the path is valid
- **Pain Point**: Collection creation fails if path doesn't exist or has permission issues
- **Desired Outcome**: Validate path works before committing to Collection
- **This PRD Delivers**: Test path locally, then `shuttersense-agent collection create` on success

### Tertiary: Photographer with Intermittent Connectivity (Jordan)

- **Current Workflow**: Uses CLI tools when offline, then manually notes results
- **Pain Point**: Cannot upload results when back online
- **Desired Outcome**: Run analysis offline, sync results when connected
- **This PRD Delivers**: Local execution with deferred result upload

---

## User Stories

### User Story 1: Test Local Path Before Collection Creation (Priority: P0 - Critical)

**As** a user setting up a new local Collection
**I want to** test that a local path works with analysis tools
**So that** I can verify accessibility before creating the Collection on the server

**Acceptance Criteria:**
- New agent CLI command: `shuttersense-agent test <path> [--tool <tool>]`
- Command validates:
  - Path exists and is readable
  - Path is within agent's authorized roots (if configured)
  - Files are found and can be listed
  - Tool can execute successfully on the path
- On success: Displays summary (file count, analysis results)
- On failure: Clear error message explaining the issue
- Results optionally saved as local HTML report
- No server communication required for basic test

**Example Usage:**
```bash
# Test a path with all available tools
$ shuttersense-agent test /photos/2024

Testing path: /photos/2024
  Checking accessibility... OK (readable, 1,247 files found)
  Running photostats... OK (analysis complete)
  Running photo_pairing... OK (analysis complete)

Test Summary:
  Files: 1,247 (1,200 photos, 47 sidecars)
  Issues: 3 orphaned sidecars found
  Ready to create Collection: Yes

# Test with specific tool
$ shuttersense-agent test /photos/2024 --tool photostats --output report.html

# Test without tool execution (accessibility only)
$ shuttersense-agent test /photos/2024 --check-only
```

**Technical Notes:**
- Uses same analysis modules as job executor
- Does NOT create a job on the server
- Authorized roots check is advisory in test mode (warn, don't block)
- Test results cached locally for subsequent `collection create` command

---

### User Story 2: Create Collection from Tested Path (Priority: P0 - Critical)

**As** a user who has tested a local path
**I want to** create a Collection on the server from that path
**So that** I can run scheduled jobs and view results in the web UI

**Acceptance Criteria:**
- New agent CLI command: `shuttersense-agent collection create <path> [--name <name>]`
- Command validates path was previously tested (or runs test automatically)
- Prompts for Collection name if not provided (suggests based on folder name)
- Creates Collection on server via API with:
  - `type: LOCAL`
  - `location: <path>`
  - `bound_agent_id: <this agent>`
- Displays created Collection GUID and web UI link
- Option to skip test: `--skip-test` (for advanced users)
- Option to run initial analysis: `--analyze` (creates job after Collection creation)

**Example Usage:**
```bash
# Create Collection from tested path
$ shuttersense-agent collection create /photos/2024

Path /photos/2024 was tested 5 minutes ago.
Collection name [2024]: Vacation Photos 2024

Creating Collection...
  Collection created: col_01hgw2bbg...
  View in web UI: https://app.shuttersense.ai/collections/col_01hgw2bbg...

# Create and immediately run analysis
$ shuttersense-agent collection create /photos/2024 --name "Wedding 2024" --analyze

Creating Collection...
  Collection created: col_01hgw2bbg...
  Starting analysis job...
  Job created: job_01hgw2ccc...
```

**Technical Notes:**
- Uses existing `POST /api/collections` endpoint
- Agent authenticates with its API key
- Collection automatically bound to creating agent
- Test cache stored in `~/.shuttersense-agent/test-cache/`

---

### User Story 3: Run Tool Offline Against Cached Collections (Priority: P1)

**As** a user with intermittent connectivity
**I want to** run analysis tools locally without server connection
**So that** I can work offline and sync results when back online

**Acceptance Criteria:**
- Agent CLI command: `shuttersense-agent run <collection-guid> --tool <tool> [--offline]`
- Offline mode runs against **cached local Collections only** (not arbitrary paths)
- Collection cache maintained by `collections list` and `collections sync` commands
- In offline mode:
  - No server connection required
  - Agent uses cached Collection metadata (GUID, name, path, type)
  - Only LOCAL Collections can run offline (remote storage unreachable)
  - Results saved to local file (JSON + HTML report)
  - Option to upload results later: `shuttersense-agent sync`
- In online mode (default):
  - Creates job on server, executes locally, reports results
  - Equivalent to web UI "Run Tool" action
- Supports all three tools: `photostats`, `photo_pairing`, `pipeline_validation`

**Acceptance Criteria - Collection Cache:**
- Cache stores Collections bound to this agent (local or via connector credentials)
- Cache updated when: agent starts, `collections list` runs, `collections sync` called
- Cache includes: GUID, name, type, location, connector info (for remote), last sync time
- Cache stored in `~/.shuttersense-agent/collection-cache.json`

**Example Usage:**
```bash
# First, sync collection cache (requires server connection)
$ shuttersense-agent collections sync

Syncing collections from server...
  Found 5 collections bound to this agent
  - 3 local collections
  - 2 remote collections (S3)
Cache updated: ~/.shuttersense-agent/collection-cache.json

# Run online (default) - creates job on server
$ shuttersense-agent run col_01hgw2bbg... --tool photostats

# Run offline against cached local collection
$ shuttersense-agent run col_01hgw2bbg... --tool photostats --offline

Running photostats on "Vacation 2024" (/photos/2024)...
Analysis complete. Results saved to:
  JSON: ~/.shuttersense-agent/results/col_01hgw2bbg_2024-01-22_photostats.json
  HTML: ~/.shuttersense-agent/results/col_01hgw2bbg_2024-01-22_photostats.html

# Attempt offline on remote collection (rejected)
$ shuttersense-agent run col_01hgw2ccc... --tool photostats --offline

Error: Cannot run offline on remote collection "S3 Archive"
  Collection type: S3 (requires network connectivity)
  Use online mode: shuttersense-agent run col_01hgw2ccc... --tool photostats

# Sync offline results to server later
$ shuttersense-agent sync

Found 3 pending results:
  - col_01hgw2bbg_2024-01-22_photostats.json (1.2 MB) → "Vacation 2024"
  - col_01hgw2bbg_2024-01-21_photo_pairing.json (0.8 MB) → "Vacation 2024"
  - col_01hgw2aaa_2024-01-20_photostats.json (1.1 MB) → "Wedding 2024"

Uploading... Done.
```

**Technical Notes:**
- Offline execution requires Collection to exist in cache (use US1 `test` for new paths)
- Results stored with Collection GUID for unambiguous matching during sync
- Remote Collections (S3, GCS, SMB) cannot run offline - network required
- Cache expiration: 7 days (warning shown, re-sync recommended)
- Results include timestamp, tool version, agent ID, Collection GUID for audit

---

### User Story 4: List and Manage Bound Collections (Priority: P1)

**As** an agent operator
**I want to** see which Collections are bound to my agent
**So that** I can manage local storage, run offline analysis, and troubleshoot issues

**Acceptance Criteria:**
- Agent CLI command: `shuttersense-agent collections list`
- Shows all Collections bound to this agent:
  - LOCAL Collections bound directly to this agent
  - REMOTE Collections where agent has connector credentials
- Displays: Collection GUID, name, type, path/location, status, last analysis date
- Filter by type: `--type local|remote|all` (default: all)
- Filter by status: `--status accessible|inaccessible|pending`
- Works offline using cached collection data (with `--offline` flag or when server unreachable)
- `shuttersense-agent collections sync` to refresh cache from server

**Acceptance Criteria - Offline Mode:**
- When offline or using `--offline` flag, displays cached Collections
- Shows cache timestamp: "Last synced: 2 hours ago"
- Warns if cache is stale (>7 days old)
- Indicates which Collections can run offline (LOCAL only)

**Example Usage:**
```bash
# Online mode (default) - fetches from server and updates cache
$ shuttersense-agent collections list

Collections bound to this agent (agt_01hgw2bbg...):

  GUID                  TYPE    NAME                LOCATION                STATUS      LAST ANALYSIS  OFFLINE
  col_01hgw2bbg00001    LOCAL   Vacation 2024       /photos/2024           Accessible  2024-01-20     Yes
  col_01hgw2bbg00002    LOCAL   Wedding 2024        /photos/wedding        Accessible  2024-01-15     Yes
  col_01hgw2bbg00003    LOCAL   Archive             /mnt/nas/archive       Inaccessible  Never        Yes
  col_01hgw2ccc00001    S3      Cloud Backup        my-bucket/photos       Accessible  2024-01-18     No
  col_01hgw2ccc00002    GCS     Google Archive      gcs-bucket/archive     Accessible  2024-01-10     No

5 collections total (4 accessible, 1 inaccessible)
3 available for offline execution

# Offline mode - uses cache
$ shuttersense-agent collections list --offline

Collections (from cache, last synced: 2 hours ago):

  GUID                  TYPE    NAME                LOCATION                OFFLINE
  col_01hgw2bbg00001    LOCAL   Vacation 2024       /photos/2024           Yes
  col_01hgw2bbg00002    LOCAL   Wedding 2024        /photos/wedding        Yes
  col_01hgw2bbg00003    LOCAL   Archive             /mnt/nas/archive       Yes
  col_01hgw2ccc00001    S3      Cloud Backup        my-bucket/photos       No
  col_01hgw2ccc00002    GCS     Google Archive      gcs-bucket/archive     No

Note: Accessibility status not shown in offline mode

# Filter to local collections only
$ shuttersense-agent collections list --type local

# Sync cache from server
$ shuttersense-agent collections sync

Syncing collections from server...
  Fetched 5 collections bound to this agent
  Cache updated: ~/.shuttersense-agent/collection-cache.json

# Re-test accessibility (requires server connection)
$ shuttersense-agent collections test col_01hgw2bbg00003

Testing collection: Archive (/mnt/nas/archive)
  Error: Path not accessible (mount not available)
  Status updated on server: Inaccessible
```

**Technical Notes:**
- Online: Queries server `GET /api/agent/v1/collections` and updates local cache
- Offline: Reads from `~/.shuttersense-agent/collection-cache.json`
- Cache includes connector metadata for remote Collections (for display, not credentials)
- Accessibility test requires server connection (updates server state)
- OFFLINE column indicates which Collections support offline execution (LOCAL only)

---

### User Story 5: Remove Standalone CLI Tools and Update Project Constitution (Priority: P2)

**As** a security-conscious maintainer preparing for production
**I want to** completely remove the standalone CLI tools from the repository
**So that** only authenticated, signed agent execution paths exist before production deployment

**Context:**
ShutterSense is pre-release; backward compatibility is not a concern. The standalone CLI tools (`photo_stats.py`, `photo_pairing.py`, `pipeline_validation.py`) represent a security risk:
- No authentication (anyone with file access can run them)
- No result signing or verification
- No audit trail or tenant isolation
- No job tracking or centralized management

These tools must be removed entirely before the web server is provisioned in production and agents are distributed.

**Acceptance Criteria - File Removal:**
- Delete `photo_stats.py` from repository root
- Delete `photo_pairing.py` from repository root
- Delete `pipeline_validation.py` from repository root
- Remove any CLI-specific test files (keep analysis module tests)
- Remove CLI-specific templates if not shared with agent

**Acceptance Criteria - Constitution Update:**
- Update `.specify/memory/constitution.md`:
  - Remove "I. Independent CLI Tools" core principle
  - Replace with "I. Agent-Only Tool Execution" principle
  - Update any references to standalone CLI execution
- Verify constitution reflects agent-first architecture

**Acceptance Criteria - Documentation Update:**
- Update `README.md`: Remove CLI tool usage examples, update quick start for agent
- Update `CLAUDE.md`: Remove CLI tool references, update project structure
- Update `docs/installation.md`: Focus on agent installation only
- Update `docs/configuration.md`: Remove CLI-specific config sections
- Update `docs/photostats.md`, `docs/photo-pairing.md`: Archive or redirect to agent commands
- **Preserve for historical reference:** `docs/prd/` and `specs/` directories (no changes needed)

**Acceptance Criteria - Code Cleanup:**
- Remove CLI-specific argument parsing code
- Remove CLI-specific signal handlers (SIGINT for graceful shutdown)
- Remove CLI-specific report file naming/saving logic
- Ensure shared analysis modules (`src/analysis/`) remain intact for agent use
- Ensure shared utilities (`utils/`) remain intact

**Files to Remove:**
```
photo_stats.py                    # DELETE
photo_pairing.py                  # DELETE
pipeline_validation.py            # DELETE
tests/test_photo_stats_cli.py     # DELETE (if exists, keep module tests)
tests/test_photo_pairing_cli.py   # DELETE (if exists, keep module tests)
```

**Files to Update:**
```
.specify/memory/constitution.md   # Update core principles
README.md                         # Remove CLI examples
CLAUDE.md                         # Remove CLI references
docs/installation.md              # Agent-only installation
docs/configuration.md             # Remove CLI config
docs/photostats.md               # Archive notice or redirect
docs/photo-pairing.md            # Archive notice or redirect
```

**Technical Notes:**
- Analysis logic lives in `src/analysis/` modules - these MUST be preserved
- Agent job executor already uses these modules directly
- CLI tools were wrappers around analysis modules; removing wrappers doesn't affect core logic
- Shared utilities (`utils/config_manager.py`, `utils/filename_parser.py`) remain for agent use

---

### User Story 6: Agent Self-Test Command (Priority: P2)

**As** a user installing a new agent
**I want to** verify the agent is correctly configured
**So that** I can troubleshoot setup issues

**Acceptance Criteria:**
- Agent CLI command: `shuttersense-agent self-test`
- Validates:
  - Agent registration with server
  - API key validity
  - Network connectivity to server
  - Tool availability (photostats, photo_pairing, pipeline_validation)
  - Authorized roots accessibility
- Reports any configuration issues with remediation steps

**Example Usage:**
```bash
$ shuttersense-agent self-test

Agent Self-Test
═══════════════════════════════════════════════════════════════

Server Connection:
  URL: https://api.shuttersense.ai      OK
  Latency: 45ms                         OK

Agent Registration:
  Agent ID: agt_01hgw2bbg...            OK
  Team: Acme Photography                OK
  Status: ONLINE                        OK

Tools:
  photostats                            OK (v1.2.3)
  photo_pairing                         OK (v1.2.3)
  pipeline_validation                   OK (v1.2.3)

Authorized Roots:
  /photos                               OK (readable, 15,234 files)
  /mnt/nas                              WARN (not mounted)

═══════════════════════════════════════════════════════════════
Self-test complete: 1 warning

Recommendation:
  Mount /mnt/nas or remove it from authorized_roots configuration
```

---

## Requirements

### Functional Requirements

#### Agent CLI Commands

- **FR-001**: Implement `shuttersense-agent test <path>` command for local path testing
- **FR-002**: Implement `shuttersense-agent collection create <path>` command
- **FR-003**: Implement `shuttersense-agent run <collection-guid> --tool <tool>` command (GUID only, not paths)
- **FR-004**: Implement `shuttersense-agent collections list` command with `--offline` support
- **FR-005**: Implement `shuttersense-agent collections test <guid>` command
- **FR-006**: Implement `shuttersense-agent sync` command for offline result upload
- **FR-007**: Implement `shuttersense-agent self-test` command
- **FR-008**: Support `--offline` flag for `run` command - LOCAL collections only (reject remote)
- **FR-009**: Support `--output <file>` flag for saving HTML reports locally
- **FR-040**: Implement `shuttersense-agent collections sync` command to refresh cache

#### Server API Extensions

- **FR-010**: Add endpoint for agent-initiated Collection creation: `POST /api/agent/v1/collections`
- **FR-011**: Add endpoint for listing agent's bound Collections: `GET /api/agent/v1/collections`
- **FR-012**: Add endpoint for uploading offline results: `POST /api/agent/v1/results/upload`
- **FR-013**: Support Collection creation with inline test results

#### CLI Tool Removal

- **FR-020**: Delete `photo_stats.py` from repository root
- **FR-021**: Delete `photo_pairing.py` from repository root
- **FR-022**: Delete `pipeline_validation.py` from repository root
- **FR-023**: Update `.specify/memory/constitution.md` to remove "Independent CLI Tools" principle
- **FR-024**: Update `README.md` to remove CLI tool references
- **FR-025**: Update `CLAUDE.md` to remove CLI tool references and update project structure
- **FR-026**: Update user documentation (`docs/`) to focus on agent-based workflow
- **FR-027**: Preserve `docs/prd/` and `specs/` for historical reference (no changes)
- **FR-028**: Ensure shared analysis modules (`src/analysis/`) remain intact for agent use

#### Local Storage and Caching

- **FR-030**: Store test results in `~/.shuttersense-agent/test-cache/`
- **FR-031**: Store offline results in `~/.shuttersense-agent/results/`
- **FR-032**: Implement cache expiration (24 hours for test cache)
- **FR-033**: Implement result cleanup after successful sync
- **FR-034**: Store collection cache in `~/.shuttersense-agent/collection-cache.json`
- **FR-035**: Collection cache includes all Collections bound to agent (local + remote via connector)
- **FR-036**: Collection cache expires after 7 days (warn user, still usable)
- **FR-037**: Auto-refresh collection cache on `collections list` (online mode)
- **FR-038**: Offline results MUST reference collection_guid (not path)

### Non-Functional Requirements

#### Performance

- **NFR-001**: Test command completes within 30 seconds for collections up to 10,000 files
- **NFR-002**: Collection creation completes within 5 seconds
- **NFR-003**: Offline result sync handles files up to 100MB

#### Reliability

- **NFR-010**: Offline results preserved across agent restarts
- **NFR-011**: Partial sync recovery (resume interrupted uploads)
- **NFR-012**: Graceful handling of server unavailability

#### Usability

- **NFR-020**: Clear, actionable error messages for all failure modes
- **NFR-021**: Progress indicators for long-running operations
- **NFR-022**: Consistent command structure across all agent subcommands
- **NFR-023**: Tab completion support for paths and Collection GUIDs

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent CLI Command Structure                           │
└─────────────────────────────────────────────────────────────────────────┘

shuttersense-agent
├── test <path>                    # Test local path (US1)
│   ├── --tool <tool>              # Specific tool or all
│   ├── --check-only               # Accessibility only
│   └── --output <file>            # Save HTML report
│
├── collection                     # Collection management
│   ├── create <path>              # Create from path (US2)
│   │   ├── --name <name>          # Collection name
│   │   ├── --skip-test            # Skip validation
│   │   └── --analyze              # Run initial analysis
│   ├── list                       # List bound collections (US4)
│   │   ├── --type <type>          # Filter: local|remote|all
│   │   ├── --status <status>      # Filter by status
│   │   └── --offline              # Use cached data
│   ├── sync                       # Refresh collection cache
│   └── test <guid>                # Re-test accessibility
│
├── run <collection-guid>          # Run tool (US3) - GUID only, not paths
│   ├── --tool <tool>              # Required
│   ├── --offline                  # No server (LOCAL collections only)
│   └── --output <file>            # Save HTML report
│
├── sync                           # Upload offline results (US3)
│   └── --dry-run                  # Show what would upload
│
└── self-test                      # Verify configuration (US6)
```

### Data Flow: Test and Create Collection

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│   User   │     │  Agent CLI   │     │ Local Files │     │  Server  │
│(Terminal)│     │              │     │             │     │          │
└────┬─────┘     └──────┬───────┘     └──────┬──────┘     └────┬─────┘
     │                  │                    │                  │
     │ 1. test /photos  │                    │                  │
     │─────────────────►│                    │                  │
     │                  │ 2. List files      │                  │
     │                  │───────────────────►│                  │
     │                  │◄───────────────────│                  │
     │                  │ 3. Run analysis    │                  │
     │                  │───────────────────►│                  │
     │                  │◄───────────────────│                  │
     │ 4. Test results  │                    │                  │
     │◄─────────────────│                    │                  │
     │                  │ 5. Cache results   │                  │
     │                  │───────────────────►│                  │
     │                  │                    │                  │
     │ 6. collection    │                    │                  │
     │    create /photos│                    │                  │
     │─────────────────►│                    │                  │
     │                  │ 7. Load cache      │                  │
     │                  │◄───────────────────│                  │
     │                  │ 8. POST /collections                  │
     │                  │─────────────────────────────────────►│
     │                  │◄─────────────────────────────────────│
     │ 9. Collection    │                    │                  │
     │    created       │                    │                  │
     │◄─────────────────│                    │                  │
```

### New Agent Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agent/v1/collections` | POST | Create Collection bound to agent |
| `/api/agent/v1/collections` | GET | List Collections bound to agent |
| `/api/agent/v1/collections/{guid}/test` | POST | Update accessibility status |
| `/api/agent/v1/results/upload` | POST | Upload offline analysis results |

### Collection Cache Schema

```python
class CachedCollection(BaseModel):
    """Collection metadata cached for offline access."""
    guid: str                           # e.g., "col_01hgw2bbg..."
    name: str                           # e.g., "Vacation 2024"
    type: Literal["LOCAL", "S3", "GCS", "SMB"]
    location: str                       # Path or bucket/prefix
    bound_agent_id: Optional[str]       # For LOCAL collections
    connector_guid: Optional[str]       # For REMOTE collections
    connector_name: Optional[str]       # Display name for connector
    is_accessible: Optional[bool]       # Last known status
    last_analysis_at: Optional[datetime]
    supports_offline: bool              # True only for LOCAL type


class CollectionCache(BaseModel):
    """Local cache of collections bound to this agent."""
    agent_id: str
    synced_at: datetime
    expires_at: datetime                # synced_at + 7 days
    collections: List[CachedCollection]
```

### Test Cache Schema

```python
class TestCacheEntry(BaseModel):
    """Cached test result for Collection creation."""
    path: str
    tested_at: datetime
    expires_at: datetime
    accessible: bool
    file_count: int
    photo_count: int
    sidecar_count: int
    tools_tested: List[str]
    issues_found: Optional[Dict[str, Any]]
    agent_id: str
    agent_version: str
```

### Offline Result Schema

```python
class OfflineResult(BaseModel):
    """Analysis result stored for later upload."""
    result_id: str                      # Local UUID
    collection_guid: str                # Required - must be from cache
    collection_name: str                # For display during sync
    tool: str
    executed_at: datetime
    agent_id: str
    agent_version: str
    analysis_data: Dict[str, Any]       # Full analysis output
    html_report: Optional[str]          # Base64-encoded HTML
```

### New Files

```
agent/src/
├── commands/
│   ├── test.py               # Test command implementation
│   ├── collection.py         # Collection subcommands (create, list, sync, test)
│   ├── run.py                # Run command implementation
│   ├── sync.py               # Sync command (upload offline results)
│   └── self_test.py          # Self-test command
├── cache/
│   ├── collection_cache.py   # Collection cache management
│   ├── test_cache.py         # Test result caching
│   └── result_store.py       # Offline result storage
└── cli.py                    # Updated CLI entry point

backend/src/api/agent/
├── collections.py            # Agent collection endpoints
└── results.py                # Offline result upload endpoint

~/.shuttersense-agent/
├── collection-cache.json     # Cached collections for offline access
├── test-cache/               # Cached test results (24h expiry)
└── results/                  # Pending offline results for sync
```

---

## Implementation Plan

### Phase 1: Test Command (Priority: P0)

**Estimated Tasks: ~20**

**Agent (15 tasks):**
1. Add `test` subcommand to agent CLI
2. Implement path accessibility checking
3. Implement file listing and counting
4. Integrate with analysis modules (reuse from job executor)
5. Implement `--tool` flag for specific tool selection
6. Implement `--check-only` flag for accessibility-only mode
7. Implement `--output` flag for HTML report generation
8. Implement test result caching
9. Add progress indicators for file scanning and analysis
10. Add clear error messages for common failure modes
11. Unit tests for test command
12. Integration tests with mock filesystem

**Documentation (5 tasks):**
1. Add `shuttersense-agent test` to CLI reference
2. Create troubleshooting guide for common errors
3. Add examples to getting started guide

**Checkpoint:** User can run `shuttersense-agent test /photos` and see analysis results.

---

### Phase 2: Collection Create Command (Priority: P0)

**Estimated Tasks: ~18**

**Backend (8 tasks):**
1. Add `POST /api/agent/v1/collections` endpoint
2. Validate agent authentication and team scoping
3. Auto-bind Collection to creating agent
4. Support inline test results in creation request
5. Return Collection GUID and web UI URL
6. Unit tests for agent collection endpoint
7. Integration tests for Collection creation flow

**Agent (10 tasks):**
1. Add `collection create` subcommand
2. Load and validate test cache
3. Implement name suggestion from folder path
4. Prompt for Collection name if not provided
5. Call server API to create Collection
6. Display success message with GUID and URL
7. Implement `--skip-test` flag
8. Implement `--analyze` flag to trigger initial job
9. Unit tests for collection create command
10. Integration tests with mock server

**Checkpoint:** User can create Collection from tested path with `shuttersense-agent collection create`.

---

### Phase 3: Run and Sync Commands (Priority: P1)

**Estimated Tasks: ~22**

**Backend (7 tasks):**
1. Add `POST /api/agent/v1/results/upload` endpoint
2. Validate result schema and agent ownership
3. Match results to Collections by path or GUID
4. Store results as AnalysisResult records
5. Handle duplicate result prevention
6. Unit tests for result upload
7. Integration tests for sync flow

**Agent (15 tasks):**
1. Add `run` subcommand for tool execution
2. Support both path and Collection GUID arguments
3. Implement `--offline` flag for local-only execution
4. Implement offline result storage
5. Add `sync` subcommand for result upload
6. Implement `--dry-run` flag for sync preview
7. Handle partial sync (resume interrupted uploads)
8. Clean up results after successful sync
9. Progress indicators for upload
10. Unit tests for run command
11. Unit tests for sync command
12. Integration tests for offline workflow

**Checkpoint:** User can run tools offline and sync results later.

---

### Phase 4: Collection Management Commands (Priority: P1)

**Estimated Tasks: ~12**

**Backend (4 tasks):**
1. Add `GET /api/agent/v1/collections` endpoint
2. Add `POST /api/agent/v1/collections/{guid}/test` endpoint
3. Return Collection details with status
4. Unit tests

**Agent (8 tasks):**
1. Add `collections list` subcommand
2. Implement table formatting for Collection display
3. Implement `--status` filter flag
4. Add `collections test` subcommand
5. Update Collection accessibility status on server
6. Unit tests for collection commands
7. Integration tests

**Checkpoint:** User can list and manage Collections from agent CLI.

---

### Phase 5: CLI Tool Removal and Constitution Update (Priority: P2)

**Estimated Tasks: ~15**

**File Removal (4 tasks):**
1. Delete `photo_stats.py` from repository root
2. Delete `photo_pairing.py` from repository root
3. Delete `pipeline_validation.py` from repository root
4. Remove CLI-specific test files (preserve analysis module tests)

**Constitution Update (3 tasks):**
1. Update `.specify/memory/constitution.md`: Remove "I. Independent CLI Tools" principle
2. Replace with "I. Agent-Only Tool Execution" principle describing agent-first architecture
3. Review and update any other constitutional references to CLI tools

**Documentation Update (8 tasks):**
1. Update `README.md`: Remove CLI examples, add agent quick start
2. Update `CLAUDE.md`: Remove CLI references, update project structure section
3. Update `docs/installation.md`: Agent-only installation guide
4. Update `docs/configuration.md`: Remove CLI-specific configuration sections
5. Archive or redirect `docs/photostats.md` to agent commands
6. Archive or redirect `docs/photo-pairing.md` to agent commands
7. Verify `docs/prd/` and `specs/` preserved for historical reference
8. Update any cross-references in documentation

**Checkpoint:** CLI tools removed, constitution updated to agent-first principles, documentation reflects agent-only workflow.

---

### Phase 6: Self-Test and Polish (Priority: P2)

**Estimated Tasks: ~10**

**Agent (10 tasks):**
1. Add `self-test` subcommand
2. Implement server connectivity check
3. Implement registration validation
4. Implement tool availability check
5. Implement authorized roots check
6. Format output with clear pass/fail indicators
7. Add remediation suggestions for failures
8. Tab completion for commands and arguments
9. Unit tests for self-test
10. End-to-end tests for complete workflows

**Checkpoint:** Complete agent CLI with all commands and self-diagnostics.

---

## Risks and Mitigation

### Risk 1: Analysis Module Regression

- **Impact**: High - Removing CLI tools accidentally breaks shared analysis modules
- **Probability**: Low
- **Mitigation**: CLI tools are thin wrappers; analysis logic in `src/analysis/` is already used by agent; comprehensive tests for analysis modules; verify agent job executor still works after removal

### Risk 2: Offline Result Conflicts

- **Impact**: Medium - Confusion when syncing old results
- **Probability**: Low
- **Mitigation**: Include timestamps in results; warn on stale results; option to discard old results during sync

### Risk 3: Test Cache Staleness

- **Impact**: Low - Collection created from outdated test
- **Probability**: Medium
- **Mitigation**: 24-hour cache expiration; warning if cache is old; re-test option during create

### Risk 4: Documentation Gaps

- **Impact**: Medium - Users confused about new workflow after CLI removal
- **Probability**: Medium
- **Mitigation**: Complete documentation rewrite before CLI removal; clear agent quick-start guide; updated README with agent-first examples

---

## Security Considerations

### Agent Authentication

- All agent CLI commands use existing agent API key
- API key stored securely in agent configuration
- Server validates agent team membership for all operations

### Collection Creation

- Agent can only create Collections bound to itself
- Collections inherit agent's team_id
- Path validation ensures agent has access to requested path

### Offline Results

- Results signed with agent credentials
- Server validates result authenticity before storing
- Tampering detected via signature verification

### Audit Trail

- All Collection creations logged with agent ID
- Offline result uploads logged with source agent
- All tool executions traceable via job records

---

## Success Metrics

### Security Metrics

- **M1**: Zero unauthenticated tool executions possible after CLI removal
- **M2**: 100% of tool executions have associated job records
- **M3**: All results signed and verifiable

### Adoption Metrics

- **M4**: 80% of users successfully complete test → create workflow
- **M5**: Agent installation success rate >95%

### Quality Metrics

- **M6**: 95% success rate for Collection creation from test
- **M7**: Zero data loss from offline result sync
- **M8**: Test command accuracy matches job executor (identical results)

### Documentation Metrics

- **M9**: Support tickets related to workflow below 5% of total
- **M10**: Documentation covers 100% of previous CLI tool functionality

---

## Dependencies

### External Dependencies

- None (uses existing server infrastructure)

### Internal Dependencies

- Agent architecture (021-distributed-agent-architecture)
- Analysis modules (src/analysis/)
- Collection API (existing endpoints)

### New Dependencies

```
# No new dependencies - uses existing agent infrastructure
```

---

## Appendix

### A. Command Reference Summary

| Command | Purpose | Server Required |
|---------|---------|-----------------|
| `shuttersense-agent test <path>` | Test local path accessibility and analysis | No |
| `shuttersense-agent collection create <path>` | Create Collection from tested path | Yes |
| `shuttersense-agent collections list` | List bound Collections | No (uses cache offline) |
| `shuttersense-agent collections sync` | Refresh collection cache from server | Yes |
| `shuttersense-agent collections test <guid>` | Re-test Collection accessibility | Yes |
| `shuttersense-agent run <guid> --tool <tool>` | Run analysis tool (GUID only) | No for LOCAL + `--offline` |
| `shuttersense-agent sync` | Upload offline results | Yes |
| `shuttersense-agent self-test` | Verify agent configuration | Yes |

### B. Migration Examples

**Before (CLI tool):**
```bash
python3 photo_stats.py /photos/2024 output.html
```

**After (Agent CLI):**
```bash
# One-time setup: test and create Collection
shuttersense-agent test /photos/2024
shuttersense-agent collection create /photos/2024 --name "Photos 2024"

# Sync collection cache (do this periodically or after creating collections)
shuttersense-agent collections sync

# Subsequent runs - online (results in web UI)
shuttersense-agent run col_01hgw2bbg... --tool photostats

# Or offline mode against cached LOCAL collection
shuttersense-agent run col_01hgw2bbg... --tool photostats --offline --output output.html

# Sync results when back online
shuttersense-agent sync
```

### C. Error Messages

| Error | Cause | Resolution |
|-------|-------|------------|
| `Path not accessible` | Directory doesn't exist or no read permission | Check path exists and agent has read access |
| `Path not in authorized roots` | Agent configured with restricted paths | Add path to agent's authorized_roots or run with `--force` |
| `Test cache expired` | More than 24 hours since test | Re-run `shuttersense-agent test` |
| `Agent not registered` | Agent API key invalid or revoked | Re-register agent with server |
| `Collection already exists` | Path already mapped to a Collection | Use existing Collection or choose different path |
| `Cannot run offline on remote collection` | Attempted `--offline` on S3/GCS/SMB Collection | Use online mode or run against LOCAL collection |
| `Collection not in cache` | Collection GUID not found in local cache | Run `shuttersense-agent collections sync` to refresh cache |
| `Collection cache expired` | Cache older than 7 days | Run `shuttersense-agent collections sync` to refresh |

---

## Revision History

- **2026-01-22 (v1.2)**: CLI tool removal (not deprecation)
  - US5: Rewritten for complete CLI tool removal instead of deprecation
  - US5: Added constitution update requirement (remove "Independent CLI Tools" principle)
  - US5: Added documentation update requirements (README, CLAUDE.md, docs/)
  - US5: Preserve docs/prd/ and specs/ for historical reference only
  - Updated Non-Goals: Backward compatibility not required (pre-release product)
  - Updated Risks: Focus on analysis module preservation and documentation gaps
  - Updated Success Metrics: Added security metrics for authenticated execution
  - Updated Functional Requirements: FR-020 to FR-028 for removal and doc updates

- **2026-01-22 (v1.1)**: Collection cache for offline execution
  - US3: Changed `run` command to require Collection GUID (not arbitrary paths)
  - US3: Offline mode limited to LOCAL collections only (remote requires network)
  - US3: Added collection cache requirement for offline execution
  - US4: Added `--offline` flag and `collections sync` command
  - US4: Collections list works offline using cached data
  - Added Collection Cache Schema and cache management requirements
  - Updated command reference and migration examples

- **2026-01-22 (v1.0)**: Initial draft
  - Defined agent CLI commands for testing and Collection creation
  - Specified offline mode and result sync workflow
  - Outlined phased implementation plan
