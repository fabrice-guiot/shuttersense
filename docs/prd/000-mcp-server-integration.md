# PRD: MCP Server — AI-Powered Photo Collection Intelligence

**Issue**: TBD
**Status**: Draft
**Created**: 2026-02-18
**Last Updated**: 2026-02-18
**Related Documents**:
- [Domain Model](../domain-model.md)
- [Distributed Agent Architecture](./021-distributed-agent-architecture.md)
- [Pipeline-Driven Analysis Tools](./217-pipeline-driven-analysis-tools.md)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)

---

## Executive Summary

This PRD defines a **Model Context Protocol (MCP) server** for ShutterSense that exposes collection metadata, analysis results, job management, event scheduling, and pipeline configuration to AI assistants such as Claude. The MCP server enables users to interact with their photo management data through natural language — querying collection health, interpreting analysis findings, scheduling jobs, and detecting calendar conflicts — without navigating the web UI.

ShutterSense already produces rich structured data through its analysis tools (PhotoStats, Photo Pairing, Pipeline Validation), trend analytics, and calendar conflict detection. However, interpreting this data requires navigating multiple pages and correlating information across domains (Collections, Results, Trends, Events, Pipelines). An MCP server transforms ShutterSense into a conversational data source where an AI assistant can synthesize cross-domain insights in a single interaction.

### Key Design Decisions

1. **Standalone service, shared models**: The MCP server runs as a separate process from the FastAPI backend, but imports the same SQLAlchemy models and service layer. This avoids duplicating business logic while keeping transport concerns isolated.
2. **Read-heavy with selective writes**: The MCP server exposes broad read access across all domains but restricts write operations to job creation and event management. Connector credentials and admin operations are excluded.
3. **API token authentication**: MCP clients authenticate using existing ShutterSense API tokens (Bearer header), inheriting the same team-scoped tenant isolation as the REST API.
4. **Streamable HTTP transport**: Uses the current MCP transport standard, compatible with Claude Desktop, Claude Code, and other MCP clients.
5. **Natural-language formatting**: Tool responses return structured markdown narratives rather than raw JSON, optimized for LLM consumption and user presentation.

---

## Background

### Current State

ShutterSense exposes its functionality through three interfaces:

1. **Web UI** (React frontend) — Full CRUD for all domains, real-time job progress, visual pipeline editor, calendar views, trend charts.
2. **REST API** (FastAPI backend) — Programmatic access for all operations, consumed by the frontend and agents.
3. **Agent CLI** (`shuttersense-agent`) — Distributed tool execution, job claiming, result upload.

Users who want quick answers about their photo collections — "Are there any orphaned files in my wedding collection?", "Which cameras were most active last month?", "Do I have scheduling conflicts next weekend?" — must open the web UI, navigate to the relevant page, apply filters, and mentally correlate data across screens.

### Problem Statement

- **Information is scattered**: Understanding collection health requires visiting Collections (accessibility status), Assets (analysis results), Analytics (trends), and Resources (pipeline validation). No single view synthesizes these signals.
- **Analysis results require domain knowledge**: A `consistency_ratio: 0.73` in Pipeline Validation or `orphaned_count: 42` in PhotoStats is meaningful only with context about what the pipeline expects and what the collection contains. Users must mentally map structured data to actionable insights.
- **Repetitive monitoring workflows**: Photographers who manage multiple collections often perform the same sequence — check status, review latest results, compare to previous run, decide whether to re-analyze — across many collections. This is tedious in a point-and-click UI.
- **No AI integration point**: Despite the growing adoption of AI assistants in developer and creative workflows, ShutterSense has no programmatic interface designed for LLM consumption.

### Strategic Context

MCP has become the standard protocol for connecting AI assistants to external data and tools, with support in Claude Desktop, Claude Code, VS Code, Cursor, and other clients. Adding an MCP server positions ShutterSense as an AI-native photo management platform, enabling workflows like:

- A photographer asks Claude: *"Run a full analysis on all my live collections and summarize anything that needs attention"*
- A team lead asks: *"Compare the orphan rates across our event collections from the last 3 months"*
- An event planner asks: *"Do any of our performers have conflicts for the March 15 festival?"*

---

## Goals

### Primary Goals

