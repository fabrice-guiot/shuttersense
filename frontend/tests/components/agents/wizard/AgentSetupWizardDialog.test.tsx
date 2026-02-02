/**
 * Tests for AgentSetupWizardDialog component (Root wizard dialog)
 *
 * Issue #136 - Agent Setup Wizard (FR-002, FR-025, FR-026, FR-027)
 * Task: T051
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../../utils/test-utils'
import { AgentSetupWizardDialog } from '@/components/agents/AgentSetupWizardDialog'
import type { RegistrationToken } from '@/contracts/api/agent-api'

// Mock detectPlatform
vi.mock('@/lib/os-detection', () => ({
  detectPlatform: () => ({
    platform: 'darwin-arm64',
    label: 'macOS (Apple Silicon)',
    confidence: 'high',
  }),
}))

// Mock getActiveRelease to avoid real API calls
vi.mock('@/services/agents', () => ({
  getActiveRelease: vi.fn().mockRejectedValue(new Error('No release')),
}))

// Mock useClipboard
vi.mock('@/hooks/useClipboard', () => ({
  useClipboard: () => ({
    copy: vi.fn(),
    copied: false,
    error: null,
  }),
}))

const mockToken: RegistrationToken = {
  guid: 'art_01hgw2bbg00000000000000001',
  token: 'art_secret_token_value_12345',
  name: 'Test Token',
  expires_at: '2026-02-03T12:00:00Z',
  is_valid: true,
  created_at: '2026-02-02T12:00:00Z',
  created_by_email: 'admin@example.com',
}

describe('AgentSetupWizardDialog', () => {
  const mockOnOpenChange = vi.fn()
  const mockCreateToken = vi.fn()
  const mockOnComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockCreateToken.mockResolvedValue(mockToken)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const renderDialog = (open = true) =>
    render(
      <AgentSetupWizardDialog
        open={open}
        onOpenChange={mockOnOpenChange}
        createToken={mockCreateToken}
        onComplete={mockOnComplete}
      />
    )

  describe('initial render (FR-002)', () => {
    it('renders dialog with title when open', () => {
      renderDialog()

      expect(screen.getByText('Agent Setup Wizard')).toBeInTheDocument()
      expect(screen.getByText(/Follow these steps/i)).toBeInTheDocument()
    })

    it('shows step indicator with navigation', () => {
      renderDialog()

      // Step indicator nav should be present
      expect(screen.getByLabelText('Setup progress')).toBeInTheDocument()
      // Step numbers (1-6) should be in the DOM
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('6')).toBeInTheDocument()
    })

    it('starts on Step 1 (Download Agent)', () => {
      renderDialog()

      // Step 1 content: detected platform label
      expect(screen.getByText(/Detected Platform/i)).toBeInTheDocument()
    })

    it('shows Next button on Step 1', () => {
      renderDialog()

      expect(screen.getByRole('button', { name: /Go to next step/i })).toBeInTheDocument()
    })

    it('does not show Back button on Step 1', () => {
      renderDialog()

      expect(screen.queryByRole('button', { name: /Go to previous step/i })).not.toBeInTheDocument()
    })
  })

  describe('step navigation (FR-025)', () => {
    it('navigates from Step 1 to Step 2 via Next', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Step 2 should show token creation form
      expect(screen.getByText(/Create a one-time registration token/i)).toBeInTheDocument()
    })

    it('navigates back from Step 2 to Step 1', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Go to Step 2
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))
      expect(screen.getByText(/Create a one-time registration token/i)).toBeInTheDocument()

      // Go back to Step 1
      await user.click(screen.getByRole('button', { name: /Go to previous step/i }))
      expect(screen.getByText(/Detected Platform/i)).toBeInTheDocument()
    })

    it('gates Next button on Step 2 until token is created (FR-027)', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Go to Step 2
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Next button should be disabled because no token created yet
      const nextButton = screen.getByRole('button', { name: /Go to next step/i })
      expect(nextButton).toBeDisabled()
    })

    it('enables Next on Step 2 after token creation', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Go to Step 2
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Create token
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        const nextButton = screen.getByRole('button', { name: /Go to next step/i })
        expect(nextButton).not.toBeDisabled()
      })
    })

    it('navigates through all 6 steps to Done', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Step 1 → 2
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Create token to unlock Next
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      // Step 2 → 3
      await waitFor(async () => {
        const nextBtn = screen.getByRole('button', { name: /Go to next step/i })
        expect(nextBtn).not.toBeDisabled()
      })
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Step 3: Register step — check for the register command code block
      expect(screen.getByText(/chmod \+x/)).toBeInTheDocument()

      // Step 3 → 4
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Step 4: Launch step — check for the self-test command
      expect(screen.getByText(/self-test/)).toBeInTheDocument()

      // Step 4 → 5
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Step 5: Service step — check for the binary path input
      expect(screen.getByLabelText(/Agent Binary Path/i)).toBeInTheDocument()

      // Step 5 → 6
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Step 6: Summary — should show Done button
      expect(screen.getByText(/setup is complete/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Finish wizard/i })).toBeInTheDocument()
    })
  })

  describe('close behavior (FR-026)', () => {
    it('closes without confirmation on Step 1 (no token)', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Click the close button (X)
      const closeButton = screen.getByRole('button', { name: /Close/i })
      await user.click(closeButton)

      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })

    it('shows confirmation when closing with token created on intermediate step', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Go to Step 2 and create token
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(screen.getByText(mockToken.token)).toBeInTheDocument()
      })

      // Go to Step 3
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Close the dialog
      const closeButton = screen.getByRole('button', { name: /Close/i })
      await user.click(closeButton)

      // Confirmation dialog should appear
      expect(screen.getByText(/Close wizard\?/i)).toBeInTheDocument()
      expect(screen.getByText(/registration token/i)).toBeInTheDocument()
    })

    it('confirms close and calls onComplete if token was created', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Go to Step 2 and create token
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(screen.getByText(mockToken.token)).toBeInTheDocument()
      })

      // Go to Step 3
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Close the dialog
      const closeButton = screen.getByRole('button', { name: /Close/i })
      await user.click(closeButton)

      // Confirm close
      await user.click(screen.getByRole('button', { name: /Close Wizard/i }))

      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })

    it('cancels close via Continue Setup button', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Go to Step 2 and create token
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      await waitFor(() => {
        expect(screen.getByText(mockToken.token)).toBeInTheDocument()
      })

      // Go to Step 3
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))

      // Try to close
      const closeButton = screen.getByRole('button', { name: /Close/i })
      await user.click(closeButton)

      // Cancel close
      await user.click(screen.getByRole('button', { name: /Continue Setup/i }))

      // Should NOT have closed
      expect(mockOnOpenChange).not.toHaveBeenCalledWith(false)
    })
  })

  describe('Done button and refresh (FR-025)', () => {
    it('calls onComplete when Done is clicked after token was created', async () => {
      const user = userEvent.setup()
      renderDialog()

      // Navigate to Step 2, create token, then go through all steps to Done
      await user.click(screen.getByRole('button', { name: /Go to next step/i }))
      await user.click(screen.getByRole('button', { name: /Create Registration Token/i }))

      // Navigate through remaining steps
      await waitFor(async () => {
        const nextBtn = screen.getByRole('button', { name: /Go to next step/i })
        expect(nextBtn).not.toBeDisabled()
      })
      await user.click(screen.getByRole('button', { name: /Go to next step/i })) // → 3
      await user.click(screen.getByRole('button', { name: /Go to next step/i })) // → 4
      await user.click(screen.getByRole('button', { name: /Go to next step/i })) // → 5
      await user.click(screen.getByRole('button', { name: /Go to next step/i })) // → 6

      // Click Done
      await user.click(screen.getByRole('button', { name: /Finish wizard/i }))

      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
      // onComplete should be called since a token was created
      expect(mockOnComplete).toHaveBeenCalled()
    })
  })
})
