/**
 * Unit tests for PerformerForm component.
 *
 * Tests form rendering, validation, and submission.
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import { PerformerForm } from '@/components/directory/PerformerForm'
import type { Performer } from '@/contracts/api/performer-api'
import type { Category } from '@/contracts/api/category-api'

// Mock categories for testing
const mockCategories: Category[] = [
  {
    guid: 'cat_01hgw2bbg00000000000000001',
    name: 'Airshow',
    icon: 'plane',
    color: '#EF4444',
    is_active: true,
    display_order: 1,
    created_at: '2026-01-10T10:00:00Z',
    updated_at: '2026-01-10T10:00:00Z',
  },
  {
    guid: 'cat_01hgw2bbg00000000000000002',
    name: 'Wildlife',
    icon: 'bird',
    color: '#22C55E',
    is_active: true,
    display_order: 2,
    created_at: '2026-01-10T10:00:00Z',
    updated_at: '2026-01-10T10:00:00Z',
  },
  {
    guid: 'cat_01hgw2bbg00000000000000003',
    name: 'Archived Event',
    icon: 'archive',
    color: '#9CA3AF',
    is_active: false,
    display_order: 3,
    created_at: '2026-01-10T10:00:00Z',
    updated_at: '2026-01-10T10:00:00Z',
  },
]

// Mock performer for editing tests
const mockPerformer: Performer = {
  guid: 'prf_01hgw2bbg00000000000000001',
  name: 'Blue Angels',
  website: 'https://blueangels.navy.mil',
  instagram_handle: 'usabordo_blueangels',
  instagram_url: 'https://instagram.com/usabordo_blueangels',
  category: {
    guid: 'cat_01hgw2bbg00000000000000001',
    name: 'Airshow',
    icon: 'plane',
    color: '#EF4444',
  },
  additional_info: 'US Navy Flight Demonstration Squadron',
  created_at: '2026-01-10T10:00:00Z',
  updated_at: '2026-01-10T10:00:00Z',
}

describe('PerformerForm', () => {
  const mockOnSubmit = vi.fn<(data: unknown) => Promise<void>>()
  const mockOnCancel = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Create Mode', () => {
    it('should render the form with required fields', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Name \*/i)).toBeInTheDocument()
      expect(screen.getByText(/Category \*/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Create Performer/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('should render optional fields', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Website/i)).toBeInTheDocument()
      // Instagram uses custom input with @ prefix, so we check for label text and placeholder
      expect(screen.getByText(/Instagram Handle/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/username/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Additional Info/i)).toBeInTheDocument()
    })

    it('should only show active categories in create mode', async () => {
      const user = userEvent.setup()

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the category select
      const categorySelect = screen.getByRole('combobox')
      await user.click(categorySelect)

      // Wait for dropdown to open and check for visible options
      await waitFor(() => {
        const airshowItems = screen.getAllByText('Airshow')
        const wildlifeItems = screen.getAllByText('Wildlife')
        expect(airshowItems.length).toBeGreaterThan(0)
        expect(wildlifeItems.length).toBeGreaterThan(0)
      })

      // Inactive category should not be shown
      expect(screen.queryByText('Archived Event')).not.toBeInTheDocument()
    })

    it('should show validation error for empty name', async () => {
      const user = userEvent.setup()

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Submit without filling form
      const submitButton = screen.getByRole('button', { name: /Create Performer/i })
      await user.click(submitButton)

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('should show validation error for empty category', async () => {
      const user = userEvent.setup()

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in name but not category
      await user.type(screen.getByLabelText(/Name \*/i), 'Test Performer')

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create Performer/i })
      await user.click(submitButton)

      // Should show validation error for category
      await waitFor(() => {
        expect(screen.getByText(/Category is required/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('should call onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      expect(mockOnCancel).toHaveBeenCalledTimes(1)
    })

    it('should submit form with valid data', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in name
      await user.type(screen.getByLabelText(/Name \*/i), 'New Test Performer')

      // Select category
      const categorySelect = screen.getByRole('combobox')
      await user.click(categorySelect)
      await waitFor(() => {
        const airshowItems = screen.getAllByText('Airshow')
        expect(airshowItems.length).toBeGreaterThan(0)
      })
      // Click the visible option
      const airshowOptions = screen.getAllByText('Airshow')
      await user.click(airshowOptions[airshowOptions.length - 1])

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create Performer/i })
      await user.click(submitButton)

      // Wait for submission
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      })

      // Verify submitted data
      const submitData = mockOnSubmit.mock.calls[0][0] as Record<string, unknown>
      expect(submitData.name).toBe('New Test Performer')
      expect(submitData.category_guid).toBe('cat_01hgw2bbg00000000000000001')
    })

    it('should submit form with all optional fields', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in all fields
      await user.type(screen.getByLabelText(/Name \*/i), 'Full Details Performer')

      // Select category
      const categorySelect = screen.getByRole('combobox')
      await user.click(categorySelect)
      await waitFor(() => {
        expect(screen.getAllByText('Airshow').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByText('Airshow').pop()!)

      // Fill optional fields
      await user.type(screen.getByLabelText(/Website/i), 'https://example.com')
      await user.type(screen.getByPlaceholderText(/username/i), 'testhandle')
      await user.type(screen.getByLabelText(/Additional Info/i), 'Some extra notes')

      // Submit form
      await user.click(screen.getByRole('button', { name: /Create Performer/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      })

      const submitData = mockOnSubmit.mock.calls[0][0] as Record<string, unknown>
      expect(submitData.name).toBe('Full Details Performer')
      expect(submitData.website).toBe('https://example.com')
      expect(submitData.instagram_handle).toBe('testhandle')
      expect(submitData.additional_info).toBe('Some extra notes')
    })

    it('should strip @ from instagram handle on submit', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill required fields
      await user.type(screen.getByLabelText(/Name \*/i), 'Test Performer')
      const categorySelect = screen.getByRole('combobox')
      await user.click(categorySelect)
      await waitFor(() => {
        expect(screen.getAllByText('Airshow').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByText('Airshow').pop()!)

      // Fill instagram with @ prefix
      await user.type(screen.getByPlaceholderText(/username/i), '@testhandle')

      // Submit form
      await user.click(screen.getByRole('button', { name: /Create Performer/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      })

      const submitData = mockOnSubmit.mock.calls[0][0] as Record<string, unknown>
      expect(submitData.instagram_handle).toBe('testhandle') // @ should be stripped
    })
  })

  describe('Edit Mode', () => {
    it('should show "Save Changes" button when editing', () => {
      render(
        <PerformerForm
          performer={mockPerformer}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument()
    })

    it('should populate form with existing performer data', () => {
      render(
        <PerformerForm
          performer={mockPerformer}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Name \*/i)).toHaveValue('Blue Angels')
      expect(screen.getByLabelText(/Website/i)).toHaveValue('https://blueangels.navy.mil')
      // Instagram field displays without @
      expect(screen.getByPlaceholderText(/username/i)).toHaveValue('usabordo_blueangels')
      expect(screen.getByLabelText(/Additional Info/i)).toHaveValue('US Navy Flight Demonstration Squadron')
    })

    it('should show all categories including inactive in edit mode', async () => {
      const user = userEvent.setup()

      render(
        <PerformerForm
          performer={mockPerformer}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the category select
      const categorySelect = screen.getByRole('combobox')
      await user.click(categorySelect)

      // Wait for dropdown to open and verify all categories including inactive are shown
      await waitFor(() => {
        expect(screen.getAllByText('Airshow').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Wildlife').length).toBeGreaterThan(0)
        // Inactive category should also be shown in edit mode
        expect(screen.getAllByText('Archived Event').length).toBeGreaterThan(0)
      })
    })

    it('should submit updated data', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <PerformerForm
          performer={mockPerformer}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Clear and update name
      const nameInput = screen.getByLabelText(/Name \*/i)
      await user.clear(nameInput)
      await user.type(nameInput, 'Updated Blue Angels')

      // Submit form
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      })

      const submitData = mockOnSubmit.mock.calls[0][0] as Record<string, unknown>
      expect(submitData.name).toBe('Updated Blue Angels')
    })
  })

  describe('Form State', () => {
    it('should disable submit button when isSubmitting is true', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          isSubmitting={true}
        />
      )

      expect(screen.getByRole('button', { name: /Create Performer/i })).toBeDisabled()
    })

    it('should disable cancel button when isSubmitting is true', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          isSubmitting={true}
        />
      )

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeDisabled()
    })

    it('should show loading indicator when submitting', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          isSubmitting={true}
        />
      )

      // Should have a spinner (Loader2 component)
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })
  })

  describe('Instagram Handle Display', () => {
    it('should show @ prefix in the input field', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // The @ symbol should be displayed as a prefix
      expect(screen.getByText('@')).toBeInTheDocument()
    })

    it('should strip @ from displayed value', () => {
      // Create a performer with @ in the handle to test display
      const performerWithAt: Performer = {
        ...mockPerformer,
        instagram_handle: '@testhandle',
      }

      render(
        <PerformerForm
          performer={performerWithAt}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // The input should display without the @
      expect(screen.getByPlaceholderText(/username/i)).toHaveValue('testhandle')
    })
  })

  describe('Form Description', () => {
    it('should show category description', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Performer will only appear for events in this category/i)).toBeInTheDocument()
    })

    it('should show website description', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Link to performer's official website/i)).toBeInTheDocument()
    })

    it('should show instagram description', () => {
      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Instagram username \(without the @\)/i)).toBeInTheDocument()
    })
  })

  describe('Empty Optional Fields', () => {
    it('should convert empty strings to null on submit', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <PerformerForm
          performer={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill only required fields
      await user.type(screen.getByLabelText(/Name \*/i), 'Minimal Performer')
      const categorySelect = screen.getByRole('combobox')
      await user.click(categorySelect)
      await waitFor(() => {
        expect(screen.getAllByText('Airshow').length).toBeGreaterThan(0)
      })
      await user.click(screen.getAllByText('Airshow').pop()!)

      // Leave optional fields empty and submit
      await user.click(screen.getByRole('button', { name: /Create Performer/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      })

      const submitData = mockOnSubmit.mock.calls[0][0] as Record<string, unknown>
      expect(submitData.website).toBe(null)
      expect(submitData.instagram_handle).toBe(null)
      expect(submitData.additional_info).toBe(null)
    })
  })
})