1. **Cross-domain querying**: Enable AI assistants to query collections, analysis results, trends, events, and pipelines through a unified MCP interface.
2. **Analysis interpretation**: Provide formatted, contextual summaries of analysis results that explain what the numbers mean and what action to take.
3. **Job lifecycle management**: Allow AI assistants to create analysis jobs, monitor progress, and retrieve completed results.
4. **Event conflict detection**: Expose calendar conflict queries so AI assistants can identify scheduling issues through conversation.

### Secondary Goals

5. **Collection health synthesis**: Enable a single query that correlates collection accessibility, latest result status, trend direction, and agent availability into a holistic health summary.
6. **Pipeline exploration**: Let AI assistants describe pipeline graph structure in natural language and preview how filenames would be classified.
7. **Guided workflows via prompts**: Provide MCP prompt templates that guide users through common multi-step interactions (health checks, troubleshooting, event planning).

### Non-Goals (v1)

1. **Connector credential management**: Creating or updating connector credentials through MCP is excluded for security reasons.
2. **Agent management**: Agent registration, revocation, and configuration are administrative operations not exposed through MCP.
3. **Pipeline editing**: Modifying pipeline graph structure (adding/removing nodes, edges) is a visual task better suited to the web UI editor.
4. **User and team administration**: Role assignments, team settings, and user management are excluded.
5. **File-level operations**: Browsing individual files within collections or downloading photos is out of scope.
6. **Real-time streaming**: WebSocket-based job progress streaming is not supported in MCP v1; polling via `get_job_status` is used instead.

---

## User Personas

### Primary: Photographer / Collection Manager

- **Need**: Quick answers about collection health across a large portfolio without navigating multiple UI screens.
- **Pain Point**: Manages 10+ collections across local and cloud storage. Checking orphan status, pairing consistency, and pipeline validation results requires visiting 3–4 different pages per collection.
- **Goal**: Ask an AI assistant *"How are my collections doing?"* and get a prioritized summary with action items.

### Secondary: Team Lead / Event Coordinator

- **Need**: Monitor team-wide trends and coordinate event coverage without deep-diving into each collection.
- **Pain Point**: Correlating analysis trends with upcoming event schedules requires switching between Analytics and Events views. Conflict detection for performer availability requires manual calendar review.
- **Goal**: Ask an AI assistant *"Are we ready for next month's events? Any collections need attention before then?"* and get a consolidated status report.

### Tertiary: Developer / Automation Builder

- **Need**: Integrate ShutterSense data into automated workflows and AI-powered scripts.
- **Pain Point**: Building custom dashboards or reports requires direct REST API integration with knowledge of endpoint schemas and pagination.
- **Goal**: Use the MCP server as a natural-language API that handles pagination, filtering, and formatting automatically.

---

## Requirements

### Functional Requirements

#### FR-100: MCP Server Infrastructure

- **FR-100.1**: Create a standalone MCP server application using the official `mcp` Python SDK that runs as a separate process from the FastAPI backend.
- **FR-100.2**: The MCP server MUST import and reuse SQLAlchemy models and service classes from `backend/src/models/` and `backend/src/services/` — no business logic duplication.
- **FR-100.3**: The MCP server MUST support Streamable HTTP transport, exposing the MCP endpoint at a configurable path (default: `/mcp`).
- **FR-100.4**: The MCP server MUST be configurable via environment variables:
  - `MCP_PORT` — HTTP port (default: `8001`)
  - `MCP_PATH` — Endpoint path (default: `/mcp`)
  - `DATABASE_URL` — Same database connection as the backend
  - `ENCRYPTION_KEY` — Same Fernet key for credential decryption (if needed for connector status checks)
- **FR-100.5**: The MCP server MUST declare its capabilities during the MCP `initialize` handshake: `tools`, `resources`, and `prompts`.
- **FR-100.6**: The MCP server MUST include a health check endpoint (`GET /health`) independent of MCP transport for deployment monitoring.

#### FR-200: Authentication and Tenant Isolation

