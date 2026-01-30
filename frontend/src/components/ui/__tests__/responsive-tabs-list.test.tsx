/**
 * Tests for ResponsiveTabsList component.
 *
 * Tests cover:
 * - Mobile select dropdown rendering (md:hidden wrapper)
 * - Desktop TabsList rendering (hidden md:inline-flex wrapper)
 * - SelectItem rendering for all tab options
 * - Icon rendering in select items
 * - Badge rendering in select items
 * - onValueChange handler from Select
 * - Desktop children (TabsTrigger) rendering
 *
 * Part of Issue #123: Mobile Responsive Tables and Tabs.
 */

import { describe, test, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tabs, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  ResponsiveTabsList,
  type TabOption,
} from '../responsive-tabs-list'

// ============================================================================
// Test Data
// ============================================================================

function MockIcon({ className }: { className?: string }) {
  return <svg data-testid="tab-icon" className={className} />
}

const basicTabs: TabOption[] = [
  { value: 'tab1', label: 'First Tab' },
  { value: 'tab2', label: 'Second Tab' },
  { value: 'tab3', label: 'Third Tab' },
]

const tabsWithIcons: TabOption[] = [
  { value: 'tab1', label: 'First Tab', icon: MockIcon },
  { value: 'tab2', label: 'Second Tab', icon: MockIcon },
]

const tabsWithBadges: TabOption[] = [
  {
    value: 'tab1',
    label: 'First Tab',
    badge: <span data-testid="tab-badge">Admin</span>,
  },
  { value: 'tab2', label: 'Second Tab' },
]

// ============================================================================
// Helper: Render wrapped in Tabs
// ============================================================================

function renderWithTabs(
  tabs: TabOption[],
  value: string,
  onValueChange: (v: string) => void
) {
  return render(
    <Tabs value={value} onValueChange={onValueChange}>
      <ResponsiveTabsList
        tabs={tabs}
        value={value}
        onValueChange={onValueChange}
      >
        {tabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value}>
            {tab.label}
          </TabsTrigger>
        ))}
      </ResponsiveTabsList>
      {tabs.map((tab) => (
        <TabsContent key={tab.value} value={tab.value}>
          Content for {tab.label}
        </TabsContent>
      ))}
    </Tabs>
  )
}

// ============================================================================
// Tests
// ============================================================================

describe('ResponsiveTabsList', () => {
  describe('mobile select view', () => {
    test('renders Select inside md:hidden wrapper', () => {
      const { container } = renderWithTabs(basicTabs, 'tab1', vi.fn())

      // Find the mobile wrapper with md:hidden
      const mobileWrapper = container.querySelector('.md\\:hidden')
      expect(mobileWrapper).toBeInTheDocument()

      // Should contain a select trigger (combobox role)
      const selectTrigger = within(mobileWrapper as HTMLElement).getByRole(
        'combobox'
      )
      expect(selectTrigger).toBeInTheDocument()
    })

    test('all TabOption items appear as SelectItem elements in the dropdown', async () => {
      const user = userEvent.setup()
      renderWithTabs(basicTabs, 'tab1', vi.fn())

      // Open the select dropdown
      const trigger = screen.getByRole('combobox')
      await user.click(trigger)

      // All tab labels should appear as options
      for (const tab of basicTabs) {
        expect(screen.getByText(tab.label, { selector: '[role="option"] *' })).toBeInTheDocument()
      }
    })

    test('icons render inside SelectItem when provided in TabOption', async () => {
      const user = userEvent.setup()
      renderWithTabs(tabsWithIcons, 'tab1', vi.fn())

      // Open the select dropdown
      const trigger = screen.getByRole('combobox')
      await user.click(trigger)

      // Icons should be rendered
      const icons = screen.getAllByTestId('tab-icon')
      expect(icons.length).toBeGreaterThanOrEqual(tabsWithIcons.length)
    })

    test('badges render inside SelectItem when provided in TabOption', async () => {
      const user = userEvent.setup()
      renderWithTabs(tabsWithBadges, 'tab1', vi.fn())

      // Open the select dropdown
      const trigger = screen.getByRole('combobox')
      await user.click(trigger)

      // Badge should be rendered
      const badge = screen.getByTestId('tab-badge')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveTextContent('Admin')
    })

    test('calling onValueChange from Select fires the handler with selected tab value', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      renderWithTabs(basicTabs, 'tab1', handleChange)

      // Open the select dropdown
      const trigger = screen.getByRole('combobox')
      await user.click(trigger)

      // Click the second tab option
      const option = screen.getByText('Second Tab', {
        selector: '[role="option"] *',
      })
      await user.click(option)

      expect(handleChange).toHaveBeenCalledWith('tab2')
    })
  })

  describe('desktop tabs view', () => {
    test('renders TabsList inside hidden md:inline-flex wrapper', () => {
      const { container } = renderWithTabs(basicTabs, 'tab1', vi.fn())

      // Find the desktop TabsList with hidden md:inline-flex
      const desktopTabsList = container.querySelector(
        '.hidden.md\\:inline-flex'
      )
      expect(desktopTabsList).toBeInTheDocument()

      // Should contain tab triggers (button role with tab name)
      const tabs = within(desktopTabsList as HTMLElement).getAllByRole('tab')
      expect(tabs).toHaveLength(basicTabs.length)
    })

    test('children (TabsTrigger elements) render inside the desktop TabsList', () => {
      const { container } = renderWithTabs(basicTabs, 'tab1', vi.fn())

      const desktopTabsList = container.querySelector(
        '.hidden.md\\:inline-flex'
      )!

      // Each tab label should appear in the desktop view
      for (const tab of basicTabs) {
        expect(
          within(desktopTabsList as HTMLElement).getByText(tab.label)
        ).toBeInTheDocument()
      }
    })
  })
})
