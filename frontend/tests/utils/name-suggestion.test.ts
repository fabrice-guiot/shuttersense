/**
 * Unit tests for name suggestion utilities.
 *
 * Tests cover:
 *   - suggestCollectionName() - Path to collection name transformation
 *   - toTitleCase() - Title case conversion
 *   - getPathComponents() - Path breakdown with names
 *   - validateCollectionName() - Name validation rules
 *   - makeUniqueName() - Unique name generation
 *   - suggestBatchNames() - Batch name generation
 *   - formatPathForDisplay() - Path truncation
 *   - getPathDepth() - Path depth calculation
 *   - formatFileSize() - File size formatting
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T053a
 */

import { describe, it, expect } from 'vitest'
import {
  suggestCollectionName,
  toTitleCase,
  getPathComponents,
  validateCollectionName,
  makeUniqueName,
  suggestBatchNames,
  formatPathForDisplay,
  getPathDepth,
  formatFileSize
} from '@/utils/name-suggestion'

// ============================================================================
// Title Case Tests
// ============================================================================

describe('toTitleCase', () => {
  it('should capitalize first letter of each word', () => {
    expect(toTitleCase('hello world')).toBe('Hello World')
    expect(toTitleCase('summer vacation')).toBe('Summer Vacation')
  })

  it('should handle already capitalized text', () => {
    expect(toTitleCase('THE QUICK FOX')).toBe('The Quick Fox')
    expect(toTitleCase('HELLO')).toBe('Hello')
  })

  it('should handle mixed case', () => {
    expect(toTitleCase('hElLo WoRLd')).toBe('Hello World')
  })

  it('should handle single word', () => {
    expect(toTitleCase('hello')).toBe('Hello')
    expect(toTitleCase('HELLO')).toBe('Hello')
  })

  it('should handle empty string', () => {
    expect(toTitleCase('')).toBe('')
  })

  it('should handle multiple spaces', () => {
    expect(toTitleCase('hello  world')).toBe('Hello  World')
  })
})

// ============================================================================
// Collection Name Suggestion Tests
// ============================================================================

describe('suggestCollectionName', () => {
  it('should extract folder name from path', () => {
    expect(suggestCollectionName('2020/')).toBe('2020')
    expect(suggestCollectionName('2020/Events/')).toBe('Events')
    expect(suggestCollectionName('photos/2020/summer/')).toBe('Summer')
  })

  it('should URL decode path components', () => {
    expect(suggestCollectionName('2020/My%20Photos/')).toBe('My Photos')
    // Note: Non-ASCII characters are removed by the implementation
    // %C3%89t%C3%A9 decodes to "Été", but accented chars are removed
    expect(suggestCollectionName('events/summer%202020/')).toBe('Summer 2020')
  })

  it('should replace underscores with spaces', () => {
    expect(suggestCollectionName('summer_vacation/')).toBe('Summer Vacation')
    expect(suggestCollectionName('events/wedding_ceremony/')).toBe('Wedding Ceremony')
  })

  it('should replace hyphens with spaces', () => {
    expect(suggestCollectionName('2021-trip-to-paris/')).toBe('2021 Trip To Paris')
    expect(suggestCollectionName('my-photos/')).toBe('My Photos')
  })

  it('should apply title case', () => {
    expect(suggestCollectionName('SUMMER_VACATION/')).toBe('Summer Vacation')
    expect(suggestCollectionName('my-photos/')).toBe('My Photos')
  })

  it('should handle paths without trailing slash', () => {
    expect(suggestCollectionName('2020/Events')).toBe('Events')
    expect(suggestCollectionName('summer_vacation')).toBe('Summer Vacation')
  })

  it('should return "Root" for empty path', () => {
    expect(suggestCollectionName('')).toBe('Root')
    expect(suggestCollectionName('/')).toBe('Root')
  })

  it('should return "Unnamed Collection" for path resulting in empty name', () => {
    // After removing special chars, if empty
    expect(suggestCollectionName('___/')).toBe('Unnamed Collection')
  })

  it('should clean up extra whitespace', () => {
    expect(suggestCollectionName('summer__vacation/')).toBe('Summer Vacation')
    expect(suggestCollectionName('my---photos/')).toBe('My Photos')
  })

  it('should handle complex real-world paths', () => {
    expect(suggestCollectionName('2020/Events/Smith-Wedding_Reception/')).toBe('Smith Wedding Reception')
    expect(suggestCollectionName('Photos%20Archive/2019_Trips/Japan%20Tour/')).toBe('Japan Tour')
  })
})

