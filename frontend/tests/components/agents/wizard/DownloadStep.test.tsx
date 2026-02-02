/**
 * Tests for DownloadStep component (Step 1: OS Detection & Binary Download)
 *
 * Issue #136 - Agent Setup Wizard (FR-004 through FR-009, FR-033 through FR-036, FR-039)
 * Task: T052
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '../../../utils/test-utils'
import { DownloadStep } from '@/components/agents/wizard/DownloadStep'
import type { ActiveReleaseResponse } from '@/contracts/api/agent-api'

// Mock the agents service
vi.mock('@/services/agents', () => ({
  getActiveRelease: vi.fn(),
}))

// Mock useClipboard
vi.mock('@/hooks/useClipboard', () => ({
  useClipboard: () => ({
    copy: vi.fn(),
    copied: false,
    error: null,
  }),
}))

import { getActiveRelease } from '@/services/agents'
const mockGetActiveRelease = vi.mocked(getActiveRelease)

const mockRelease: ActiveReleaseResponse = {
  guid: 'rel_01hgw2bbg00000000000000001',
  version: '1.2.3',
  artifacts: [
    {
      platform: 'darwin-arm64',
      filename: 'shuttersense-agent-darwin-arm64',
      checksum: 'sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
      file_size: 15728640,
      download_url: '/api/agent/v1/releases/rel_01hgw2bbg00000000000000001/download/darwin-arm64',
      signed_url: '/api/agent/v1/releases/rel_01hgw2bbg00000000000000001/download/darwin-arm64?expires=9999999999&signature=abc123',
    },
    {
      platform: 'linux-amd64',
      filename: 'shuttersense-agent-linux-amd64',
      checksum: 'sha256:fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321',
      file_size: 14680064,
      download_url: '/api/agent/v1/releases/rel_01hgw2bbg00000000000000001/download/linux-amd64',
      signed_url: null,
    },
  ],
  notes: 'Test release',
  dev_mode: false,
}

const mockDevRelease: ActiveReleaseResponse = {
  guid: 'rel_01hgw2bbg00000000000000002',
  version: '0.0.1-dev',
  artifacts: [],
  notes: null,
  dev_mode: true,
}

describe('DownloadStep', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetActiveRelease.mockResolvedValue(mockRelease)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('platform display (FR-004)', () => {
    it('shows the detected platform', async () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      // "macOS (Apple Silicon)" appears in both detected label and dropdown, so use getAllByText
      const matches = screen.getAllByText(/macOS \(Apple Silicon\)/)
      expect(matches.length).toBeGreaterThanOrEqual(1)
    })

    it('shows low confidence warning', () => {
      render(
        <DownloadStep
          detectedPlatform="linux-amd64"
          selectedPlatform="linux-amd64"
          onPlatformChange={vi.fn()}
          platformConfidence="low"
        />
      )

      expect(screen.getByText(/low confidence/i)).toBeInTheDocument()
    })

    it('has a target platform dropdown', () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      expect(screen.getByText('Target Platform')).toBeInTheDocument()
      // The select trigger button should be present
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })
  })

  describe('platform override warning (FR-006)', () => {
    it('shows warning when selected platform differs from detected', () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="linux-amd64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      expect(screen.getByText(/different platform than detected/i)).toBeInTheDocument()
    })

    it('does not show warning when platforms match', () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      expect(screen.queryByText(/different platform than detected/i)).not.toBeInTheDocument()
    })
  })

  describe('release loading and error', () => {
    it('shows loading state while fetching release', () => {
      mockGetActiveRelease.mockReturnValue(new Promise(() => {}))

      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      expect(screen.getByText(/Loading release information/i)).toBeInTheDocument()
    })

    it('shows error when no release is available (FR-008)', async () => {
      mockGetActiveRelease.mockRejectedValue(new Error('Not found'))

      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/No release available/i)).toBeInTheDocument()
      })
    })
  })

  describe('download button (FR-007, FR-009)', () => {
    it('shows download button with filename and size when artifact available', async () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Download shuttersense-agent-darwin-arm64/i)).toBeInTheDocument()
      })

      // File size should be shown
      expect(screen.getByText(/15\.0 MB/)).toBeInTheDocument()
    })

    it('shows version number', async () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText('1.2.3')).toBeInTheDocument()
      })
    })

    it('shows checksum for the artifact', async () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Checksum:/)).toBeInTheDocument()
      })
    })

    it('shows no-artifact message when platform has no artifact', async () => {
      // In test env, import.meta.env.DEV is true, so dev mode is active.
      // Dev mode shows "not available in this environment" for missing artifacts.
      render(
        <DownloadStep
          detectedPlatform="windows-amd64"
          selectedPlatform="windows-amd64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/not available in this environment/i)).toBeInTheDocument()
      })
    })
  })

  describe('signed URL section (FR-009)', () => {
    it('shows signed URL section with curl command for artifact with signed URL', async () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Remote Download Link/i)).toBeInTheDocument()
      })

      // Should show curl command
      expect(screen.getByText(/curl/)).toBeInTheDocument()
    })

    it('does not show signed URL section when signed_url is null', async () => {
      render(
        <DownloadStep
          detectedPlatform="linux-amd64"
          selectedPlatform="linux-amd64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Download shuttersense-agent-linux-amd64/i)).toBeInTheDocument()
      })

      expect(screen.queryByText(/Remote Download Link/i)).not.toBeInTheDocument()
    })

    it('shows remote-specific message when platform is overridden', async () => {
      render(
        <DownloadStep
          detectedPlatform="linux-amd64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/setting up a remote machine/i)).toBeInTheDocument()
      })
    })

    it('has a Copy Link button', async () => {
      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByLabelText(/Copy signed download link/i)).toBeInTheDocument()
      })
    })
  })

  describe('dev/QA mode (FR-033, FR-034)', () => {
    it('shows dev mode banner in dev mode', async () => {
      mockGetActiveRelease.mockResolvedValue(mockDevRelease)

      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Development\/QA mode/i)).toBeInTheDocument()
      })
    })

    it('shows disabled download button in dev mode with no artifact', async () => {
      mockGetActiveRelease.mockResolvedValue(mockDevRelease)

      render(
        <DownloadStep
          detectedPlatform="darwin-arm64"
          selectedPlatform="darwin-arm64"
          onPlatformChange={vi.fn()}
          platformConfidence="high"
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/not available in this environment/i)).toBeInTheDocument()
      })
    })
  })
})
