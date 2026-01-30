/**
 * Tests for ResponsiveTable component.
 *
 * Tests cover:
 * - Desktop table rendering (hidden md:block wrapper)
 * - Mobile card rendering (md:hidden wrapper)
 * - Card role system (title, subtitle, badge, detail, action, hidden)
 * - Default cardRole behavior
 * - Empty state handling
 * - Conditional rendering of badge/action areas
 *
 * Part of Issue #123: Mobile Responsive Tables and Tabs.
 */

import { describe, test, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ResponsiveTable, type ColumnDef } from '../responsive-table'

// ============================================================================
// Test Data
// ============================================================================

interface TestItem {
  id: string
  name: string
  status: string
  category: string
  created: string
}

const mockItems: TestItem[] = [
  {
    id: 'item-1',
    name: 'First Item',
    status: 'Active',
    category: 'Alpha',
    created: '2025-01-01',
  },
  {
    id: 'item-2',
    name: 'Second Item',
    status: 'Inactive',
    category: 'Beta',
    created: '2025-01-02',
  },
]

// ============================================================================
// Column Definitions for Various Test Scenarios
// ============================================================================

const allRolesColumns: ColumnDef<TestItem>[] = [
  { header: 'Name', cell: (item) => item.name, cardRole: 'title' },
  { header: 'Category', cell: (item) => item.category, cardRole: 'subtitle' },
  {
    header: 'Status',
    cell: (item) => <span data-testid="badge">{item.status}</span>,
    cardRole: 'badge',
  },
  { header: 'Created', cell: (item) => item.created, cardRole: 'detail' },
  {
    header: 'Actions',
    cell: (item) => (
      <button data-testid={`action-${item.id}`}>Edit</button>
    ),
    cardRole: 'action',
  },
  {
    header: 'Internal ID',
    cell: (item) => item.id,
    cardRole: 'hidden',
  },
]

const noActionColumns: ColumnDef<TestItem>[] = [
  { header: 'Name', cell: (item) => item.name, cardRole: 'title' },
  { header: 'Status', cell: (item) => item.status, cardRole: 'badge' },
  { header: 'Created', cell: (item) => item.created, cardRole: 'detail' },
]

const noBadgeColumns: ColumnDef<TestItem>[] = [
  { header: 'Name', cell: (item) => item.name, cardRole: 'title' },
  { header: 'Created', cell: (item) => item.created, cardRole: 'detail' },
]

const noExplicitRoleColumns: ColumnDef<TestItem>[] = [
  { header: 'Name', cell: (item) => item.name },
  { header: 'Status', cell: (item) => item.status },
  { header: 'Category', cell: (item) => item.category },
]

// ============================================================================
// Tests
// ============================================================================

