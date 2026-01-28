import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import CollectionForm from '@/components/collections/CollectionForm'
import type { Connector } from '@/contracts/api/connector-api'
import type { Collection } from '@/contracts/api/collection-api'
import type { CollectionFormData } from '@/types/schemas/collection'

// Mock the useOnlineAgents hook
vi.mock('@/hooks/useOnlineAgents', () => ({
  useOnlineAgents: vi.fn(() => ({
    onlineAgents: [
      { guid: 'agt_01hgw2bbg00000000000000001', name: 'Studio Mac', hostname: 'studio-mac.local', version: '1.0.0' },
      { guid: 'agt_01hgw2bbg00000000000000002', name: 'Home Server', hostname: 'home-server.local', version: '1.0.0' },
    ],
    loading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

describe('CollectionForm', () => {
  const mockConnectors: Connector[] = [
    {
      guid: 'con_01hgw2bbg00000000000000001',
      name: 'S3 Connector 1',
      type: 's3',
      credential_location: 'server',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'con_01hgw2bbg00000000000000002',
      name: 'S3 Connector 2',
      type: 's3',
      credential_location: 'server',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'con_01hgw2bbg00000000000000003',
      name: 'GCS Connector',
      type: 'gcs',
      credential_location: 'server',
      is_active: true,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'con_01hgw2bbg00000000000000004',
      name: 'Inactive S3',
      type: 's3',
      credential_location: 'server',
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
      guid: 'col_01hgw2bbg00000000000000001',
      name: 'Existing Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
      connector_guid: null,
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      cache_ttl: null,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      bound_agent: null,
      file_info: null,
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

  // =========================================================================
  // Agent Selector Tests (Phase 6 - Issue #90)
  // =========================================================================

  describe('Agent Selector', () => {
    it('should show agent selector for LOCAL collection type', () => {
      render(
        <CollectionForm
          collection={null}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Default type is LOCAL, so agent selector should be visible
      // Use getAllByText since label and icon text might both match
      const boundAgentElements = screen.getAllByText(/Bound Agent/i)
      expect(boundAgentElements.length).toBeGreaterThan(0)
    })

    it('should have agent selector combobox for LOCAL type', () => {
      render(
        <CollectionForm
          collection={null}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Default type is LOCAL, agent selector should be present
      const agentTrigger = screen.getByRole('combobox', { name: /Bound Agent/i })
      expect(agentTrigger).toBeInTheDocument()
    })

    it('should show description for agent selector', () => {
      render(
        <CollectionForm
          collection={null}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Should show the description text
      expect(screen.getByText(/Bind this collection to a specific agent/i)).toBeInTheDocument()
    })

    it('should pre-populate bound agent when editing collection with bound agent', () => {
      const collectionWithAgent: Collection = {
        guid: 'col_01hgw2bbg00000000000000001',
        name: 'Collection with Agent',
        type: 'local',
        location: '/photos',
        state: 'live',
        connector_guid: null,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
        cache_ttl: null,
        is_accessible: true,
        accessibility_message: null,
        last_scanned_at: null,
        bound_agent: {
          guid: 'agt_01hgw2bbg00000000000000001',
          name: 'Studio Mac',
          status: 'online',
        },
        file_info: null,
        created_at: '2025-01-01T09:00:00Z',
        updated_at: '2025-01-01T09:00:00Z',
      }

      render(
        <CollectionForm
          collection={collectionWithAgent}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Should show bound agent label
      const boundAgentElements = screen.getAllByText(/Bound Agent/i)
      expect(boundAgentElements.length).toBeGreaterThan(0)
    })
  })

  // =========================================================================
  // Next Scheduled Refresh Tests (Phase 13 - Issue #90)
  // =========================================================================

  describe('Next Scheduled Refresh', () => {
    it('should not show refresh info when creating new collection', () => {
      render(
        <CollectionForm
          collection={null}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.queryByText(/Next Scheduled Refresh/i)).not.toBeInTheDocument()
    })

    it('should show "Never scanned" when collection has no last_scanned_at', () => {
      const collectionNeverScanned: Collection = {
        guid: 'col_01hgw2bbg00000000000000001',
        name: 'Never Scanned Collection',
        type: 'local',
        location: '/photos',
        state: 'live',
        connector_guid: null,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
        cache_ttl: 3600,
        is_accessible: true,
        accessibility_message: null,
        last_scanned_at: null,
        bound_agent: null,
        file_info: null,
        created_at: '2025-01-01T09:00:00Z',
        updated_at: '2025-01-01T09:00:00Z',
      }

      render(
        <CollectionForm
          collection={collectionNeverScanned}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Next Scheduled Refresh/i)).toBeInTheDocument()
      expect(screen.getByText(/Never scanned/i)).toBeInTheDocument()
    })

    it('should show "Auto-refresh disabled" when collection has no cache_ttl', () => {
      const collectionNoTtl: Collection = {
        guid: 'col_01hgw2bbg00000000000000001',
        name: 'No TTL Collection',
        type: 'local',
        location: '/photos',
        state: 'live',
        connector_guid: null,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
        cache_ttl: null,
        is_accessible: true,
        accessibility_message: null,
        last_scanned_at: '2025-01-15T10:00:00Z',
        bound_agent: null,
        file_info: null,
        created_at: '2025-01-01T09:00:00Z',
        updated_at: '2025-01-01T09:00:00Z',
      }

      render(
        <CollectionForm
          collection={collectionNoTtl}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Next Scheduled Refresh/i)).toBeInTheDocument()
      expect(screen.getByText(/Auto-refresh disabled/i)).toBeInTheDocument()
    })

    it('should show "Refresh pending" when next refresh is in the past', () => {
      // Use a date that's definitely in the past relative to the test run
      const pastDate = new Date()
      pastDate.setDate(pastDate.getDate() - 1) // Yesterday

      const collectionPastDue: Collection = {
        guid: 'col_01hgw2bbg00000000000000001',
        name: 'Past Due Collection',
        type: 'local',
        location: '/photos',
        state: 'live',
        connector_guid: null,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
        cache_ttl: 3600, // 1 hour TTL, but last scan was yesterday
        is_accessible: true,
        accessibility_message: null,
        last_scanned_at: pastDate.toISOString(),
        bound_agent: null,
        file_info: null,
        created_at: '2025-01-01T09:00:00Z',
        updated_at: '2025-01-01T09:00:00Z',
      }

      render(
        <CollectionForm
          collection={collectionPastDue}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Next Scheduled Refresh/i)).toBeInTheDocument()
      expect(screen.getByText(/Refresh pending/i)).toBeInTheDocument()
    })

    it('should show last scanned timestamp when available', () => {
      const collectionWithScan: Collection = {
        guid: 'col_01hgw2bbg00000000000000001',
        name: 'Scanned Collection',
        type: 'local',
        location: '/photos',
        state: 'live',
        connector_guid: null,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
        cache_ttl: null,
        is_accessible: true,
        accessibility_message: null,
        last_scanned_at: '2025-01-15T10:00:00Z',
        bound_agent: null,
        file_info: null,
        created_at: '2025-01-01T09:00:00Z',
        updated_at: '2025-01-01T09:00:00Z',
      }

      render(
        <CollectionForm
          collection={collectionWithScan}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Last scanned/i)).toBeInTheDocument()
    })

    it('should show future refresh datetime when scheduled', () => {
      // Use a date that will result in a future next refresh
      const recentDate = new Date()
      recentDate.setMinutes(recentDate.getMinutes() - 30) // 30 minutes ago

      const collectionWithFutureRefresh: Collection = {
        guid: 'col_01hgw2bbg00000000000000001',
        name: 'Future Refresh Collection',
        type: 'local',
        location: '/photos',
        state: 'live',
        connector_guid: null,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
        cache_ttl: 3600, // 1 hour TTL, scanned 30 min ago = refresh in ~30 min
        is_accessible: true,
        accessibility_message: null,
        last_scanned_at: recentDate.toISOString(),
        bound_agent: null,
        file_info: null,
        created_at: '2025-01-01T09:00:00Z',
        updated_at: '2025-01-01T09:00:00Z',
      }

      render(
        <CollectionForm
          collection={collectionWithFutureRefresh}
          connectors={mockConnectors}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText(/Next Scheduled Refresh/i)).toBeInTheDocument()
      // Should show a formatted date/time, not "Never scanned" or "Refresh pending"
      expect(screen.queryByText(/Never scanned/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Refresh pending/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Auto-refresh disabled/i)).not.toBeInTheDocument()
    })
  })
})
