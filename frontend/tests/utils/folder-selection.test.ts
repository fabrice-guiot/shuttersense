/**
 * Unit tests for folder selection utilities.
 *
 * Tests cover:
 *   - isAncestor() - Path hierarchy detection
 *   - isDescendant() - Inverse hierarchy detection
 *   - getAncestorPaths() - Ancestor path extraction
 *   - hasHierarchicalRelation() - Combined hierarchy check
 *   - canSelectPath() - Selection constraint validation
 *   - togglePathSelection() - Selection state management
 *   - getDisabledPaths() - Bulk disabled path calculation
 *   - buildFolderTree() - Tree construction from flat list
 *   - filterTree() - Search filtering
 *   - getSelectionSummary() - Selection statistics
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T046a
 */

import { describe, it, expect } from 'vitest'
import {
  isAncestor,
  isDescendant,
  getAncestorPaths,
  hasHierarchicalRelation,
  canSelectPath,
  togglePathSelection,
  getDisabledPaths,
  buildFolderTree,
  filterTree,
  getParentPath,
  flattenTree,
  getSelectionSummary,
  type FolderSelectionState
} from '@/utils/folder-selection'
import type { InventoryFolder } from '@/contracts/api/inventory-api'

// ============================================================================
// Path Hierarchy Tests
// ============================================================================

describe('isAncestor', () => {
  it('should return true when path is ancestor', () => {
    expect(isAncestor('2020/', '2020/Events/')).toBe(true)
    expect(isAncestor('2020/', '2020/Events/Wedding/')).toBe(true)
    expect(isAncestor('photos/', 'photos/2020/summer/')).toBe(true)
  })

  it('should return false when path is not ancestor', () => {
    expect(isAncestor('2020/Events/', '2020/')).toBe(false)
    expect(isAncestor('2021/', '2020/Events/')).toBe(false)
    expect(isAncestor('photos/2020/', 'photos/2021/')).toBe(false)
  })

  it('should return false for same path', () => {
    expect(isAncestor('2020/', '2020/')).toBe(false)
    expect(isAncestor('2020/Events/', '2020/Events/')).toBe(false)
  })

  it('should handle paths without trailing slash', () => {
    expect(isAncestor('2020', '2020/Events/')).toBe(true)
    expect(isAncestor('2020/', '2020/Events')).toBe(true)
    expect(isAncestor('2020', '2020/Events')).toBe(true)
  })

  it('should not match partial folder names', () => {
    // "photo" should not be ancestor of "photos/"
    expect(isAncestor('photo/', 'photos/')).toBe(false)
    expect(isAncestor('2020/', '2020-backup/')).toBe(false)
  })
})

describe('isDescendant', () => {
  it('should return true when path is descendant', () => {
    expect(isDescendant('2020/Events/', '2020/')).toBe(true)
    expect(isDescendant('2020/Events/Wedding/', '2020/')).toBe(true)
  })

  it('should return false when path is not descendant', () => {
    expect(isDescendant('2020/', '2020/Events/')).toBe(false)
    expect(isDescendant('2021/', '2020/')).toBe(false)
  })

  it('should return false for same path', () => {
    expect(isDescendant('2020/', '2020/')).toBe(false)
  })
})

describe('getAncestorPaths', () => {
  it('should return all ancestor paths', () => {
    const ancestors = getAncestorPaths('2020/Events/Wedding/')
    expect(ancestors).toEqual(['2020/', '2020/Events/'])
  })

  it('should return empty array for root-level path', () => {
    const ancestors = getAncestorPaths('2020/')
    expect(ancestors).toEqual([])
  })

  it('should handle paths without trailing slash', () => {
    const ancestors = getAncestorPaths('2020/Events/Wedding')
    expect(ancestors).toEqual(['2020/', '2020/Events/'])
  })

  it('should handle deeply nested paths', () => {
    const ancestors = getAncestorPaths('a/b/c/d/e/')
    expect(ancestors).toEqual(['a/', 'a/b/', 'a/b/c/', 'a/b/c/d/'])
  })
})

