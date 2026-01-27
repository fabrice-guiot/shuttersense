/**
 * FolderTree Component
 *
 * Renders the complete folder tree with:
 * - Virtualization for 10k+ folders (tanstack-virtual)
 * - Search/filter functionality
 * - Selection management with hierarchy constraints
 * - Visual indicators for mapped folders
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T045, T046, T047, T048
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Search, FolderTree as FolderTreeIcon, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { InventoryFolder, FolderTreeNode as TreeNodeType } from '@/contracts/api/inventory-api'
import {
  buildFolderTree,
  filterTree,
  togglePathSelection,
  getSelectionSummary,
  type FolderSelectionState
} from '@/utils/folder-selection'
import { formatFileSize } from '@/utils/name-suggestion'
import { FolderTreeNode } from './FolderTreeNode'

// ============================================================================
// Types
// ============================================================================

export interface FolderTreeProps {
  /** List of folders from the API */
  folders: InventoryFolder[]
  /** Whether folders are being loaded */
  loading?: boolean
  /** Paths of already-mapped folders */
  mappedPaths?: Set<string>
  /** Called when selection changes */
  onSelectionChange?: (selectedPaths: Set<string>) => void
  /** Initial selected paths */
  initialSelection?: Set<string>
  /** Maximum height of the tree (for virtualization) */
  maxHeight?: number
}

// ============================================================================
// Flatten tree for virtualization
// ============================================================================

interface FlatNode {
  node: TreeNodeType
  depth: number
}

function flattenTreeWithDepth(
  nodes: TreeNodeType[],
  depth: number = 0
): FlatNode[] {
  const result: FlatNode[] = []

  for (const node of nodes) {
    result.push({ node, depth })
    if (node.isExpanded && node.children.length > 0) {
      result.push(...flattenTreeWithDepth(node.children, depth + 1))
    }
  }

  return result
}

// ============================================================================
// Component
// ============================================================================

export function FolderTree({
  folders,
  loading = false,
  mappedPaths = new Set(),
  onSelectionChange,
  initialSelection = new Set(),
  maxHeight = 400
}: FolderTreeProps) {
  // Selection state
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(initialSelection)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')

  // Expansion state (tracked separately for performance)
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())

  // Ref for virtualized container
  const parentRef = useRef<HTMLDivElement>(null)

  // Build selection state
  const selectionState: FolderSelectionState = useMemo(
    () => ({
      selectedPaths,
      mappedPaths
    }),
    [selectedPaths, mappedPaths]
  )

  // Build and filter tree
  const tree = useMemo(() => {
    const builtTree = buildFolderTree(folders, selectionState)

    // Apply expansion state
    const applyExpansion = (nodes: TreeNodeType[]): TreeNodeType[] => {
      return nodes.map(node => ({
        ...node,
        isExpanded: expandedPaths.has(node.path),
        children: applyExpansion(node.children)
      }))
    }

    let result = applyExpansion(builtTree)

    // Apply search filter
    if (searchQuery.trim()) {
      result = filterTree(result, searchQuery)
    }

    return result
  }, [folders, selectionState, expandedPaths, searchQuery])

  // Flatten for virtualization
  const flatNodes = useMemo(() => flattenTreeWithDepth(tree), [tree])

  // Setup virtualizer
  const virtualizer = useVirtualizer({
    count: flatNodes.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36, // Approximate row height
    overscan: 10
  })

  // Handle selection toggle
  const handleSelect = useCallback(
    (path: string, _selected: boolean) => {
      setSelectedPaths(prev => {
        const newState = togglePathSelection(path, {
          selectedPaths: prev,
          mappedPaths
        })

        // Only update if actually changed
        if (newState.selectedPaths !== prev) {
          onSelectionChange?.(newState.selectedPaths)
        }

        return newState.selectedPaths
      })
    },
    [mappedPaths, onSelectionChange]
  )

  // Handle expansion toggle
  const handleToggle = useCallback((path: string, expanded: boolean) => {
    setExpandedPaths(prev => {
      const next = new Set(prev)
      if (expanded) {
        next.add(path)
      } else {
        next.delete(path)
      }
      return next
    })
  }, [])

  // Expand/collapse all
  const handleExpandAll = useCallback(() => {
    const allPaths = new Set<string>()
    const collectPaths = (nodes: TreeNodeType[]) => {
      for (const node of nodes) {
        if (node.children.length > 0) {
          allPaths.add(node.path)
          collectPaths(node.children)
        }
      }
    }
    collectPaths(tree)
    setExpandedPaths(allPaths)
  }, [tree])

  const handleCollapseAll = useCallback(() => {
    setExpandedPaths(new Set())
  }, [])

  // Get selection summary
  const summary = useMemo(
    () => getSelectionSummary(selectedPaths, folders),
    [selectedPaths, folders]
  )

  // Sync initial selection
  useEffect(() => {
    if (initialSelection.size > 0 && selectedPaths.size === 0) {
      setSelectedPaths(initialSelection)
    }
  }, [initialSelection])

  // Notify parent of selection changes
  useEffect(() => {
    onSelectionChange?.(selectedPaths)
  }, [selectedPaths, onSelectionChange])

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search folders..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Expand/Collapse Controls */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={handleExpandAll}>
            <ChevronDown className="h-4 w-4 mr-1" />
            Expand All
          </Button>
          <Button variant="ghost" size="sm" onClick={handleCollapseAll}>
            <ChevronUp className="h-4 w-4 mr-1" />
            Collapse All
          </Button>
        </div>
      </div>

      {/* Selection Summary */}
      {summary.count > 0 && (
        <div className="flex items-center gap-4 p-2 bg-primary/5 rounded-md text-sm">
          <span className="font-medium text-primary">
            {summary.count} folder{summary.count !== 1 ? 's' : ''} selected
          </span>
          <span className="text-muted-foreground">
            {summary.totalObjects.toLocaleString()} files
          </span>
          <span className="text-muted-foreground">
            {formatFileSize(summary.totalSize)}
          </span>
        </div>
      )}

      {/* Tree Container */}
      <div
        ref={parentRef}
        className="border rounded-md overflow-auto"
        style={{ height: maxHeight }}
      >
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading folders...</span>
          </div>
        ) : flatNodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <FolderTreeIcon className="h-12 w-12 mb-2 opacity-50" />
            {searchQuery ? (
              <p>No folders match "{searchQuery}"</p>
            ) : (
              <p>No folders available</p>
            )}
          </div>
        ) : (
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative'
            }}
          >
            {virtualizer.getVirtualItems().map(virtualRow => {
              const { node, depth } = flatNodes[virtualRow.index]
              return (
                <div
                  key={node.path}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`
                  }}
                >
                  <FolderTreeNode
                    node={node}
                    depth={depth}
                    onSelect={handleSelect}
                    onToggle={handleToggle}
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {folders.length.toLocaleString()} total folder{folders.length !== 1 ? 's' : ''}
        </span>
        <span>
          {mappedPaths.size} already mapped
        </span>
      </div>
    </div>
  )
}
