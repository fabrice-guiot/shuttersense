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

// ============================================================================
// Relative Time Formatting (User Story 2)
// ============================================================================

/**
 * Result from getRelativeTimeUnit containing the value and unit for relative formatting.
 */
export interface RelativeTimeUnit {
  value: number
  unit: Intl.RelativeTimeFormatUnit
}

/**
 * Threshold in milliseconds for when to switch from relative to absolute time.
 * Set to 1 day - relative time is only shown for recent timestamps (< 24 hours).
 */
const RELATIVE_TIME_THRESHOLD_MS = 24 * 60 * 60 * 1000

/**
 * Calculates the appropriate time unit and value for relative time formatting.
 *
 * Given a millisecond difference, determines the most appropriate unit
 * (seconds, minutes, hours, days, weeks, months, years) and returns
 * the value as a negative number (for "ago" formatting).
 *
 * @param diffMs - Difference in milliseconds (positive = past, negative = future)
 * @returns Object with value (negative for past) and unit for Intl.RelativeTimeFormat
 *
 * @example
 * getRelativeTimeUnit(30000) // { value: -30, unit: 'second' }
 * getRelativeTimeUnit(3600000) // { value: -1, unit: 'hour' }
 * getRelativeTimeUnit(86400000) // { value: -1, unit: 'day' }
 */
export function getRelativeTimeUnit(diffMs: number): RelativeTimeUnit {
  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)
  const months = Math.floor(days / 30)
  const years = Math.floor(days / 365)

  // Return the largest appropriate unit
  // Note: Using || 0 to avoid -0 (negative zero) which can cause Object.is comparison issues
  if (years !== 0) return { value: -years, unit: 'year' }
  if (months !== 0) return { value: -months, unit: 'month' }
  if (weeks !== 0) return { value: -weeks, unit: 'week' }
  if (days !== 0) return { value: -days, unit: 'day' }
  if (hours !== 0) return { value: -hours, unit: 'hour' }
  if (minutes !== 0) return { value: -minutes, unit: 'minute' }
  return { value: -seconds || 0, unit: 'second' }
}

/**
 * Formats a date string as relative time (e.g., "2 hours ago", "yesterday").
 *
 * Uses Intl.RelativeTimeFormat with numeric: 'auto' for natural language
 * (e.g., "yesterday" instead of "1 day ago").
 *
 * Falls back to absolute date format (formatDateTime) for:
 *   - Dates older than 7 days
 *   - When Intl.RelativeTimeFormat is not supported
 *
 * **Usage Guidelines:**
 * - Use formatRelativeTime() for recently updated timestamps where "freshness" matters
 *   (e.g., "last updated", "created at" for recent items)
 * - Use formatDateTime() for historical records or when exact time is important
 *   (e.g., report generation dates, scheduled events)
 *
 * @param dateString - ISO 8601 date string, null, or undefined
 * @returns Relative time string (e.g., "5 minutes ago"), or absolute date if > 7 days,
 *          "Never" for null/undefined, "Invalid date" for invalid input
 *
 * @example
 * formatRelativeTime('2026-01-11T11:55:00Z') // "5 minutes ago" (if now is 12:00)
 * formatRelativeTime('2026-01-10T12:00:00Z') // "yesterday"
 * formatRelativeTime('2026-01-01T12:00:00Z') // "Jan 1, 2026, 12:00 PM" (> 7 days)
 * formatRelativeTime(null) // "Never"
 */
export function formatRelativeTime(
  dateString: string | null | undefined
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

  // Calculate difference from now
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()

  // For dates older than threshold, use absolute format
  if (Math.abs(diffMs) > RELATIVE_TIME_THRESHOLD_MS) {
    return formatDateTime(dateString)
  }

  // Check for RelativeTimeFormat support
  if (!hasRelativeTimeSupport()) {
    return formatDateTime(dateString)
  }

  // Get the appropriate unit and value
  const { value, unit } = getRelativeTimeUnit(Math.abs(diffMs))

  // Adjust value sign for future dates
  const adjustedValue = diffMs >= 0 ? value : -value

  // Format with Intl.RelativeTimeFormat
  try {
    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
    return rtf.format(adjustedValue, unit)
  } catch {
    // Fallback to absolute format on error
    return formatDateTime(dateString)
  }
}