- **FR-200.1**: MCP clients MUST authenticate using ShutterSense API tokens via Bearer header on the HTTP transport. The token is passed in the initial HTTP connection headers.
- **FR-200.2**: The MCP server MUST resolve the API token to a `TenantContext` (team_id, user_id) using the same `api_token_service` validation as the backend.
- **FR-200.3**: All tool invocations and resource reads MUST be scoped to the authenticated user's team. Cross-team data access MUST return empty results (not errors) to prevent information leakage.
- **FR-200.4**: Unauthenticated MCP connections MUST be rejected during transport initialization with a clear error message.
- **FR-200.5**: API tokens used for MCP MUST NOT grant access to super admin operations, consistent with existing API token restrictions.

#### FR-300: MCP Tools — Collection Management

- **FR-300.1**: `list_collections` tool — List collections with optional filters:
  - Parameters: `state` (live/closed/archived), `type` (local/s3/gcs/smb), `name` (search string), `limit` (default 20)
  - Returns: Formatted markdown table with name, type, state, file count, last analyzed date, accessibility status
- **FR-300.2**: `get_collection` tool — Get detailed collection information:
  - Parameters: `guid` (collection GUID)
  - Returns: Full collection details including assigned pipeline, bound agent, connector status, latest result summary, and accessibility status
- **FR-300.3**: `get_collection_health` tool — Synthesized health report for a collection:
  - Parameters: `guid` (collection GUID)
  - Returns: Narrative summary combining accessibility status, latest analysis results (per tool), trend direction (improving/declining/stable), agent availability, and pipeline validation status

#### FR-400: MCP Tools — Analysis & Jobs

- **FR-400.1**: `run_analysis` tool — Queue an analysis job:
  - Parameters: `collection_guid`, `tool` (photostats/photo_pairing/pipeline_validation)
  - Returns: Job GUID and confirmation message
  - MUST validate that the collection exists and is accessible before queuing
  - MUST warn if no agents are available to process the job
- **FR-400.2**: `get_job_status` tool — Check job progress:
  - Parameters: `guid` (job GUID)
  - Returns: Status, progress percentage, current stage, duration, assigned agent name
- **FR-400.3**: `list_results` tool — List analysis results with filters:
  - Parameters: `collection_guid` (optional), `tool` (optional), `status` (optional), `limit` (default 10)
  - Returns: Formatted list with result GUID, tool, collection name, date, status, key metrics (issues found, files scanned)
- **FR-400.4**: `get_result` tool — Get detailed result with interpretation:
  - Parameters: `guid` (result GUID)
  - Returns: Tool-specific analysis summary in natural language:
    - **PhotoStats**: File type breakdown, orphaned file count and percentage, comparison to previous run
    - **Photo Pairing**: Camera usage summary, pairing success rate, processing method distribution
    - **Pipeline Validation**: Consistency ratio with explanation, node-level pass/fail summary, unmatched files
- **FR-400.5**: `get_trends` tool — Fetch trend data for a tool:
  - Parameters: `tool` (photostats/photo_pairing/pipeline_validation), `collection_guid` (optional), `days` (default 90)
  - Returns: Narrative trend summary (improving/declining/stable) with key data points

#### FR-500: MCP Tools — Events & Calendar

- **FR-500.1**: `list_events` tool — Query calendar events:
  - Parameters: `start_date`, `end_date`, `status` (optional), `category_guid` (optional), `limit` (default 20)
  - Returns: Formatted event list with date, title, location, status, performer count
- **FR-500.2**: `detect_conflicts` tool — Check for scheduling conflicts:
  - Parameters: `start_date`, `end_date`, `performer_guid` (optional)
  - Returns: List of conflicts with event names, dates, and affected performers
- **FR-500.3**: `get_event` tool — Get event details:
  - Parameters: `guid` (event GUID)
  - Returns: Full event details including location, organizer, performers, logistics status, attendance tracking

#### FR-600: MCP Tools — Pipelines & Configuration

- **FR-600.1**: `list_pipelines` tool — List pipelines:
  - Parameters: `active_only` (boolean, default true), `limit` (default 10)
  - Returns: Pipeline list with name, version, active/default status, node count, edge count
- **FR-600.2**: `describe_pipeline` tool — Natural-language description of a pipeline:
  - Parameters: `guid` (pipeline GUID)
  - Returns: Human-readable description of the pipeline graph structure, explaining what file types it recognizes, what processing stages it defines, and what pairings it expects
