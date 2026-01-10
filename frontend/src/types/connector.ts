/**
 * Connector Type Definitions
 *
 * TypeScript interfaces for connector entities and API interactions.
 * These mirror the backend FastAPI endpoints for remote storage connections.
 */

// ============================================================================
// Core Types
// ============================================================================

export type ConnectorType = 's3' | 'gcs' | 'smb'

export interface Connector {
  id: number
  guid: string  // External identifier (con_xxx)
  name: string
  type: ConnectorType
  is_active: boolean
  metadata?: Record<string, unknown> | null
  last_validated?: string | null
  last_error?: string | null
  created_at: string  // ISO 8601 timestamp
  updated_at: string  // ISO 8601 timestamp
}

// ============================================================================
// Credentials Types (Polymorphic by ConnectorType)
// ============================================================================

export type ConnectorCredentials =
  | S3Credentials
  | GCSCredentials
  | SMBCredentials

export interface S3Credentials {
  aws_access_key_id: string
  aws_secret_access_key: string
  region: string
  bucket?: string
}

export interface GCSCredentials {
  service_account_json: string
  bucket?: string
}

export interface SMBCredentials {
  server: string
  share: string
  username: string
  password: string
  domain?: string
}

// ============================================================================
// API Request Types
// ============================================================================

export interface ConnectorCreateRequest {
  name: string
  type: ConnectorType
  credentials: Record<string, unknown>
  metadata?: Record<string, unknown> | null
}

export interface ConnectorUpdateRequest {
  name?: string
  credentials?: Record<string, unknown>
  metadata?: Record<string, unknown> | null
  is_active?: boolean
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ConnectorListResponse {
  connectors: Connector[]
  total: number
}

export interface ConnectorDetailResponse {
  connector: Connector
}

export interface ConnectorTestResponse {
  success: boolean
  message: string
  details?: {
    connection_time_ms?: number
    endpoint?: string
    [key: string]: unknown
  }
}

export interface ConnectorDeleteResponse {
  success: boolean
  message: string
}

// ============================================================================
// Form Data Types
// ============================================================================

export interface ConnectorFormData {
  name: string
  type: ConnectorType
  active: boolean
  credentials: Partial<ConnectorCredentials>
}

export interface ConnectorCreate extends Omit<Connector, 'id' | 'created_at' | 'updated_at'> {}
export interface ConnectorUpdate extends Partial<ConnectorCreate> {}
