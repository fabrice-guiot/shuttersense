/**
 * Tests for TokenStep component (Step 2: Registration Token Creation)
 *
 * Issue #136 - Agent Setup Wizard (FR-010 through FR-013)
 * Task: T053
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../../utils/test-utils'
import { TokenStep } from '@/components/agents/wizard/TokenStep'
import type { RegistrationToken } from '@/contracts/api/agent-api'

const mockToken: RegistrationToken = {
  guid: 'art_01hgw2bbg00000000000000001',
  token: 'art_secret_token_value_12345',
  name: 'Test Agent Token',
  expires_at: '2026-02-03T12:00:00Z',
  is_valid: true,
  created_at: '2026-02-02T12:00:00Z',
  created_by_email: 'admin@example.com',
}

describe('TokenStep', () => {
  const mockOnTokenCreated = vi.fn()
  const mockCreateToken = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockCreateToken.mockResolvedValue(mockToken)
  })

  describe('initial form state (no token created)', () => {
    it('renders the creation form when no token exists', () => {
      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      expect(screen.getByText(/Create a one-time registration token/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Token Name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Expiration/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Create Registration Token/i })).toBeInTheDocument()
    })

    it('has default expiration of 24 hours', () => {
      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      const expiryInput = screen.getByLabelText(/Expiration/i)
      expect(expiryInput).toHaveValue(24)
    })

    it('creates token with default values when no name entered', async () => {
      const user = userEvent.setup()

      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(mockCreateToken).toHaveBeenCalledWith({
          name: undefined,
          expires_in_hours: 24,
        })
      })

      expect(mockOnTokenCreated).toHaveBeenCalledWith(mockToken)
    })

    it('creates token with custom name', async () => {
      const user = userEvent.setup()

      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      await user.type(screen.getByLabelText(/Token Name/i), 'My Agent')
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(mockCreateToken).toHaveBeenCalled()
        const callArg = mockCreateToken.mock.calls[0][0]
        expect(callArg.name).toBe('My Agent')
      })
    })

    it('shows error when token creation fails', async () => {
      const user = userEvent.setup()
      mockCreateToken.mockRejectedValue({ userMessage: 'Rate limit exceeded' })

      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(screen.getByText('Rate limit exceeded')).toBeInTheDocument()
      })

      // Should NOT call onTokenCreated
      expect(mockOnTokenCreated).not.toHaveBeenCalled()
    })

    it('shows generic error when creation fails without userMessage', async () => {
      const user = userEvent.setup()
      mockCreateToken.mockRejectedValue(new Error('Network error'))

      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to create registration token')).toBeInTheDocument()
      })
    })

    it('disables form while creating', async () => {
      const user = userEvent.setup()
      // Make createToken never resolve
      mockCreateToken.mockReturnValue(new Promise(() => {}))

      render(
        <TokenStep
          createdToken={null}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/Token Name/i)).toBeDisabled()
        expect(screen.getByLabelText(/Expiration/i)).toBeDisabled()
      })
    })
  })

  describe('token display (token already created)', () => {
    it('shows read-only token display when token exists', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      expect(screen.getByText(/Registration token created/i)).toBeInTheDocument()
      expect(screen.getByText(mockToken.token)).toBeInTheDocument()
    })

    it('shows token name when available', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      expect(screen.getByText(/Test Agent Token/)).toBeInTheDocument()
    })

    it('shows "shown once" warning on first view', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
          isRevisit={false}
        />
      )

      expect(screen.getByText(/only be shown once/i)).toBeInTheDocument()
    })

    it('shows "previously created" message on revisit (FR-012)', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
          isRevisit={true}
        />
      )

      expect(screen.getByText(/previously created in this session/i)).toBeInTheDocument()
      // Should NOT show the "only shown once" amber warning
      expect(screen.queryByText(/only be shown once/i)).not.toBeInTheDocument()
    })

    it('shows expiry date', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      expect(screen.getByText(/Expires:/i)).toBeInTheDocument()
    })

    it('does not show the creation form when token exists', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      expect(screen.queryByRole('button', { name: /Create Registration Token/i })).not.toBeInTheDocument()
    })

    it('has a copy button for the token', () => {
      render(
        <TokenStep
          createdToken={mockToken}
          onTokenCreated={mockOnTokenCreated}
          createToken={mockCreateToken}
        />
      )

      // CopyableCodeBlock provides a copy button via aria-label
      expect(screen.getByLabelText(/Copy registration token/i)).toBeInTheDocument()
    })
  })
})