- **FR-600.3**: `preview_pipeline` tool — Show how a pipeline would classify sample filenames:
  - Parameters: `guid` (pipeline GUID), `filenames` (list of sample filenames, optional)
  - Returns: Classification of each filename (matched node, camera ID extracted, processing method detected, extension category)
- **FR-600.4**: `get_agent_status` tool — Agent pool summary:
  - Parameters: none
  - Returns: Online/offline/total agent counts, capability summary, any collections with no available agents

#### FR-700: MCP Resources

- **FR-700.1**: `shuttersense://stats/overview` — Team-wide KPI summary (total collections, total files, total images, active agents, pending jobs).
- **FR-700.2**: `shuttersense://collections/{guid}/stats` — Collection-level statistics (file count by extension, storage used, last analyzed timestamp).
- **FR-700.3**: `shuttersense://results/{guid}/summary` — Pre-formatted analysis result summary for a specific result GUID.
- **FR-700.4**: `shuttersense://pipelines/{guid}/graph` — Pipeline graph structure as a readable node/edge description.
- **FR-700.5**: `shuttersense://config/extensions` — Configured photo and metadata extensions for the team.
- **FR-700.6**: `shuttersense://agents/pool` — Agent pool status (online count, offline count, capabilities).

#### FR-800: MCP Prompts

- **FR-800.1**: `collection-health-check` prompt — Guided workflow that walks the AI through checking a collection's accessibility, latest results, trend direction, and agent availability, producing a prioritized action list.
- **FR-800.2**: `troubleshoot-orphans` prompt — Step-by-step diagnosis template for investigating orphaned files: check pipeline configuration, review PhotoStats results, compare sidecar requirements, suggest corrective actions.
- **FR-800.3**: `plan-event-coverage` prompt — Template for planning photo coverage of upcoming events: review event schedule, check assigned collections, verify pipeline readiness, identify equipment needs.
- **FR-800.4**: `portfolio-review` prompt — Template for a comprehensive review of all collections: health status, recent trends, pending jobs, collections needing attention.

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: Tool invocations MUST respond within 2 seconds for read operations (list, get, trends).
- **NFR-100.2**: Job creation (`run_analysis`) MUST respond within 3 seconds, including validation.
- **NFR-100.3**: Resource reads MUST respond within 1 second.
- **NFR-100.4**: The MCP server MUST handle at least 10 concurrent MCP sessions without degradation.

#### NFR-200: Security

- **NFR-200.1**: The MCP server MUST NOT expose connector credentials, encryption keys, or agent API keys through any tool or resource.
- **NFR-200.2**: The MCP server MUST NOT expose internal database IDs. All entity references use GUIDs.
- **NFR-200.3**: Tool responses MUST NOT include raw SQL, stack traces, or internal error details. Errors are returned as user-friendly messages.
- **NFR-200.4**: Rate limiting MUST be applied to write operations (job creation): maximum 10 per minute per API token, consistent with the REST API.

#### NFR-300: Compatibility

- **NFR-300.1**: The MCP server MUST implement MCP protocol version `2025-11-25` or later.
- **NFR-300.2**: The MCP server MUST work with Claude Desktop, Claude Code, and any MCP-compliant client.
- **NFR-300.3**: The MCP server MUST be deployable alongside the existing backend without port conflicts (separate port or path-based routing).

#### NFR-400: Testing

- **NFR-400.1**: Unit tests MUST cover all tool implementations with mocked service layer calls.
- **NFR-400.2**: Unit tests MUST verify tenant isolation — tools invoked with Team A's token MUST NOT return Team B's data.
- **NFR-400.3**: Unit tests MUST verify authentication rejection for invalid or missing tokens.
- **NFR-400.4**: Integration tests MUST verify end-to-end MCP protocol handshake, tool listing, tool invocation, and resource reading.
- **NFR-400.5**: Test coverage target: >80% for MCP server code.

#### NFR-500: Observability

- **NFR-500.1**: The MCP server MUST log all tool invocations with tool name, user GUID, team GUID, and response time.
- **NFR-500.2**: The MCP server MUST log authentication failures with client IP and token prefix (first 8 chars).
- **NFR-500.3**: The `/health` endpoint MUST report database connectivity and MCP transport status.

