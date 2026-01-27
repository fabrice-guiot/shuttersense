/**
 * Name Suggestion Utilities
 *
 * Transforms folder paths into human-readable collection names:
 * - URL decodes path components
 * - Applies title case
 * - Cleans up special characters
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T053
 */

// ============================================================================
// Name Transformation
// ============================================================================

/**
 * Suggest a collection name from a folder path.
 *
 * Transformation steps:
 * 1. Extract the last path component (folder name)
 * 2. URL decode the name
 * 3. Replace underscores and hyphens with spaces
 * 4. Apply title case
 * 5. Clean up extra whitespace
 *
 * @param path - Folder path (e.g., "2020/Summer_Vacation/")
 * @returns Suggested collection name (e.g., "Summer Vacation")
 *
 * @example
 * suggestCollectionName('2020/My%20Photos/') // 'My Photos'
 * suggestCollectionName('events/wedding_ceremony/') // 'Wedding Ceremony'
 * suggestCollectionName('2021-trip-to-paris/') // '2021 Trip To Paris'
 */
export function suggestCollectionName(path: string): string {
  // Extract the last path component
  const parts = path.split('/').filter(Boolean)
  if (parts.length === 0) return 'Root'

  let name = parts[parts.length - 1]

  // URL decode
  try {
    name = decodeURIComponent(name)
  } catch {
    // If decode fails, use as-is
  }

  // Replace separators with spaces
  name = name.replace(/[-_]+/g, ' ')

  // Remove any remaining special characters except spaces and alphanumeric
  name = name.replace(/[^\w\s]/g, ' ')

  // Apply title case
  name = toTitleCase(name)

  // Clean up extra whitespace
  name = name.replace(/\s+/g, ' ').trim()

  return name || 'Unnamed Collection'
}

/**
 * Convert a string to title case.
 * Capitalizes the first letter of each word.
 *
 * @example
 * toTitleCase('hello world') // 'Hello World'
 * toTitleCase('THE QUICK FOX') // 'The Quick Fox'
 */
export function toTitleCase(str: string): string {
  return str
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Extract all path components with their suggested names.
 * Useful for breadcrumb display or path context.
 *
 * @example
 * getPathComponents('2020/Events/Wedding/')
 * // Returns: [
 * //   { path: '2020/', name: '2020' },
 * //   { path: '2020/Events/', name: 'Events' },
 * //   { path: '2020/Events/Wedding/', name: 'Wedding' }
 * // ]
 */
export function getPathComponents(path: string): Array<{ path: string; name: string }> {
  const parts = path.split('/').filter(Boolean)
  const components: Array<{ path: string; name: string }> = []

  for (let i = 0; i < parts.length; i++) {
    const componentPath = parts.slice(0, i + 1).join('/') + '/'
    components.push({
      path: componentPath,
      name: suggestCollectionName(parts[i] + '/')
    })
  }

  return components
}

/**
 * Validate a collection name.
 * Returns validation errors if the name is invalid.
 *
 * Rules:
 * - Must be 1-255 characters
 * - Cannot be only whitespace
 * - Cannot contain control characters
 */
export function validateCollectionName(name: string): string[] {
  const errors: string[] = []

  if (!name || name.trim().length === 0) {
    errors.push('Name is required')
  } else {
    if (name.length > 255) {
      errors.push('Name must be 255 characters or less')
    }

    // Check for control characters
    // eslint-disable-next-line no-control-regex
    if (/[\x00-\x1f\x7f]/.test(name)) {
      errors.push('Name cannot contain control characters')
    }
  }

  return errors
}

/**
 * Generate a unique name by appending a number if needed.
 *
 * @example
 * makeUniqueName('Photos', new Set(['Photos', 'Photos (2)']))
 * // Returns: 'Photos (3)'
 */
export function makeUniqueName(baseName: string, existingNames: Set<string>): string {
  if (!existingNames.has(baseName)) {
    return baseName
  }

  let counter = 2
  while (existingNames.has(`${baseName} (${counter})`)) {
    counter++
  }

  return `${baseName} (${counter})`
}

// ============================================================================
// Batch Name Generation
// ============================================================================

/**
 * Generate unique suggested names for multiple folders.
 * Handles duplicate suggestions by appending numbers.
 *
 * @param paths - Array of folder paths
 * @returns Map of path -> suggested unique name
 */
export function suggestBatchNames(paths: string[]): Map<string, string> {
  const result = new Map<string, string>()
  const usedNames = new Set<string>()

  for (const path of paths) {
    const baseName = suggestCollectionName(path)
    const uniqueName = makeUniqueName(baseName, usedNames)
    result.set(path, uniqueName)
    usedNames.add(uniqueName)
  }

  return result
}

// ============================================================================
// Path Display Formatting
// ============================================================================

/**
 * Format a folder path for display.
 * Truncates long paths with ellipsis in the middle.
 *
 * @example
 * formatPathForDisplay('very/long/path/to/folder/', 20)
 * // Returns: 'very/...to/folder/'
 */
export function formatPathForDisplay(path: string, maxLength: number = 50): string {
  if (path.length <= maxLength) return path

  const parts = path.split('/').filter(Boolean)
  if (parts.length <= 2) return path

  // Keep first and last parts, replace middle with ellipsis
  const first = parts[0]
  const last = parts[parts.length - 1]

  const result = `${first}/.../${last}/`
  if (result.length <= maxLength) return result

  // If still too long, just truncate
  return path.substring(0, maxLength - 3) + '...'
}

/**
 * Get depth of a folder path (number of levels).
 *
 * @example
 * getPathDepth('2020/Events/Wedding/') // 3
 * getPathDepth('photos/') // 1
 */
export function getPathDepth(path: string): number {
  return path.split('/').filter(Boolean).length
}

/**
 * Format file size for display.
 *
 * @example
 * formatFileSize(1024) // '1.00 KB'
 * formatFileSize(1500000) // '1.43 MB'
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`
}
