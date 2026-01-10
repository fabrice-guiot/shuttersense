import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import ConnectorForm from '@/components/connectors/ConnectorForm'
import type { Connector } from '@/contracts/api/connector-api'
import type { ConnectorFormData } from '@/types/schemas/connector'

describe('ConnectorForm', () => {
  const mockOnSubmit = vi.fn<(data: ConnectorFormData) => Promise<void>>()
  const mockOnCancel = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should render the form with required fields', () => {
    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Create/i })).toBeInTheDocument()
    expect(screen.getByText(/Cancel/i)).toBeInTheDocument()
  })

  it('should show S3 credential fields by default', () => {
    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // S3 credentials should be visible by default
    expect(screen.getByLabelText(/Access Key ID/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Secret Access Key/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/AWS Region/i)).toBeInTheDocument()
  })

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    await user.click(screen.getByText(/Cancel/i))

    expect(mockOnCancel).toHaveBeenCalledTimes(1)
  })

  it('should show Update button when editing existing connector', () => {
    const existingConnector: Connector = {
      guid: 'con_01hgw2bbg00000000000000001',
      name: 'Existing Connector',
      type: 's3',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    }

    render(
      <ConnectorForm
        connector={existingConnector}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByRole('button', { name: /Update/i })).toBeInTheDocument()
  })

  it('should show validation error for empty name', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Submit without filling form
    const submitButton = screen.getByRole('button', { name: /Create/i })
    await user.click(submitButton)

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/Connector name is required/i)).toBeInTheDocument()
    })
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('should display active checkbox', () => {
    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Active checkbox should be present
    const activeCheckbox = screen.getByRole('checkbox', { name: /Active/i })
    expect(activeCheckbox).toBeInTheDocument()
    expect(activeCheckbox).toBeChecked() // Should be checked by default
  })
})