---

## Technical Approach

### 1. Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Desktop  │     │   Claude Code    │     │  Other MCP      │
│  / AI Client     │     │                  │     │  Clients        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │  Streamable HTTP              │                        │
         │  (Bearer token)               │                        │
         └──────────────┬────────────────┘────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  MCP Server     │
              │  :8001/mcp      │
              │                 │
              │  ┌───────────┐  │
              │  │  Auth     │  │  ← Validates API token → TenantContext
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │  Tools    │  │  ← 14 tools (collections, analysis,
              │  │           │  │     events, pipelines, agents)
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │ Resources │  │  ← 6 resource URIs (stats, config,
              │  │           │  │     graphs, summaries)
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │  Prompts  │  │  ← 4 guided workflow templates
              │  └───────────┘  │
              └────────┬────────┘
                       │
                       │  SQLAlchemy (shared models & services)
                       │
                       ▼
              ┌─────────────────┐
              │  PostgreSQL     │  ← Same database as backend
              └─────────────────┘
```

### 2. Project Structure

```
mcp_server/
├── __init__.py
├── __main__.py                # Entry point: `python -m mcp_server`
├── server.py                  # MCP server setup, transport config, capability declaration
├── auth.py                    # API token validation → TenantContext resolution
├── db.py                      # Database session management (shared config with backend)
├── tools/
│   ├── __init__.py            # Tool registry
│   ├── collections.py         # list_collections, get_collection, get_collection_health
│   ├── analysis.py            # run_analysis, get_job_status, list_results, get_result, get_trends
│   ├── events.py              # list_events, detect_conflicts, get_event
│   └── pipelines.py           # list_pipelines, describe_pipeline, preview_pipeline, get_agent_status
├── resources/
│   ├── __init__.py            # Resource registry
│   ├── stats.py               # Team-wide and collection-level stats
│   ├── results.py             # Pre-formatted result summaries
│   ├── pipelines.py           # Pipeline graph descriptions
│   └── config.py              # Team configuration (extensions)
├── prompts/
│   ├── __init__.py            # Prompt registry
│   └── workflows.py           # Health check, troubleshoot, plan, review templates
├── formatters/
│   ├── __init__.py
│   ├── collections.py         # Collection → markdown formatting
│   ├── results.py             # Analysis result → narrative formatting
│   ├── events.py              # Event → readable formatting
│   └── pipelines.py           # Pipeline graph → natural language description
└── tests/
    ├── __init__.py
    ├── conftest.py             # Fixtures: mock services, test tokens, sample data
    ├── test_auth.py            # Authentication and tenant isolation tests
    ├── test_tools_collections.py
    ├── test_tools_analysis.py
    ├── test_tools_events.py
    ├── test_tools_pipelines.py
    ├── test_resources.py
    └── test_formatters.py
```

### 3. Server Entry Point

**File**: `mcp_server/server.py`

```python
import os

from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPTransport

from mcp_server.auth import resolve_tenant_context
from mcp_server.tools import register_tools
from mcp_server.resources import register_resources
from mcp_server.prompts import register_prompts

server = Server(
    name="shuttersense-mcp",
    version="1.0.0",
)

register_tools(server)
register_resources(server)
register_prompts(server)


def create_app():
    """Create ASGI app with MCP transport mounted."""
    from starlette.applications import Starlette
    from starlette.routing import Mount

    mcp_path = os.getenv("MCP_PATH", "/mcp")
    transport = StreamableHTTPTransport(mcp_path)

    app = Starlette(
        routes=[
            Mount(mcp_path, app=transport.asgi_app(server)),
        ],
    )
    return app
```

### 4. Authentication Flow

**File**: `mcp_server/auth.py`

```python
from backend.src.services.api_token_service import ApiTokenService
from backend.src.middleware.tenant import TenantContext


async def resolve_tenant_context(
    authorization: str,
    db_session,
) -> TenantContext:
    """
    Resolve a Bearer API token to a TenantContext.

    Uses the same ApiTokenService as the backend to validate the token
    and extract team_id + user_id.

    Raises:
        AuthenticationError: If token is missing, invalid, or revoked.
    """
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing Bearer token")

    token = authorization[7:]
    token_service = ApiTokenService(db_session)
    api_token = token_service.validate_token(token)

    if not api_token:
        raise AuthenticationError("Invalid or revoked API token")

    return TenantContext(
        team_id=api_token.team_id,
        user_id=api_token.user_id,
    )