describe('hasHierarchicalRelation', () => {
  it('should return true when one is ancestor of other', () => {
    expect(hasHierarchicalRelation('2020/', '2020/Events/')).toBe(true)
    expect(hasHierarchicalRelation('2020/Events/', '2020/')).toBe(true)
  })

  it('should return false when no relation', () => {
    expect(hasHierarchicalRelation('2020/', '2021/')).toBe(false)
    expect(hasHierarchicalRelation('2020/Events/', '2020/Photos/')).toBe(false)
  })
})

describe('getParentPath', () => {
  it('should return parent path', () => {
    expect(getParentPath('2020/Events/Wedding/')).toBe('2020/Events/')
    expect(getParentPath('2020/Events/')).toBe('2020/')
  })

  it('should return null for root-level path', () => {
    expect(getParentPath('2020/')).toBe(null)
    expect(getParentPath('photos/')).toBe(null)
  })
})

// ============================================================================
// Selection State Tests
// ============================================================================

describe('canSelectPath', () => {
  it('should allow selecting path with empty state', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }
    const result = canSelectPath('2020/', state)
    expect(result.canSelect).toBe(true)
    expect(result.reason).toBeUndefined()
  })

  it('should disallow selecting already mapped path', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set(['2020/'])
    }
    const result = canSelectPath('2020/', state)
    expect(result.canSelect).toBe(false)
    expect(result.reason).toContain('Already mapped')
  })

  it('should disallow selecting when ancestor is selected', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set()
    }
    const result = canSelectPath('2020/Events/', state)
    expect(result.canSelect).toBe(false)
    expect(result.reason).toContain('Parent folder')
    expect(result.reason).toContain('2020/')
  })

  it('should disallow selecting when descendant is selected', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/Events/']),
      mappedPaths: new Set()
    }
    const result = canSelectPath('2020/', state)
    expect(result.canSelect).toBe(false)
    expect(result.reason).toContain('subfolder')
  })

  it('should allow selecting sibling paths', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/Events/']),
      mappedPaths: new Set()
    }
    const result = canSelectPath('2020/Photos/', state)
    expect(result.canSelect).toBe(true)
  })

  it('should allow selecting unrelated paths', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set()
    }
    const result = canSelectPath('2021/', state)
    expect(result.canSelect).toBe(true)
  })
})

describe('togglePathSelection', () => {
  it('should add path to selection', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }
    const newState = togglePathSelection('2020/', state)
    expect(newState.selectedPaths.has('2020/')).toBe(true)
  })

  it('should remove path from selection', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set()
    }
    const newState = togglePathSelection('2020/', state)
    expect(newState.selectedPaths.has('2020/')).toBe(false)
  })

  it('should not add path if cannot select', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set()
    }
    const newState = togglePathSelection('2020/Events/', state)
    // Should not add because ancestor is selected
    expect(newState.selectedPaths.has('2020/Events/')).toBe(false)
    expect(newState.selectedPaths.has('2020/')).toBe(true)
  })

  it('should preserve mapped paths', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set(['mapped/'])
    }
    const newState = togglePathSelection('2020/', state)
    expect(newState.mappedPaths.has('mapped/')).toBe(true)
  })
})

describe('getDisabledPaths', () => {
  it('should return disabled paths with reasons', () => {
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set(['mapped/'])
    }
    const allPaths = ['2020/', '2020/Events/', '2021/', 'mapped/']
    const disabled = getDisabledPaths(allPaths, state)

    expect(disabled.has('2020/Events/')).toBe(true)
    expect(disabled.get('2020/Events/')).toContain('Parent folder')
    expect(disabled.has('mapped/')).toBe(true)
    expect(disabled.get('mapped/')).toContain('Already mapped')
    expect(disabled.has('2021/')).toBe(false)
  })
})

// ============================================================================
// Tree Building Tests
// ============================================================================

