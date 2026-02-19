/**
 * Release Manifests API client for super admin management.
 *
 * Provides functions for creating, listing, and managing release manifests.
 * All endpoints require super admin privileges.
 *
 * Part of Issue #90 - Distributed Agent Architecture
 */

import api from './api'
import type {
  ReleaseManifest,
  ReleaseManifestCreateRequest,
  ReleaseManifestUpdateRequest,
  ReleaseManifestListResponse,
  ReleaseManifestStatsResponse,
  ReleaseManifestListOptions,
} from '@/contracts/api/release-manifests-api'

// ============================================================================
// API Functions
// ============================================================================

/**
 * Create a new release manifest.
 *
 * @param data - Manifest creation request
 * @returns The created manifest
 */
export async function createManifest(
  data: ReleaseManifestCreateRequest
): Promise<ReleaseManifest> {
  const response = await api.post<ReleaseManifest>('/admin/release-manifests', data)
  return response.data
}

/**
 * List release manifests with optional filters.
 *
 * @param options - Optional filters
 * @returns List of manifests with counts
 */
export async function listManifests(
  options?: ReleaseManifestListOptions
): Promise<ReleaseManifestListResponse> {
  const params = new URLSearchParams()
  if (options?.active_only) {
    params.append('active_only', 'true')
  }
  if (options?.platform) {
    params.append('platform', options.platform)
  }
  if (options?.version) {
    params.append('version', options.version)
  }
  if (options?.latest_only) {
    params.append('latest_only', 'true')
  }

  const response = await api.get<ReleaseManifestListResponse>('/admin/release-manifests', {
    params,
  })
  return response.data
}

/**
 * Get release manifest statistics.
 *
 * @returns Aggregate statistics about release manifests
 */
export async function getManifestStats(): Promise<ReleaseManifestStatsResponse> {
  const response = await api.get<ReleaseManifestStatsResponse>('/admin/release-manifests/stats')
  return response.data
}

/**
 * Get a specific release manifest by GUID.
 *
 * @param guid - Manifest GUID (rel_xxx)
 * @returns Manifest details
 */
export async function getManifest(guid: string): Promise<ReleaseManifest> {
  const response = await api.get<ReleaseManifest>(`/admin/release-manifests/${guid}`)
  return response.data
}

/**
 * Update a release manifest.
 *
 * Only is_active and notes can be updated.
 *
 * @param guid - Manifest GUID (rel_xxx)
 * @param data - Fields to update
 * @returns Updated manifest
 */
export async function updateManifest(
  guid: string,
  data: ReleaseManifestUpdateRequest
): Promise<ReleaseManifest> {
  const response = await api.patch<ReleaseManifest>(`/admin/release-manifests/${guid}`, data)
  return response.data
}

/**
 * Delete a release manifest.
 *
 * Consider deactivating instead to preserve the record.
 *
 * @param guid - Manifest GUID (rel_xxx)
 */
export async function deleteManifest(guid: string): Promise<void> {
  await api.delete(`/admin/release-manifests/${guid}`)
}