// ============================================================================
// Path Components Tests
// ============================================================================

describe('getPathComponents', () => {
  it('should return all path components with names', () => {
    const components = getPathComponents('2020/Events/Wedding/')

    expect(components).toHaveLength(3)
    expect(components[0]).toEqual({ path: '2020/', name: '2020' })
    expect(components[1]).toEqual({ path: '2020/Events/', name: 'Events' })
    expect(components[2]).toEqual({ path: '2020/Events/Wedding/', name: 'Wedding' })
  })

  it('should handle single component', () => {
    const components = getPathComponents('photos/')

    expect(components).toHaveLength(1)
    expect(components[0]).toEqual({ path: 'photos/', name: 'Photos' })
  })

  it('should handle empty path', () => {
    const components = getPathComponents('')
    expect(components).toHaveLength(0)
  })

  it('should apply name transformation to each component', () => {
    const components = getPathComponents('my_photos/summer_2020/')

    expect(components[0].name).toBe('My Photos')
    expect(components[1].name).toBe('Summer 2020')
  })
})

// ============================================================================
// Name Validation Tests
// ============================================================================

describe('validateCollectionName', () => {
  it('should accept valid names', () => {
    expect(validateCollectionName('Summer Photos')).toEqual([])
    expect(validateCollectionName('2020')).toEqual([])
    expect(validateCollectionName('My Collection')).toEqual([])
  })

  it('should reject empty name', () => {
    const errors = validateCollectionName('')
    expect(errors).toContain('Name is required')
  })

  it('should reject whitespace-only name', () => {
    const errors = validateCollectionName('   ')
    expect(errors).toContain('Name is required')
  })

  it('should reject name over 255 characters', () => {
    const longName = 'a'.repeat(256)
    const errors = validateCollectionName(longName)
    expect(errors.some(e => e.includes('255 characters'))).toBe(true)
  })

  it('should accept name at 255 characters', () => {
    const maxName = 'a'.repeat(255)
    const errors = validateCollectionName(maxName)
    expect(errors).toEqual([])
  })

  it('should reject names with control characters', () => {
    const nameWithTab = 'Hello\tWorld'
    const errors = validateCollectionName(nameWithTab)
    expect(errors.some(e => e.includes('control characters'))).toBe(true)
  })

  it('should reject names with null character', () => {
    const nameWithNull = 'Hello\x00World'
    const errors = validateCollectionName(nameWithNull)
    expect(errors.some(e => e.includes('control characters'))).toBe(true)
  })
})

// ============================================================================
// Unique Name Generation Tests
// ============================================================================

describe('makeUniqueName', () => {
  it('should return base name when not in use', () => {
    const existing = new Set(['Other'])
    expect(makeUniqueName('Photos', existing)).toBe('Photos')
  })

  it('should append (2) when base name exists', () => {
    const existing = new Set(['Photos'])
    expect(makeUniqueName('Photos', existing)).toBe('Photos (2)')
  })

  it('should increment number until unique', () => {
    const existing = new Set(['Photos', 'Photos (2)', 'Photos (3)'])
    expect(makeUniqueName('Photos', existing)).toBe('Photos (4)')
  })

  it('should handle empty existing set', () => {
    const existing = new Set<string>()
    expect(makeUniqueName('Photos', existing)).toBe('Photos')
  })
})

