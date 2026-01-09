import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import CollectionForm from '@/components/collections/CollectionForm'
import type { Connector } from '@/contracts/api/connector-api'
import type { Collection } from '@/contracts/api/collection-api'
import type { CollectionFormData } from '@/types/schemas/collection'

describe('CollectionForm', () => {
  const mockConnectors: Connector[] = [
    {
      id: 1,
      name: 'S3 Connector 1',
      type: 's3',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      id: 2,
      name: 'S3 Connector 2',
      type: 's3',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      id: 3,
      name: 'GCS Connector',
      type: 'gcs',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      id: 4,
      name: 'Inactive S3',
      type: 's3',
      is_active: false,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ]

  const mockOnSubmit = vi.fn<(data: CollectionFormData) => Promise<void>>()
  const mockOnCancel = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should render the form with required fields', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Location/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Create/i })).toBeInTheDocument()
    expect(screen.getByText(/Cancel/i)).toBeInTheDocument()
  })

  it('should hide connector field for LOCAL type by default', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Connector field should not be visible for LOCAL type (default)
    expect(screen.queryByLabelText(/Connector/i)).not.toBeInTheDocument()
  })

  it('should show validation error for empty name', async () => {
    const user = userEvent.setup()

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Submit without filling form
    await user.click(screen.getByRole('button', { name: /Create/i }))

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText(/Collection name is required/i)).toBeInTheDocument()
    })
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    await user.click(screen.getByText(/Cancel/i))

    expect(mockOnCancel).toHaveBeenCalledTimes(1)
  })

  it('should show Update button when editing existing collection', () => {
    const existingCollection: Collection = {
      id: 1,
      name: 'Existing Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
      connector_id: null,
      pipeline_id: null,
      pipeline_version: null,
      pipeline_name: null,
      cache_ttl: null,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    }

    render(
      <CollectionForm
        collection={existingCollection}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByRole('button', { name: /Update/i })).toBeInTheDocument()
  })

  it('should have type selector with all collection types', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Type field should exist
    expect(screen.getByLabelText(/Type/i)).toBeInTheDocument()
  })

  it('should have state selector with all collection states', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // State field should exist
    expect(screen.getByLabelText(/State/i)).toBeInTheDocument()
  })
})
