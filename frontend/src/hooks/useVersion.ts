/**
 * useVersion React hook
 *
 * Fetches the application version from the backend API.
 * The version is synchronized with GitHub release tags.
 *
 * Usage:
 *   const { version, loading, error } = useVersion()
 */

import { useState, useEffect } from 'react'
import api from '@/services/api'

interface VersionResponse {
  version: string
}

interface UseVersionReturn {
  version: string
  loading: boolean
  error: string | null
}

/**
 * Fetch and manage application version state
 *
 * Automatically fetches version on mount. Returns a fallback version
 * if the API call fails to ensure graceful degradation.
 *
 * @returns Version state object
 */
export const useVersion = (): UseVersionReturn => {
  const [version, setVersion] = useState<string>('...')
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchVersion = async () => {
      setLoading(true)
      setError(null)

      try {
        // Fetch version from backend API
        const response = await api.get<VersionResponse>('/version', {
          timeout: 5000, // 5 second timeout for version check
        })

        setVersion(response.data.version)
      } catch (err: any) {
        console.warn('[useVersion] Failed to fetch version from API:', err.message)

        // Set error but don't fail - use fallback
        setError('Failed to fetch version')

        // Fallback to a development version indicator
        setVersion('v0.0.0-dev')
      } finally {
        setLoading(false)
      }
    }

    fetchVersion()
  }, []) // Run once on mount

  return { version, loading, error }
}

export default useVersion
