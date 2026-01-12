/**
 * useLocations React hook
 *
 * Manages location state with fetch, create, update, delete operations
 * Issue #39 - Calendar Events feature (Phase 8)
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as locationService from '../services/locations'
import type {
  Location,
  LocationCreateRequest,
  LocationUpdateRequest,
  LocationListParams,
  LocationStatsResponse,
  GeocodeResponse
} from '@/contracts/api/location-api'

// ============================================================================
// Main Locations Hook
// ============================================================================

interface UseLocationsReturn {
  locations: Location[]
  total: number
  loading: boolean
  error: string | null
  fetchLocations: (params?: LocationListParams) => Promise<{ items: Location[]; total: number }>
  createLocation: (locationData: LocationCreateRequest) => Promise<Location>
  updateLocation: (guid: string, updates: LocationUpdateRequest) => Promise<Location>
  deleteLocation: (guid: string) => Promise<void>
  geocodeAddress: (address: string) => Promise<GeocodeResponse | null>
}

export const useLocations = (autoFetch = true, initialParams?: LocationListParams): UseLocationsReturn => {
  const [locations, setLocations] = useState<Location[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch locations with optional filters
   */
  const fetchLocations = useCallback(async (params: LocationListParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await locationService.listLocations(params)
      setLocations(data.items)
      setTotal(data.total)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load locations'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new location
   */
  const createLocation = useCallback(async (locationData: LocationCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newLocation = await locationService.createLocation(locationData)
      setLocations(prev => [...prev, newLocation])
      setTotal(prev => prev + 1)
      toast.success('Location created successfully')
      return newLocation
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create location'
      setError(errorMessage)
      toast.error('Failed to create location', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing location
   */
  const updateLocation = useCallback(async (guid: string, updates: LocationUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await locationService.updateLocation(guid, updates)
      setLocations(prev =>
        prev.map(l => l.guid === guid ? updated : l)
      )
      toast.success('Location updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update location'
      setError(errorMessage)
      toast.error('Failed to update location', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a location
   */
  const deleteLocation = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await locationService.deleteLocation(guid)
      setLocations(prev => prev.filter(l => l.guid !== guid))
      setTotal(prev => prev - 1)
      toast.success('Location deleted successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete location'
      setError(errorMessage)
      toast.error('Failed to delete location', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Geocode an address
   */
  const geocodeAddress = useCallback(async (address: string): Promise<GeocodeResponse | null> => {
    try {
      const result = await locationService.geocodeAddress(address)
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to geocode address'
      toast.error('Geocoding failed', {
        description: errorMessage
      })
      return null
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchLocations(initialParams)
    }
  }, [autoFetch, fetchLocations, initialParams])

  return {
    locations,
    total,
    loading,
    error,
    fetchLocations,
    createLocation,
    updateLocation,
    deleteLocation,
    geocodeAddress
  }
}

// ============================================================================
// Location Stats Hook
// ============================================================================

interface UseLocationStatsReturn {
  stats: LocationStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching location KPI statistics
 * Returns total, known, and geocoded location counts
 */
export const useLocationStats = (autoFetch = true): UseLocationStatsReturn => {
  const [stats, setStats] = useState<LocationStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await locationService.getLocationStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load location statistics'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      refetch()
    }
  }, [autoFetch, refetch])

  return { stats, loading, error, refetch }
}

// ============================================================================
// Locations by Category Hook
// ============================================================================

interface UseLocationsByCategoryReturn {
  locations: Location[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching locations filtered by category
 * Used when creating/editing events to show compatible locations
 *
 * @param categoryGuid - Category GUID to filter by (null disables fetching)
 * @param knownOnly - If true, only return saved locations (default: true)
 */
export const useLocationsByCategory = (
  categoryGuid: string | null,
  knownOnly: boolean = true
): UseLocationsByCategoryReturn => {
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (!categoryGuid) {
      setLocations([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await locationService.getLocationsByCategory(categoryGuid, knownOnly)
      setLocations(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load locations'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [categoryGuid, knownOnly])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { locations, loading, error, refetch }
}
