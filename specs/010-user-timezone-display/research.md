# Research: User Timezone Display

**Feature Branch**: `010-user-timezone-display`
**Date**: 2026-01-11

## Overview

This document captures research findings for implementing browser-based timezone display in the photo-admin frontend. The feature uses native browser Intl APIs for locale-aware date formatting.

---

## Research Topics

### 1. Current Date Formatting in Codebase

**Decision**: Replace all inline date formatting with centralized utility

**Findings**:

| Component | Current Pattern | Location |
|-----------|-----------------|----------|
| ConnectorList.tsx | `formatDate()` helper → `toLocaleString()` | Line ~45 |
| ResultsTable.tsx | `formatDate()` helper → `toLocaleString()` | Inline |
| ResultDetailPanel.tsx | `formatDate()` helper → `toLocaleString()` | Inline |
| JobProgressCard.tsx | `formatDate()` helper → `toLocaleString()` | Inline |
| PipelineCard.tsx | `toLocaleDateString('en-US', {...})` | Inline |
| TrendChart.tsx | `toLocaleDateString('en-US', {...})` | Inline |
| TrendSummaryCard.tsx | `toLocaleDateString()` | Inline |
| PipelineValidationTrend.tsx | `toLocaleString()` | Inline |

**Issues Identified**:
- 4 components have internal `formatDate()` helper functions (code duplication)
- 3 components use inline formatting (inconsistent)
- Some hardcode `'en-US'` locale, others use browser default
- No handling for null/undefined dates
- No relative time formatting

**Rationale**: A single centralized utility eliminates duplication, ensures consistency, and provides a single place to add features like relative time and null handling.

---

### 2. Intl.DateTimeFormat Best Practices

**Decision**: Use `Intl.DateTimeFormat` with default browser locale

**API Overview**:
```typescript
// Basic usage - uses browser's default locale
new Intl.DateTimeFormat().format(date)

// With options
new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short'
}).format(date)

// Get user's timezone
Intl.DateTimeFormat().resolvedOptions().timeZone
// Returns: "America/New_York", "Europe/London", etc.
```

**Format Options**:

| Option | Values | Result Example |
|--------|--------|----------------|
| `dateStyle: 'full'` | - | "Saturday, January 7, 2026" |
| `dateStyle: 'long'` | - | "January 7, 2026" |
| `dateStyle: 'medium'` | - | "Jan 7, 2026" |
| `dateStyle: 'short'` | - | "1/7/26" |
| `timeStyle: 'short'` | - | "3:45 PM" |
| `timeStyle: 'medium'` | - | "3:45:30 PM" |

**Recommended Default** (per PRD):
```typescript
{
  dateStyle: 'medium',
  timeStyle: 'short'
}
// Result: "Jan 7, 2026, 3:45 PM"
```

**Browser Support**:
| Browser | Intl.DateTimeFormat | Required Version |
|---------|---------------------|------------------|
| Chrome | Full support | 24+ |
| Firefox | Full support | 29+ |
| Safari | Full support | 10+ |
| Edge | Full support | 12+ |

**Rationale**: Native Intl APIs are well-supported, avoid external dependencies, and automatically handle locale and timezone conversion.

---

### 3. Relative Time Formatting (Intl.RelativeTimeFormat)

**Decision**: Use `Intl.RelativeTimeFormat` with manual time unit calculation

**API Overview**:
```typescript
const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

rtf.format(-1, 'day')    // "yesterday"
rtf.format(-2, 'day')    // "2 days ago"
rtf.format(-1, 'hour')   // "1 hour ago"
rtf.format(-30, 'minute') // "30 minutes ago"
```

**Numeric Options**:
- `numeric: 'always'` → "1 day ago", "2 days ago"
- `numeric: 'auto'` → "yesterday", "2 days ago" (more natural)

**Time Unit Selection Algorithm**:
```typescript
function getRelativeTimeUnit(diffMs: number): { value: number; unit: Intl.RelativeTimeFormatUnit } {
  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)
  const months = Math.floor(days / 30)
  const years = Math.floor(days / 365)

  if (years !== 0) return { value: -years, unit: 'year' }
  if (months !== 0) return { value: -months, unit: 'month' }
  if (weeks !== 0) return { value: -weeks, unit: 'week' }
  if (days !== 0) return { value: -days, unit: 'day' }
  if (hours !== 0) return { value: -hours, unit: 'hour' }
  if (minutes !== 0) return { value: -minutes, unit: 'minute' }
  return { value: -seconds, unit: 'second' }
}
```

**Browser Support**:
| Browser | Intl.RelativeTimeFormat | Required Version |
|---------|-------------------------|------------------|
| Chrome | Full support | 71+ |
| Firefox | Full support | 65+ |
| Safari | Full support | 14+ |
| Edge | Full support | 79+ |

**Threshold Decision**: Display relative time for dates within 7 days, absolute for older dates.

