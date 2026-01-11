# Data Model: User Timezone Display

**Feature Branch**: `010-user-timezone-display`
**Date**: 2026-01-11

## Overview

This feature is **frontend-only** and requires no data model changes. The backend continues to store timestamps in UTC format (ISO 8601), and all timezone conversion happens in the browser during display.

---

## Existing Entities (Unchanged)

The following entities have timestamp fields that will be formatted by the new utility:

### Collection
| Field | Type | Notes |
|-------|------|-------|
| `created_at` | datetime (UTC) | No change - formatted in frontend |
| `updated_at` | datetime (UTC) | No change - formatted in frontend |
| `last_scanned_at` | datetime (UTC) | No change - formatted in frontend |

### Connector
| Field | Type | Notes |
|-------|------|-------|
| `created_at` | datetime (UTC) | No change - formatted in frontend |
| `updated_at` | datetime (UTC) | No change - formatted in frontend |
| `last_validated` | datetime (UTC) | No change - may be null ("Never") |

### Result
| Field | Type | Notes |
|-------|------|-------|
| `created_at` | datetime (UTC) | No change - formatted in frontend |
| `completed_at` | datetime (UTC) | No change - formatted in frontend |

### Job (in-memory)
| Field | Type | Notes |
|-------|------|-------|
| `created_at` | datetime (UTC) | No change - formatted in frontend |
| `updated_at` | datetime (UTC) | No change - formatted in frontend |

---

## API Response Format (Unchanged)

All timestamp fields continue to be serialized as ISO 8601 strings without timezone suffix (implicitly UTC):

```json
{
  "guid": "con_01hgw2bbg0000000000000001",
  "name": "My Connector",
  "created_at": "2026-01-07T15:45:00",
  "updated_at": "2026-01-10T10:30:00",
  "last_validated": null
}
```

The frontend's date formatting utility handles:
- Parsing ISO 8601 strings (treating them as UTC)
- Converting to user's local timezone
- Formatting for display

---

## Frontend Data Types

### New Type: DateFormatOptions

```typescript
// Options for absolute date formatting
interface DateFormatOptions {
  dateStyle?: 'full' | 'long' | 'medium' | 'short'
  timeStyle?: 'full' | 'long' | 'medium' | 'short'
}
```

### Utility Function Signatures

```typescript
// Format date/time with locale awareness
function formatDateTime(
  dateString: string | null | undefined,
  options?: DateFormatOptions
): string

// Format as relative time ("2 hours ago")
function formatRelativeTime(
  dateString: string | null | undefined
): string

// Format date only (no time)
function formatDate(
  dateString: string | null | undefined,
  options?: DateFormatOptions
): string

// Format time only (no date)
function formatTime(
  dateString: string | null | undefined,
  options?: DateFormatOptions
): string
```

---

## No Database Migrations Required

This feature requires no database schema changes. All timestamp storage remains in UTC as currently implemented.