```

### 5. Tool Implementation Pattern

**File**: `mcp_server/tools/collections.py` (example)

```python
from mcp.server import Server
from mcp_server.formatters.collections import format_collection_list, format_collection_health


def register_collection_tools(server: Server):

    @server.tool(
        name="list_collections",
        description="List photo collections with optional filters by state, type, or name.",
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["live", "closed", "archived"],
                    "description": "Filter by collection state",
                },
                "type": {
                    "type": "string",
                    "enum": ["local", "s3", "gcs", "smb"],
                    "description": "Filter by storage type",
                },
                "name": {
                    "type": "string",
                    "description": "Search collections by name (partial match)",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of results",
                },
            },
        },
    )
    async def list_collections(arguments: dict, context) -> str:
        ctx = context.tenant  # TenantContext from auth
        service = CollectionService(context.db)

        collections = service.list_collections(
            team_id=ctx.team_id,
            state=arguments.get("state"),
            storage_type=arguments.get("type"),
            name_search=arguments.get("name"),
            limit=arguments.get("limit", 20),
        )

        return format_collection_list(collections)
```

### 6. Result Formatter Pattern

**File**: `mcp_server/formatters/results.py` (example)

```python
def format_photostats_result(result) -> str:
    """Format a PhotoStats result as a narrative summary."""
    data = result.results_json

    total = data.get("total_files", 0)
    orphaned = data.get("orphaned_count", 0)
    orphan_pct = (orphaned / total * 100) if total > 0 else 0

    summary = f"""## PhotoStats Analysis — {result.collection.name}

**Scanned**: {result.files_scanned:,} files | **Duration**: {result.duration_seconds}s
**Date**: {result.created_at.strftime('%Y-%m-%d %H:%M')}

### File Breakdown
"""

    for ext, count in sorted(data.get("by_extension", {}).items()):
        summary += f"- `{ext}`: {count:,} files\n"

    summary += f"""
### Orphaned Files
- **{orphaned:,}** orphaned files ({orphan_pct:.1f}% of total)
"""

    if orphaned > 0:
        summary += (
            "\n> **Action needed**: These files are missing their expected "
            "sidecar files. Check your pipeline's sidecar requirements "
            "and ensure XMP files are generated for all captures.\n"
        )
    else:
        summary += "\n> All files have their expected sidecars. No action needed.\n"

    return summary
