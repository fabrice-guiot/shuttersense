import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import { ConnectorList } from '@/components/connectors/ConnectorList'
import type { Connector } from '@/contracts/api/connector-api'

describe('ConnectorList', () => {
  const mockConnectors: Connector[] = [
    {
      guid: 'con_01hgw2bbg00000000000000001',
      name: 'S3 Connector',
      type: 's3',
      is_active: true,
      last_validated: '2025-01-01T10:00:00Z',
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T10:00:00Z',
    },
    {
      guid: 'con_01hgw2bbg00000000000000002',
      name: 'GCS Connector',
      type: 'gcs',
      is_active: false,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'con_01hgw2bbg00000000000000003',
      name: 'SMB Connector',
      type: 'smb',
      is_active: true,
      last_validated: '2025-01-02T12:00:00Z',
      created_at: '2025-01-02T09:00:00Z',
      updated_at: '2025-01-02T12:00:00Z',
    },
  ]

  const mockOnEdit = vi.fn()
  const mockOnDelete = vi.fn()
  const mockOnTest = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should render loading state', () => {
    render(
      <ConnectorList
        connectors={[]}
        loading={true}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    // Look for loading spinner
    const spinner = screen.getByRole('status', { hidden: true })
    expect(spinner).toBeInTheDocument()
  })

  it('should render connector list', () => {
    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('S3 Connector')).toBeInTheDocument()
    expect(screen.getByText('GCS Connector')).toBeInTheDocument()
    expect(screen.getByText('SMB Connector')).toBeInTheDocument()
  })

  it('should display connector types as badges', () => {
    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    expect(screen.getByText('Amazon S3')).toBeInTheDocument()
    expect(screen.getByText('Google Cloud Storage')).toBeInTheDocument()
    expect(screen.getByText('SMB/CIFS')).toBeInTheDocument()
  })

  it('should display active/inactive status', () => {
    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const activeChips = screen.getAllByText('Active')
    const inactiveChips = screen.getAllByText('Inactive')

    expect(activeChips).toHaveLength(2)
    expect(inactiveChips).toHaveLength(1)
  })

  it('should display created timestamp', () => {
    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    // All connectors should have created_at timestamps
    // formatDateTime produces format like "Jan 15, 2024, 3:45 PM" or similar locale-dependent format
    // Look for common patterns: month abbreviation with year, or date with time separator
    const timestamps = screen.getAllByText(/\d{4}|AM|PM|:\d{2}/)
    expect(timestamps.length).toBeGreaterThan(0)
  })

  it('should show confirmation dialog when delete button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const deleteButtons = screen.getAllByRole('button', { name: /Delete Connector/i })

    // Click first delete button
    await user.click(deleteButtons[0])

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(screen.getByText(/Delete Connector/i)).toBeInTheDocument()
      expect(screen.getByText(/Are you sure you want to delete "S3 Connector"/i)).toBeInTheDocument()
    })

    // Should have Cancel and Delete buttons in dialog
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('Cancel')).toBeInTheDocument()
    expect(within(dialog).getByText('Delete')).toBeInTheDocument()
  })

  it('should call onDelete when delete is confirmed', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const deleteButtons = screen.getAllByRole('button', { name: /Delete Connector/i })

    // Click first delete button
    await user.click(deleteButtons[0])

    // Wait for dialog
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Click Delete in confirmation dialog
    const dialog = screen.getByRole('dialog')
    const confirmButton = within(dialog).getByText('Delete')
    await user.click(confirmButton)

    // onDelete should be called with the connector object
    await waitFor(() => {
      expect(mockOnDelete).toHaveBeenCalledTimes(1)
      expect(mockOnDelete).toHaveBeenCalledWith(mockConnectors[0])
    })
  })

  it('should close dialog when cancel is clicked', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const deleteButtons = screen.getAllByRole('button', { name: /Delete Connector/i })

    // Click first delete button
    await user.click(deleteButtons[0])

    // Wait for dialog
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Click Cancel
    const dialog = screen.getByRole('dialog')
    const cancelButton = within(dialog).getByText('Cancel')
    await user.click(cancelButton)

    // Dialog should close and onDelete should not be called
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(mockOnDelete).not.toHaveBeenCalled()
  })

  it('should call onEdit when edit button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const editButtons = screen.getAllByRole('button', { name: /Edit Connector/i })

    await user.click(editButtons[0])

    expect(mockOnEdit).toHaveBeenCalledTimes(1)
    expect(mockOnEdit).toHaveBeenCalledWith(mockConnectors[0])
  })

  it('should call onTest when test connection button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <ConnectorList
        connectors={mockConnectors}
        loading={false}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onTest={mockOnTest}
      />
    )

    const testButtons = screen.getAllByRole('button', { name: /Test Connection/i })

    await user.click(testButtons[0])

    expect(mockOnTest).toHaveBeenCalledTimes(1)
    expect(mockOnTest).toHaveBeenCalledWith(mockConnectors[0])
  })
})
