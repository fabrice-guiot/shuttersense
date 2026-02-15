import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import { validateGuid } from '@/utils/guid'
import {
  listLocations,
  getLocation,
  createLocation,
  updateLocation,
  deleteLocation,
  getLocationStats,
  getLocationsByCategory,
  geocodeAddress,
  validateCategoryMatch,
} from '@/services/locations'
import type {
  Location,
  LocationCreateRequest,
  LocationUpdateRequest,
  LocationListResponse,
  LocationStatsResponse,
  GeocodeResponse,
  CategoryMatchResponse,
} from '@/contracts/api/location-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('@/utils/guid', () => ({
  validateGuid: vi.fn((guid: string) => guid),
}))

describe('Locations API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockLocation: Location = {
    guid: 'loc_01hgw2bbg00000000000000001',
    name: 'Test Venue',
    address: '123 Main St',
    city: 'San Francisco',
    state: 'CA',
    country: 'USA',
    postal_code: '94102',
    website: 'https://example.com',
    instagram_handle: 'testvenue',
    instagram_url: 'https://instagram.com/testvenue',
    latitude: 37.7749,
    longitude: -122.4194,
    timezone: 'America/Los_Angeles',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Venue',
      icon: 'map-pin',
      color: '#ff0000',
    },
    rating: 4,
    timeoff_required_default: false,
    travel_required_default: true,
    notes: 'Test notes',
    is_known: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }

  describe('listLocations', () => {
    test('lists locations without filters', async () => {
      const mockResponse: LocationListResponse = {
        items: [mockLocation],
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listLocations()

      expect(api.get).toHaveBeenCalledWith('/locations', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('lists locations with category filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listLocations({ category_guid: 'cat_01hgw2bbg00000000000000001' })

      expect(api.get).toHaveBeenCalledWith('/locations', {
        params: { category_guid: 'cat_01hgw2bbg00000000000000001' },
      })
    })

    test('lists locations with known_only filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listLocations({ known_only: true })

      expect(api.get).toHaveBeenCalledWith('/locations', {
        params: { known_only: true },
      })
    })

    test('lists locations with search filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listLocations({ search: '  test query  ' })

      expect(api.get).toHaveBeenCalledWith('/locations', {
        params: { search: 'test query' },
      })
    })

    test('lists locations with pagination', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listLocations({ limit: 50, offset: 100 })

      expect(api.get).toHaveBeenCalledWith('/locations', {
        params: { limit: 50, offset: 100 },
      })
    })

    test('trims empty search string', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listLocations({ search: '   ' })

      expect(api.get).toHaveBeenCalledWith('/locations', { params: {} })
    })
  })

  describe('getLocation', () => {
    test('retrieves a single location by GUID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockLocation })

      const result = await getLocation('loc_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('loc_01hgw2bbg00000000000000001', 'loc')
      expect(api.get).toHaveBeenCalledWith('/locations/loc_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockLocation)
    })
  })

  describe('createLocation', () => {
    test('creates a location with required fields', async () => {
      const request: LocationCreateRequest = {
        name: 'New Venue',
        category_guid: 'cat_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockLocation })

      const result = await createLocation(request)

      expect(api.post).toHaveBeenCalledWith('/locations', request)
      expect(result).toEqual(mockLocation)
    })

    test('creates a location with all optional fields', async () => {
      const request: LocationCreateRequest = {
        name: 'New Venue',
        category_guid: 'cat_01hgw2bbg00000000000000001',
        address: '456 Oak St',
        city: 'Oakland',
        state: 'CA',
        country: 'USA',
        postal_code: '94601',
        website: 'https://newvenue.com',
        instagram_handle: 'newvenue',
        latitude: 37.8044,
        longitude: -122.2712,
        timezone: 'America/Los_Angeles',
        rating: 5,
        timeoff_required_default: true,
        travel_required_default: false,
        notes: 'Great location',
        is_known: true,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockLocation })

      await createLocation(request)

      expect(api.post).toHaveBeenCalledWith('/locations', request)
    })
  })

  describe('updateLocation', () => {
    test('updates a location with partial data', async () => {
      const updateData: LocationUpdateRequest = {
        name: 'Updated Venue',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: { ...mockLocation, name: 'Updated Venue' } })

      const result = await updateLocation('loc_01hgw2bbg00000000000000001', updateData)

      expect(validateGuid).toHaveBeenCalledWith('loc_01hgw2bbg00000000000000001', 'loc')
      expect(api.patch).toHaveBeenCalledWith('/locations/loc_01hgw2bbg00000000000000001', updateData)
      expect(result.name).toBe('Updated Venue')
    })

    test('updates a location with multiple fields', async () => {
      const updateData: LocationUpdateRequest = {
        name: 'Updated Venue',
        rating: 5,
        notes: 'Updated notes',
        is_known: false,
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockLocation })

      await updateLocation('loc_01hgw2bbg00000000000000001', updateData)

      expect(api.patch).toHaveBeenCalledWith('/locations/loc_01hgw2bbg00000000000000001', updateData)
    })
  })

  describe('deleteLocation', () => {
    test('deletes a location by GUID', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: undefined })

      await deleteLocation('loc_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('loc_01hgw2bbg00000000000000001', 'loc')
      expect(api.delete).toHaveBeenCalledWith('/locations/loc_01hgw2bbg00000000000000001')
    })
  })

  describe('getLocationStats', () => {
    test('retrieves location statistics', async () => {
      const mockStats: LocationStatsResponse = {
        total_count: 100,
        known_count: 75,
        with_coordinates_count: 90,
        with_instagram_count: 50,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getLocationStats()

      expect(api.get).toHaveBeenCalledWith('/locations/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('getLocationsByCategory', () => {
    test('retrieves locations for a category with default known_only=true', async () => {
      const mockLocations: Location[] = [mockLocation]

      vi.mocked(api.get).mockResolvedValue({ data: mockLocations })

      const result = await getLocationsByCategory('cat_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith('/locations/by-category/cat_01hgw2bbg00000000000000001', {
        params: { known_only: true },
      })
      expect(result).toEqual(mockLocations)
    })

    test('retrieves locations for a category with known_only=false', async () => {
      const mockLocations: Location[] = [mockLocation]

      vi.mocked(api.get).mockResolvedValue({ data: mockLocations })

      const result = await getLocationsByCategory('cat_01hgw2bbg00000000000000001', false)

      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith('/locations/by-category/cat_01hgw2bbg00000000000000001', {
        params: { known_only: false },
      })
      expect(result).toEqual(mockLocations)
    })
  })

  describe('geocodeAddress', () => {
    test('geocodes an address successfully', async () => {
      const mockResponse: GeocodeResponse = {
        address: '123 Main St',
        city: 'San Francisco',
        state: 'CA',
        country: 'USA',
        postal_code: '94102',
        latitude: 37.7749,
        longitude: -122.4194,
        timezone: 'America/Los_Angeles',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await geocodeAddress('123 Main St, San Francisco, CA')

      expect(api.post).toHaveBeenCalledWith('/locations/geocode', {
        address: '123 Main St, San Francisco, CA',
      })
      expect(result).toEqual(mockResponse)
    })

    test('geocodes with null optional fields', async () => {
      const mockResponse: GeocodeResponse = {
        address: null,
        city: null,
        state: null,
        country: null,
        postal_code: null,
        latitude: 37.7749,
        longitude: -122.4194,
        timezone: null,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await geocodeAddress('Approximate Location')

      expect(result.latitude).toBe(37.7749)
      expect(result.longitude).toBe(-122.4194)
      expect(result.address).toBeNull()
    })
  })

  describe('validateCategoryMatch', () => {
    test('validates matching categories', async () => {
      const mockResponse: CategoryMatchResponse = {
        matches: true,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await validateCategoryMatch(
        'loc_01hgw2bbg00000000000000001',
        'cat_01hgw2bbg00000000000000001'
      )

      expect(validateGuid).toHaveBeenCalledWith('loc_01hgw2bbg00000000000000001', 'loc')
      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith(
        '/locations/loc_01hgw2bbg00000000000000001/validate-category/cat_01hgw2bbg00000000000000001'
      )
      expect(result).toBe(true)
    })

    test('validates non-matching categories', async () => {
      const mockResponse: CategoryMatchResponse = {
        matches: false,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await validateCategoryMatch(
        'loc_01hgw2bbg00000000000000001',
        'cat_01hgw2bbg00000000000000002'
      )

      expect(result).toBe(false)
    })
  })
})
