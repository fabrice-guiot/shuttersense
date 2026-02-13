/**
 * Day offset label utility
 *
 * Computes a compact "D-1", "D+2" etc. label when an event's date differs
 * from a reference date (e.g., the currently selected calendar day).
 * Returns null when the dates match or when either date is missing.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker
 */

/**
 * Returns a compact day-offset label like "D-1" or "D+3", or null if same day.
 *
 * @param eventDate  - Event date as YYYY-MM-DD string
 * @param refDate    - Reference date as YYYY-MM-DD string (e.g., selected day)
 */
export function dayOffsetLabel(
  eventDate: string | null | undefined,
  refDate: string | null | undefined,
): string | null {
  if (!eventDate || !refDate) return null

  // Parse as UTC to avoid timezone-induced off-by-one errors
  const ev = new Date(eventDate + 'T00:00:00Z')
  const ref = new Date(refDate + 'T00:00:00Z')
  const diffMs = ev.getTime() - ref.getTime()
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return null
  return diffDays > 0 ? `D+${diffDays}` : `D${diffDays}`
}
