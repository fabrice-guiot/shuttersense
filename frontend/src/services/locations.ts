/**
 * Location API service
 *
 * Handles all API calls related to event locations
 * Issue #39 - Calendar Events feature (Phase 8)
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Location,
  LocationCreateRequest,
  LocationUpdateRequest,
  LocationListResponse,
  LocationListParams,
  LocationStatsResponse,
  GeocodeRequest,
  GeocodeResponse,
  CategoryMatchResponse
} from '@/contracts/api/location-api'

/**
 * List all locations with optional filters
 */
export const listLocations = async (params: LocationListParams = {}): Promise<LocationListResponse> => {
  const queryParams: Record<string, string | number | boolean> = {}

  if (params.category_guid !== undefined) {
    queryParams.category_guid = params.category_guid
  }
  if (params.known_only !== undefined) {
    queryParams.known_only = params.known_only
  }
  if (params.search !== undefined && params.search.trim()) {
    queryParams.search = params.search.trim()
  }
  if (params.limit !== undefined) {
    queryParams.limit = params.limit
  }
  if (params.offset !== undefined) {
    queryParams.offset = params.offset
  }

  const response = await api.get<LocationListResponse>('/locations', { params: queryParams })
  return response.data
}

/**
 * Get a single location by GUID
 * @param guid - External ID (loc_xxx format)
 */
export const getLocation = async (guid: string): Promise<Location> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'loc'))
  const response = await api.get<Location>(`/locations/${safeGuid}`)
  return response.data
}

/**
 * Create a new location
 */
export const createLocation = async (data: LocationCreateRequest): Promise<Location> => {
  const response = await api.post<Location>('/locations', data)
  return response.data
}

/**
 * Update an existing location
 * @param guid - External ID (loc_xxx format)
 */
export const updateLocation = async (guid: string, data: LocationUpdateRequest): Promise<Location> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'loc'))
  const response = await api.patch<Location>(`/locations/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a location
 * @param guid - External ID (loc_xxx format)
 * @throws Error 409 if events reference this location
 */
export const deleteLocation = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'loc'))
  await api.delete(`/locations/${safeGuid}`)
}

/**
 * Get location statistics (KPIs)
 * Returns aggregated stats for all locations
 */
export const getLocationStats = async (): Promise<LocationStatsResponse> => {
  const response = await api.get<LocationStatsResponse>('/locations/stats')
  return response.data
}

/**
 * Get locations filtered by category
 * Used when creating/editing events to show compatible locations
 *
 * @param categoryGuid - Category GUID (cat_xxx format)
 * @param knownOnly - If true, only return saved "known" locations (default: true)
 */
export const getLocationsByCategory = async (
  categoryGuid: string,
  knownOnly: boolean = true
): Promise<Location[]> => {
  const safeGuid = encodeURIComponent(validateGuid(categoryGuid, 'cat'))
  const response = await api.get<Location[]>(`/locations/by-category/${safeGuid}`, {
    params: { known_only: knownOnly }
  })
  return response.data
}

/**
 * Geocode an address to get coordinates and timezone
 *
 * @param address - Full address string to geocode
 * @returns Geocoding result with coordinates and address components
 * @throws Error 400 if address cannot be geocoded
 */
export const geocodeAddress = async (address: string): Promise<GeocodeResponse> => {
  const data: GeocodeRequest = { address }
  const response = await api.post<GeocodeResponse>('/locations/geocode', data)
  return response.data
}

/**
 * Validate that a location's category matches an event's category
 *
 * @param locationGuid - Location GUID (loc_xxx format)
 * @param eventCategoryGuid - Event's category GUID (cat_xxx format)
 * @returns Whether the categories match
 */
export const validateCategoryMatch = async (
  locationGuid: string,
  eventCategoryGuid: string
): Promise<boolean> => {
  const safeLocationGuid = encodeURIComponent(validateGuid(locationGuid, 'loc'))
  const safeCategoryGuid = encodeURIComponent(validateGuid(eventCategoryGuid, 'cat'))
  const response = await api.get<CategoryMatchResponse>(
    `/locations/${safeLocationGuid}/validate-category/${safeCategoryGuid}`
  )
  return response.data.matches
}
