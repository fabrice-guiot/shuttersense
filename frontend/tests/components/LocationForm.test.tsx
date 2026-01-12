/**
 * Unit tests for LocationForm component.
 *
 * Tests form rendering, validation, geocoding, and submission.
 * Issue #39 - Calendar Events feature (Phase 8)
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import { LocationForm } from '@/components/directory/LocationForm'
import type { Location, GeocodeResponse } from '@/contracts/api/location-api'
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

// Mock location for editing tests
const mockLocation: Location = {
  guid: 'loc_01hgw2bbg00000000000000001',
  name: 'EAA Grounds',
  address: '3000 Poberezny Road',
  city: 'Oshkosh',
  state: 'Wisconsin',
  country: 'USA',
  postal_code: '54902',
  latitude: 43.9847,
  longitude: -88.5568,
  timezone: 'America/Chicago',
  category: {
    guid: 'cat_01hgw2bbg00000000000000001',
    name: 'Airshow',
    icon: 'plane',
    color: '#EF4444',
  },
  rating: 5,
  timeoff_required_default: true,
  travel_required_default: true,
  notes: 'Home of AirVenture',
  is_known: true,
  created_at: '2026-01-10T10:00:00Z',
  updated_at: '2026-01-10T10:00:00Z',
}

describe('LocationForm', () => {
  const mockOnSubmit = vi.fn<(data: unknown) => Promise<void>>()
  const mockOnCancel = vi.fn()
  const mockOnGeocode = vi.fn<(address: string) => Promise<GeocodeResponse | null>>()

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Create Mode', () => {
    it('should render the form with required fields', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Name \*/i)).toBeInTheDocument()
      expect(screen.getByText(/Category \*/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Create Location/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('should only show active categories in create mode', async () => {
      const user = userEvent.setup()

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the category select (first combobox)
      const comboboxes = screen.getAllByRole('combobox')
      const categorySelect = comboboxes[0]
      await user.click(categorySelect)

      // Wait for dropdown to open and check for visible options
      await waitFor(() => {
        const airshowItems = screen.getAllByText('Airshow')
        const wildlifeItems = screen.getAllByText('Wildlife')
        // Should have at least one of each active category visible
        expect(airshowItems.length).toBeGreaterThan(0)
        expect(wildlifeItems.length).toBeGreaterThan(0)
      })

      // Inactive category should not be shown
      expect(screen.queryByText('Archived Event')).not.toBeInTheDocument()
    })

    it('should show validation error for empty name', async () => {
      const user = userEvent.setup()

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Submit without filling form
      const submitButton = screen.getByRole('button', { name: /Create Location/i })
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
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in name but not category
      await user.type(screen.getByLabelText(/Name \*/i), 'Test Location')

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create Location/i })
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
        <LocationForm
          location={null}
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
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in name
      await user.type(screen.getByLabelText(/Name \*/i), 'New Test Location')

      // Select category (first combobox)
      const comboboxes = screen.getAllByRole('combobox')
      const categorySelect = comboboxes[0]
      await user.click(categorySelect)
      await waitFor(() => {
        const airshowItems = screen.getAllByText('Airshow')
        expect(airshowItems.length).toBeGreaterThan(0)
      })
      // Click the visible option (not the hidden select option)
      const airshowOptions = screen.getAllByText('Airshow')
      await user.click(airshowOptions[airshowOptions.length - 1])

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Create Location/i })
      await user.click(submitButton)

      // Wait for submission
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      })

      // Verify submitted data
      const submitData = mockOnSubmit.mock.calls[0][0] as Record<string, unknown>
      expect(submitData.name).toBe('New Test Location')
      expect(submitData.category_guid).toBe('cat_01hgw2bbg00000000000000001')
      expect(submitData.is_known).toBe(true)
    })

    it('should show "Save as known location" checkbox', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      const knownCheckbox = screen.getByRole('checkbox', { name: /Save as known location/i })
      expect(knownCheckbox).toBeInTheDocument()
      expect(knownCheckbox).toBeChecked() // Default is true
    })
  })

  describe('Edit Mode', () => {
    it('should show "Save Changes" button when editing', () => {
      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument()
    })

    it('should populate form with existing location data', () => {
      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Name \*/i)).toHaveValue('EAA Grounds')
      // Address details should be auto-expanded when location has address fields
    })

    it('should show all categories including inactive in edit mode', async () => {
      const user = userEvent.setup()

      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the category select (first combobox)
      const comboboxes = screen.getAllByRole('combobox')
      const categorySelect = comboboxes[0]
      await user.click(categorySelect)

      // Wait for dropdown to open and verify all categories including inactive are shown
      await waitFor(() => {
        const airshowItems = screen.getAllByText('Airshow')
        const wildlifeItems = screen.getAllByText('Wildlife')
        expect(airshowItems.length).toBeGreaterThan(0)
        expect(wildlifeItems.length).toBeGreaterThan(0)
        // Inactive category should also be shown in edit mode
        expect(screen.getAllByText('Archived Event').length).toBeGreaterThan(0)
      })
    })
  })

  describe('Address Lookup', () => {
    it('should show address lookup field when onGeocode is provided', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          onGeocode={mockOnGeocode}
        />
      )

      expect(screen.getByText(/Address Lookup/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/Enter full address to lookup/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Lookup/i })).toBeInTheDocument()
    })

    it('should not show address lookup when onGeocode is not provided', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.queryByText(/Address Lookup/i)).not.toBeInTheDocument()
    })

    it('should call onGeocode when lookup button is clicked', async () => {
      const user = userEvent.setup()
      const geocodeResult: GeocodeResponse = {
        address: '3000 Poberezny Road',
        city: 'Oshkosh',
        state: 'Wisconsin',
        country: 'United States',
        postal_code: '54902',
        latitude: 43.9847,
        longitude: -88.5568,
        timezone: 'America/Chicago',
      }
      mockOnGeocode.mockResolvedValue(geocodeResult)

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          onGeocode={mockOnGeocode}
        />
      )

      // Type address
      const addressInput = screen.getByPlaceholderText(/Enter full address to lookup/i)
      await user.type(addressInput, '3000 Poberezny Road, Oshkosh, WI')

      // Click lookup
      await user.click(screen.getByRole('button', { name: /Lookup/i }))

      await waitFor(() => {
        expect(mockOnGeocode).toHaveBeenCalledWith('3000 Poberezny Road, Oshkosh, WI')
      })
    })

    it('should populate form fields with geocode result', async () => {
      const user = userEvent.setup()
      const geocodeResult: GeocodeResponse = {
        address: '3000 Poberezny Road',
        city: 'Oshkosh',
        state: 'Wisconsin',
        country: 'United States',
        postal_code: '54902',
        latitude: 43.9847,
        longitude: -88.5568,
        timezone: 'America/Chicago',
      }
      mockOnGeocode.mockResolvedValue(geocodeResult)

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          onGeocode={mockOnGeocode}
        />
      )

      // Type address and lookup
      const addressInput = screen.getByPlaceholderText(/Enter full address to lookup/i)
      await user.type(addressInput, 'Some address')
      await user.click(screen.getByRole('button', { name: /Lookup/i }))

      // Wait for geocode result to populate fields
      await waitFor(() => {
        expect(screen.getByLabelText(/Latitude/i)).toHaveValue(43.9847)
        expect(screen.getByLabelText(/Longitude/i)).toHaveValue(-88.5568)
      })

      // Address details should be expanded after geocoding
      expect(screen.getByLabelText(/Street Address/i)).toHaveValue('3000 Poberezny Road')
      expect(screen.getByLabelText(/City/i)).toHaveValue('Oshkosh')
      expect(screen.getByLabelText(/State\/Province/i)).toHaveValue('Wisconsin')
      expect(screen.getByLabelText(/Country/i)).toHaveValue('United States')
      expect(screen.getByLabelText(/Postal Code/i)).toHaveValue('54902')
    })

    it('should disable lookup button when address is empty', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          onGeocode={mockOnGeocode}
        />
      )

      const lookupButton = screen.getByRole('button', { name: /Lookup/i })
      expect(lookupButton).toBeDisabled()
    })

    it('should trigger geocode on Enter key', async () => {
      const user = userEvent.setup()
      mockOnGeocode.mockResolvedValue(null)

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          onGeocode={mockOnGeocode}
        />
      )

      // Type address and press Enter
      const addressInput = screen.getByPlaceholderText(/Enter full address to lookup/i)
      await user.type(addressInput, 'Some address{Enter}')

      await waitFor(() => {
        expect(mockOnGeocode).toHaveBeenCalledWith('Some address')
      })
    })
  })

  describe('Collapsible Address Details', () => {
    it('should toggle address details section', async () => {
      const user = userEvent.setup()

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Address details should be hidden by default
      expect(screen.queryByLabelText(/Street Address/i)).not.toBeInTheDocument()

      // Click to expand
      await user.click(screen.getByText(/Address Details/i))

      // Address fields should now be visible
      expect(screen.getByLabelText(/Street Address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/City/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/State\/Province/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Country/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Postal Code/i)).toBeInTheDocument()

      // Click to collapse
      await user.click(screen.getByText(/Address Details/i))

      // Address fields should be hidden
      expect(screen.queryByLabelText(/Street Address/i)).not.toBeInTheDocument()
    })

    it('should auto-expand address details when editing location with address', () => {
      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Address details should be visible because location has address
      expect(screen.getByLabelText(/Street Address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Street Address/i)).toHaveValue('3000 Poberezny Road')
    })
  })

  describe('Rating Selector', () => {
    it('should render rating field', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Look for the Rating label - there may be multiple due to form structure
      const ratingLabels = screen.getAllByText(/^Rating$/i)
      expect(ratingLabels.length).toBeGreaterThan(0)
    })
  })

  describe('Default Settings', () => {
    it('should render default settings checkboxes', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Default Settings for New Events/i)).toBeInTheDocument()
      expect(screen.getByRole('checkbox', { name: /Time-off required/i })).toBeInTheDocument()
      expect(screen.getByRole('checkbox', { name: /Travel required/i })).toBeInTheDocument()
    })

    it('should have default settings unchecked by default', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('checkbox', { name: /Time-off required/i })).not.toBeChecked()
      expect(screen.getByRole('checkbox', { name: /Travel required/i })).not.toBeChecked()
    })

    it('should show checked defaults when editing location with defaults set', () => {
      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('checkbox', { name: /Time-off required/i })).toBeChecked()
      expect(screen.getByRole('checkbox', { name: /Travel required/i })).toBeChecked()
    })
  })

  describe('Form State', () => {
    it('should disable submit button when isSubmitting is true', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          isSubmitting={true}
        />
      )

      expect(screen.getByRole('button', { name: /Create Location/i })).toBeDisabled()
    })

    it('should disable submit button while geocoding', async () => {
      const user = userEvent.setup()
      // Never resolve the promise to keep geocoding state
      mockOnGeocode.mockImplementation(() => new Promise(() => {}))

      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          onGeocode={mockOnGeocode}
        />
      )

      // Type address and trigger geocode
      const addressInput = screen.getByPlaceholderText(/Enter full address to lookup/i)
      await user.type(addressInput, 'Some address')
      await user.click(screen.getByRole('button', { name: /Lookup/i }))

      // Submit button should be disabled during geocoding
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Location/i })).toBeDisabled()
      })
    })
  })

  describe('Coordinate Fields', () => {
    it('should render latitude and longitude fields', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Latitude/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Longitude/i)).toBeInTheDocument()
    })

    it('should populate coordinates when editing location', () => {
      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Latitude/i)).toHaveValue(43.9847)
      expect(screen.getByLabelText(/Longitude/i)).toHaveValue(-88.5568)
    })
  })

  describe('Notes Field', () => {
    it('should render notes textarea', () => {
      render(
        <LocationForm
          location={null}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Notes/i)).toBeInTheDocument()
    })

    it('should populate notes when editing', () => {
      render(
        <LocationForm
          location={mockLocation}
          categories={mockCategories}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/Notes/i)).toHaveValue('Home of AirVenture')
    })
  })
})
