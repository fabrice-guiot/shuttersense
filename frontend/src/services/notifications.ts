/**
 * Notifications API service
 *
 * Handles all API calls for push subscriptions, notification preferences,
 * and notification history.
 *
 * Issue #114 - PWA with Push Notifications
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  PushSubscriptionCreateRequest,
  PushSubscriptionResponse,
  PushSubscriptionRemoveRequest,
  SubscriptionStatusResponse,
  NotificationPreferencesResponse,
  NotificationPreferencesUpdateRequest,
  NotificationResponse,
  NotificationListResponse,
  NotificationListParams,
  UnreadCountResponse,
  VapidKeyResponse,
} from '@/contracts/api/notification-api'

// ============================================================================
// Push Subscription
// ============================================================================

/**
 * Register a push subscription for the current device
 */
export const subscribe = async (
  data: PushSubscriptionCreateRequest
): Promise<PushSubscriptionResponse> => {
  const response = await api.post<PushSubscriptionResponse>(
    '/notifications/subscribe',
    data
  )
  return response.data
}

/**
 * Remove a push subscription by endpoint
 */
export const unsubscribe = async (
  data: PushSubscriptionRemoveRequest
): Promise<void> => {
  await api.delete('/notifications/subscribe', { data })
}

/**
 * Get push subscription status (enabled state + active subscriptions)
 */
export const getStatus = async (): Promise<SubscriptionStatusResponse> => {
  const response = await api.get<SubscriptionStatusResponse>(
    '/notifications/status'
  )
  return response.data
}

// ============================================================================
// Notification Preferences
// ============================================================================

/**
 * Get notification preferences for the current user
 */
export const getPreferences = async (): Promise<NotificationPreferencesResponse> => {
  const response = await api.get<NotificationPreferencesResponse>(
    '/notifications/preferences'
  )
  return response.data
}

/**
 * Update notification preferences (partial update)
 */
export const updatePreferences = async (
  data: NotificationPreferencesUpdateRequest
): Promise<NotificationPreferencesResponse> => {
  const response = await api.put<NotificationPreferencesResponse>(
    '/notifications/preferences',
    data
  )
  return response.data
}

// ============================================================================
// Notification History
// ============================================================================

/**
 * List notifications with optional filtering and pagination
 */
export const listNotifications = async (
  params: NotificationListParams = {}
): Promise<NotificationListResponse> => {
  const queryParams: Record<string, string | number | boolean> = {}

  if (params.limit !== undefined) queryParams.limit = params.limit
  if (params.offset !== undefined) queryParams.offset = params.offset
  if (params.category) queryParams.category = params.category
  if (params.unread_only !== undefined) queryParams.unread_only = params.unread_only

  const response = await api.get<NotificationListResponse>('/notifications', {
    params: queryParams,
  })
  return response.data
}

/**
 * Get unread notification count for the bell badge
 */
export const getUnreadCount = async (): Promise<UnreadCountResponse> => {
  const response = await api.get<UnreadCountResponse>(
    '/notifications/unread-count'
  )
  return response.data
}

/**
 * Mark a notification as read
 *
 * @param guid - Notification GUID (ntf_xxx)
 */
export const markAsRead = async (
  guid: string
): Promise<NotificationResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'ntf'))
  const response = await api.post<NotificationResponse>(
    `/notifications/${safeGuid}/read`
  )
  return response.data
}

// ============================================================================
// VAPID Key
// ============================================================================

/**
 * Get the server's VAPID public key for PushManager.subscribe()
 */
export const getVapidKey = async (): Promise<VapidKeyResponse> => {
  const response = await api.get<VapidKeyResponse>(
    '/notifications/vapid-key'
  )
  return response.data
}
