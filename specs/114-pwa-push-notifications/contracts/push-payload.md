# Push Notification Payload Contract

**Feature Branch**: `114-pwa-push-notifications`

## Push Payload Schema

All push notifications delivered to the service worker use this JSON payload structure:

```json
{
  "title": "string (required, max 100 chars)",
  "body": "string (required, max 500 chars)",
  "icon": "/icons/icon-192x192.png",
  "badge": "/icons/badge-72x72.png",
  "tag": "string (optional, prevents duplicate display)",
  "data": {
    "url": "string (required, in-app navigation path)",
    "category": "string (notification category)",
    "notification_guid": "string (ntf_ GUID for mark-as-read)"
  }
}
```

## Category-Specific Payloads

### Job Failure

```json
{
  "title": "Analysis Failed",
  "body": "{tool_name} analysis of \"{collection_name}\" failed: {error_summary}",
  "tag": "job_failure_{job_guid}",
  "data": {
    "url": "/tools?job={job_guid}",
    "category": "job_failure",
    "notification_guid": "ntf_xxx",
    "job_guid": "job_xxx",
    "collection_guid": "col_xxx"
  }
}
```

### Inflection Point

```json
{
  "title": "New Analysis Results",
  "body": "{tool_name} found changes in \"{collection_name}\": {issue_delta_summary}",
  "tag": "inflection_point_{result_guid}",
  "data": {
    "url": "/collections/{collection_guid}/results/{result_guid}",
    "category": "inflection_point",
    "notification_guid": "ntf_xxx",
    "result_guid": "res_xxx",
    "collection_guid": "col_xxx"
  }
}
```

### Agent Pool Offline

```json
{
  "title": "Agent Pool Offline",
  "body": "All agents are offline. Jobs cannot be processed until an agent reconnects.",
  "tag": "agent_pool_offline_{team_guid}",
  "data": {
    "url": "/agents",
    "category": "agent_status",
    "notification_guid": "ntf_xxx"
  }
}
```

### Agent Error

```json
{
  "title": "Agent Error",
  "body": "Agent \"{agent_name}\" reported an error: {error_description}",
  "tag": "agent_error_{agent_guid}",
  "data": {
    "url": "/agents/{agent_guid}",
    "category": "agent_status",
    "notification_guid": "ntf_xxx",
    "agent_guid": "agt_xxx"
  }
}
```

### Agent Recovery

```json
{
  "title": "Agents Available",
  "body": "Agent \"{agent_name}\" is back online. Job processing has resumed.",
  "tag": "agent_recovery_{team_guid}",
  "data": {
    "url": "/agents",
    "category": "agent_status",
    "notification_guid": "ntf_xxx"
  }
}
```

### Deadline Reminder

```json
{
  "title": "Deadline Approaching",
  "body": "\"{event_name}\" deadline in {days_remaining} days",
  "tag": "deadline_{event_guid}_{days_before}",
  "data": {
    "url": "/events/{event_guid}",
    "category": "deadline",
    "notification_guid": "ntf_xxx",
    "event_guid": "evt_xxx"
  }
}
```

### Retry Warning

```json
{
  "title": "Job Retry Warning",
  "body": "{tool_name} analysis of \"{collection_name}\" is on final retry attempt",
  "tag": "retry_warning_{job_guid}",
  "data": {
    "url": "/tools?job={job_guid}",
    "category": "retry_warning",
    "notification_guid": "ntf_xxx",
    "job_guid": "job_xxx",
    "collection_guid": "col_xxx"
  }
}
```

## Tag Deduplication

The `tag` field prevents duplicate notifications from being displayed. If a push notification arrives with the same tag as an existing displayed notification, the existing one is replaced. This handles:

- Multiple retries of the same job failure delivery
- Rapid agent status changes (debounced at server, tag as safety net)

## Service Worker Handling

The service worker processes the push payload as follows:

1. Parse `event.data.json()` to extract the payload
2. Call `self.registration.showNotification(title, { body, icon, badge, tag, data })`
3. On `notificationclick`: extract `data.url` and navigate/focus the appropriate window
