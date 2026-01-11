/**
 * Date formatting utilities for the frontend application.
 *
 * Provides centralized date/time formatting functions using native browser
 * Intl APIs for locale-aware display. All timestamps are displayed in the
 * user's local timezone.
 *
 * Features:
 *   - Absolute date/time formatting (e.g., "Jan 7, 2026, 3:45 PM")
 *   - Relative time formatting (e.g., "2 hours ago", "yesterday")
 *   - Graceful handling of null, undefined, and invalid dates
 *   - No external dependencies (uses native Intl APIs)
 *
 * Browser Support:
 *   - Chrome 71+, Firefox 65+, Safari 14+, Edge 79+
 *
 * @module dateFormat
 */

// ============================================================================
// Types
// ============================================================================

/**
 * Options for absolute date/time formatting.
 * Subset of Intl.DateTimeFormatOptions for common use cases.
 */
export interface DateFormatOptions {
  dateStyle?: 'full' | 'long' | 'medium' | 'short'
  timeStyle?: 'full' | 'long' | 'medium' | 'short'
}

// ============================================================================
// Internal Helpers
// ============================================================================

/**
 * Checks if the browser supports Intl.DateTimeFormat.
 *
 * @returns True if Intl.DateTimeFormat is available
 */
export function hasIntlSupport(): boolean {
  return (
    typeof Intl !== 'undefined' && typeof Intl.DateTimeFormat !== 'undefined'
  )
}

/**
 * Checks if the browser supports Intl.RelativeTimeFormat.
 *
 * @returns True if Intl.RelativeTimeFormat is available
 */
export function hasRelativeTimeSupport(): boolean {
  return (
    typeof Intl !== 'undefined' &&
    typeof Intl.RelativeTimeFormat !== 'undefined'
  )
}

/**
 * Parses a date string into a Date object.
 *
 * Handles null, undefined, empty strings, and invalid date strings gracefully.
 * Returns null for any input that cannot be parsed into a valid date.
 *
 * IMPORTANT: Date strings without timezone indicators (e.g., "2026-01-07T15:45:00")
 * are treated as UTC. This matches the backend behavior where datetime.utcnow()
 * creates naive datetimes that represent UTC time but are serialized without "Z".
 *
 * @param dateString - ISO 8601 date string, null, or undefined
 * @returns Date object if valid, null otherwise
 *
 * @example
 * parseDate('2026-01-07T15:45:00') // Date object (treated as UTC)
 * parseDate('2026-01-07T15:45:00Z') // Date object (explicit UTC)
 * parseDate('2026-01-07T15:45:00+02:00') // Date object (with offset)
 * parseDate(null) // null
 * parseDate('invalid') // null
 */
export function parseDate(dateString: string | null | undefined): Date | null {
  // Handle null, undefined, and empty strings
  if (!dateString) {
    return null
  }

  // Normalize the date string to ensure UTC interpretation
  // Backend sends dates without timezone (e.g., "2026-01-07T15:45:00")
  // which JavaScript would interpret as local time. We treat them as UTC.
  let normalizedDateString = dateString

  // Check if the string already has a timezone indicator
  // Patterns: ends with 'Z', or has '+HH:MM' / '-HH:MM' offset at the end
  const hasTimezone =
    /Z$/i.test(dateString) || /[+-]\d{2}:\d{2}$/.test(dateString)

  // If no timezone and looks like an ISO datetime (has 'T'), append 'Z' for UTC
  if (!hasTimezone && dateString.includes('T')) {
    normalizedDateString = dateString + 'Z'
  }

  // Attempt to parse the date string
  const date = new Date(normalizedDateString)

  // Check if the date is valid (getTime() returns NaN for invalid dates)
  if (isNaN(date.getTime())) {
    return null
  }

  return date
}

// ============================================================================
// Public API
// ============================================================================

