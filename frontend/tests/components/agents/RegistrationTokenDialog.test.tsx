/**
 * Tests for RegistrationTokenDialog component
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T045
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { RegistrationTokenDialog } from '@/components/agents/RegistrationTokenDialog'
import type { RegistrationToken } from '@/contracts/api/agent-api'

describe('RegistrationTokenDialog', () => {
  const mockOnOpenChange = vi.fn()
  const mockOnCreateToken = vi.fn()

  const mockToken: RegistrationToken = {
    guid: 'art_01hgw2bbg00000000000000001',
    token: 'art_secret_token_value_12345',
    name: 'Test Token',
    expires_at: '2026-01-20T12:00:00Z',
    is_valid: true,
    created_at: '2026-01-18T12:00:00Z',
    created_by_email: 'admin@example.com',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockOnCreateToken.mockResolvedValue(mockToken)
  })

  it('renders form step initially', () => {
    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    expect(screen.getByText('Create Registration Token')).toBeInTheDocument()
    expect(screen.getByLabelText(/Token Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Expires In/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Create Token/i })).toBeInTheDocument()
  })

  it('shows cancel button that closes dialog', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    await user.click(cancelButton)

    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('creates token with default values', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    await waitFor(() => {
      expect(mockOnCreateToken).toHaveBeenCalledWith({
        name: undefined,
        expires_in_hours: 24,
      })
    })
  })

  it('creates token with custom name', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    // Fill in token name
    const nameInput = screen.getByLabelText(/Token Name/i)
    await user.type(nameInput, 'Studio Mac Token')

    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    await waitFor(() => {
      expect(mockOnCreateToken).toHaveBeenCalled()
      const callArg = mockOnCreateToken.mock.calls[0][0]
      expect(callArg.name).toBe('Studio Mac Token')
    })
  })

  it('shows token step after successful creation', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    // Should show token created step
    await waitFor(() => {
      expect(screen.getByText('Token Created')).toBeInTheDocument()
    })

    // Should display the token value
    expect(screen.getByDisplayValue(mockToken.token)).toBeInTheDocument()

    // Should show warning about single display
    expect(screen.getByText(/only be shown once/i)).toBeInTheDocument()
  })

  it('has copy button in token step', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    // Create token first
    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    // Wait for token step
    await waitFor(() => {
      expect(screen.getByText('Token Created')).toBeInTheDocument()
    })

    // Verify copy button exists
    const copyButton = screen.getByTitle(/Copy to clipboard/i)
    expect(copyButton).toBeInTheDocument()
  })

  it('shows error message when token creation fails', async () => {
    const user = userEvent.setup()
    mockOnCreateToken.mockRejectedValue({ userMessage: 'Token creation failed' })

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('Token creation failed')).toBeInTheDocument()
    })

    // Should stay on form step
    expect(screen.getByText('Create Registration Token')).toBeInTheDocument()
  })

  it('closes dialog and resets state after Done is clicked', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    // Create token
    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    // Wait for token step
    await waitFor(() => {
      expect(screen.getByText('Token Created')).toBeInTheDocument()
    })

    // Click Done
    const doneButton = screen.getByRole('button', { name: /Done/i })
    await user.click(doneButton)

    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('displays next steps instructions', async () => {
    const user = userEvent.setup()

    render(
      <RegistrationTokenDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onCreateToken={mockOnCreateToken}
      />
    )

    // Create token
    const createButton = screen.getByRole('button', { name: /Create Token/i })
    await user.click(createButton)

    // Wait for token step
    await waitFor(() => {
      expect(screen.getByText('Token Created')).toBeInTheDocument()
    })

    // Should show next steps
    expect(screen.getByText('Next steps:')).toBeInTheDocument()
    expect(screen.getByText(/shuttersense-agent register/i)).toBeInTheDocument()
  })
})
