/**
 * Unit tests for OS detection utility.
 *
 * Tests cover:
 *   - macOS detection (Apple Silicon via WebGL, Intel fallback)
 *   - Linux detection (x86_64 and ARM64)
 *   - Windows detection
 *   - Fallback for unknown platforms
 *   - WebGL failure graceful degradation
 *
 * Issue #136 - Agent Setup Wizard
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { detectPlatform } from '@/lib/os-detection'

// Helper to mock navigator properties
function mockNavigator(platform: string, userAgent: string) {
  Object.defineProperty(navigator, 'platform', {
    value: platform,
    writable: true,
    configurable: true,
  })
  Object.defineProperty(navigator, 'userAgent', {
    value: userAgent,
    writable: true,
    configurable: true,
  })
}

// Helper to mock WebGL for Apple Silicon detection
function mockWebGL(renderer: string | null) {
  const mockGetExtension = vi.fn().mockReturnValue(
    renderer
      ? { UNMASKED_RENDERER_WEBGL: 0x9246 }
      : null
  )
  const mockGetParameter = vi.fn().mockReturnValue(renderer)
  const mockGetContext = vi.fn().mockReturnValue(
    renderer !== undefined
      ? { getExtension: mockGetExtension, getParameter: mockGetParameter }
      : null
  )

  vi.spyOn(document, 'createElement').mockReturnValue({
    getContext: mockGetContext,
  } as unknown as HTMLCanvasElement)
}

// Cleanup mocks between tests
beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('detectPlatform', () => {
  describe('macOS detection', () => {
    it('should detect macOS Apple Silicon via WebGL renderer', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      mockWebGL('Apple M1')

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-arm64')
      expect(result.label).toBe('macOS (Apple Silicon)')
      expect(result.confidence).toBe('high')
    })

    it('should detect macOS Apple Silicon via Apple M2 renderer', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      mockWebGL('Apple M2 Pro')

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-arm64')
      expect(result.label).toBe('macOS (Apple Silicon)')
      expect(result.confidence).toBe('high')
    })

    it('should detect macOS Apple Silicon via Apple GPU renderer', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      mockWebGL('Apple GPU')

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-arm64')
      expect(result.confidence).toBe('high')
    })

    it('should detect macOS Apple Silicon via userAgent ARM hint', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; ARM Mac OS X)')
      mockWebGL(null) // WebGL fails but UA has ARM

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-arm64')
      expect(result.confidence).toBe('high')
    })

    it('should detect macOS Intel when WebGL shows non-Apple GPU', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      mockWebGL('AMD Radeon Pro 5500M')

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-amd64')
      expect(result.label).toBe('macOS (Intel)')
      expect(result.confidence).toBe('high')
    })

    it('should fall back to macOS Intel when WebGL is unavailable', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      // WebGL context returns null
      vi.spyOn(document, 'createElement').mockReturnValue({
        getContext: vi.fn().mockReturnValue(null),
      } as unknown as HTMLCanvasElement)

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-amd64')
      expect(result.label).toBe('macOS (Intel)')
      expect(result.confidence).toBe('high')
    })

    it('should fall back to macOS Intel when WebGL debug extension is unavailable', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      mockWebGL(null) // No debug extension

      const result = detectPlatform()
      expect(result.platform).toBe('darwin-amd64')
      expect(result.confidence).toBe('high')
    })
  })

  describe('Linux detection', () => {
    it('should detect Linux x86_64', () => {
      mockNavigator('Linux x86_64', 'Mozilla/5.0 (X11; Linux x86_64)')
      mockWebGL(null)

      const result = detectPlatform()
      expect(result.platform).toBe('linux-amd64')
      expect(result.label).toBe('Linux (x86_64)')
      expect(result.confidence).toBe('high')
    })

    it('should detect Linux ARM64 via userAgent', () => {
      mockNavigator('Linux aarch64', 'Mozilla/5.0 (X11; Linux aarch64)')
      mockWebGL(null)

      const result = detectPlatform()
      expect(result.platform).toBe('linux-arm64')
      expect(result.label).toBe('Linux (ARM64)')
      expect(result.confidence).toBe('high')
    })

    it('should detect Linux ARM64 via arm64 in userAgent', () => {
      mockNavigator('Linux arm64', 'Mozilla/5.0 (X11; Linux arm64)')
      mockWebGL(null)

      const result = detectPlatform()
      expect(result.platform).toBe('linux-arm64')
      expect(result.confidence).toBe('high')
    })
  })

  describe('Windows detection', () => {
    it('should detect Windows x86_64', () => {
      mockNavigator('Win32', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
      mockWebGL(null)

      const result = detectPlatform()
      expect(result.platform).toBe('windows-amd64')
      expect(result.label).toBe('Windows (x86_64)')
      expect(result.confidence).toBe('high')
    })
  })

  describe('fallback', () => {
    it('should fall back to linux-amd64 with low confidence for unknown platforms', () => {
      mockNavigator('FreeBSD', 'Mozilla/5.0 (FreeBSD)')
      mockWebGL(null)

      const result = detectPlatform()
      expect(result.platform).toBe('linux-amd64')
      expect(result.label).toBe('Linux (x86_64)')
      expect(result.confidence).toBe('low')
    })

    it('should fall back to linux-amd64 for empty platform string', () => {
      mockNavigator('', '')
      mockWebGL(null)

      const result = detectPlatform()
      expect(result.platform).toBe('linux-amd64')
      expect(result.confidence).toBe('low')
    })
  })

  describe('WebGL error handling', () => {
    it('should not throw when WebGL throws an error', () => {
      mockNavigator('MacIntel', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
      vi.spyOn(document, 'createElement').mockImplementation(() => {
        throw new Error('Canvas not supported')
      })

      // Should not throw — falls back to Intel
      const result = detectPlatform()
      expect(result.platform).toBe('darwin-amd64')
      expect(result.confidence).toBe('high')
    })
  })
})
