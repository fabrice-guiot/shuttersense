import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  subscribe,
  unsubscribe,
  unsubscribeByGuid,
  getStatus,
  getPreferences,
  updatePreferences,
  listNotifications,
  getNotificationStats,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  getVapidKey,
} from '@/services/notifications'
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
  NotificationStatsResponse,
  UnreadCountResponse,
  MarkAllReadResponse,
  VapidKeyResponse,
} from '@/contracts/api/notification-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Notifications Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('subscribe', () => {
    test('registers a push subscription', async () => {
      const requestData: PushSubscriptionCreateRequest = {
        endpoint: 'https://fcm.googleapis.com/fcm/send/...',
        p256dh_key: 'BKxH...==',
        auth_key: 'Ab3D...==',
        device_name: 'My MacBook Pro',
      }

      const mockResponse: PushSubscriptionResponse = {
        guid: 'sub_01hgw2bbg00000000000000001',
        endpoint: requestData.endpoint,
        device_name: requestData.device_name || null,
        created_at: '2026-01-01T00:00:00Z',
        last_used_at: null,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await subscribe(requestData)

      expect(api.post).toHaveBeenCalledWith('/notifications/subscribe', requestData)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('unsubscribe', () => {
    test('removes a push subscription by endpoint', async () => {
      const requestData: PushSubscriptionRemoveRequest = {
        endpoint: 'https://fcm.googleapis.com/fcm/send/...',
      }

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await unsubscribe(requestData)

      expect(api.delete).toHaveBeenCalledWith('/notifications/subscribe', { data: requestData })
    })
  })

  describe('unsubscribeByGuid', () => {
    test('removes a push subscription by GUID', async () => {
      const guid = 'sub_01hgw2bbg00000000000000001'

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await unsubscribeByGuid(guid)

      expect(api.delete).toHaveBeenCalledWith(`/notifications/subscribe/${encodeURIComponent(guid)}`)
    })

    test('throws error for invalid GUID', async () => {
      await expect(unsubscribeByGuid('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('getStatus', () => {
    test('fetches subscription status', async () => {
      const mockResponse: SubscriptionStatusResponse = {
        notifications_enabled: true,
        subscriptions: [
          {
            guid: 'sub_01hgw2bbg00000000000000001',
            endpoint: 'https://fcm.googleapis.com/fcm/send/...',
            device_name: 'My MacBook Pro',
            created_at: '2026-01-01T00:00:00Z',
            last_used_at: '2026-01-01T12:00:00Z',
          },
        ],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getStatus()

      expect(api.get).toHaveBeenCalledWith('/notifications/status')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getPreferences', () => {
    test('fetches notification preferences', async () => {
      const mockResponse: NotificationPreferencesResponse = {
        enabled: true,
        job_failures: true,
        inflection_points: true,
        agent_status: false,
        deadline: true,
        conflict: true,
        retry_warning: true,
        deadline_days_before: 7,
        timezone: 'America/New_York',
        retention_days: 90,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getPreferences()

      expect(api.get).toHaveBeenCalledWith('/notifications/preferences')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('updatePreferences', () => {
    test('updates notification preferences', async () => {
      const requestData: NotificationPreferencesUpdateRequest = {
        job_failures: false,
        deadline_days_before: 14,
      }

      const mockResponse: NotificationPreferencesResponse = {
        enabled: true,
        job_failures: false,
        inflection_points: true,
        agent_status: false,
        deadline: true,
        conflict: true,
        retry_warning: true,
        deadline_days_before: 14,
        timezone: 'America/New_York',
        retention_days: 90,
      }

      vi.mocked(api.put).mockResolvedValue({ data: mockResponse })

      const result = await updatePreferences(requestData)

      expect(api.put).toHaveBeenCalledWith('/notifications/preferences', requestData)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('listNotifications', () => {
    test('lists notifications without filters', async () => {
      const mockResponse: NotificationListResponse = {
        items: [
          {
            guid: 'ntf_01hgw2bbg00000000000000001',
            category: 'job_failure',
            title: 'Job Failed',
            body: 'PhotoStats analysis failed',
            data: { job_guid: 'job_123' },
            read_at: null,
            created_at: '2026-01-01T00:00:00Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listNotifications()

      expect(api.get).toHaveBeenCalledWith('/notifications', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('lists notifications with all query parameters', async () => {
      const params: NotificationListParams = {
        limit: 50,
        offset: 10,
        category: 'job_failure',
        unread_only: true,
        search: 'PhotoStats',
        from_date: '2026-01-01',
        to_date: '2026-01-31',
        read_only: false,
      }

      const mockResponse: NotificationListResponse = {
        items: [],
        total: 0,
        limit: 50,
        offset: 10,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listNotifications(params)

      expect(api.get).toHaveBeenCalledWith('/notifications', {
        params: {
          limit: 50,
          offset: 10,
          category: 'job_failure',
          unread_only: true,
          search: 'PhotoStats',
          from_date: '2026-01-01',
          to_date: '2026-01-31',
          read_only: false,
        },
      })
      expect(result).toEqual(mockResponse)
    })

    test('omits undefined parameters', async () => {
      const params: NotificationListParams = {
        category: 'job_failure',
      }

      vi.mocked(api.get).mockResolvedValue({
        data: { items: [], total: 0, limit: 20, offset: 0 },
      })

      await listNotifications(params)

      expect(api.get).toHaveBeenCalledWith('/notifications', {
        params: { category: 'job_failure' },
      })
    })
  })

  describe('getNotificationStats', () => {
    test('fetches notification statistics', async () => {
      const mockResponse: NotificationStatsResponse = {
        total_count: 100,
        unread_count: 15,
        this_week_count: 42,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getNotificationStats()

      expect(api.get).toHaveBeenCalledWith('/notifications/stats')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getUnreadCount', () => {
    test('fetches unread notification count', async () => {
      const mockResponse: UnreadCountResponse = {
        unread_count: 5,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getUnreadCount()

      expect(api.get).toHaveBeenCalledWith('/notifications/unread-count')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('markAsRead', () => {
    test('marks a notification as read with valid GUID', async () => {
      const guid = 'ntf_01hgw2bbg00000000000000001'

      const mockResponse: NotificationResponse = {
        guid,
        category: 'job_failure',
        title: 'Job Failed',
        body: 'PhotoStats analysis failed',
        data: null,
        read_at: '2026-01-01T12:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await markAsRead(guid)

      expect(api.post).toHaveBeenCalledWith(`/notifications/${encodeURIComponent(guid)}/read`)
      expect(result).toEqual(mockResponse)
    })

    test('throws error for invalid GUID', async () => {
      await expect(markAsRead('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('markAllAsRead', () => {
    test('marks all notifications as read', async () => {
      const mockResponse: MarkAllReadResponse = {
        updated_count: 10,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await markAllAsRead()

      expect(api.post).toHaveBeenCalledWith('/notifications/mark-all-read')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getVapidKey', () => {
    test('fetches VAPID public key', async () => {
      const mockResponse: VapidKeyResponse = {
        vapid_public_key:
          'BNxj...public_key_here...xyz',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getVapidKey()

      expect(api.get).toHaveBeenCalledWith('/notifications/vapid-key')
      expect(result).toEqual(mockResponse)
    })
  })
})
