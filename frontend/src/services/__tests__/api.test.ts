import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import api from '@/services/api'
import type { ApiErrorResponse, PydanticValidationError } from '@/services/api'
import type { AxiosError } from 'axios'

/**
 * Tests for the API service (axios instance + interceptors)
 *
 * Strategy: Import the real api instance and test its configuration directly.
 * For interceptors, extract the installed handlers from the axios internals
 * and invoke them with crafted request/response objects.
 */

// Extract the response error interceptor from the real api instance
function getResponseErrorInterceptor(): (error: AxiosError<ApiErrorResponse>) => Promise<never> {
  const handlers = (api.interceptors.response as any).handlers as Array<{
    fulfilled: any
    rejected: any
  }>
  const handler = handlers.find((h) => h?.rejected)
  if (!handler) throw new Error('No response error interceptor found on api instance')
  return handler.rejected
}

function getResponseSuccessInterceptor(): (response: any) => any {
  const handlers = (api.interceptors.response as any).handlers as Array<{
    fulfilled: any
    rejected: any
  }>
  const handler = handlers.find((h) => h?.fulfilled)
  if (!handler) throw new Error('No response success interceptor found on api instance')
  return handler.fulfilled
}

describe('API Service', () => {
  beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Instance Configuration', () => {
    test('has correct baseURL', () => {
      expect(api.defaults.baseURL).toBe('/api')
    })

    test('has 30 second timeout', () => {
      expect(api.defaults.timeout).toBe(30000)
    })

    test('has JSON content type header', () => {
      expect(api.defaults.headers['Content-Type']).toBe('application/json')
    })
  })

  describe('Response Interceptor - Success', () => {
    test('returns the response', () => {
      const interceptor = getResponseSuccessInterceptor()
      const response = {
        status: 200,
        config: { url: '/collections' },
        data: { items: [] },
      }

      const result = interceptor(response)
      expect(result).toBe(response)
    })
  })

  describe('Response Interceptor - 401 Redirect', () => {
    let errorInterceptor: ReturnType<typeof getResponseErrorInterceptor>
    let originalHref: string

    beforeEach(() => {
      errorInterceptor = getResponseErrorInterceptor()

      // Save originals
      originalHref = window.location.href

      // Mock window.location
      delete (window as any).location
      window.location = {
        href: '',
        pathname: '/collections',
        search: '',
      } as any

      // Mock sessionStorage
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {})
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => null)
    })

    afterEach(() => {
      // Restore location
      delete (window as any).location
      window.location = { href: originalHref } as any
    })

    test('redirects to login on 401 and stores return URL', () => {
      const error = {
        config: { url: '/collections' },
        response: {
          status: 401,
          data: { detail: 'Not authenticated' },
        },
        isAxiosError: true,
        message: 'Request failed with status code 401',
      } as AxiosError<ApiErrorResponse>

      // 401 handler returns a never-resolving promise (navigation redirect)
      errorInterceptor(error)

      expect(sessionStorage.setItem).toHaveBeenCalledWith('returnUrl', '/collections')
      expect(window.location.href).toBe('/login')
    })

    test('skips redirect for auth endpoints', async () => {
      const error = {
        config: { url: '/auth/login' },
        response: {
          status: 401,
          data: { detail: 'Invalid credentials' },
        },
        isAxiosError: true,
        message: 'Request failed with status code 401',
      } as AxiosError<ApiErrorResponse>

      await expect(errorInterceptor(error)).rejects.toHaveProperty(
        'userMessage',
        'Invalid credentials'
      )

      expect(window.location.href).toBe('')
      expect(sessionStorage.setItem).not.toHaveBeenCalled()
    })

    test('does not store returnUrl when already on login page', () => {
      window.location.pathname = '/login'

      const error = {
        config: { url: '/collections' },
        response: {
          status: 401,
          data: { detail: 'Not authenticated' },
        },
        isAxiosError: true,
        message: 'Request failed with status code 401',
      } as AxiosError<ApiErrorResponse>

      errorInterceptor(error)

      expect(sessionStorage.setItem).not.toHaveBeenCalled()
      expect(window.location.href).toBe('/login')
    })
  })

  describe('Response Interceptor - Error Formatting', () => {
    let errorInterceptor: ReturnType<typeof getResponseErrorInterceptor>

    beforeEach(() => {
      errorInterceptor = getResponseErrorInterceptor()
    })

    test('formats Pydantic validation errors (array of objects)', async () => {
      const validationErrors: PydanticValidationError[] = [
        {
          type: 'string_too_short',
          loc: ['body', 'name'],
          msg: 'String should have at least 1 character',
        },
        {
          type: 'missing',
          loc: ['body', 'category_guid'],
          msg: 'Field required',
        },
      ]

      const error = {
        config: { url: '/events' },
        response: {
          status: 422,
          data: { detail: validationErrors },
        },
        isAxiosError: true,
        message: 'Request failed with status code 422',
      } as AxiosError<ApiErrorResponse>

      await expect(errorInterceptor(error)).rejects.toHaveProperty(
        'userMessage',
        'name: String should have at least 1 character; category_guid: Field required'
      )
    })

    test('filters out "body" from validation error location', async () => {
      const validationErrors: PydanticValidationError[] = [
        {
          type: 'missing',
          loc: ['body'],
          msg: 'Request body is required',
        },
      ]

      const error = {
        config: { url: '/events' },
        response: {
          status: 422,
          data: { detail: validationErrors },
        },
        isAxiosError: true,
        message: 'Request failed with status code 422',
      } as AxiosError<ApiErrorResponse>

      await expect(errorInterceptor(error)).rejects.toHaveProperty(
        'userMessage',
        'Request body is required'
      )
    })

    test('extracts string detail from error response', async () => {
      const error = {
        config: { url: '/events/evt_xxx' },
        response: {
          status: 404,
          data: { detail: 'Event not found' },
        },
        isAxiosError: true,
        message: 'Request failed with status code 404',
      } as AxiosError<ApiErrorResponse>

      await expect(errorInterceptor(error)).rejects.toHaveProperty(
        'userMessage',
        'Event not found'
      )
    })

    test('extracts message from nested error object', async () => {
      const error = {
        config: { url: '/events' },
        response: {
          status: 500,
          data: {
            error: {
              message: 'Database connection failed',
              code: 'DB_ERROR',
            },
          },
        },
        isAxiosError: true,
        message: 'Request failed with status code 500',
      } as AxiosError<ApiErrorResponse>

      await expect(errorInterceptor(error)).rejects.toHaveProperty(
        'userMessage',
        'Database connection failed'
      )
    })

    test('falls back to axios error message if no detail provided', async () => {
      const error = {
        config: { url: '/events' },
        response: {
          status: 500,
          data: {},
        },
        isAxiosError: true,
        message: 'Request failed with status code 500',
      } as AxiosError<ApiErrorResponse>

      await expect(errorInterceptor(error)).rejects.toHaveProperty(
        'userMessage',
        'Request failed with status code 500'
      )
    })

    test('attaches userMessage property to error object', async () => {
      const error = {
        config: { url: '/events' },
        response: {
          status: 400,
          data: { detail: 'Invalid request' },
        },
        isAxiosError: true,
        message: 'Request failed with status code 400',
      } as AxiosError<ApiErrorResponse>

      try {
        await errorInterceptor(error)
        expect.fail('Should have rejected')
      } catch (e: any) {
        expect(e).toHaveProperty('userMessage')
        expect(e.userMessage).toBe('Invalid request')
      }
    })
  })
})
