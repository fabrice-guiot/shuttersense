# ShutterSense Architecture

This document describes the high-level architecture of the ShutterSense application.

## System Overview

ShutterSense consists of three main components that work together:

```
┌─────────────────────────────────────────────────────────┐
│                      Browser (SPA)                       │
│                                                          │
│  React 18 + TypeScript + Tailwind CSS                    │
│  PWA with Service Worker for Push Notifications          │
│                                                          │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Auth   │  │  Pages  │  │  Hooks   │  │ Services │  │
│  │ Context │  │ (18)    │  │ (33)     │  │ (21)     │  │
│  └─────────┘  └─────────┘  └──────────┘  └──────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS (API + WebSocket)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │   API    │  │Middleware│  │ Services │               │
│  │ Routes   │  │ (Auth,   │  │ (31+)    │               │
│  │ (140+)   │  │ Tenant)  │  │          │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Models  │  │   SPA    │  │Background│               │
│  │  (25)    │  │ Serving  │  │  Tasks   │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │ Agent API (REST)
           ▼                          ▼
┌──────────────────┐    ┌─────────────────────────────────┐
│   PostgreSQL     │    │      ShutterSense Agent          │
│                  │    │                                   │
│  - Entities      │    │  ┌───────────┐  ┌────────────┐  │
│  - JSONB data    │    │  │  Polling   │  │  Analysis  │  │
│  - GIN indexes   │    │  │  Loop     │  │  Modules   │  │
│                  │    │  └───────────┘  └────────────┘  │
│                  │    │  ┌───────────┐  ┌────────────┐  │
│                  │    │  │  Storage  │  │   Local    │  │
│                  │    │  │  Adapters │  │   Cache    │  │
│                  │    │  └───────────┘  └────────────┘  │
└──────────────────┘    └─────────────────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  Photo Storage   │
                        │  (Local, S3,     │
                        │   GCS, SMB)      │
                        └──────────────────┘
```

## Request Flow

### Web Application Requests

```
Browser → FastAPI Router → Auth Middleware → Tenant Middleware → Service → SQLAlchemy → PostgreSQL
                                                                   │
                                                                   ▼
Browser ← JSON Response ← Pydantic Schema ← Service Result ───────┘
```

1. **Browser** sends HTTP request to FastAPI
2. **Auth Middleware** validates session cookie or API token
3. **Tenant Middleware** extracts `team_id` and creates `TenantContext`
4. **Router** dispatches to appropriate endpoint handler
5. **Service** executes business logic with `team_id` scoping
6. **SQLAlchemy** queries PostgreSQL with tenant filter
7. **Pydantic** serializes response (GUIDs, not internal IDs)

### Job Execution Flow

```
1. User creates job        →  Server queues job (status: PENDING)
2. Agent polls /jobs/claim →  Server assigns job (status: ASSIGNED)
3. Agent executes tool     →  Agent reports progress via REST
4. Agent uploads results   →  Server stores results (status: COMPLETED)
5. Server sends notification → User sees result in UI
```

Detailed sequence:

```
User (Browser)          Backend Server           Agent
     │                       │                     │
     │  POST /api/tools/run  │                     │
     │──────────────────────►│                     │
     │                       │ Create Job           │
     │                       │ (PENDING)            │
     │  202 Accepted         │                     │
     │◄──────────────────────│                     │
     │                       │                     │
     │                       │ POST /agent/v1/     │
     │                       │   jobs/claim        │
     │                       │◄────────────────────│
     │                       │ Assign Job           │
     │                       │ (ASSIGNED → RUNNING) │
     │                       │────────────────────►│
     │                       │                     │ Execute
     │                       │                     │ Analysis
     │                       │ POST progress       │
     │                       │◄────────────────────│
     │  WebSocket update     │                     │
     │◄──────────────────────│                     │
     │                       │                     │
     │                       │ POST complete       │
     │                       │◄────────────────────│
     │                       │ Store Results        │
     │                       │ Send Notification    │
     │  Push Notification    │                     │
     │◄──────────────────────│                     │
```

## Multi-Tenancy Model

All data is scoped to a Team. Every authenticated request carries a `TenantContext`:

```python
@router.get("/collections")
async def list_collections(ctx: TenantContext = Depends(get_tenant_context)):
    # ctx.team_id is automatically extracted from the authenticated user
    # All queries MUST filter by team_id
    return service.list_collections(team_id=ctx.team_id)
```

- Each User belongs to exactly one Team
- A default personal Team is created for solo users
- Cross-team access returns 404 (not 403) to prevent information leakage
- All services accept and enforce `team_id` parameter

