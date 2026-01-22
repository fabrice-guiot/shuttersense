# WebSocket Protocol: Agent Progress Streaming

**Feature**: 021-distributed-agent-architecture
**Created**: 2026-01-18

---

## Overview

Agents use WebSocket connections to stream real-time progress updates during job execution. The server proxies these updates to frontend clients, maintaining the existing real-time UX.

## Connection

### URL Format

```
wss://{server_url}/ws/agent/jobs/{job_guid}/progress?token={api_key}
```

### Authentication

Query parameter: `token={agent_api_key}`

### Connection Lifecycle

1. Agent claims job via REST (`POST /jobs/claim`)
2. Agent opens WebSocket connection
3. Server validates agent and job ownership
4. Agent streams progress updates
5. Agent closes WebSocket after completion
6. Agent reports final results via REST (`POST /jobs/{guid}/complete`)

---

## Message Format

All messages are JSON with the following structure:

```json
{
  "type": "message_type",
  "timestamp": "2026-01-18T12:00:00.000Z",
  "data": { ... }
}
```

---

## Agent → Server Messages

### Progress Update

Sent during job execution to report progress.

```json
{
  "type": "progress",
  "timestamp": "2026-01-18T12:00:05.123Z",
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

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| stage | string | Yes | Current execution stage |
| percentage | integer | Yes | Progress 0-100 |
| files_scanned | integer | No | Files processed so far |
| total_files | integer | No | Total files to process |
| current_file | string | No | Current file being processed |
| message | string | No | Human-readable status message |

**Stages**:
- `initializing` - Setting up job execution
- `scanning` - Scanning filesystem
- `analyzing` - Processing files
- `generating_report` - Creating HTML report
- `uploading` - Uploading results

### Stage Transition

Sent when moving to a new execution stage.

```json
{
  "type": "stage",
  "timestamp": "2026-01-18T12:01:00.000Z",
  "data": {
    "previous_stage": "scanning",
    "current_stage": "analyzing",
    "message": "Analyzing 2741 files..."
  }
}
```

### Warning (Non-Fatal Error)

Sent when an error occurs that doesn't stop execution.

```json
{
  "type": "warning",
  "timestamp": "2026-01-18T12:01:30.000Z",
  "data": {
    "message": "Could not read EXIF from IMG_5678.jpg",
    "file": "IMG_5678.jpg",
    "error_type": "exif_read_error"
  }
}
```

### Pong (Keep-Alive Response)

Response to server ping.

```json
{
  "type": "pong",
  "timestamp": "2026-01-18T12:02:30.050Z"
}
```

---

## Server → Agent Messages

### Cancellation Request

Sent when user requests job cancellation.

```json
{
  "type": "cancel",
  "timestamp": "2026-01-18T12:02:00.000Z",
  "data": {
    "reason": "User requested cancellation"
  }
}
```

Agent should:
1. Stop execution gracefully
2. Close WebSocket connection
3. Report status via REST with `status: "cancelled"`

### Ping (Keep-Alive)

Sent every 30 seconds to verify connection health.

```json
{
  "type": "ping",
  "timestamp": "2026-01-18T12:02:30.000Z"
}
```

Agent must respond with `pong` within 10 seconds.

---

## Server Proxying to Frontend

The server proxies agent progress to frontend WebSocket channels.

### Frontend Channel: Job-Specific

URL: `/ws/jobs/{job_guid}`

Messages:
```json
{
  "type": "job_progress",
  "job_guid": "job_01hgw2bbg...",
  "progress": {
    "stage": "analyzing",
    "percentage": 67,
    "files_scanned": 1800,
    "total_files": 2741,
    "message": "Analyzing files..."
  }
}
```

### Frontend Channel: Global Job Feed

URL: `/ws/jobs/all`

Same message format as job-specific, for dashboard views.

### Job Completion Broadcast

When job completes (via REST):
```json
{
  "type": "job_completed",
  "job_guid": "job_01hgw2bbg...",
  "status": "completed",
  "result_guid": "res_01hgw2bbg..."
}
```

---

## Connection Error Handling

### Agent-Side Errors

| Error | Action |
|-------|--------|
| Connection refused | Retry with exponential backoff (5s, 10s, 20s, max 60s) |
| Connection dropped | Attempt reconnect (3 times), then fallback to REST |
| Auth failure (4001) | Log error and stop (requires manual intervention) |
| Job not found (4004) | Abort job, report as failed |

### Server-Side Handling

| Condition | Action |
|-----------|--------|
| Agent disconnects during job | Wait 30s, mark agent offline, release job |
| No pong for 30s | Close connection, mark agent offline |
| Invalid message format | Log warning, ignore message |

---

## REST Fallback

If WebSocket is unavailable (firewall, proxy issues), agent falls back to REST:

```http
POST /api/agent/v1/jobs/{job_guid}/progress
Authorization: Bearer agt_key_xxxxx
Content-Type: application/json

{
  "stage": "scanning",
  "percentage": 45,
  "files_scanned": 1234,
  "message": "Scanning files..."
}
```

Response:
```json
{
  "acknowledged": true,
  "cancelled": false
}
```

**Fallback Behavior**:
- Try WebSocket first (3 connection attempts)
- If all fail, switch to REST mode
- REST updates sent every 2-5 seconds
- Check `cancelled` field to detect user cancellation

---

## Header Agent Pool Status

### Frontend WebSocket Channel

URL: `/ws/agents/pool-status`

The server broadcasts agent pool status changes:

```json
{
  "type": "pool_status",
  "timestamp": "2026-01-18T12:00:00.000Z",
  "data": {
    "online_count": 3,
    "idle_count": 2,
    "running_jobs_count": 1,
    "status": "running"
  }
}
```

**Status Values**:
| Value | Condition | Badge Color |
|-------|-----------|-------------|
| `offline` | online_count = 0 | Red |
| `idle` | online_count > 0 AND running_jobs_count = 0 | Blue |
| `running` | running_jobs_count > 0 | Green |

**Triggers**:
- Agent comes online (heartbeat after offline)
- Agent goes offline (90s without heartbeat)
- Job starts executing (status → RUNNING)
- Job completes/fails (status → COMPLETED/FAILED)

---

## Message Flow Example

```
Agent                          Server                         Frontend
  │                              │                               │
  │ POST /jobs/claim             │                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ Job assignment + WS URL      │                               │
  │<─────────────────────────────│                               │
  │                              │                               │
  │ WS Connect /ws/agent/jobs/xxx│                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ WS Connection accepted       │                               │
  │<─────────────────────────────│                               │
  │                              │                               │
  │ {"type":"progress",...}      │                               │
  │─────────────────────────────>│ Proxy to /ws/jobs/xxx        │
  │                              │──────────────────────────────>│
  │                              │                               │
  │ {"type":"progress",...}      │                               │
  │─────────────────────────────>│ Proxy to /ws/jobs/xxx        │
  │                              │──────────────────────────────>│
  │                              │                               │
  │ {"type":"ping"}              │                               │
  │<─────────────────────────────│                               │
  │                              │                               │
  │ {"type":"pong"}              │                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ WS Close                     │                               │
  │─────────────────────────────>│                               │
  │                              │                               │
  │ POST /jobs/xxx/complete      │                               │
  │─────────────────────────────>│ Broadcast job_completed      │
  │                              │──────────────────────────────>│
  │                              │                               │
  │ {"result_guid":"res_xxx"}    │                               │
  │<─────────────────────────────│                               │
```
