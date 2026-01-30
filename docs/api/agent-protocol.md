# Agent-Server Protocol

This document describes the communication protocol between ShutterSense agents and the backend server.

## Overview

Agents are lightweight binaries that run on user machines and execute photo analysis jobs. They communicate with the server via a REST API at `/api/agent/v1/`.

## Agent Registration

### Prerequisites

1. A registration token generated from the web UI (Settings > Agents > Generate Token)
2. Network access to the ShutterSense server

### Registration Flow

```
Agent                              Server
  │                                  │
  │  POST /api/agent/v1/register     │
  │  { token, name, hostname, os }   │
  │─────────────────────────────────►│
  │                                  │ Validate one-time token
  │                                  │ Create Agent record
  │                                  │ Generate API key
  │  { agent_guid, api_key }         │
  │◄─────────────────────────────────│
  │                                  │
  │  Store api_key locally           │
  │  (encrypted credential store)    │
```

### Registration Endpoint

```
POST /api/agent/v1/register
```

**Request:**
```json
{
  "token": "art_01hgw2bbg...",
  "name": "My Agent",
  "hostname": "workstation.local",
  "os_info": "macOS 15.2 (arm64)",
  "version": "v1.2.3",
  "capabilities": {
    "tools": ["photostats", "photo_pairing", "pipeline_validation"],
    "connectors": ["local", "s3"]
  }
}
```

**Response:**
```json
{
  "agent_guid": "agt_01hgw2bbg...",
  "api_key": "tok_...",
  "team_guid": "tea_01hgw2bbg..."
}
```

The `api_key` is shown only once. The agent stores it in its local encrypted credential store.

## Agent Polling Loop

After registration, the agent enters a polling loop:

```
┌──────────────────────────────────────────────┐
│                 Polling Loop                  │
│                                               │
│  1. POST /heartbeat                           │
│  2. POST /jobs/claim                          │
│     ├── No job → sleep(interval) → goto 1     │
│     └── Job claimed → execute                 │
│         ├── POST /jobs/{guid}/progress (N×)  │
│         ├── POST /uploads/initiate (if large) │
│         │   ├── PUT /uploads/{id}/{chunk}     │
│         │   └── POST /uploads/{id}/finalize   │
│         ├── POST /jobs/{guid}/complete        │
│         └── POST /jobs/{guid}/fail            │
│  3. goto 1                                    │
└──────────────────────────────────────────────┘
```

## Job Lifecycle

```
SCHEDULED → PENDING → ASSIGNED → RUNNING → COMPLETED
                                         → FAILED
                                         → CANCELLED
```

| Status | Description | Set By |
|--------|-------------|--------|
| `SCHEDULED` | Job created, waiting for scheduling | Server |
| `PENDING` | Ready for agent pickup | Server |
| `ASSIGNED` | Claimed by an agent | Server (on claim) |
| `RUNNING` | Agent is executing the job | Agent (on first progress) |
| `COMPLETED` | Job finished successfully | Agent |
| `FAILED` | Job encountered an error | Agent or Server |
| `CANCELLED` | Job cancelled by user | Server |

## Endpoint Reference

All endpoints require `Authorization: Bearer <api_key>` header (except `register` which uses a one-time token).

### POST /api/agent/v1/register

Register a new agent. Uses a one-time registration token.

### POST /api/agent/v1/heartbeat

Send periodic heartbeat. The server marks agents as offline if heartbeats stop.

**Request:**
```json
{
  "version": "v1.2.3",
  "load": {
    "active_jobs": 1,
    "max_concurrent": 4
  }
}
```

### GET /api/agent/v1/me

Get the current agent's information.

### POST /api/agent/v1/disconnect

Gracefully disconnect the agent. Sets status to OFFLINE.

### POST /api/agent/v1/jobs/claim

Attempt to claim a queued job. Returns `204 No Content` if no jobs are available.

**Request:**
```json
{
  "capabilities": {
    "tools": ["photostats", "photo_pairing", "pipeline_validation"],
    "connectors": ["local", "s3"]
  }
}
```

**Response (200):**
```json
{
  "job_guid": "job_01hgw2bbg...",
  "tool": "photostats",
  "collection_guid": "col_01hgw2bbg...",
  "collection_type": "LOCAL",
  "collection_location": "/photos/2026",
  "pipeline_guid": "pip_01hgw2bbg...",
  "pipeline_version": 3
}
```

### POST /api/agent/v1/jobs/{guid}/progress

Report execution progress.

**Request:**
```json
{
  "progress_percent": 45,
  "message": "Scanning files: 450/1000",
  "files_scanned": 450,
  "issues_found": 3
}
```

### POST /api/agent/v1/jobs/{guid}/no-change

Report that analysis detected no changes since the last run. The server may skip result storage.

### POST /api/agent/v1/jobs/{guid}/complete

Complete the job with results.

**Request:**
```json
{
  "results_json": { ... },
  "report_html": "<html>...</html>",
  "files_scanned": 1000,
  "issues_found": 12,
  "duration_seconds": 45.2
}
```

For large payloads, use chunked upload instead (see below).

### POST /api/agent/v1/jobs/{guid}/fail

Report job failure.

**Request:**
```json
{
  "error_message": "Collection path not accessible: /photos/2026",
  "duration_seconds": 1.5
}
```

### GET /api/agent/v1/jobs/{guid}/config

Get tool-specific configuration for a job (pipeline definition, team config, etc.).

### GET /api/agent/v1/config

Get the team's configuration (photo extensions, camera mappings, processing methods).

## Chunked Upload

For large results (HTML reports can be several MB), the agent uses chunked upload:

```
1. POST /api/agent/v1/jobs/{guid}/uploads/initiate
   → { upload_id, chunk_size }

2. PUT /api/agent/v1/uploads/{upload_id}/{chunk_index}
   (binary chunk data)
   → repeat for each chunk

3. GET /api/agent/v1/uploads/{upload_id}/status
   → { chunks_received, total_chunks }

4. POST /api/agent/v1/uploads/{upload_id}/finalize
   → { success: true }
```

To cancel an upload: `DELETE /api/agent/v1/uploads/{upload_id}`

## Heartbeat Mechanism

- Agents send heartbeats every **30 seconds**
- The server considers an agent offline after **120 seconds** without a heartbeat
- A background task (`dead_agent_safety_net`) runs every 120 seconds to detect dead agents
- When all agents go offline, a `pool_offline` notification is sent

## Credential Handling

- **Server-side credentials** (S3, GCS, SMB connector credentials) are stored encrypted on the server
- When an agent needs to access a remote collection, it either:
  - Has locally configured connector credentials (`shuttersense-agent connectors configure`)
  - Or receives temporary credentials via the job configuration endpoint
- **Agent API key** is stored locally in the agent's encrypted credential store

## Tool Implementation

Agents include three analysis tools:

| Tool | Module | Description |
|------|--------|-------------|
| `photostats` | `agent/src/analysis/photostats_analyzer.py` | File statistics, orphan detection |
| `photo_pairing` | `agent/src/analysis/photo_pairing_analyzer.py` | Filename pattern grouping |
| `pipeline_validation` | `agent/src/analysis/pipeline_analyzer.py` | Pipeline compliance checking |

For adding new tools, see the [Tool Implementation Pattern](../tool-implementation-pattern.md) specification.
