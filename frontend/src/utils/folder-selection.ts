/**
 * Folder Selection Utilities
 *
 * Logic for managing hierarchical folder selection with constraints:
 * - No ancestor/descendant overlap (prevents nested collection paths)
 * - Already-mapped folders are disabled
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T046
 */

import type { InventoryFolder, FolderTreeNode } from '@/contracts/api/inventory-api'

// ============================================================================
// Path Hierarchy Utilities
// ============================================================================

/**
 * Check if a path is an ancestor of another path.
 * @param possibleAncestor - The path that might be an ancestor
 * @param path - The path to check against
 * @returns True if possibleAncestor is an ancestor of path
 *
 * @example
 * isAncestor('2020/', '2020/Events/') // true
 * isAncestor('2020/Events/', '2020/') // false
 * isAncestor('2020/', '2021/') // false
 */
export function isAncestor(possibleAncestor: string, path: string): boolean {
  if (possibleAncestor === path) return false
  // Ensure both paths end with /
  const normalizedAncestor = possibleAncestor.endsWith('/') ? possibleAncestor : `${possibleAncestor}/`
  const normalizedPath = path.endsWith('/') ? path : `${path}/`
  return normalizedPath.startsWith(normalizedAncestor)
}

/**
 * Check if a path is a descendant of another path.
 * @param possibleDescendant - The path that might be a descendant
 * @param path - The path to check against
 * @returns True if possibleDescendant is a descendant of path
 */
export function isDescendant(possibleDescendant: string, path: string): boolean {
  return isAncestor(path, possibleDescendant)
}

/**
 * Get all ancestor paths for a given path.
 * @param path - The path to get ancestors for
 * @returns Array of ancestor paths (from root to immediate parent)
 *
 * @example
 * getAncestorPaths('2020/Events/Wedding/')
 * // Returns: ['2020/', '2020/Events/']
 */
export function getAncestorPaths(path: string): string[] {
  const parts = path.split('/').filter(Boolean)
  const ancestors: string[] = []

  for (let i = 1; i < parts.length; i++) {
    ancestors.push(parts.slice(0, i).join('/') + '/')
  }

  return ancestors
}

/**
 * Check if two paths have any hierarchical relationship.
 * @returns True if one path is an ancestor or descendant of the other
 */
export function hasHierarchicalRelation(path1: string, path2: string): boolean {
  return isAncestor(path1, path2) || isDescendant(path1, path2)
}

// ============================================================================
// Selection State Management
// ============================================================================

export interface FolderSelectionState {
  selectedPaths: Set<string>
  mappedPaths: Set<string>
}

/**
 * Check if a path can be selected given current selection state.
 * A path cannot be selected if:
 * 1. It is already mapped to a collection
 * 2. Any of its ancestors is selected
 * 3. Any of its descendants is selected
 *
 * @returns { canSelect, reason } - Whether the path can be selected and why not if disabled
 */
export function canSelectPath(
  path: string,
  state: FolderSelectionState
): { canSelect: boolean; reason?: string } {
  // Already mapped paths cannot be selected
  if (state.mappedPaths.has(path)) {
    return { canSelect: false, reason: 'Already mapped to a collection' }
  }

  // Check if any ancestor is selected
  const ancestors = getAncestorPaths(path)
  for (const ancestor of ancestors) {
    if (state.selectedPaths.has(ancestor)) {
      return {
        canSelect: false,
        reason: `Parent folder "${ancestor}" is already selected`
      }
    }
  }

  // Check if any descendant is selected
  for (const selectedPath of state.selectedPaths) {
    if (isDescendant(selectedPath, path)) {
      return {
        canSelect: false,
        reason: `A subfolder is already selected`
      }
    }
  }

  return { canSelect: true }
}

/**
 * Toggle selection of a path, enforcing hierarchy constraints.
 * Returns the new selection state.
 */
export function togglePathSelection(
  path: string,
  state: FolderSelectionState
): FolderSelectionState {
  const newSelected = new Set(state.selectedPaths)

  if (newSelected.has(path)) {
    // Deselect
    newSelected.delete(path)
  } else {
    // Check if we can select
    const { canSelect } = canSelectPath(path, state)
    if (canSelect) {
      newSelected.add(path)
    }
  }

  return {
    ...state,
    selectedPaths: newSelected
  }
}

/**
 * Get paths that should be disabled (not selectable) based on current selection.
 * Returns a map of path -> reason for being disabled.
 */
export function getDisabledPaths(
  allPaths: string[],
  state: FolderSelectionState
): Map<string, string> {
  const disabled = new Map<string, string>()

  for (const path of allPaths) {
    const { canSelect, reason } = canSelectPath(path, state)
    if (!canSelect && reason) {
      disabled.set(path, reason)
    }
  }

  return disabled
}

// ============================================================================
// Tree Building
// ============================================================================

/**
 * Build a tree structure from flat folder list.
 * Groups folders by their parent paths and maintains hierarchy.
 */
