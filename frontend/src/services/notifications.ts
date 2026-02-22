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
  PushSubscriptionUpdateRequest,
  PushSubscriptionRemoveRequest,
  TestPushResponse,
  SubscriptionStatusResponse,
  NotificationPreferencesResponse,
  NotificationPreferencesUpdateRequest,
  NotificationResponse,
  NotificationListResponse,
  NotificationListParams,
  NotificationStatsResponse,
  UnreadCountResponse,
  MarkAllReadResponse,
  VapidKeyResponse,
  PushHealthResponse,
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
 * Remove a push subscription by endpoint (current device)
 */
export const unsubscribe = async (
  data: PushSubscriptionRemoveRequest
): Promise<void> => {
  await api.delete('/notifications/subscribe', { data })
}

/**
 * Remove a push subscription by GUID (any device, e.g. lost devices)
 *
 * @param guid - Subscription GUID (sub_xxx)
 */
export const unsubscribeByGuid = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'sub'))
  await api.delete(`/notifications/subscribe/${safeGuid}`)
}

/**
 * Send a test push notification to a specific device
 *
 * @param guid - Subscription GUID (sub_xxx)
 */
export const testDevice = async (guid: string): Promise<TestPushResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'sub'))
  const response = await api.post<TestPushResponse>(
    `/notifications/subscribe/${safeGuid}/test`
  )
  return response.data
}

/**
 * Rename a push subscription device
 *
 * @param guid - Subscription GUID (sub_xxx)
 * @param deviceName - New device name
 */
export const renameDevice = async (
  guid: string,
  deviceName: string
): Promise<PushSubscriptionResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'sub'))
  const response = await api.patch<PushSubscriptionResponse>(
    `/notifications/subscribe/${safeGuid}`,
    { device_name: deviceName } satisfies PushSubscriptionUpdateRequest
  )
  return response.data
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
  if (params.search) queryParams.search = params.search
  if (params.from_date) queryParams.from_date = params.from_date
  if (params.to_date) queryParams.to_date = params.to_date
  if (params.read_only !== undefined) queryParams.read_only = params.read_only

  const response = await api.get<NotificationListResponse>('/notifications', {
    params: queryParams,
  })
  return response.data
}

/**
 * Get notification stats for TopHeader KPIs
 */
export const getNotificationStats = async (): Promise<NotificationStatsResponse> => {
  const response = await api.get<NotificationStatsResponse>(
    '/notifications/stats'
  )
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

/**
 * Mark all unread notifications as read
 */
export const markAllAsRead = async (): Promise<MarkAllReadResponse> => {
  const response = await api.post<MarkAllReadResponse>(
    '/notifications/mark-all-read'
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

// ============================================================================
// Push Health
// ============================================================================

/**
 * Get push notification health status for PWA diagnostics
 */
export const getPushHealth = async (): Promise<PushHealthResponse> => {
  const response = await api.get<PushHealthResponse>(
    '/notifications/push/health'
  )
  return response.data
}
