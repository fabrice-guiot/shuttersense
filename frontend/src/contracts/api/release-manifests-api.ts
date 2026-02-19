/**
 * Release Manifests API contract.
 *
 * Defines TypeScript interfaces for the Release Manifests admin API.
 * Used for managing known-good agent binary checksums.
 *
 * Part of Issue #90 - Distributed Agent Architecture
 */

import type { AuditInfo } from './audit-api'

/**
 * Per-platform binary artifact within a release manifest (admin view).
 */
export interface ManifestArtifact {
  /** Platform identifier (e.g., "darwin-arm64") */
  platform: string
  /** Binary filename (e.g., "shuttersense-agent-darwin-arm64") */
  filename: string
  /** sha256:-prefixed hex checksum */
  checksum: string
  /** File size in bytes, or null if unknown */
  file_size: number | null
  /** Creation timestamp (ISO 8601) */
  created_at: string
}

/**
 * Artifact data for creating artifacts alongside a manifest.
 */
export interface ManifestArtifactCreateRequest {
  /** Platform identifier */
  platform: string
  /** Binary filename */
  filename: string
  /** sha256:-prefixed hex checksum */
  checksum: string
  /** File size in bytes (optional) */
  file_size?: number | null
}

/**
 * Release manifest entity.
 */
export interface ReleaseManifest {
  /** Release manifest GUID (rel_xxx) */
  guid: string
  /** Semantic version (e.g., "1.0.0") */
  version: string
  /** Platforms this binary supports (e.g., ["darwin-arm64", "darwin-amd64"]) */
  platforms: string[]
  /** SHA-256 checksum of the binary (64 hex characters) */
  checksum: string
  /** Whether this manifest allows agent registration */
  is_active: boolean
  /** Optional notes about this release */
  notes: string | null
  /** Per-platform binary artifacts (populated from admin detail endpoint) */
  artifacts: ManifestArtifact[]
  /** Creation timestamp (ISO 8601) */
  created_at: string
  /** Last update timestamp (ISO 8601) */
  updated_at: string
  audit?: AuditInfo | null
}

/**
 * Request to create a new release manifest.
 */
export interface ReleaseManifestCreateRequest {
  /** Semantic version (e.g., "1.0.0") */
  version: string
  /** Platforms this binary supports */
  platforms: string[]
  /** SHA-256 checksum of the binary (64 hex characters) */
  checksum: string
  /** Optional notes about this release */
  notes?: string
  /** Whether to activate immediately (default: true) */
  is_active?: boolean
  /** Optional per-platform binary artifacts */
  artifacts?: ManifestArtifactCreateRequest[]
}

/**
 * Request to update an existing release manifest.
 * Only is_active and notes can be updated.
 */
export interface ReleaseManifestUpdateRequest {
  /** Whether this manifest allows agent registration */
  is_active?: boolean
  /** Optional notes about this release */
  notes?: string
}

/**
 * Response from listing release manifests.
 */
export interface ReleaseManifestListResponse {
  /** List of release manifests */
  manifests: ReleaseManifest[]
  /** Total count of manifests (matching filters) */
  total_count: number
  /** Count of active manifests (matching filters) */
  active_count: number
}

/**
 * Release manifest statistics.
 */
export interface ReleaseManifestStatsResponse {
  /** Total number of release manifests */
  total_count: number
  /** Number of active release manifests */
  active_count: number
  /** List of unique platforms across all manifests */
  platforms: string[]
  /** List of unique versions (sorted descending) */
  versions: string[]
}

/**
 * Options for listing release manifests.
 */
export interface ReleaseManifestListOptions {
  /** Filter to only active manifests */
  active_only?: boolean
  /** Filter by platform (manifests that support this platform) */
  platform?: string
  /** Filter by version */
  version?: string
  /** Only return the most recent manifest per version string */
  latest_only?: boolean
}

/**
 * Valid platform identifiers for agent binaries.
 */
export const VALID_PLATFORMS = [
  'darwin-arm64',
  'darwin-amd64',
  'linux-amd64',
  'linux-arm64',
  'windows-amd64',
] as const

/**
 * Type for valid platform identifiers.
 */
export type ValidPlatform = (typeof VALID_PLATFORMS)[number]

/**
 * Platform display labels for the UI.
 */
export const PLATFORM_LABELS: Record<ValidPlatform, string> = {
  'darwin-arm64': 'macOS (Apple Silicon)',
  'darwin-amd64': 'macOS (Intel)',
  'linux-amd64': 'Linux (x86_64)',
  'linux-arm64': 'Linux (ARM64)',
  'windows-amd64': 'Windows (x86_64)',
}
