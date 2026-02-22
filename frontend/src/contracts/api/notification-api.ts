/**
 * Notification API Type Definitions
 *
 * Types for push subscription, notification preferences, and history endpoints.
 * Issue #114 - PWA with Push Notifications
 */

import type { NotificationCategory } from '../domain-labels'
import type { AuditInfo } from './audit-api'

// ============================================================================
// Push Subscription Types
// ============================================================================

/**
 * Request body for creating a push subscription
 */
export interface PushSubscriptionCreateRequest {
  endpoint: string
  p256dh_key: string
  auth_key: string
  device_name?: string
}

/**
 * Push subscription response
 */
export interface PushSubscriptionResponse {
  guid: string
  endpoint: string
  device_name: string | null
  created_at: string
  last_used_at: string | null
  audit?: AuditInfo | null
}

/**
 * Subscription status response
 */
export interface SubscriptionStatusResponse {
  notifications_enabled: boolean
  subscriptions: PushSubscriptionResponse[]
}

/**
 * Request body for updating a push subscription (rename)
 */
export interface PushSubscriptionUpdateRequest {
  device_name: string
}

/**
 * Response for test push delivery
 */
export interface TestPushResponse {
  success: boolean
  error?: string | null
}

/**
 * Request body for removing a push subscription
 */
export interface PushSubscriptionRemoveRequest {
  endpoint: string
}

// ============================================================================
// Notification Preferences Types
// ============================================================================

/**
 * Notification preferences response
 */
export interface NotificationPreferencesResponse {
  enabled: boolean
  job_failures: boolean
  inflection_points: boolean
  agent_status: boolean
  deadline: boolean
  conflict: boolean
  retry_warning: boolean
  deadline_days_before: number
  timezone: string
  retention_days: number
}

/**
 * Notification preferences update request (all fields optional)
 */
export interface NotificationPreferencesUpdateRequest {
  enabled?: boolean
  job_failures?: boolean
  inflection_points?: boolean
  agent_status?: boolean
  deadline?: boolean
  conflict?: boolean
  retry_warning?: boolean
  deadline_days_before?: number
  timezone?: string
  retention_days?: number
}

// ============================================================================
// Notification History Types
// ============================================================================

/**
 * Notification data payload
 */
export interface NotificationData {
  url?: string
  job_guid?: string
  collection_guid?: string
  result_guid?: string
  event_guid?: string
  agent_guid?: string
}

/**
 * Single notification response
 */
export interface NotificationResponse {
  guid: string
  category: NotificationCategory
  title: string
  body: string
  data: NotificationData | null
  read_at: string | null
  created_at: string
  audit?: AuditInfo | null
}

/**
 * Paginated notification list response
 */
export interface NotificationListResponse {
  items: NotificationResponse[]
  total: number
  limit: number
  offset: number
}

/**
 * Query parameters for listing notifications
 */
export interface NotificationListParams {
  limit?: number
  offset?: number
  category?: NotificationCategory
  unread_only?: boolean
  search?: string
  from_date?: string
  to_date?: string
  read_only?: boolean
}

/**
 * Notification stats response for TopHeader KPIs
 */
export interface NotificationStatsResponse {
  total_count: number
  unread_count: number
  this_week_count: number
}

/**
 * Unread count response
 */
export interface UnreadCountResponse {
  unread_count: number
}

/**
 * Mark all read response
 */
export interface MarkAllReadResponse {
  updated_count: number
}

/**
 * VAPID public key response
 */
export interface VapidKeyResponse {
  vapid_public_key: string
}