## Authentication Flow

### OAuth 2.0 PKCE Flow

```
Browser                  Backend                 OAuth Provider
   │                       │                          │
   │  GET /api/auth/       │                          │
   │    google/login       │                          │
   │──────────────────────►│                          │
   │                       │  Generate PKCE params    │
   │  302 Redirect         │                          │
   │◄──────────────────────│                          │
   │                       │                          │
   │  User authenticates   │                          │
   │──────────────────────────────────────────────────►│
   │                       │                          │
   │  Callback with code   │                          │
   │──────────────────────►│                          │
   │                       │  Exchange code for       │
   │                       │  tokens                  │
   │                       │─────────────────────────►│
   │                       │                          │
   │                       │  User info               │
   │                       │◄─────────────────────────│
   │                       │                          │
   │                       │  Create/update User      │
   │                       │  Set session cookie      │
   │  302 Redirect to SPA  │                          │
   │◄──────────────────────│                          │
```

### API Token Authentication

Agents and programmatic clients use Bearer token authentication:

```
Agent                    Backend
  │                        │
  │  POST /agent/v1/       │
  │  register              │
  │  (with one-time token) │
  │───────────────────────►│
  │                        │  Create Agent + API key
  │  { api_key: "..." }    │
  │◄───────────────────────│
  │                        │
  │  Authorization:        │
  │  Bearer <api_key>      │
  │───────────────────────►│
  │                        │  Validate token
  │                        │  Extract team_id
  │  Response              │
  │◄───────────────────────│
```

## WebSocket Protocol

Real-time progress updates use WebSocket connections:

- `/api/tools/ws/jobs/all` - All job progress updates for the team
- `/api/tools/ws/jobs/{job_id}` - Single job progress
- `/api/agent/v1/pool-status` - Agent pool status (WebSocket)

Messages are JSON-encoded with type discriminators:

```json
{
  "type": "job_progress",
  "job_id": "job_01hgw...",
  "progress": 75,
  "message": "Processing file 750/1000"
}
```

## SPA Serving Architecture

In production, FastAPI serves both the API and the React SPA from the same server:

```
                    ┌──────────────────────────┐
                    │       FastAPI Server      │
                    │                          │
  /api/*     ───►   │  API Routes (JSON)       │
  /health    ───►   │  Health Check            │
  /docs      ───►   │  OpenAPI Documentation   │
  /assets/*  ───►   │  Static Assets (dist/)   │
  /*         ───►   │  index.html (SPA)        │
                    └──────────────────────────┘
```

- Static assets are served from `frontend/dist/assets/`
- All non-API, non-static routes serve `index.html` for client-side routing
- Configurable via `SHUSAI_SPA_DIST_PATH` environment variable

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18, TypeScript 5.9, Tailwind CSS 4.x | UI framework |
| UI Components | shadcn/ui, Radix UI, Lucide React | Component library |
| Build | Vite 6, Vitest | Build and test tooling |
| Backend | FastAPI, Python 3.10+ | API framework |
| ORM | SQLAlchemy 2.0, Alembic | Database access and migrations |
| Database | PostgreSQL 12+ | Primary data store |
| Auth | Authlib (OAuth), PyJWT (tokens) | Authentication |
| Agent | Click (CLI), httpx (HTTP), websockets | Distributed executor |
| Storage | boto3 (S3), google-cloud-storage (GCS) | Cloud storage access |
| Encryption | cryptography (Fernet) | Credential encryption |
| Notifications | pywebpush | Web Push notifications |

## Background Tasks

The backend runs periodic background tasks:

1. **Dead Agent Safety Net** (every 120s) - Marks unresponsive agents as offline and triggers pool status notifications
2. **Deadline Check Scheduler** (every 3600s) - Sends reminder notifications for approaching event deadlines

## Key Design Decisions

1. **Agent-only execution** - The server never executes analysis tools directly. All jobs are dispatched to agents, ensuring the server remains lightweight and agents can access local storage.

2. **GUID-based APIs** - All external identifiers use `{prefix}_{crockford_base32}` format. Internal numeric IDs are never exposed in APIs.

3. **Single-server deployment** - The SPA is served from FastAPI, simplifying deployment (no separate web server needed for the frontend).

4. **Team-scoped everything** - Every query includes `team_id` filtering. There is no global data access except for super admin endpoints.

5. **Offline-capable agents** - Agents can execute jobs offline and sync results later, supporting disconnected environments.
