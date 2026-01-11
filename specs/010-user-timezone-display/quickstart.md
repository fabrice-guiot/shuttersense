# Quickstart: User Timezone Display

**Feature Branch**: `010-user-timezone-display`
**Date**: 2026-01-11

## Overview

This guide shows how to use the centralized date formatting utility in the photo-admin frontend.

---

## Installation

No installation required - the utility uses native browser Intl APIs with no external dependencies.

---

## Usage

### Import the Utility

```typescript
import { formatDateTime, formatRelativeTime, formatDate, formatTime } from '@/utils/dateFormat'
```

### Format Date with Time

```typescript
// Default format: "Jan 7, 2026, 3:45 PM"
formatDateTime('2026-01-07T15:45:00')

// Custom format options
formatDateTime('2026-01-07T15:45:00', { dateStyle: 'full', timeStyle: 'long' })
// Result: "Saturday, January 7, 2026 at 3:45:00 PM EST"
```

### Format Relative Time

```typescript
// Automatically displays human-friendly relative times
formatRelativeTime('2026-01-07T15:45:00')
// If current time is Jan 7, 2026, 6:00 PM → "2 hours ago"
// If current time is Jan 8, 2026, 9:00 AM → "yesterday"
// If current time is Jan 21, 2026 → Absolute date shown
```

### Format Date Only (No Time)

```typescript
// Default format: "Jan 7, 2026"
formatDate('2026-01-07T15:45:00')

// Short format: "1/7/26"
formatDate('2026-01-07T15:45:00', { dateStyle: 'short' })
```

### Format Time Only (No Date)

```typescript
// Default format: "3:45 PM"
formatTime('2026-01-07T15:45:00')
```

### Handle Null/Undefined Values

```typescript
// All functions gracefully handle null/undefined
formatDateTime(null)       // Returns: "Never"
formatDateTime(undefined)  // Returns: "Never"
formatRelativeTime(null)   // Returns: "Never"
```

---

## Component Migration Examples

### Before (Inline Function)

```typescript
// Old pattern - inline helper function
const formatDate = (dateString: string | undefined) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

// In JSX
<span>{formatDate(connector.created_at)}</span>
```

### After (Centralized Utility)

```typescript
import { formatDateTime } from '@/utils/dateFormat'

// In JSX - no local helper needed
<span>{formatDateTime(connector.created_at)}</span>
```

### Using Relative Time

```typescript
import { formatRelativeTime } from '@/utils/dateFormat'

// Shows "2 hours ago", "yesterday", etc.
<span>{formatRelativeTime(connector.last_validated)}</span>
```

---

## Format Options Reference

### dateStyle Options

| Value | Example Output |
|-------|----------------|
| `'full'` | Saturday, January 7, 2026 |
| `'long'` | January 7, 2026 |
| `'medium'` | Jan 7, 2026 |
| `'short'` | 1/7/26 |

### timeStyle Options

| Value | Example Output |
|-------|----------------|
| `'full'` | 3:45:00 PM Eastern Standard Time |
| `'long'` | 3:45:00 PM EST |
| `'medium'` | 3:45:30 PM |
| `'short'` | 3:45 PM |

---

## Testing

### Run Unit Tests

```bash
cd frontend
npm test -- tests/utils/dateFormat.test.ts
```

### Test with Different Timezones

```bash
# Run tests with mocked timezone
TZ=America/New_York npm test
TZ=Europe/London npm test
TZ=Asia/Tokyo npm test
```

---

## Troubleshooting

### Dates Show in UTC Instead of Local Time

Ensure the date string is being parsed correctly. The utility expects ISO 8601 format:

```typescript
// Correct: ISO 8601 format (no timezone suffix = UTC)
formatDateTime('2026-01-07T15:45:00')

// Also correct: with explicit UTC
formatDateTime('2026-01-07T15:45:00Z')

// Incorrect: ambiguous formats
formatDateTime('01/07/2026 3:45 PM')  // May not parse correctly
```

### "Invalid date" Displayed

The input string could not be parsed as a valid date. Check the API response format.

### "Never" Displayed When Value Exists

The value might be an empty string. Check if the API returns `""` instead of `null` for unset dates.
