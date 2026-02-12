/**
 * Unit tests for LocationPicker component.
 *
 * Tests location selection, address lookup, and location creation.
 * Issue #39 - Calendar Events feature (Phase 8)
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import { LocationPicker } from '@/components/events/LocationPicker'
import type { Location } from '@/contracts/api/location-api'

// Mock location for testing
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
  website: null,
  instagram_handle: null,
  instagram_url: null,
  created_at: '2026-01-10T10:00:00Z',
  updated_at: '2026-01-10T10:00:00Z',
}

describe('LocationPicker', () => {
  const mockOnChange = vi.fn()
  const mockOnTimezoneHint = vi.fn()
  const categoryGuid = 'cat_01hgw2bbg00000000000000001'

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should render with placeholder when no value', () => {
      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByRole('combobox')).toHaveTextContent('Select or enter location...')
    })

    it('should render with location name when value is set', () => {
      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={mockLocation}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByRole('combobox')).toHaveTextContent('EAA Grounds')
    })

    it('should be disabled when categoryGuid is null', () => {
      render(
        <LocationPicker
          categoryGuid={null}
          value={null}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByRole('combobox')).toBeDisabled()
    })

    it('should be disabled when disabled prop is true', () => {
      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
          disabled={true}
        />
      )

      expect(screen.getByRole('combobox')).toBeDisabled()
    })
  })

  describe('Opening Popover', () => {
    it('should open popover on click', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search known locations...')).toBeInTheDocument()
      })
    })

    it('should show "Enter new address..." option', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('Enter new address...')).toBeInTheDocument()
      })
    })
  })

  describe('Selecting Known Location', () => {
    it('should show known locations from the category', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByRole('combobox'))

      // Wait for locations to load (from MSW mock)
      await waitFor(() => {
        expect(screen.getByText('EAA Grounds')).toBeInTheDocument()
      })
    })

    it('should call onChange when selecting a location', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('EAA Grounds')).toBeInTheDocument()
      })

      await user.click(screen.getByText('EAA Grounds'))

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledTimes(1)
      })

      // Verify the location was passed
      const calledWith = mockOnChange.mock.calls[0][0]
      expect(calledWith.name).toBe('EAA Grounds')
    })

    it('should call onTimezoneHint when selecting location with timezone', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
          onTimezoneHint={mockOnTimezoneHint}
        />
      )

      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('EAA Grounds')).toBeInTheDocument()
      })

      await user.click(screen.getByText('EAA Grounds'))

      await waitFor(() => {
        expect(mockOnTimezoneHint).toHaveBeenCalledWith('America/Chicago')
      })
    })
  })

  describe('New Address Mode', () => {
    it('should switch to new address mode when clicking "Enter new address..."', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByText('Enter new address...')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Enter new address...'))

      await waitFor(() => {
        expect(screen.getByText('New Location')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('123 Main St, City, Country')).toBeInTheDocument()
      })
    })

    it('should show "Save as known location" checkbox after geocoding', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      // Open picker
      await user.click(screen.getByRole('combobox'))

      // Switch to new address mode
      await waitFor(() => {
        expect(screen.getByText('Enter new address...')).toBeInTheDocument()
      })
      await user.click(screen.getByText('Enter new address...'))

      // Enter address and lookup
      await waitFor(() => {
        expect(screen.getByPlaceholderText('123 Main St, City, Country')).toBeInTheDocument()
      })

      const addressInput = screen.getByPlaceholderText('123 Main St, City, Country')
      await user.type(addressInput, '3000 Poberezny Road, Oshkosh, WI')

      // Click lookup button - find by looking for button next to input
      const buttons = screen.getAllByRole('button')
      // The lookup button is the one with the search icon, it's in the address form
      const lookupButton = buttons.find(btn => btn.querySelector('svg.lucide-search'))
      expect(lookupButton).toBeDefined()
      await user.click(lookupButton!)

      // Wait for geocode result
      await waitFor(() => {
        expect(screen.getByText(/Save as known location/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Clearing Selection', () => {
    it('should show clear button when value is set', () => {
      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={mockLocation}
          onChange={mockOnChange}
        />
      )

      // The X icon should be visible in the trigger
      const combobox = screen.getByRole('combobox')
      expect(combobox.querySelector('svg.lucide-x')).toBeInTheDocument()
    })

    it('should call onChange with null when clearing', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={mockLocation}
          onChange={mockOnChange}
        />
      )

      // Find and click the X icon
      const combobox = screen.getByRole('combobox')
      const clearButton = combobox.querySelector('svg.lucide-x')
      expect(clearButton).toBeInTheDocument()

      await user.click(clearButton!)

      expect(mockOnChange).toHaveBeenCalledWith(null)
    })
  })

  describe('Display Formatting', () => {
    it('should display location with city and country', () => {
      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={mockLocation}
          onChange={mockOnChange}
        />
      )

      // Should show "EAA Grounds, Oshkosh, USA"
      expect(screen.getByRole('combobox')).toHaveTextContent('EAA Grounds')
      expect(screen.getByRole('combobox')).toHaveTextContent('Oshkosh')
    })

    it('should use custom placeholder', () => {
      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
          placeholder="Choose a venue..."
        />
      )

      expect(screen.getByRole('combobox')).toHaveTextContent('Choose a venue...')
    })
  })

  describe('Search Filtering', () => {
    it('should filter known locations by search input', async () => {
      const user = userEvent.setup()

      render(
        <LocationPicker
          categoryGuid={categoryGuid}
          value={null}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByRole('combobox'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search known locations...')).toBeInTheDocument()
      })

      // Type in search
      const searchInput = screen.getByPlaceholderText('Search known locations...')
      await user.type(searchInput, 'EAA')

      // Should still show EAA Grounds
      await waitFor(() => {
        expect(screen.getByText('EAA Grounds')).toBeInTheDocument()
      })
    })
  })
})