export function buildFolderTree(
  folders: InventoryFolder[],
  selectionState: FolderSelectionState
): FolderTreeNode[] {
  // Create a map for quick lookup
  const folderMap = new Map<string, InventoryFolder>()
  for (const folder of folders) {
    folderMap.set(folder.path, folder)
  }

  // Get all unique paths including implicit parent paths
  const allPaths = new Set<string>()
  for (const folder of folders) {
    allPaths.add(folder.path)
    // Add ancestor paths that might not be in the folder list
    const ancestors = getAncestorPaths(folder.path)
    for (const ancestor of ancestors) {
      allPaths.add(ancestor)
    }
  }

  // Build nodes for each path
  const nodeMap = new Map<string, FolderTreeNode>()

  for (const path of allPaths) {
    const folder = folderMap.get(path)
    const parts = path.split('/').filter(Boolean)
    const rawName = parts[parts.length - 1] || path
    // Decode URL-encoded characters (e.g., %2C -> comma, %20 -> space)
    const name = decodeURIComponent(rawName)

    const isMapped = folder?.collection_guid !== null && folder?.collection_guid !== undefined
    const { canSelect, reason } = canSelectPath(path, selectionState)

    // Determine if disabled - either from selection constraints or backend's is_mappable
    // Backend marks folders as not mappable when ancestors or descendants are already mapped to collections
    let isDisabled = !canSelect
    let disabledReason = reason

    if (folder && !folder.is_mappable && !isMapped) {
      isDisabled = true
      disabledReason = disabledReason || 'A parent or child folder is already mapped to a collection'
    }

    const node: FolderTreeNode = {
      path,
      name,
      objectCount: folder?.object_count ?? 0,
      totalSize: folder?.total_size_bytes ?? 0,
      children: [],
      isExpanded: false,
      isSelected: selectionState.selectedPaths.has(path),
      isMapped,
      isDisabled,
      disabledReason
    }

    nodeMap.set(path, node)
  }

  // Build parent-child relationships
  const rootNodes: FolderTreeNode[] = []

  for (const [path, node] of nodeMap) {
    const parentPath = getParentPath(path)

    if (parentPath && nodeMap.has(parentPath)) {
      const parent = nodeMap.get(parentPath)!
      parent.children.push(node)
    } else {
      rootNodes.push(node)
    }
  }

  // Sort children alphabetically at each level
  const sortNodes = (nodes: FolderTreeNode[]) => {
    nodes.sort((a, b) => a.name.localeCompare(b.name))
    for (const node of nodes) {
      sortNodes(node.children)
    }
  }
  sortNodes(rootNodes)

  return rootNodes
}

/**
 * Get the parent path of a folder path.
 * @example
 * getParentPath('2020/Events/Wedding/') // '2020/Events/'
 * getParentPath('2020/') // null
 */
export function getParentPath(path: string): string | null {
  const parts = path.split('/').filter(Boolean)
  if (parts.length <= 1) return null
  return parts.slice(0, -1).join('/') + '/'
}

/**
 * Flatten a tree back to a list of paths (for search/filter).
 */
export function flattenTree(nodes: FolderTreeNode[]): FolderTreeNode[] {
  const result: FolderTreeNode[] = []

  const traverse = (nodeList: FolderTreeNode[]) => {
    for (const node of nodeList) {
      result.push(node)
      traverse(node.children)
    }
  }

  traverse(nodes)
  return result
}

/**
 * Filter tree nodes by search query (matches on name or path).
 */
export function filterTree(
  nodes: FolderTreeNode[],
  query: string
): FolderTreeNode[] {
  if (!query.trim()) return nodes

  const lowerQuery = query.toLowerCase()

  const matchNode = (node: FolderTreeNode): FolderTreeNode | null => {
    const nameMatches = node.name.toLowerCase().includes(lowerQuery)
    const pathMatches = node.path.toLowerCase().includes(lowerQuery)

    // Recursively filter children
    const filteredChildren = node.children
      .map(matchNode)
      .filter((n): n is FolderTreeNode => n !== null)

    // Include this node if it matches or has matching children
    if (nameMatches || pathMatches || filteredChildren.length > 0) {
      return {
        ...node,
        children: filteredChildren,
        isExpanded: filteredChildren.length > 0 // Auto-expand if has matching children
      }
    }

    return null
  }

  return nodes
    .map(matchNode)
    .filter((n): n is FolderTreeNode => n !== null)
}

// ============================================================================
// Selection Summary
// ============================================================================

/**
 * Get summary statistics for selected folders.
 */
export function getSelectionSummary(
  selectedPaths: Set<string>,
  folders: InventoryFolder[]
): {
  count: number
  totalObjects: number
  totalSize: number
} {
  let totalObjects = 0
  let totalSize = 0

  for (const folder of folders) {
    if (selectedPaths.has(folder.path)) {
      totalObjects += folder.object_count
      totalSize += folder.total_size_bytes
    }
  }

  return {
    count: selectedPaths.size,
    totalObjects,
    totalSize
  }
}
