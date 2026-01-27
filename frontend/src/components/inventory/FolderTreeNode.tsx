/**
 * FolderTreeNode Component
 *
 * Renders a single node in the folder tree with:
 * - Expand/collapse toggle for nodes with children
 * - Checkbox for selection (with disabled state)
 * - Visual indicators for mapped folders
 * - File count and size display
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T044
 */

import { ChevronRight, Folder, FolderOpen, Link2, FolderCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import type { FolderTreeNode as TreeNodeType } from '@/contracts/api/inventory-api'
import { formatFileSize } from '@/utils/name-suggestion'

// ============================================================================
// Types
// ============================================================================

export interface FolderTreeNodeProps {
  /** Tree node data */
  node: TreeNodeType
  /** Nesting depth (for indentation) */
  depth?: number
  /** Called when node is selected/deselected */
  onSelect?: (path: string, selected: boolean) => void
  /** Called when node is expanded/collapsed */
  onToggle?: (path: string, expanded: boolean) => void
}

// ============================================================================
// Component
// ============================================================================

export function FolderTreeNode({
  node,
  depth = 0,
  onSelect,
  onToggle
}: FolderTreeNodeProps) {
  const hasChildren = node.children.length > 0
  const indentPx = depth * 20

  const handleCheckboxChange = (checked: boolean | 'indeterminate') => {
    if (checked !== 'indeterminate') {
      onSelect?.(node.path, checked)
    }
  }

  const handleToggleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (hasChildren) {
      onToggle?.(node.path, !node.isExpanded)
    }
  }

  const handleRowClick = () => {
    if (!node.isDisabled && !node.isMapped) {
      onSelect?.(node.path, !node.isSelected)
    }
  }

  // Determine which icon to show
  const FolderIcon = node.isMapped
    ? FolderCheck
    : node.isExpanded
      ? FolderOpen
      : Folder

  return (
    <>
      <div
        className={cn(
          'flex items-center gap-2 py-1.5 px-2 rounded-md transition-colors',
          'hover:bg-muted/50',
          node.isSelected && 'bg-primary/10',
          node.isDisabled && 'opacity-50',
          !node.isDisabled && !node.isMapped && 'cursor-pointer'
        )}
        style={{ paddingLeft: `${indentPx + 8}px` }}
        onClick={handleRowClick}
      >
        {/* Expand/Collapse Toggle */}
        <button
          type="button"
          className={cn(
            'p-0.5 rounded hover:bg-muted transition-colors',
            !hasChildren && 'invisible'
          )}
          onClick={handleToggleClick}
          aria-label={node.isExpanded ? 'Collapse' : 'Expand'}
        >
          <ChevronRight
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform',
              node.isExpanded && 'rotate-90'
            )}
          />
        </button>

        {/* Selection Checkbox */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div onClick={e => e.stopPropagation()}>
              <Checkbox
                checked={node.isSelected}
                onCheckedChange={handleCheckboxChange}
                disabled={node.isDisabled || node.isMapped}
                aria-label={`Select ${node.name}`}
              />
            </div>
          </TooltipTrigger>
          {(node.isDisabled || node.isMapped) && (
            <TooltipContent side="right">
              {node.isMapped
                ? 'Already mapped to a collection'
                : node.disabledReason}
            </TooltipContent>
          )}
        </Tooltip>

        {/* Folder Icon */}
        <FolderIcon
          className={cn(
            'h-4 w-4 flex-shrink-0',
            node.isMapped
              ? 'text-success'
              : node.isSelected
                ? 'text-primary'
                : 'text-muted-foreground'
          )}
        />

        {/* Folder Name */}
        <span
          className={cn(
            'flex-1 truncate text-sm',
            node.isSelected && 'font-medium',
            node.isMapped && 'text-muted-foreground'
          )}
        >
          {node.name}
        </span>

        {/* Mapped Indicator */}
        {node.isMapped && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Link2 className="h-3.5 w-3.5 text-success flex-shrink-0" />
            </TooltipTrigger>
            <TooltipContent>Mapped to collection</TooltipContent>
          </Tooltip>
        )}

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground flex-shrink-0">
          {node.objectCount > 0 && (
            <span>{node.objectCount.toLocaleString()} files</span>
          )}
          {node.totalSize > 0 && (
            <span className="w-16 text-right">{formatFileSize(node.totalSize)}</span>
          )}
        </div>
      </div>
    </>
  )
}
