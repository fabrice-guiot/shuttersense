/**
 * GUID utilities for entity identification.
 *
 * Provides validation and parsing functions for GUIDs
 * in the format {prefix}_{base32_uuid}.
 *
 * GUID Format:
 *   - prefix: 3-character entity type identifier
 *   - separator: underscore (_)
 *   - uuid: 26-character Crockford Base32 encoded UUIDv7
 *
 * Entity Prefixes:
 *   Database entities (persisted):
 *   - col: Collection
 *   - con: Connector
 *   - pip: Pipeline
 *   - res: AnalysisResult
 *   - evt: Event (calendar event)
 *   - ser: EventSeries (multi-day event grouping)
 *   - loc: Location (known locations)
 *   - org: Organizer (event organizers)
 *   - prf: Performer (event performers)
 *   - cat: Category (event categories)
 *   In-memory entities (transient):
 *   - job: Job
 *   - imp: Import
 */

/**
 * Entity type prefixes
 */
export type EntityPrefix =
  | 'col'
  | 'con'
  | 'pip'
  | 'res'
  | 'evt'
  | 'ser'
  | 'loc'
  | 'org'
  | 'prf'
  | 'cat'
  | 'job'
  | 'imp'

/**
 * Entity type names mapped to prefixes
 */
export const ENTITY_PREFIXES: Record<EntityPrefix, string> = {
  col: 'Collection',
  con: 'Connector',
  pip: 'Pipeline',
  res: 'AnalysisResult',
  evt: 'Event',
  ser: 'EventSeries',
  loc: 'Location',
  org: 'Organizer',
  prf: 'Performer',
  cat: 'Category',
  job: 'Job',
  imp: 'Import',
}

/**
 * Crockford Base32 alphabet (excludes I, L, O, U to avoid confusion)
 */
const CROCKFORD_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

/**
 * Regex pattern for validating GUIDs
 * Format: {3-char prefix}_{26-char Crockford Base32}
 */
const GUID_PATTERN =
  /^(col|con|pip|res|evt|ser|loc|org|prf|cat|job|imp)_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$/i

/**
 * Validates if a string is a valid GUID.
 *
 * @param id - The string to validate
 * @param expectedPrefix - Optional prefix to validate against
 * @returns True if valid GUID format
 *
 * @example
 * isValidGuid('col_01hgw2bbg0000000000000000') // true
 * isValidGuid('col_01hgw2bbg0000000000000000', 'col') // true
 * isValidGuid('col_01hgw2bbg0000000000000000', 'con') // false
 */
export function isValidGuid(id: string, expectedPrefix?: EntityPrefix): boolean {
  if (!id || typeof id !== 'string') {
    return false
  }

  if (!GUID_PATTERN.test(id)) {
    return false
  }

  if (expectedPrefix) {
    const prefix = id.slice(0, 3).toLowerCase() as EntityPrefix
    return prefix === expectedPrefix
  }

  return true
}

/**
 * Extracts the entity type from a GUID.
 *
 * @param guid - The GUID string
 * @returns The entity type name, or null if invalid
 *
 * @example
 * getEntityType('col_01hgw2bbg0000000000000000') // 'Collection'
 * getEntityType('con_01hgw2bbg0000000000000001') // 'Connector'
 * getEntityType('invalid') // null
 */
export function getEntityType(guid: string): string | null {
  if (!guid || guid.length < 3) {
    return null
  }

  const prefix = guid.slice(0, 3).toLowerCase() as EntityPrefix
  return ENTITY_PREFIXES[prefix] || null
}

/**
 * Extracts the prefix from a GUID.
 *
 * @param guid - The GUID string
 * @returns The prefix, or null if invalid
 *
 * @example
 * getPrefix('col_01hgw2bbg0000000000000000') // 'col'
 * getPrefix('invalid') // null
 */
export function getPrefix(guid: string): EntityPrefix | null {
  if (!isValidGuid(guid)) {
    return null
  }

  return guid.slice(0, 3).toLowerCase() as EntityPrefix
}

/**
 * Checks if a string is a numeric ID (for backward compatibility).
 *
 * @param id - The string to check
 * @returns True if the string is numeric
 *
 * @example
 * isNumericId('123') // true
 * isNumericId('col_xxx') // false
 */
export function isNumericId(id: string): boolean {
  if (!id || typeof id !== 'string') {
    return false
  }

  return /^\d+$/.test(id)
}

/**
 * Checks if a string is a GUID.
 *
 * @param id - The string to check
 * @returns True if the string matches GUID format
 *
 * @example
 * isGuid('col_01hgw2bbg0000000000000000') // true
 * isGuid('123') // false
 */
export function isGuid(id: string): boolean {
  return isValidGuid(id)
}

/**
 * Determines the identifier type (numeric or guid).
 *
 * @param id - The identifier string
 * @returns 'numeric' | 'guid' | 'invalid'
 *
 * @example
 * getIdentifierType('123') // 'numeric'
 * getIdentifierType('col_xxx') // 'guid'
 * getIdentifierType('invalid') // 'invalid'
 */
export function getIdentifierType(id: string): 'numeric' | 'guid' | 'invalid' {
  if (isNumericId(id)) {
    return 'numeric'
  }

  if (isGuid(id)) {
    return 'guid'
  }

  return 'invalid'
}

/**
 * Formats a GUID for display (truncated with ellipsis).
 *
 * @param guid - The GUID string
 * @param showPrefix - Whether to include the prefix (default: true)
 * @returns Formatted string for display
 *
 * @example
 * formatGuid('col_01hgw2bbg0000000000000000') // 'col_01hgw2bb...'
 * formatGuid('col_01hgw2bbg0000000000000000', false) // '01hgw2bb...'
 */
export function formatGuid(guid: string, showPrefix = true): string {
  if (!isValidGuid(guid)) {
    return guid
  }

  if (showPrefix) {
    // Show prefix + first 8 chars of base32 + ellipsis
    return guid.slice(0, 12) + '...'
  }

  // Show first 8 chars of base32 + ellipsis
  return guid.slice(4, 12) + '...'
}

/**
 * Copies a GUID to the clipboard.
 *
 * @param guid - The GUID to copy
 * @returns Promise that resolves when copied
 */
export async function copyGuid(guid: string): Promise<void> {
  if (typeof navigator?.clipboard?.writeText === 'function') {
    await navigator.clipboard.writeText(guid)
  } else {
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = guid
    textArea.style.position = 'fixed'
    textArea.style.opacity = '0'
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
  }
}

/**
 * Validates a GUID and returns it if valid, throws if invalid.
 * Use this before using a GUID in API URLs to prevent URL injection.
 *
 * @param guid - The GUID to validate
 * @param expectedPrefix - Optional prefix to validate against
 * @returns The validated GUID
 * @throws Error if GUID is invalid
 *
 * @example
 * const validGuid = validateGuid(userInput, 'res')
 * await api.get(`/results/${validGuid}`)
 */
export function validateGuid(guid: string, expectedPrefix?: EntityPrefix): string {
  if (!isValidGuid(guid, expectedPrefix)) {
    const prefixMsg = expectedPrefix ? ` with prefix '${expectedPrefix}'` : ''
    throw new Error(`Invalid GUID format${prefixMsg}: ${guid}`)
  }
  return guid
}
