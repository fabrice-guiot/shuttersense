/**
 * Camera API Contracts
 *
 * Defines TypeScript interfaces for camera management endpoints.
 * These contracts mirror the backend FastAPI endpoints for Camera CRUD and discovery.
 */

import type { AuditInfo } from './audit-api'

// ============================================================================
// Entity Types
// ============================================================================

export type CameraStatus = 'temporary' | 'confirmed'

export interface CameraResponse {
  guid: string // External identifier (cam_xxx)
  camera_id: string // Short alphanumeric ID from filenames
  status: CameraStatus
  display_name: string | null
  make: string | null
  model: string | null
  serial_number: string | null
  notes: string | null
  metadata_json: Record<string, unknown> | null
  created_at: string // ISO 8601 timestamp
  updated_at: string // ISO 8601 timestamp
  audit?: AuditInfo | null
}

// ============================================================================
// API Request Types
// ============================================================================

export interface CameraUpdateRequest {
  status?: CameraStatus
  display_name?: string
  make?: string
  model?: string
  serial_number?: string
  notes?: string
}

// ============================================================================
// API Response Types
// ============================================================================

export interface CameraListResponse {
  items: CameraResponse[]
  total: number
  limit: number
  offset: number
}

export interface CameraStatsResponse {
  total_cameras: number
  confirmed_count: number
  temporary_count: number
}

export interface CameraDeleteResponse {
  message: string
  deleted_guid: string
}

// ============================================================================
// Discovery Types (Agent-facing, included for completeness)
// ============================================================================

export interface CameraDiscoverRequest {
  camera_ids: string[]
}

export interface CameraDiscoverItem {
  guid: string
  camera_id: string
  status: CameraStatus
  display_name: string | null
}

export interface CameraDiscoverResponse {
  cameras: CameraDiscoverItem[]
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface CameraListQueryParams {
  limit?: number
  offset?: number
  status?: CameraStatus
  search?: string
}