```

---

## Implementation Plan

### Phase 1: Server Foundation (Backend)

- Set up `mcp_server/` package structure
- Implement MCP server initialization with Streamable HTTP transport
- Implement API token authentication and TenantContext resolution
- Implement database session management (shared with backend)
- Add `/health` endpoint
- Add unit tests for auth and server initialization
- **Checkpoint**: MCP handshake succeeds with a valid API token; `tools/list` returns an empty list

### Phase 2: Core Read Tools (Backend)

- Implement `list_collections`, `get_collection`, `get_collection_health`
- Implement `list_results`, `get_result`, `get_trends`
- Implement `list_pipelines`, `describe_pipeline`
- Implement `get_agent_status`
- Build formatters for collection, result, and pipeline data
- Add unit tests for all tools and formatters
- **Checkpoint**: An MCP client can query collections, read analysis results with narrative formatting, and view pipeline descriptions

### Phase 3: Write Tools & Events (Backend)

- Implement `run_analysis` with validation and agent availability warnings
- Implement `get_job_status`
- Implement `list_events`, `get_event`, `detect_conflicts`
- Build formatters for job status and event data
- Add rate limiting for `run_analysis`
- Add unit tests for write operations and event tools
- **Checkpoint**: An MCP client can create analysis jobs, track progress, and query the event calendar

### Phase 4: Resources & Prompts

- Implement all 6 MCP resources (FR-700)
- Implement all 4 MCP prompts (FR-800)
- Add unit tests for resources and prompts
- **Checkpoint**: MCP clients can read resources and use prompt templates

### Phase 5: Integration Testing & Documentation

- End-to-end integration tests (full MCP protocol flow)
- Tenant isolation verification tests
- Create `claude_desktop_config.json` example for Claude Desktop connection
- Create `CLAUDE.md` MCP server section with setup instructions
- Document all tools, resources, and prompts in `docs/mcp-server.md`
- **Checkpoint**: Complete, tested MCP server ready for deployment

---

## Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Embed MCP in existing FastAPI backend** | Single deployment, shared middleware | Mixes HTTP transport with REST API, complicates routing, harder to scale independently | Rejected — separation of concerns |
| **FastMCP framework** | High-level decorators, rapid prototyping | Additional dependency, less control over transport and auth, abstracts away protocol details | Rejected — official SDK provides enough ergonomics with more control |
| **fastapi_mcp (auto-convert REST to MCP)** | Minimal code, automatic endpoint conversion | Raw JSON responses (no narrative formatting), no custom resource URIs, limited prompt support | Rejected — narrative formatting is the key differentiator |
| **Standalone MCP server with official SDK** | Full control, shared models, independent scaling, narrative formatting | Additional deployment artifact, separate port | **Selected** |

---

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| MCP protocol version changes break compatibility | Medium | Low | Pin protocol version in server declaration; monitor MCP specification updates |
| High database load from concurrent MCP queries | Medium | Medium | Read-only replica support; connection pooling; response caching for stats/trends |
| API token leakage in MCP client configuration | High | Low | Document secure token storage practices; recommend scoped tokens with limited permissions |
| Formatter output quality varies across result types | Low | Medium | Comprehensive formatter tests with snapshot assertions; iterative refinement based on user feedback |
| Service layer changes in backend break MCP server | Medium | Medium | Shared test fixtures; CI pipeline runs MCP tests alongside backend tests |

---

## Success Metrics

- **M1: Tool coverage** — All 14 tools pass integration tests against a seeded database within 4 weeks of development start.
- **M2: Response quality** — Result interpretation formatters produce actionable narratives (validated through manual review of 10+ sample results per tool type).
- **M3: Auth correctness** — 100% of tenant isolation tests pass; no cross-team data leakage in any tool or resource.
- **M4: Client compatibility** — Successful connection and tool invocation from both Claude Desktop and Claude Code.
- **M5: Adoption signal** — At least 5 unique API tokens used for MCP connections within 30 days of deployment.

---

## Dependencies

### Internal Dependencies

- **Backend service layer** (`backend/src/services/`) — All tools delegate to existing services. Service API changes must be coordinated.
- **SQLAlchemy models** (`backend/src/models/`) — Shared model imports. Model migrations must be applied before MCP server startup.
- **API token service** (`backend/src/services/api_token_service.py`) — Authentication reuse. Token validation logic must remain stable.
- **Trend endpoints** (`backend/src/api/trends/`) — Trend tool relies on existing aggregation queries.

### External Dependencies

- **`mcp` Python SDK** — Official MCP server library (pip installable). Version pinned in `requirements.txt`.
- **Starlette / ASGI server** — HTTP transport layer. `uvicorn` as the ASGI server (already used by the backend).

### New Dependencies

| Package | Purpose | License |
|---------|---------|---------|
| `mcp` | MCP server SDK (tools, resources, prompts, transport) | MIT |

No new GUID prefixes required — the MCP server reads existing entities and does not create new entity types.

---

## Future Enhancements

### v1.1

- **SSE transport fallback** — Add SSE transport option for clients that don't support Streamable HTTP.
- **Result comparison tool** — Compare two analysis results for the same collection side-by-side.
- **Bulk health check** — Single tool call that checks all live collections and returns a prioritized attention list.

### v2.0

- **Sampling support** — Allow the MCP server to request LLM completions from the client for advanced analysis interpretation (MCP sampling capability).
- **Notification subscription** — MCP resource subscriptions for real-time notifications when jobs complete or agents go offline.
- **Pipeline suggestion tool** — Given a collection's file listing, suggest a pipeline configuration that matches the naming conventions.
- **Write operations for events** — Create and update events through MCP for AI-assisted event planning workflows.

---

## Revision History

- **2026-02-18 (v1.0)**: Initial draft
