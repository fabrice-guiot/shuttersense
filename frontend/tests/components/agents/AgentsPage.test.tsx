/**
 * Tests for AgentsPage component
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T044
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import AgentsPage from '@/pages/AgentsPage'
import * as agentService from '@/services/agents'
import type { Agent, RegistrationToken } from '@/contracts/api/agent-api'

// Mock the service
vi.mock('@/services/agents')

// Mock HeaderStatsContext
vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: () => ({
    setStats: vi.fn(),
  }),
}))

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('AgentsPage', () => {
  const mockAgents: Agent[] = [
    {
      guid: 'agt_01hgw2bbg00000000000000001',
      name: 'Studio Mac',
      hostname: 'studio-mac.local',
      os_info: 'macOS 14.0',
      status: 'online',
      error_message: null,
      last_heartbeat: '2026-01-18T12:00:00Z',
      capabilities: ['local_filesystem', 'tool:photostats:1.0.0'],
      authorized_roots: ['/Users/photographer/Photos', '/Volumes/External'],
      version: '1.0.0',
      is_outdated: false,
      platform: 'darwin-arm64',
      created_at: '2026-01-15T10:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: null,
      running_jobs_count: 0,
    },
    {
      guid: 'agt_01hgw2bbg00000000000000002',
      name: 'Home Server',
      hostname: 'home-server.local',
      os_info: 'Ubuntu 22.04',
      status: 'offline',
      error_message: null,
      last_heartbeat: '2026-01-17T10:00:00Z',
      capabilities: ['local_filesystem'],
      authorized_roots: ['/home/photos'],
      version: '1.0.0',
      is_outdated: false,
      platform: 'linux-amd64',
      created_at: '2026-01-10T08:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: null,
      running_jobs_count: 0,
    },
  ]

  const mockToken: RegistrationToken = {
    guid: 'art_01hgw2bbg00000000000000001',
    token: 'art_secret_token_value',
    name: 'Test Token',
    expires_at: '2026-01-20T12:00:00Z',
    is_valid: true,
    created_at: '2026-01-18T12:00:00Z',
    created_by_email: 'admin@example.com',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.listAgents).mockResolvedValue(mockAgents)
    vi.mocked(agentService.getAgentStats).mockResolvedValue({
      total_agents: 2,
      online_agents: 1,
      offline_agents: 1,
    })
    vi.mocked(agentService.listRegistrationTokens).mockResolvedValue([])
    vi.mocked(agentService.createRegistrationToken).mockResolvedValue(mockToken)
    vi.mocked(agentService.updateAgent).mockImplementation(async (guid, data) => ({
      ...mockAgents.find(a => a.guid === guid)!,
      ...data,
    }))
    vi.mocked(agentService.revokeAgent).mockResolvedValue(undefined)
  })

  it('renders page with action buttons', async () => {
    render(<AgentsPage />)

    // Should show refresh and new token buttons
    expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /New Registration Token/i })).toBeInTheDocument()

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })
  })

  it('renders agent list after loading', async () => {
    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    expect(screen.getAllByText('Home Server')[0]).toBeInTheDocument()
  })

  it('displays agent status badges', async () => {
    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    expect(screen.getAllByText('Online')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Offline')[0]).toBeInTheDocument()
  })

  it('displays agent hostname and OS info', async () => {
    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('studio-mac.local')[0]).toBeInTheDocument()
    })

    expect(screen.getAllByText('macOS 14.0')[0]).toBeInTheDocument()
    expect(screen.getAllByText('home-server.local')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Ubuntu 22.04')[0]).toBeInTheDocument()
  })

  it('displays agent version', async () => {
    render(<AgentsPage />)

    await waitFor(() => {
      // 2 agents × 2 views (desktop table + mobile cards) = 4
      expect(screen.getAllByText('1.0.0')).toHaveLength(4)
    })
  })

  it('shows empty state when no agents', async () => {
    vi.mocked(agentService.listAgents).mockResolvedValue([])

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getByText('No agents registered yet.')).toBeInTheDocument()
    })
  })

  it('opens registration token dialog', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    const newTokenButton = screen.getByRole('button', { name: /New Registration Token/i })
    await user.click(newTokenButton)

    expect(screen.getByText('Create Registration Token')).toBeInTheDocument()
  })

  it('opens rename dialog when rename is clicked', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    // Find the first action menu
    const actionButtons = screen.getAllByRole('button', { name: /Actions/i })
    await user.click(actionButtons[0])

    // Click Rename
    const renameOption = screen.getByRole('menuitem', { name: /Rename/i })
    await user.click(renameOption)

    expect(screen.getByText('Rename Agent')).toBeInTheDocument()
  })

  it('renames agent successfully', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    // Open action menu and click rename
    const actionButtons = screen.getAllByRole('button', { name: /Actions/i })
    await user.click(actionButtons[0])
    const renameOption = screen.getByRole('menuitem', { name: /Rename/i })
    await user.click(renameOption)

    // Update name
    const nameInput = screen.getByLabelText('Name')
    await user.clear(nameInput)
    await user.type(nameInput, 'Updated Studio Mac')

    // Save
    const saveButton = screen.getByRole('button', { name: /Save/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(agentService.updateAgent).toHaveBeenCalledWith(
        'agt_01hgw2bbg00000000000000001',
        { name: 'Updated Studio Mac' }
      )
    })
  })

  it('opens revoke confirmation dialog', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    // Open action menu and click revoke
    const actionButtons = screen.getAllByRole('button', { name: /Actions/i })
    await user.click(actionButtons[0])
    const revokeOption = screen.getByRole('menuitem', { name: /Revoke/i })
    await user.click(revokeOption)

    expect(screen.getByText('Revoke Agent')).toBeInTheDocument()
    expect(screen.getByText(/Are you sure you want to revoke "Studio Mac"/i)).toBeInTheDocument()
  })

  it('revokes agent when confirmed', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    // Open action menu and click revoke
    const actionButtons = screen.getAllByRole('button', { name: /Actions/i })
    await user.click(actionButtons[0])
    const revokeOption = screen.getByRole('menuitem', { name: /Revoke/i })
    await user.click(revokeOption)

    // Confirm revoke
    const dialog = screen.getByRole('alertdialog')
    const confirmButton = within(dialog).getByRole('button', { name: /Revoke/i })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(agentService.revokeAgent).toHaveBeenCalledWith('agt_01hgw2bbg00000000000000001', undefined)
    })
  })

  it('cancels revoke when cancel is clicked', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    // Open action menu and click revoke
    const actionButtons = screen.getAllByRole('button', { name: /Actions/i })
    await user.click(actionButtons[0])
    const revokeOption = screen.getByRole('menuitem', { name: /Revoke/i })
    await user.click(revokeOption)

    // Cancel
    const dialog = screen.getByRole('alertdialog')
    const cancelButton = within(dialog).getByRole('button', { name: /Cancel/i })
    await user.click(cancelButton)

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })

    expect(agentService.revokeAgent).not.toHaveBeenCalled()
  })

  it('refreshes agent list when refresh is clicked', async () => {
    const user = userEvent.setup()

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Studio Mac')[0]).toBeInTheDocument()
    })

    // Clear mock calls from initial load
    vi.mocked(agentService.listAgents).mockClear()

    const refreshButton = screen.getByRole('button', { name: /Refresh/i })
    await user.click(refreshButton)

    await waitFor(() => {
      expect(agentService.listAgents).toHaveBeenCalled()
    })
  })

  it('displays error when agent has error status', async () => {
    const errorAgent: Agent = {
      ...mockAgents[0],
      status: 'error',
      error_message: 'Connection timeout',
      authorized_roots: [],
    }
    vi.mocked(agentService.listAgents).mockResolvedValue([errorAgent])

    render(<AgentsPage />)

    await waitFor(() => {
      expect(screen.getAllByText('Error')[0]).toBeInTheDocument()
    })

    expect(screen.getAllByText('Connection timeout')[0]).toBeInTheDocument()
  })
})
