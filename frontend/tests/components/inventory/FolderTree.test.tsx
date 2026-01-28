/**
 * FolderTree Component Tests
 *
 * Tests for the folder tree component including:
 * - Rendering folders with proper hierarchy
 * - Search/filter functionality
 * - Selection management with hierarchy constraints
 * - Expand/collapse functionality
 * - Mapped folder visual indicators
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T049
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { FolderTree } from '@/components/inventory/FolderTree'
import type { InventoryFolder } from '@/contracts/api/inventory-api'

// Mock @tanstack/react-virtual since JSDOM doesn't have real dimensions
vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        index,
        key: index,
        start: index * 36,
        size: 36
      })),
    getTotalSize: () => count * 36,
    scrollToIndex: vi.fn()
  })
}))

// ============================================================================
// Test Data
// ============================================================================

const createFolder = (
  path: string,
  overrides: Partial<InventoryFolder> = {}
): InventoryFolder => ({
  guid: `folder_${path.replace(/\//g, '_')}`,
  path,
  object_count: 100,
  total_size_bytes: 1024 * 1024,
  deepest_modified: '2024-01-15T10:00:00Z',
  discovered_at: '2024-01-01T00:00:00Z',
  collection_guid: null,
  suggested_name: path.split('/').filter(Boolean).pop() || path,
  is_mappable: true,
  ...overrides
})

const sampleFolders: InventoryFolder[] = [
  createFolder('2020/'),
  createFolder('2020/Events/'),
  createFolder('2020/Events/Wedding/'),
  createFolder('2020/Events/Birthday/'),
  createFolder('2020/Portraits/'),
  createFolder('2021/'),
  createFolder('2021/Events/'),
  createFolder('2021/Landscapes/')
]

// ============================================================================
// Tests
// ============================================================================

describe('FolderTree', () => {
  const mockOnSelectionChange = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render folder count in footer', () => {
      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      expect(screen.getByText(/8 total folders/i)).toBeInTheDocument()
    })

    it('should show loading state', () => {
      render(
        <FolderTree
          folders={[]}
          loading={true}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      expect(screen.getByText(/loading folders/i)).toBeInTheDocument()
    })

    it('should show empty state when no folders', () => {
      render(
        <FolderTree
          folders={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      expect(screen.getByText(/no folders available/i)).toBeInTheDocument()
    })

    it('should display mapped folders count', () => {
      const mappedPaths = new Set(['2020/', '2021/'])

      render(
        <FolderTree
          folders={sampleFolders}
          mappedPaths={mappedPaths}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      expect(screen.getByText(/2 already mapped/i)).toBeInTheDocument()
    })

    it('should render root-level folders initially collapsed', async () => {
      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Root folders should be visible (as text in the tree)
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
        expect(screen.getByText('2021')).toBeInTheDocument()
      })

      // Child folders should not be visible (collapsed)
      expect(screen.queryByText('Events')).not.toBeInTheDocument()
      expect(screen.queryByText('Portraits')).not.toBeInTheDocument()
    })
  })

  describe('Expand/Collapse', () => {
    it('should expand folder when expand button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree to render
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // Initially children not visible
      expect(screen.queryByText('Events')).not.toBeInTheDocument()

      // Click expand button for 2020
      const expandButtons = screen.getAllByLabelText('Expand')
      await user.click(expandButtons[0])

      // Children should now be visible
      await waitFor(() => {
        expect(screen.getByText('Events')).toBeInTheDocument()
      })
    })

    it('should expand all folders when Expand All is clicked', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // Click Expand All
      await user.click(screen.getByText('Expand All'))

      // All nested folders should be visible
      await waitFor(() => {
        expect(screen.getByText('Wedding')).toBeInTheDocument()
        expect(screen.getByText('Birthday')).toBeInTheDocument()
        expect(screen.getByText('Landscapes')).toBeInTheDocument()
      })
    })

    it('should collapse all folders when Collapse All is clicked', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // First expand all
      await user.click(screen.getByText('Expand All'))

      // Verify expanded
      await waitFor(() => {
        expect(screen.getByText('Wedding')).toBeInTheDocument()
      })

      // Now collapse all
      await user.click(screen.getByText('Collapse All'))

      // Children should no longer be visible
      await waitFor(() => {
        expect(screen.queryByText('Wedding')).not.toBeInTheDocument()
      })
    })
  })

  describe('Selection', () => {
    it('should select folder when checkbox is clicked', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // Click checkbox for first folder (2020)
      const checkbox = screen.getByLabelText('Select 2020')
      await user.click(checkbox)

      // Should call onSelectionChange with the selected path
      await waitFor(() => {
        expect(mockOnSelectionChange).toHaveBeenCalled()
        const lastCall = mockOnSelectionChange.mock.calls[mockOnSelectionChange.mock.calls.length - 1]
        expect(lastCall[0]).toBeInstanceOf(Set)
        expect(lastCall[0].has('2020/')).toBe(true)
      })
    })

    it('should show selection summary when folders are selected', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // Select a folder
      const checkbox = screen.getByLabelText('Select 2020')
      await user.click(checkbox)

      // Summary should appear
      await waitFor(() => {
        expect(screen.getByText(/1 folder selected/i)).toBeInTheDocument()
      })
    })

    it('should deselect folder when checkbox is clicked again', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          initialSelection={new Set(['2020/'])}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Verify initially selected
      await waitFor(() => {
        expect(screen.getByText(/1 folder selected/i)).toBeInTheDocument()
      })

      // Click to deselect
      const checkbox = screen.getByLabelText('Select 2020')
      await user.click(checkbox)

      // Summary should update
      await waitFor(() => {
        expect(screen.queryByText(/1 folder selected/i)).not.toBeInTheDocument()
      })
    })

    it('should initialize with provided selection', () => {
      render(
        <FolderTree
          folders={sampleFolders}
          initialSelection={new Set(['2020/', '2021/'])}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      expect(screen.getByText(/2 folders selected/i)).toBeInTheDocument()
    })
  })

  describe('Hierarchy Constraints', () => {
    it('should call onSelectionChange with valid selection only', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // Select a folder
      await user.click(screen.getByLabelText('Select 2020'))

      // Verify selection was passed correctly
      await waitFor(() => {
        expect(mockOnSelectionChange).toHaveBeenCalled()
        const lastCall = mockOnSelectionChange.mock.calls[mockOnSelectionChange.mock.calls.length - 1]
        expect(lastCall[0].has('2020/')).toBe(true)
      })

      // Select another root folder (should be allowed)
      await user.click(screen.getByLabelText('Select 2021'))

      // Verify both are selected
      await waitFor(() => {
        const lastCall = mockOnSelectionChange.mock.calls[mockOnSelectionChange.mock.calls.length - 1]
        expect(lastCall[0].has('2020/')).toBe(true)
        expect(lastCall[0].has('2021/')).toBe(true)
      })
    })
  })

  describe('Mapped Folders', () => {
    it('should disable checkbox for mapped folders', async () => {
      const mappedPaths = new Set(['2020/'])

      render(
        <FolderTree
          folders={sampleFolders.map(f =>
            f.path === '2020/' ? { ...f, collection_guid: 'col_123' } : f
          )}
          mappedPaths={mappedPaths}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      const checkbox = screen.getByLabelText('Select 2020')
      expect(checkbox).toBeDisabled()
    })
  })

  describe('Search', () => {
    it('should filter folders by search query', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      // Expand all first to make all folders visible
      await user.click(screen.getByText('Expand All'))

      // Wait for expansion
      await waitFor(() => {
        expect(screen.getByText('Wedding')).toBeInTheDocument()
        expect(screen.getByText('Landscapes')).toBeInTheDocument()
      })

      // Type in search
      const searchInput = screen.getByPlaceholderText(/search folders/i)
      await user.type(searchInput, 'Wedding')

      // Only matching folders and their ancestors should be visible
      await waitFor(() => {
        expect(screen.getByText('Wedding')).toBeInTheDocument()
        // Non-matching folders at same level should be hidden
        expect(screen.queryByText('Landscapes')).not.toBeInTheDocument()
      })
    })

    it('should show no match message when search has no results', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search folders/i)
      await user.type(searchInput, 'nonexistent')

      await waitFor(() => {
        expect(screen.getByText(/no folders match/i)).toBeInTheDocument()
      })
    })

    it('should clear search results when search is cleared', async () => {
      const user = userEvent.setup()

      render(
        <FolderTree
          folders={sampleFolders}
          onSelectionChange={mockOnSelectionChange}
        />
      )

      // Wait for tree
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search folders/i)

      // Search for something
      await user.type(searchInput, 'Wedding')

      // Clear search
      await user.clear(searchInput)

      // Root folders should be visible again
      await waitFor(() => {
        expect(screen.getByText('2020')).toBeInTheDocument()
        expect(screen.getByText('2021')).toBeInTheDocument()
      })
    })
  })
})
