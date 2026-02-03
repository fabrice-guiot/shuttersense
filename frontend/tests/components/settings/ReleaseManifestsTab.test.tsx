/**
 * Tests for ReleaseManifestsTab component
 *
 * Part of Issue #90 - Distributed Agent Architecture (Phase 14)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { ReleaseManifestsTab } from '@/components/settings/ReleaseManifestsTab'
import * as releaseManifestsApi from '@/services/release-manifests-api'
import type {
  ReleaseManifest,
  ReleaseManifestListResponse,
  ReleaseManifestStatsResponse,
} from '@/contracts/api/release-manifests-api'

// Mock the service
vi.mock('@/services/release-manifests-api')

// Mock HeaderStatsContext
vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: () => ({
    setStats: vi.fn(),
  }),
}))

describe('ReleaseManifestsTab', () => {
  const mockManifests: ReleaseManifest[] = [
    {
      guid: 'rel_01hgw2bbg00000000000000001',
      version: '1.0.0',
      platforms: ['darwin-arm64', 'darwin-amd64'],
      checksum: 'a'.repeat(64),
      is_active: true,
      notes: 'Initial macOS universal binary',
      artifacts: [],
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
    },
    {
      guid: 'rel_01hgw2bbg00000000000000002',
      version: '1.1.0',
      platforms: ['linux-amd64'],
      checksum: 'b'.repeat(64),
      is_active: false,
      notes: null,
      artifacts: [],
      created_at: '2026-01-16T10:00:00Z',
      updated_at: '2026-01-16T10:00:00Z',
    },
  ]

  const mockListResponse: ReleaseManifestListResponse = {
    manifests: mockManifests,
    total_count: 2,
    active_count: 1,
  }

  const mockStats: ReleaseManifestStatsResponse = {
    total_count: 2,
    active_count: 1,
    platforms: ['darwin-arm64', 'darwin-amd64', 'linux-amd64'],
    versions: ['1.0.0', '1.1.0'],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(releaseManifestsApi.listManifests).mockResolvedValue(mockListResponse)
    vi.mocked(releaseManifestsApi.getManifestStats).mockResolvedValue(mockStats)
    vi.mocked(releaseManifestsApi.createManifest).mockImplementation(async (data): Promise<ReleaseManifest> => ({
      guid: 'rel_01hgw2bbg00000000000000003',
      version: data.version,
      platforms: data.platforms,
      checksum: data.checksum,
      notes: data.notes ?? null,
      is_active: data.is_active ?? true,
      artifacts: [],
      created_at: '2026-01-17T10:00:00Z',
      updated_at: '2026-01-17T10:00:00Z',
    }))
    vi.mocked(releaseManifestsApi.updateManifest).mockImplementation(async (guid, data) => {
      const existing = mockManifests.find(m => m.guid === guid)!
      return { ...existing, ...data }
    })
    vi.mocked(releaseManifestsApi.deleteManifest).mockResolvedValue(undefined)
  })

  describe('Table rendering', () => {
    it('renders page with New Manifest button', async () => {
      render(<ReleaseManifestsTab />)

      expect(screen.getByRole('button', { name: /New Manifest/i })).toBeInTheDocument()
    })

    it('shows loading state', async () => {
      render(<ReleaseManifestsTab />)

      expect(screen.getByText(/Loading release manifests/i)).toBeInTheDocument()
    })

    it('renders manifest list after loading', async () => {
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      expect(screen.getAllByText('1.1.0')[0]).toBeInTheDocument()
    })

    it('displays platform badges', async () => {
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('darwin-arm64')[0]).toBeInTheDocument()
      })

      expect(screen.getAllByText('darwin-amd64')[0]).toBeInTheDocument()
      expect(screen.getAllByText('linux-amd64')[0]).toBeInTheDocument()
    })

    it('displays status badges', async () => {
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('Active')[0]).toBeInTheDocument()
      })

      expect(screen.getAllByText('Inactive')[0]).toBeInTheDocument()
    })

    it('displays truncated checksums', async () => {
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        // Checksum is truncated: first 8 + ... + last 4
        expect(screen.getAllByText('aaaaaaaa...aaaa')[0]).toBeInTheDocument()
      })

      expect(screen.getAllByText('bbbbbbbb...bbbb')[0]).toBeInTheDocument()
    })

    it('displays notes for manifests', async () => {
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('Initial macOS universal binary')[0]).toBeInTheDocument()
      })
    })

    it('shows empty state when no manifests', async () => {
      vi.mocked(releaseManifestsApi.listManifests).mockResolvedValue({
        manifests: [],
        total_count: 0,
        active_count: 0,
      })

      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getByText(/No release manifests found/i)).toBeInTheDocument()
      })
    })

    it('displays error alert when fetch fails', async () => {
      vi.mocked(releaseManifestsApi.listManifests).mockRejectedValue(
        new Error('Network error')
      )

      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('Create manifest dialog', () => {
    it('opens create dialog when clicking New Manifest', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Manifest/i }))

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('Create Release Manifest')).toBeInTheDocument()
    })

    it('shows platform select dropdown in create dialog', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Manifest/i }))

      const dialog = screen.getByRole('dialog')

      // Should have a platform select dropdown
      expect(within(dialog).getByLabelText(/Platform/i)).toBeInTheDocument()
      expect(within(dialog).getByRole('combobox')).toBeInTheDocument()
    })

    it('validates that a platform is selected', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Manifest/i }))

      const dialog = screen.getByRole('dialog')

      // Fill version and checksum but no platform selected
      await user.type(within(dialog).getByLabelText(/Version/i), '2.0.0')
      await user.type(within(dialog).getByLabelText(/SHA-256 Checksum/i), 'c'.repeat(64))

      // Submit form
      await user.click(within(dialog).getByRole('button', { name: /Create Manifest/i }))

      // Should show validation error
      expect(within(dialog).getByText(/Please select a platform/i)).toBeInTheDocument()
    })

    it('validates checksum is 64 hex characters', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Manifest/i }))

      const dialog = screen.getByRole('dialog')

      // Fill form with short checksum
      await user.type(within(dialog).getByLabelText(/Version/i), '2.0.0')
      // Select platform from dropdown
      await user.click(within(dialog).getByRole('combobox'))
      await user.click(screen.getByRole('option', { name: /macOS \(Apple Silicon\)/i }))
      await user.type(within(dialog).getByLabelText(/SHA-256 Checksum/i), 'abc123')
      // Fill required filename
      await user.type(within(dialog).getByLabelText(/Binary Filename/i), 'shuttersense-agent-darwin-arm64')

      // Submit form
      await user.click(within(dialog).getByRole('button', { name: /Create Manifest/i }))

      // Should show validation error
      expect(within(dialog).getByText(/Checksum must be exactly 64 hexadecimal characters/i)).toBeInTheDocument()
    })

    it('creates manifest successfully', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Manifest/i }))

      const dialog = screen.getByRole('dialog')

      // Fill form
      await user.type(within(dialog).getByLabelText(/Version/i), '2.0.0')
      // Select platform from dropdown (single selection)
      await user.click(within(dialog).getByRole('combobox'))
      await user.click(screen.getByRole('option', { name: /macOS \(Apple Silicon\)/i }))
      await user.type(within(dialog).getByLabelText(/SHA-256 Checksum/i), 'c'.repeat(64))
      await user.type(within(dialog).getByLabelText(/Notes \(optional\)/i), 'ARM64 binary')
      // Fill required filename
      await user.type(within(dialog).getByLabelText(/Binary Filename/i), 'shuttersense-agent-darwin-arm64')

      // Submit form
      await user.click(within(dialog).getByRole('button', { name: /Create Manifest/i }))

      await waitFor(() => {
        expect(releaseManifestsApi.createManifest).toHaveBeenCalledWith({
          version: '2.0.0',
          platforms: ['darwin-arm64'],
          checksum: 'c'.repeat(64),
          is_active: true,
          notes: 'ARM64 binary',
          artifacts: [{
            platform: 'darwin-arm64',
            filename: 'shuttersense-agent-darwin-arm64',
            checksum: 'sha256:' + 'c'.repeat(64),
          }],
        })
      })
    })

    it('closes dialog when cancel is clicked', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Manifest/i }))
      expect(screen.getByRole('dialog')).toBeInTheDocument()

      await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Cancel/i }))

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })
    })
  })

  describe('Toggle active status', () => {
    it('toggles manifest active status', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row for active manifest and click deactivate button
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const deactivateButton = within(row).getByTitle('Deactivate')

      await user.click(deactivateButton)

      await waitFor(() => {
        expect(releaseManifestsApi.updateManifest).toHaveBeenCalledWith(
          'rel_01hgw2bbg00000000000000001',
          { is_active: false }
        )
      })
    })
  })

  describe('Edit notes dialog', () => {
    it('opens edit dialog with current notes', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row and click edit button
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const editButton = within(row).getByTitle('Edit notes')

      await user.click(editButton)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toBeInTheDocument()
      expect(screen.getByText('Edit Notes')).toBeInTheDocument()

      // Should have current notes value - find within dialog
      const textarea = within(dialog).getByLabelText(/Notes/i)
      expect(textarea).toHaveValue('Initial macOS universal binary')
    })

    it('updates notes successfully', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row and click edit button
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const editButton = within(row).getByTitle('Edit notes')

      await user.click(editButton)

      // Find dialog and interact with its elements
      const dialog = screen.getByRole('dialog')

      // Clear and type new notes - find within dialog
      const textarea = within(dialog).getByLabelText(/Notes/i)
      await user.clear(textarea)
      await user.type(textarea, 'Updated notes')

      // Submit
      await user.click(within(dialog).getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(releaseManifestsApi.updateManifest).toHaveBeenCalledWith(
          'rel_01hgw2bbg00000000000000001',
          { notes: 'Updated notes' }
        )
      })
    })
  })

  describe('Delete dialog', () => {
    it('opens delete confirmation dialog', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row and click delete button
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const deleteButton = within(row).getByTitle('Delete')

      await user.click(deleteButton)

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
      expect(screen.getByText('Delete Release Manifest?')).toBeInTheDocument()
      expect(screen.getByText(/v1.0.0/i)).toBeInTheDocument()
    })

    it('deletes manifest when confirmed', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row and click delete button
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const deleteButton = within(row).getByTitle('Delete')

      await user.click(deleteButton)

      // Confirm delete - find button within alertdialog
      const alertDialog = screen.getByRole('alertdialog')
      await user.click(within(alertDialog).getByRole('button', { name: /^Delete$/ }))

      await waitFor(() => {
        expect(releaseManifestsApi.deleteManifest).toHaveBeenCalledWith(
          'rel_01hgw2bbg00000000000000001'
        )
      })
    })

    it('cancels delete when cancel is clicked', async () => {
      const user = userEvent.setup()
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row and click delete button
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const deleteButton = within(row).getByTitle('Delete')

      await user.click(deleteButton)

      // Cancel delete
      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      await waitFor(() => {
        expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
      })

      expect(releaseManifestsApi.deleteManifest).not.toHaveBeenCalled()
    })
  })

  describe('Copy checksum', () => {
    it('renders copy button for checksum', async () => {
      render(<ReleaseManifestsTab />)

      await waitFor(() => {
        expect(screen.getAllByText('1.0.0')[0]).toBeInTheDocument()
      })

      // Find the row and verify copy button exists
      const row = screen.getAllByText('1.0.0')[0].closest('tr')!
      const copyButton = within(row).getByTitle('Copy full checksum')

      expect(copyButton).toBeInTheDocument()
    })
  })
})