describe('buildFolderTree', () => {
  const createFolder = (path: string, objectCount = 10, totalSize = 1000): InventoryFolder => ({
    guid: `fld_${path.replace(/\//g, '')}`,
    path,
    object_count: objectCount,
    total_size_bytes: totalSize,
    deepest_modified: '2026-01-01T00:00:00Z',
    discovered_at: '2026-01-01T00:00:00Z',
    collection_guid: null,
    suggested_name: null,
    is_mappable: true
  })

  it('should build tree from flat folder list', () => {
    const folders: InventoryFolder[] = [
      createFolder('2020/'),
      createFolder('2020/Events/'),
      createFolder('2020/Events/Wedding/'),
      createFolder('2021/')
    ]
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)

    expect(tree).toHaveLength(2) // 2020/ and 2021/
    expect(tree[0].name).toBe('2020')
    expect(tree[0].children).toHaveLength(1) // Events/
    expect(tree[0].children[0].name).toBe('Events')
    expect(tree[0].children[0].children).toHaveLength(1) // Wedding/
  })

  it('should mark selected nodes', () => {
    const folders: InventoryFolder[] = [createFolder('2020/')]
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)
    expect(tree[0].isSelected).toBe(true)
  })

  it('should mark mapped nodes', () => {
    const folders: InventoryFolder[] = [{
      ...createFolder('2020/'),
      collection_guid: 'col_test123'
    }]
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)
    expect(tree[0].isMapped).toBe(true)
  })

  it('should mark disabled nodes with reason', () => {
    const folders: InventoryFolder[] = [
      createFolder('2020/'),
      createFolder('2020/Events/')
    ]
    const state: FolderSelectionState = {
      selectedPaths: new Set(['2020/']),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)
    const eventsNode = tree[0].children[0]
    expect(eventsNode.isDisabled).toBe(true)
    expect(eventsNode.disabledReason).toContain('Parent folder')
  })

  it('should sort children alphabetically', () => {
    const folders: InventoryFolder[] = [
      createFolder('photos/'),
      createFolder('archive/'),
      createFolder('backups/')
    ]
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)
    expect(tree[0].name).toBe('archive')
    expect(tree[1].name).toBe('backups')
    expect(tree[2].name).toBe('photos')
  })

  it('should create implicit parent nodes', () => {
    // Only have deep path, but parent should be created
    const folders: InventoryFolder[] = [
      createFolder('2020/Events/Wedding/')
    ]
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)
    expect(tree).toHaveLength(1)
    expect(tree[0].name).toBe('2020')
    expect(tree[0].objectCount).toBe(0) // Implicit parent has no data
    expect(tree[0].children[0].name).toBe('Events')
    expect(tree[0].children[0].children[0].name).toBe('Wedding')
    expect(tree[0].children[0].children[0].objectCount).toBe(10) // Real folder has data
  })
})

describe('flattenTree', () => {
  it('should flatten tree to list', () => {
    const folders: InventoryFolder[] = [
      {
        guid: 'fld_1',
        path: '2020/',
        object_count: 10,
        total_size_bytes: 1000,
        deepest_modified: '2026-01-01T00:00:00Z',
        discovered_at: '2026-01-01T00:00:00Z',
        collection_guid: null,
        suggested_name: null,
        is_mappable: true
      },
      {
        guid: 'fld_2',
        path: '2020/Events/',
        object_count: 5,
        total_size_bytes: 500,
        deepest_modified: '2026-01-01T00:00:00Z',
        discovered_at: '2026-01-01T00:00:00Z',
        collection_guid: null,
        suggested_name: null,
        is_mappable: true
      }
    ]
    const state: FolderSelectionState = {
      selectedPaths: new Set(),
      mappedPaths: new Set()
    }

    const tree = buildFolderTree(folders, state)
    const flat = flattenTree(tree)

    expect(flat).toHaveLength(2)
    expect(flat[0].path).toBe('2020/')
    expect(flat[1].path).toBe('2020/Events/')
  })
})

// ============================================================================
// Tree Filtering Tests
// ============================================================================