**Rationale**: `numeric: 'auto'` provides natural language ("yesterday" vs "1 day ago"). 7-day threshold balances human-friendliness with precision.

**Alternatives Considered**:
- **date-fns**: Rejected - adds ~6KB dependency, Intl API sufficient
- **dayjs**: Rejected - adds external dependency, Intl API sufficient
- **moment.js**: Rejected - large bundle size, deprecated

---

### 4. Null/Invalid Date Handling

**Decision**: Return "Never" for null/undefined, graceful fallback for invalid dates

**Implementation Strategy**:
```typescript
export function formatDateTime(
  dateString: string | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  // Handle null/undefined
  if (!dateString) return 'Never'

  // Attempt to parse
  const date = new Date(dateString)

  // Handle invalid dates
  if (isNaN(date.getTime())) return 'Invalid date'

  // Format with Intl
  try {
    return new Intl.DateTimeFormat(undefined, options).format(date)
  } catch {
    // Fallback for unsupported options
    return date.toLocaleString()
  }
}
```

**Edge Cases**:
| Input | Output |
|-------|--------|
| `null` | "Never" |
| `undefined` | "Never" |
| `""` (empty string) | "Never" |
| `"invalid"` | "Invalid date" |
| `"2026-13-45"` | "Invalid date" |
| Valid ISO string | Formatted date |

**Rationale**: "Never" is user-friendly for fields like "last_validated" that may genuinely have never occurred. "Invalid date" signals a data issue without crashing.

---

### 5. Fallback Strategy

**Decision**: Use `toLocaleString()` as fallback when Intl APIs unavailable

**Detection**:
```typescript
function hasIntlSupport(): boolean {
  return typeof Intl !== 'undefined'
    && typeof Intl.DateTimeFormat !== 'undefined'
}

function hasRelativeTimeSupport(): boolean {
  return typeof Intl !== 'undefined'
    && typeof Intl.RelativeTimeFormat !== 'undefined'
}
```

**Fallback Implementation**:
```typescript
if (!hasIntlSupport()) {
  return date.toLocaleString()
}
```

**Rationale**: Modern browser requirements (Chrome 71+, etc.) mean fallback is rarely needed, but provides graceful degradation for edge cases.

---

### 6. Testing Strategy

**Decision**: Comprehensive unit tests with timezone and locale mocking

**Test Categories**:
1. **formatDateTime tests**
   - Valid ISO 8601 strings
   - Null/undefined inputs
   - Invalid date strings
   - Custom format options

2. **formatRelativeTime tests**
   - Just now (< 1 minute)
   - Minutes ago
   - Hours ago
   - Days ago / yesterday
   - Weeks ago
   - Months ago
   - Years ago
   - Threshold behavior (switch to absolute)

3. **formatDate tests** (date only)
4. **formatTime tests** (time only)
5. **Locale tests** (en-US, fr-FR, de-DE)
6. **Edge cases** (year boundaries, DST transitions)

**Mocking Strategy**:
```typescript
// Mock current time for relative time tests
vi.useFakeTimers()
vi.setSystemTime(new Date('2026-01-11T12:00:00Z'))

// Reset after tests
vi.useRealTimers()
```

**Coverage Target**: 90%+ per NFR-004

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Date library | Native Intl APIs | No external dependencies, full browser support |
| Locale detection | Browser default (`undefined`) | Automatic, user-appropriate |
| Default format | `dateStyle: 'medium', timeStyle: 'short'` | "Jan 7, 2026, 3:45 PM" - readable, concise |
| Relative time | Intl.RelativeTimeFormat with `numeric: 'auto'` | Natural language ("yesterday") |
| Relative threshold | 7 days | Balance of friendliness and precision |
| Null handling | Return "Never" | User-friendly for unset fields |
| Invalid handling | Return "Invalid date" | Signals data issue gracefully |
| Fallback | `toLocaleString()` | Graceful degradation |
| Testing | Vitest with time mocking | Deterministic, comprehensive |

---

## Files to Create/Modify

### New Files
1. `frontend/src/utils/dateFormat.ts` - Core utility functions
2. `frontend/tests/utils/dateFormat.test.ts` - Comprehensive tests

### Modified Files
1. `frontend/src/utils/index.ts` - Add exports
2. `frontend/src/components/connectors/ConnectorList.tsx` - Replace inline formatDate
3. `frontend/src/components/results/ResultsTable.tsx` - Replace inline formatDate
4. `frontend/src/components/results/ResultDetailPanel.tsx` - Replace inline formatDate
5. `frontend/src/components/pipelines/PipelineCard.tsx` - Replace inline formatDate
6. `frontend/src/components/tools/JobProgressCard.tsx` - Replace inline formatDate
7. `frontend/src/components/trends/TrendChart.tsx` - Replace inline formatting
8. `frontend/src/components/trends/TrendSummaryCard.tsx` - Replace inline formatting
9. `frontend/src/components/trends/PipelineValidationTrend.tsx` - Replace inline formatting