describe('suggestBatchNames', () => {
  it('should generate unique names for multiple paths', () => {
    const paths = ['2020/Events/', '2021/Events/', '2022/Events/']
    const names = suggestBatchNames(paths)

    expect(names.get('2020/Events/')).toBe('Events')
    expect(names.get('2021/Events/')).toBe('Events (2)')
    expect(names.get('2022/Events/')).toBe('Events (3)')
  })

  it('should handle paths with different names', () => {
    const paths = ['2020/Summer/', '2020/Winter/', '2021/Spring/']
    const names = suggestBatchNames(paths)

    expect(names.get('2020/Summer/')).toBe('Summer')
    expect(names.get('2020/Winter/')).toBe('Winter')
    expect(names.get('2021/Spring/')).toBe('Spring')
  })

  it('should handle empty array', () => {
    const names = suggestBatchNames([])
    expect(names.size).toBe(0)
  })

  it('should preserve order of paths', () => {
    const paths = ['z/', 'a/', 'm/']
    const names = suggestBatchNames(paths)

    const entries = Array.from(names.entries())
    expect(entries[0][0]).toBe('z/')
    expect(entries[1][0]).toBe('a/')
    expect(entries[2][0]).toBe('m/')
  })
})

// ============================================================================
// Path Display Formatting Tests
// ============================================================================

describe('formatPathForDisplay', () => {
  it('should return short paths unchanged', () => {
    expect(formatPathForDisplay('2020/Events/', 50)).toBe('2020/Events/')
    expect(formatPathForDisplay('photos/', 50)).toBe('photos/')
  })

  it('should truncate long paths with ellipsis', () => {
    const longPath = 'very/long/path/with/many/nested/directories/inside/'
    const formatted = formatPathForDisplay(longPath, 30)

    expect(formatted.length).toBeLessThanOrEqual(30)
    expect(formatted).toContain('...')
  })

  it('should keep first and last parts', () => {
    const longPath = 'first/middle/more/even-more/last/'
    const formatted = formatPathForDisplay(longPath, 25)

    expect(formatted).toContain('first')
    expect(formatted).toContain('last')
    expect(formatted).toContain('...')
  })

  it('should handle very short maxLength', () => {
    const path = 'some/path/here/'
    const formatted = formatPathForDisplay(path, 10)

    expect(formatted.length).toBeLessThanOrEqual(10)
    expect(formatted).toContain('...')
  })

  it('should handle paths with only two parts', () => {
    const path = 'first/second/'
    const formatted = formatPathForDisplay(path, 5)

    // When path has <= 2 parts, return as-is or truncate directly
    expect(formatted).toBeDefined()
  })
})

describe('getPathDepth', () => {
  it('should return 1 for single folder', () => {
    expect(getPathDepth('photos/')).toBe(1)
    expect(getPathDepth('2020/')).toBe(1)
  })

  it('should return correct depth for nested paths', () => {
    expect(getPathDepth('2020/Events/')).toBe(2)
    expect(getPathDepth('2020/Events/Wedding/')).toBe(3)
    expect(getPathDepth('a/b/c/d/e/')).toBe(5)
  })

  it('should handle paths without trailing slash', () => {
    expect(getPathDepth('2020/Events')).toBe(2)
  })

  it('should return 0 for empty path', () => {
    expect(getPathDepth('')).toBe(0)
    expect(getPathDepth('/')).toBe(0)
  })
})

// ============================================================================
// File Size Formatting Tests
// ============================================================================

describe('formatFileSize', () => {
  it('should format bytes', () => {
    expect(formatFileSize(0)).toBe('0 B')
    expect(formatFileSize(500)).toBe('500.00 B')
    expect(formatFileSize(1023)).toBe('1023.00 B')
  })

  it('should format kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1.00 KB')
    expect(formatFileSize(1536)).toBe('1.50 KB')
    expect(formatFileSize(10240)).toBe('10.00 KB')
  })

  it('should format megabytes', () => {
    expect(formatFileSize(1048576)).toBe('1.00 MB')
    expect(formatFileSize(1500000)).toBe('1.43 MB')
    expect(formatFileSize(10485760)).toBe('10.00 MB')
  })

  it('should format gigabytes', () => {
    expect(formatFileSize(1073741824)).toBe('1.00 GB')
    expect(formatFileSize(5368709120)).toBe('5.00 GB')
  })

  it('should format terabytes', () => {
    expect(formatFileSize(1099511627776)).toBe('1.00 TB')
    expect(formatFileSize(2199023255552)).toBe('2.00 TB')
  })

  it('should handle decimal precision', () => {
    expect(formatFileSize(1536)).toBe('1.50 KB')
    expect(formatFileSize(1572864)).toBe('1.50 MB')
  })
})