describe('ResponsiveTable', () => {
  describe('desktop view', () => {
    test('renders table element inside hidden md:block wrapper', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      // Find the desktop wrapper with hidden md:block
      const desktopWrapper = container.querySelector('.hidden.md\\:block')
      expect(desktopWrapper).toBeInTheDocument()

      // Table should be inside the desktop wrapper
      const table = desktopWrapper!.querySelector('table')
      expect(table).toBeInTheDocument()

      // All column headers should be rendered
      const headers = within(desktopWrapper as HTMLElement).getAllByRole(
        'columnheader'
      )
      expect(headers).toHaveLength(allRolesColumns.length)
    })
  })

  describe('mobile card view', () => {
    test('renders card list inside md:hidden wrapper', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      // Find the mobile wrapper with md:hidden
      const mobileWrapper = container.querySelector('.md\\:hidden')
      expect(mobileWrapper).toBeInTheDocument()

      // Should have a card for each data item
      const cards = mobileWrapper!.querySelectorAll('.rounded-lg.border')
      expect(cards).toHaveLength(mockItems.length)
    })

    test('columns with cardRole title render as bold text in card header', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!
      const cards = mobileWrapper.querySelectorAll('.rounded-lg.border')

      // First card should have the title text rendered with font-medium
      const titleEl = cards[0].querySelector('.font-medium')
      expect(titleEl).toBeInTheDocument()
      expect(titleEl).toHaveTextContent('First Item')
    })

    test('columns with cardRole badge render in the title row right-aligned area', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!
      const firstCard = mobileWrapper.querySelector('.rounded-lg.border')!

      // Badge should be rendered inside the card
      const badge = within(firstCard as HTMLElement).getByTestId('badge')
      expect(badge).toHaveTextContent('Active')

      // Badge container should have shrink-0 class (right-aligned area)
      const badgeArea = firstCard.querySelector('.shrink-0')
      expect(badgeArea).toBeInTheDocument()
    })

    test('columns with cardRole hidden do not appear in card view', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!

      // The hidden column's value (item id) should not appear in mobile view
      // "item-1" only appears via the hidden column's cell renderer
      // But "item-1" might also appear in the action button testid attribute,
      // so check the text content specifically
      const firstCard = mobileWrapper.querySelector('.rounded-lg.border')!
      // Internal ID header should not appear as a label in the card
      expect(firstCard.textContent).not.toContain('Internal ID')
    })

    test('columns with no explicit cardRole default to detail rendering as key-value rows', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={noExplicitRoleColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!
      const firstCard = mobileWrapper.querySelector('.rounded-lg.border')!

      // All columns should render as detail rows with "Header: Value" pattern
      expect(firstCard.textContent).toContain('Name')
      expect(firstCard.textContent).toContain('First Item')
      expect(firstCard.textContent).toContain('Status')
      expect(firstCard.textContent).toContain('Active')
      expect(firstCard.textContent).toContain('Category')
      expect(firstCard.textContent).toContain('Alpha')
    })

    test('cardRole action columns render in bottom action row with border separator', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!
      const firstCard = mobileWrapper.querySelector('.rounded-lg.border')!

      // Action button should be rendered
      const actionBtn = within(firstCard as HTMLElement).getByTestId(
        'action-item-1'
      )
      expect(actionBtn).toBeInTheDocument()
      expect(actionBtn).toHaveTextContent('Edit')

      // Action row should have border-t for separation and min-h-11 for touch targets
      const actionRow = actionBtn.closest('.border-t.border-border')
      expect(actionRow).toBeInTheDocument()
      expect(actionRow).toHaveClass('min-h-11')
    })

    test('action row and separator are omitted when no action columns exist', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={noActionColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!
      const firstCard = mobileWrapper.querySelector('.rounded-lg.border')!

      // No action row should exist (no element with min-h-11)
      const actionRow = firstCard.querySelector('.min-h-11')
      expect(actionRow).not.toBeInTheDocument()
    })

    test('badge area is omitted when no badge columns exist', () => {
      const { container } = render(
        <ResponsiveTable
          data={mockItems}
          columns={noBadgeColumns}
          keyField="id"
        />
      )

      const mobileWrapper = container.querySelector('.md\\:hidden')!
      const firstCard = mobileWrapper.querySelector('.rounded-lg.border')!

      // No badge area (flex-wrap container) should exist in the title row
      const badgeArea = firstCard.querySelector('.flex-wrap')
      expect(badgeArea).not.toBeInTheDocument()
    })
  })

  describe('empty state', () => {
    test('emptyState prop renders when data array is empty', () => {
      render(
        <ResponsiveTable
          data={[]}
          columns={allRolesColumns}
          keyField="id"
          emptyState={<div data-testid="empty">No items found</div>}
        />
      )

      expect(screen.getByTestId('empty')).toBeInTheDocument()
      expect(screen.getByText('No items found')).toBeInTheDocument()
    })

    test('renders nothing when data is empty and no emptyState provided', () => {
      const { container } = render(
        <ResponsiveTable
          data={[]}
          columns={allRolesColumns}
          keyField="id"
        />
      )

      expect(container.innerHTML).toBe('')
    })
  })
})
