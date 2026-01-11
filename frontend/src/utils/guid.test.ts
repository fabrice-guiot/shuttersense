/**
 * Tests for GUID utilities.
 *
 * Tests cover:
 * - GUID validation
 * - Entity type extraction
 * - Identifier type detection
 * - Format utilities
 */

import { describe, test, expect, vi } from 'vitest'
import {
  isValidGuid,
  getEntityType,
  getPrefix,
  isNumericId,
  isGuid,
  getIdentifierType,
  formatGuid,
  copyGuid,
  ENTITY_PREFIXES,
} from './guid'

describe('isValidGuid', () => {
  test('validates correct GUIDs', () => {
    expect(isValidGuid('col_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isValidGuid('con_ABCDEFGHJKMNPQRSTVWXYZ0123')).toBe(true)
    expect(isValidGuid('pip_01hgw2bbg00000000000000002')).toBe(true) // 26 chars after prefix
    expect(isValidGuid('res_01HGW2BBG00000000000000003')).toBe(true) // 26 chars after prefix
  })

  test('validates calendar events GUIDs', () => {
    expect(isValidGuid('evt_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isValidGuid('ser_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isValidGuid('loc_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isValidGuid('org_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isValidGuid('prf_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isValidGuid('cat_01234567890abcdefghjkmnpqr')).toBe(true)
  })

  test('validates case-insensitively', () => {
    expect(isValidGuid('COL_01234567890ABCDEFGHJKMNPQR')).toBe(true)
    expect(isValidGuid('Col_01234567890abcdefghjkmnpqr')).toBe(true)
  })

  test('validates with expected prefix', () => {
    expect(isValidGuid('col_01234567890abcdefghjkmnpqr', 'col')).toBe(true)
    expect(isValidGuid('col_01234567890abcdefghjkmnpqr', 'con')).toBe(false)
  })

  test('rejects invalid GUIDs', () => {
    // Empty or null
    expect(isValidGuid('')).toBe(false)
    expect(isValidGuid(null as any)).toBe(false)
    expect(isValidGuid(undefined as any)).toBe(false)

    // Wrong prefix
    expect(isValidGuid('xxx_01234567890abcdefghjkmnpqr')).toBe(false)

    // Too short
    expect(isValidGuid('col_123')).toBe(false)

    // Too long
    expect(isValidGuid('col_01234567890abcdefghjkmnpqrs')).toBe(false)

    // Wrong separator
    expect(isValidGuid('col-01234567890abcdefghjkmnpqr')).toBe(false)

    // Contains invalid Crockford characters (I, L, O, U)
    expect(isValidGuid('col_IIIIIIIIIIIIIIIIIIIIIIIIII')).toBe(false)
    expect(isValidGuid('col_LLLLLLLLLLLLLLLLLLLLLLLLLL')).toBe(false)
    expect(isValidGuid('col_OOOOOOOOOOOOOOOOOOOOOOOOOO')).toBe(false)
    expect(isValidGuid('col_UUUUUUUUUUUUUUUUUUUUUUUUUU')).toBe(false)
  })
})

describe('getEntityType', () => {
  test('returns entity type for valid GUIDs', () => {
    expect(getEntityType('col_01234567890abcdefghjkmnpqr')).toBe('Collection')
    expect(getEntityType('con_01234567890abcdefghjkmnpqr')).toBe('Connector')
    expect(getEntityType('pip_01234567890abcdefghjkmnpqr')).toBe('Pipeline')
    expect(getEntityType('res_01234567890abcdefghjkmnpqr')).toBe('AnalysisResult')
    expect(getEntityType('evt_01234567890abcdefghjkmnpqr')).toBe('Event')
    expect(getEntityType('ser_01234567890abcdefghjkmnpqr')).toBe('EventSeries')
    expect(getEntityType('loc_01234567890abcdefghjkmnpqr')).toBe('Location')
    expect(getEntityType('org_01234567890abcdefghjkmnpqr')).toBe('Organizer')
    expect(getEntityType('prf_01234567890abcdefghjkmnpqr')).toBe('Performer')
    expect(getEntityType('cat_01234567890abcdefghjkmnpqr')).toBe('Category')
  })

  test('returns null for invalid GUIDs', () => {
    expect(getEntityType('')).toBe(null)
    expect(getEntityType('xy')).toBe(null)
    expect(getEntityType('xyz_123')).toBe(null)
    expect(getEntityType('invalid')).toBe(null)
  })
})

describe('getPrefix', () => {
  test('returns prefix for valid GUIDs', () => {
    expect(getPrefix('col_01234567890abcdefghjkmnpqr')).toBe('col')
    expect(getPrefix('con_01234567890abcdefghjkmnpqr')).toBe('con')
    expect(getPrefix('pip_01234567890abcdefghjkmnpqr')).toBe('pip')
    expect(getPrefix('res_01234567890abcdefghjkmnpqr')).toBe('res')
    expect(getPrefix('evt_01234567890abcdefghjkmnpqr')).toBe('evt')
    expect(getPrefix('ser_01234567890abcdefghjkmnpqr')).toBe('ser')
    expect(getPrefix('loc_01234567890abcdefghjkmnpqr')).toBe('loc')
    expect(getPrefix('org_01234567890abcdefghjkmnpqr')).toBe('org')
    expect(getPrefix('prf_01234567890abcdefghjkmnpqr')).toBe('prf')
    expect(getPrefix('cat_01234567890abcdefghjkmnpqr')).toBe('cat')
  })

  test('returns null for invalid GUIDs', () => {
    expect(getPrefix('')).toBe(null)
    expect(getPrefix('invalid')).toBe(null)
    expect(getPrefix('123')).toBe(null)
  })
})

describe('isNumericId', () => {
  test('identifies numeric IDs', () => {
    expect(isNumericId('123')).toBe(true)
    expect(isNumericId('0')).toBe(true)
    expect(isNumericId('999999')).toBe(true)
  })

  test('rejects non-numeric strings', () => {
    expect(isNumericId('')).toBe(false)
    expect(isNumericId('abc')).toBe(false)
    expect(isNumericId('col_123')).toBe(false)
    expect(isNumericId('12.34')).toBe(false)
    expect(isNumericId('-123')).toBe(false)
    expect(isNumericId(null as any)).toBe(false)
  })
})

describe('isGuid', () => {
  test('identifies GUIDs', () => {
    expect(isGuid('col_01234567890abcdefghjkmnpqr')).toBe(true)
    expect(isGuid('con_01234567890abcdefghjkmnpqr')).toBe(true)
  })

  test('rejects non-GUIDs', () => {
    expect(isGuid('123')).toBe(false)
    expect(isGuid('invalid')).toBe(false)
    expect(isGuid('')).toBe(false)
  })
})

describe('getIdentifierType', () => {
  test('identifies numeric type', () => {
    expect(getIdentifierType('123')).toBe('numeric')
    expect(getIdentifierType('999')).toBe('numeric')
  })

  test('identifies guid type', () => {
    expect(getIdentifierType('col_01234567890abcdefghjkmnpqr')).toBe('guid')
    expect(getIdentifierType('con_01234567890abcdefghjkmnpqr')).toBe('guid')
  })

  test('identifies invalid type', () => {
    expect(getIdentifierType('')).toBe('invalid')
    expect(getIdentifierType('invalid')).toBe('invalid')
    expect(getIdentifierType('col_123')).toBe('invalid')
  })
})

describe('formatGuid', () => {
  test('formats with prefix', () => {
    const result = formatGuid('col_01234567890abcdefghjkmnpqr')
    expect(result).toBe('col_01234567...')
  })

  test('formats without prefix', () => {
    const result = formatGuid('col_01234567890abcdefghjkmnpqr', false)
    expect(result).toBe('01234567...')
  })

  test('returns original for invalid ID', () => {
    expect(formatGuid('invalid')).toBe('invalid')
    expect(formatGuid('')).toBe('')
  })
})

describe('copyGuid', () => {
  test('copies to clipboard using Clipboard API', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    })

    await copyGuid('col_01234567890abcdefghjkmnpqr')

    expect(writeTextMock).toHaveBeenCalledWith('col_01234567890abcdefghjkmnpqr')
  })
})

describe('ENTITY_PREFIXES', () => {
  test('contains all entity types', () => {
    expect(ENTITY_PREFIXES.col).toBe('Collection')
    expect(ENTITY_PREFIXES.con).toBe('Connector')
    expect(ENTITY_PREFIXES.pip).toBe('Pipeline')
    expect(ENTITY_PREFIXES.res).toBe('AnalysisResult')
    expect(ENTITY_PREFIXES.evt).toBe('Event')
    expect(ENTITY_PREFIXES.ser).toBe('EventSeries')
    expect(ENTITY_PREFIXES.loc).toBe('Location')
    expect(ENTITY_PREFIXES.org).toBe('Organizer')
    expect(ENTITY_PREFIXES.prf).toBe('Performer')
    expect(ENTITY_PREFIXES.cat).toBe('Category')
    expect(ENTITY_PREFIXES.job).toBe('Job')
    expect(ENTITY_PREFIXES.imp).toBe('Import')
  })
})