describe('filterTree', () => {
  const createTreeNode = (name: string, path: string, children: any[] = []) => ({
    path,
    name,
    objectCount: 10,
    totalSize: 1000,
    children,
    isExpanded: false,
    isSelected: false,
    isMapped: false,
    isDisabled: false
  })

  it('should filter nodes by name match', () => {
    const tree = [
      createTreeNode('2020', '2020/', [
        createTreeNode('Events', '2020/Events/'),
        createTreeNode('Photos', '2020/Photos/')
      ]),
      createTreeNode('2021', '2021/')
    ]

    const filtered = filterTree(tree, 'Events')
    expect(filtered).toHaveLength(1) // Only 2020
    expect(filtered[0].children).toHaveLength(1) // Only Events
    expect(filtered[0].children[0].name).toBe('Events')
  })

  it('should filter nodes by path match', () => {
    const tree = [
      createTreeNode('2020', '2020/'),
      createTreeNode('2021', '2021/')
    ]

    const filtered = filterTree(tree, '2020')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].name).toBe('2020')
  })

  it('should be case insensitive', () => {
    const tree = [
      createTreeNode('Events', 'Events/')
    ]

    const filtered = filterTree(tree, 'events')
    expect(filtered).toHaveLength(1)
  })

  it('should return all nodes for empty query', () => {
    const tree = [
      createTreeNode('2020', '2020/'),
      createTreeNode('2021', '2021/')
    ]

    const filtered = filterTree(tree, '')
    expect(filtered).toHaveLength(2)
  })

  it('should auto-expand nodes with matching children', () => {
    const tree = [
      createTreeNode('2020', '2020/', [
        createTreeNode('Wedding', '2020/Wedding/')
      ])
    ]

    const filtered = filterTree(tree, 'Wedding')
    expect(filtered[0].isExpanded).toBe(true)
  })

  it('should include parent when child matches', () => {
    const tree = [
      createTreeNode('2020', '2020/', [
        createTreeNode('Events', '2020/Events/', [
          createTreeNode('Wedding', '2020/Events/Wedding/')
        ])
      ])
    ]

    const filtered = filterTree(tree, 'Wedding')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].name).toBe('2020')
    expect(filtered[0].children[0].name).toBe('Events')
    expect(filtered[0].children[0].children[0].name).toBe('Wedding')
  })
})

// ============================================================================
// Selection Summary Tests
// ============================================================================

describe('getSelectionSummary', () => {
  const createFolder = (path: string, objectCount: number, totalSize: number): InventoryFolder => ({
    guid: `fld_${path.replace(/\//g, '')}`,
    path,
    object_count: objectCount,
    total_size_bytes: totalSize,
    deepest_modified: '2026-01-01T00:00:00Z',
    discovered_at: '2026-01-01T00:00:00Z',
    collection_guid: null,
    suggested_name: null,
    is_mappable: true
  })

  it('should return count of selected folders', () => {
    const folders = [
      createFolder('2020/', 100, 1000),
      createFolder('2021/', 200, 2000)
    ]
    const selected = new Set(['2020/', '2021/'])

    const summary = getSelectionSummary(selected, folders)
    expect(summary.count).toBe(2)
  })

  it('should sum object counts of selected folders', () => {
    const folders = [
      createFolder('2020/', 100, 1000),
      createFolder('2021/', 200, 2000)
    ]
    const selected = new Set(['2020/', '2021/'])

    const summary = getSelectionSummary(selected, folders)
    expect(summary.totalObjects).toBe(300)
  })

  it('should sum sizes of selected folders', () => {
    const folders = [
      createFolder('2020/', 100, 1000),
      createFolder('2021/', 200, 2000)
    ]
    const selected = new Set(['2020/', '2021/'])

    const summary = getSelectionSummary(selected, folders)
    expect(summary.totalSize).toBe(3000)
  })

  it('should return zeros for empty selection', () => {
    const folders = [createFolder('2020/', 100, 1000)]
    const selected = new Set<string>()

    const summary = getSelectionSummary(selected, folders)
    expect(summary.count).toBe(0)
    expect(summary.totalObjects).toBe(0)
    expect(summary.totalSize).toBe(0)
  })

  it('should only count selected folders', () => {
    const folders = [
      createFolder('2020/', 100, 1000),
      createFolder('2021/', 200, 2000),
      createFolder('2022/', 300, 3000)
    ]
    const selected = new Set(['2020/'])

    const summary = getSelectionSummary(selected, folders)
    expect(summary.count).toBe(1)
    expect(summary.totalObjects).toBe(100)
    expect(summary.totalSize).toBe(1000)
  })
})
