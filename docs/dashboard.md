# Dashboard

The Dashboard is the landing page of ShutterSense, providing an at-a-glance overview of your photo collection management activity.

## Overview

The Dashboard displays key performance indicators, recent activity, job queue status, and trend summaries to help users quickly assess the state of their collections and processing workflows.

## KPI Cards

The top section shows aggregated statistics across all collections and tools:

| KPI | Description | Source |
|-----|-------------|--------|
| Total Collections | Number of registered collections | `/api/collections/stats` |
| Total Files | Sum of files across all collections | `/api/collections/stats` |
| Active Agents | Number of online agents | `/api/agent/v1/pool-status` |
| Jobs (Last 7 Days) | Jobs completed in the past week | `/api/tools/queue-status` |
| Storage Used | Total storage across collections | `/api/analytics/storage` |
| Issues Found | Total issues from recent analysis | `/api/results/stats` |

KPIs are also displayed in the TopHeader stats area (next to the bell icon) for visibility across all pages. This is managed by the `useHeaderStats` hook and `HeaderStatsContext`.

### Implementation

```typescript
// Frontend: src/contexts/HeaderStatsContext.tsx
const { setStats } = useHeaderStats()

useEffect(() => {
  if (stats) {
    setStats([
      { label: 'Collections', value: stats.total_collections },
      { label: 'Agents', value: stats.agents_online },
      { label: 'Jobs', value: stats.jobs_last_7d },
    ])
  }
  return () => setStats([])
}, [stats, setStats])
```

## Activity Feed

The activity feed shows recent events across the application:

- **Job completions** - Analysis jobs that finished (with result summary)
- **Job failures** - Jobs that encountered errors (with error message)
- **Agent status changes** - Agents coming online or going offline
- **Collection updates** - New collections or configuration changes

The feed is assembled from existing endpoints (`/api/tools/jobs`, `/api/agent/v1/pool-status`, `/api/collections`) and displays the most recent entries with timestamps rendered in the user's local timezone.

## Queue Status

The queue status section shows the current state of the job processing pipeline:

| Status | Description |
|--------|-------------|
| Queued | Jobs waiting for an agent to claim them |
| Running | Jobs currently being executed by agents |
| Completed | Jobs finished in the current session |
| Failed | Jobs that encountered errors |

Data is fetched from `/api/tools/queue-status`. When no agents are available, a warning banner is displayed to inform users that jobs will remain queued.

## Trend Charts

The Dashboard includes summary trend charts powered by [Recharts](https://recharts.org/):

- **Jobs over time** - Bar chart of completed jobs per day/week
- **Issues trend** - Line chart of issues found over time
- **Collection growth** - Area chart of total files over time

Trend data is fetched from `/api/trends` endpoints. Each chart supports date range filtering and can be expanded to the full Trends page for detailed analysis.

## Agent Pool Status

The agent pool indicator shows the health of the distributed processing system:

| State | Indicator | Meaning |
|-------|-----------|---------|
| All Online | Green badge | All registered agents are connected |
| Partial | Yellow badge | Some agents are offline |
| All Offline | Red badge | No agents available for processing |

This indicator appears in both the Dashboard and the application header. When all agents go offline, a `pool_offline` notification is sent to users with push notifications enabled.

## Data Fetching

Dashboard data is fetched using the following hooks and endpoints:

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useHeaderStats` | Multiple | KPI aggregation for header display |
| `useAnalyticsStorage` | `/api/analytics/storage` | Storage metrics |
| `useQueueStatus` | `/api/tools/queue-status` | Job queue state |
| `useTrends` | `/api/trends/*` | Trend chart data |
| `useAgentPoolStatus` | `/api/agent/v1/pool-status` | Agent availability |

All data auto-refreshes on a configurable interval and supports manual refresh via pull-to-refresh on mobile.
