import { describe, it, expect } from 'vitest'
import type { NodeType } from '@/contracts/api/pipelines-api'
import { generateNodeId, getNodeConfig, getDefaultProperties } from '../node-defaults'

const ALL_TYPES: NodeType[] = ['capture', 'file', 'process', 'pairing', 'branching', 'termination']

describe('generateNodeId', () => {
  it('produces expected format for a type with no existing IDs', () => {
    expect(generateNodeId('file', [])).toBe('file_1')
  })

  it('increments counter when ID exists', () => {
    expect(generateNodeId('file', ['file_1'])).toBe('file_2')
  })

  it('handles gaps in numbering', () => {
    expect(generateNodeId('file', ['file_1', 'file_3'])).toBe('file_2')
  })

  it('handles all 6 node types', () => {
    for (const type of ALL_TYPES) {
      const id = generateNodeId(type, [])
      expect(id).toBe(`${type}_1`)
    }
  })
})

describe('getNodeConfig', () => {
  it('returns correct config for capture node', () => {
    const config = getNodeConfig('capture')
    expect(config.colorClass).toContain('primary')
    expect(config.defaultWidth).toBe(224) // w-56
    expect(config.defaultHeight).toBe(80)
  })

  it('returns correct config for file node', () => {
    const config = getNodeConfig('file')
    expect(config.colorClass).toContain('muted')
    expect(config.defaultWidth).toBe(192) // w-48
  })

  it('returns correct config for process node', () => {
    const config = getNodeConfig('process')
    expect(config.colorClass).toContain('purple')
  })

  it('returns correct config for pairing node', () => {
    const config = getNodeConfig('pairing')
    expect(config.colorClass).toContain('info')
    expect(config.defaultWidth).toBe(208) // w-52
  })

  it('returns correct config for branching node', () => {
    const config = getNodeConfig('branching')
    expect(config.colorClass).toContain('warning')
    expect(config.defaultWidth).toBe(208) // w-52
  })

  it('returns correct config for termination node', () => {
    const config = getNodeConfig('termination')
    expect(config.colorClass).toContain('success')
  })

  it('returns an icon component for every node type', () => {
    for (const type of ALL_TYPES) {
      const config = getNodeConfig(type)
      expect(config.icon).toBeDefined()
      // Lucide icons are React forwardRef objects, not plain functions
      expect(typeof config.icon === 'function' || typeof config.icon === 'object').toBe(true)
    }
  })

  it('returns defaultWidth and defaultHeight for every type', () => {
    for (const type of ALL_TYPES) {
      const config = getNodeConfig(type)
      expect(config.defaultWidth).toBeGreaterThan(0)
      expect(config.defaultHeight).toBeGreaterThan(0)
    }
  })
})

describe('getDefaultProperties', () => {
  it('returns empty string defaults for capture node text fields', () => {
    const props = getDefaultProperties('capture')
    expect(props.sample_filename).toBe('')
    expect(props.filename_regex).toBe('')
  })

  it('returns select default for capture camera_id_group', () => {
    const props = getDefaultProperties('capture')
    expect(props.camera_id_group).toBe('1')
  })

  it('returns extension and optional defaults for file node', () => {
    const props = getDefaultProperties('file')
    expect(props.extension).toBe('')
    expect(props.optional).toBe(false)
  })

  it('returns empty array for process node method_ids', () => {
    const props = getDefaultProperties('process')
    expect(props.method_ids).toEqual([])
  })

  it('returns empty object for pairing node (no properties)', () => {
    const props = getDefaultProperties('pairing')
    expect(Object.keys(props)).toHaveLength(0)
  })

  it('returns empty object for branching node (no properties)', () => {
    const props = getDefaultProperties('branching')
    expect(Object.keys(props)).toHaveLength(0)
  })

  it('returns termination_type default for termination node', () => {
    const props = getDefaultProperties('termination')
    expect(props.termination_type).toBe('Black Box Archive')
  })
})