/**
 * Formats a date/time string for display in the user's local timezone.
 *
 * Uses Intl.DateTimeFormat for locale-aware formatting. Falls back to
 * toLocaleString() if Intl API is unavailable.
 *
 * @param dateString - ISO 8601 date string, null, or undefined
 * @param options - Formatting options (dateStyle, timeStyle)
 * @returns Formatted date/time string, "Never" for null/undefined, "Invalid date" for invalid input
 *
 * @example
 * formatDateTime('2026-01-07T15:45:00') // "Jan 7, 2026, 3:45 PM"
 * formatDateTime('2026-01-07T15:45:00', { dateStyle: 'full' }) // "Wednesday, January 7, 2026, 3:45 PM"
 * formatDateTime(null) // "Never"
 */
export function formatDateTime(
  dateString: string | null | undefined,
  options?: DateFormatOptions
): string {
  // Handle null/undefined/empty
  if (!dateString) {
    return 'Never'
  }

  // Parse the date
  const date = parseDate(dateString)
  if (!date) {
    return 'Invalid date'
  }

  // Default options: medium date, short time
  const formatOptions: Intl.DateTimeFormatOptions = {
    dateStyle: options?.dateStyle ?? 'medium',
    timeStyle: options?.timeStyle ?? 'short',
  }

  // Format with Intl API (with fallback)
  try {
    if (hasIntlSupport()) {
      return new Intl.DateTimeFormat(undefined, formatOptions).format(date)
    }
    return date.toLocaleString()
  } catch {
    // Fallback for any formatting errors
    return date.toLocaleString()
  }
}

/**
 * Formats a date string for display (date only, no time).
 *
 * @param dateString - ISO 8601 date string, null, or undefined
 * @param options - Formatting options (dateStyle only, timeStyle is ignored)
 * @returns Formatted date string, "Never" for null/undefined, "Invalid date" for invalid input
 *
 * @example
 * formatDate('2026-01-07T15:45:00') // "Jan 7, 2026"
 * formatDate('2026-01-07T15:45:00', { dateStyle: 'short' }) // "1/7/26"
 */
export function formatDate(
  dateString: string | null | undefined,
  options?: DateFormatOptions
): string {
  // Handle null/undefined/empty
  if (!dateString) {
    return 'Never'
  }

  // Parse the date
  const date = parseDate(dateString)
  if (!date) {
    return 'Invalid date'
  }

  // Default options: medium date, no time
  const formatOptions: Intl.DateTimeFormatOptions = {
    dateStyle: options?.dateStyle ?? 'medium',
  }

  // Format with Intl API (with fallback)
  try {
    if (hasIntlSupport()) {
      return new Intl.DateTimeFormat(undefined, formatOptions).format(date)
    }
    return date.toLocaleDateString()
  } catch {
    return date.toLocaleDateString()
  }
}

/**
 * Formats a date string for display (time only, no date).
 *
 * @param dateString - ISO 8601 date string, null, or undefined
 * @param options - Formatting options (timeStyle only, dateStyle is ignored)
 * @returns Formatted time string, "Never" for null/undefined, "Invalid date" for invalid input
 *
 * @example
 * formatTime('2026-01-07T15:45:00') // "3:45 PM"
 * formatTime('2026-01-07T15:45:30', { timeStyle: 'medium' }) // "3:45:30 PM"
 */
export function formatTime(
  dateString: string | null | undefined,
  options?: DateFormatOptions
): string {
  // Handle null/undefined/empty
  if (!dateString) {
    return 'Never'
  }

  // Parse the date
  const date = parseDate(dateString)
  if (!date) {
    return 'Invalid date'
  }

  // Default options: short time, no date
  const formatOptions: Intl.DateTimeFormatOptions = {
    timeStyle: options?.timeStyle ?? 'short',
  }

  // Format with Intl API (with fallback)
  try {
    if (hasIntlSupport()) {
      return new Intl.DateTimeFormat(undefined, formatOptions).format(date)
    }
    return date.toLocaleTimeString()
  } catch {
    return date.toLocaleTimeString()
  }
}

// formatRelativeTime will be implemented in Phase 4
