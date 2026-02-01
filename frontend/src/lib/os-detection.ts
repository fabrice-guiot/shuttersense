/**
 * OS Detection utility for the Agent Setup Wizard.
 *
 * Detects the user's operating system and architecture using browser APIs.
 * Uses WebGL renderer string as a heuristic for Apple Silicon detection.
 *
 * Issue #136 - Agent Setup Wizard
 */

import type { ValidPlatform } from '@/contracts/api/release-manifests-api'
import { PLATFORM_LABELS } from '@/contracts/api/release-manifests-api'

export interface DetectedOS {
  /** Platform identifier matching ValidPlatform */
  platform: ValidPlatform
  /** Human-friendly label (e.g., "macOS (Apple Silicon)") */
  label: string
  /** Detection confidence — 'low' when falling back to defaults */
  confidence: 'high' | 'low'
}

/**
 * Attempt Apple Silicon detection via WebGL renderer string.
 * Returns true if the GPU is a known Apple Silicon GPU, false otherwise.
 * This is a best-effort heuristic — the user can always override manually.
 */
function checkAppleSilicon(): boolean {
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    if (!gl) return false
    const debugExt = (gl as WebGLRenderingContext).getExtension('WEBGL_debug_renderer_info')
    if (!debugExt) return false
    const renderer = (gl as WebGLRenderingContext).getParameter(debugExt.UNMASKED_RENDERER_WEBGL)
    // Apple Silicon GPUs report "Apple M1", "Apple M2", "Apple GPU", etc.
    return /Apple (M\d|GPU)/i.test(renderer)
  } catch {
    return false
  }
}

/**
 * Detect the current platform from browser APIs.
 *
 * Detection strategy:
 * 1. Check navigator.platform for OS family (Mac, Linux, Win)
 * 2. For macOS, probe WebGL renderer for Apple Silicon
 * 3. For Linux, check userAgent for ARM hints
 * 4. Falls back to linux-amd64 with low confidence
 */
export function detectPlatform(): DetectedOS {
  const ua = navigator.userAgent
  const platform = navigator.platform

  if (/Mac/.test(platform)) {
    const isArm = /ARM|aarch64|arm64/i.test(ua) || checkAppleSilicon()
    const detected: ValidPlatform = isArm ? 'darwin-arm64' : 'darwin-amd64'
    return {
      platform: detected,
      label: PLATFORM_LABELS[detected],
      confidence: 'high',
    }
  }

  if (/Linux/.test(platform)) {
    const isArm = /aarch64|arm64/i.test(ua)
    const detected: ValidPlatform = isArm ? 'linux-arm64' : 'linux-amd64'
    return {
      platform: detected,
      label: PLATFORM_LABELS[detected],
      confidence: 'high',
    }
  }

  if (/Win/.test(platform)) {
    return {
      platform: 'windows-amd64',
      label: PLATFORM_LABELS['windows-amd64'],
      confidence: 'high',
    }
  }

  // Fallback — unknown platform defaults to Linux x86_64
  return {
    platform: 'linux-amd64',
    label: PLATFORM_LABELS['linux-amd64'],
    confidence: 'low',
  }
}
