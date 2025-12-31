import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CollectionForm from '../../src/components/collections/CollectionForm';

describe('CollectionForm', () => {
  const mockConnectors = [
    { id: 1, name: 'S3 Connector 1', type: 's3', is_active: true },
    { id: 2, name: 'S3 Connector 2', type: 's3', is_active: true },
    { id: 3, name: 'GCS Connector', type: 'gcs', is_active: true },
    { id: 4, name: 'Inactive S3', type: 's3', is_active: false },
  ];

  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render the form with default local type', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/Collection Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/State/i)).toBeInTheDocument();
    expect(screen.getByText(/Create/i)).toBeInTheDocument();
    expect(screen.getByText(/Cancel/i)).toBeInTheDocument();
  });

  it('should hide connector field for local type', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Connector field should not be visible for local type
    expect(screen.queryByLabelText(/Connector/i)).not.toBeInTheDocument();
  });

  it('should show connector dropdown for S3 type', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Switch to S3
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Amazon S3/i));

    // Connector dropdown should now be visible
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });
  });

  it('should show connector dropdown for GCS type', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Switch to GCS
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Google Cloud Storage/i));

    // Connector dropdown should now be visible
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });
  });

  it('should show connector dropdown for SMB type', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Switch to SMB
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/SMB\/CIFS/i));

    // Connector dropdown should now be visible
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });
  });

  it('should filter connectors by type and active status', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Switch to S3
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Amazon S3/i));

    // Wait for connector dropdown
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });

    // Click on connector dropdown
    const connectorSelect = screen.getByLabelText(/Connector/i);
    await user.click(connectorSelect);

    // Should show only active S3 connectors
    await waitFor(() => {
      expect(screen.getByText('S3 Connector 1')).toBeInTheDocument();
      expect(screen.getByText('S3 Connector 2')).toBeInTheDocument();
    });

    // Should not show GCS connector
    expect(screen.queryByText('GCS Connector')).not.toBeInTheDocument();
    // Should not show inactive connector
    expect(screen.queryByText('Inactive S3')).not.toBeInTheDocument();
  });

  it('should validate required fields', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Submit without filling form
    await user.click(screen.getByText(/Create/i));

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText(/Name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Location is required/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should require connector for remote collection types', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill name and location
    await user.type(screen.getByLabelText(/Collection Name/i), 'Test Collection');
    await user.type(screen.getByLabelText(/Location/i), 'bucket/prefix');

    // Switch to S3
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Amazon S3/i));

    // Wait for connector field to appear
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });

    // Submit without selecting connector
    await user.click(screen.getByText(/Create/i));

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/Connector is required for remote collections/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should allow optional cache TTL override', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill form
    await user.type(screen.getByLabelText(/Collection Name/i), 'Test Collection');
    await user.type(screen.getByLabelText(/Location/i), '/photos');
    await user.type(screen.getByLabelText(/Cache TTL/i), '7200');

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify submit was called with cache_ttl
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      const submittedData = mockOnSubmit.mock.calls[0][0];
      expect(submittedData.cache_ttl).toBe('7200');
    });
  });

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    await user.click(screen.getByText(/Cancel/i));

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('should disable type selection when editing existing collection', () => {
    const existingCollection = {
      id: 1,
      name: 'Existing Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
    };

    render(
      <CollectionForm
        collection={existingCollection}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const typeSelect = screen.getByLabelText(/Type/i);
    expect(typeSelect).toBeDisabled();
    expect(screen.getByText(/Update/i)).toBeInTheDocument();
  });

  it('should successfully submit local collection form', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill form
    await user.type(screen.getByLabelText(/Collection Name/i), 'My Local Collection');
    await user.type(screen.getByLabelText(/Location/i), '/path/to/photos');

    // Select state
    const stateSelect = screen.getByLabelText(/State/i);
    await user.click(stateSelect);
    await user.click(screen.getByText(/Closed \(24hr cache\)/i));

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify submit was called with correct data
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'My Local Collection',
        type: 'local',
        location: '/path/to/photos',
        state: 'closed',
        connector_id: null,
        cache_ttl: '',
        metadata: {},
      });
    });
  });

  it('should successfully submit remote S3 collection form', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill name and location
    await user.type(screen.getByLabelText(/Collection Name/i), 'My S3 Collection');
    await user.type(screen.getByLabelText(/Location/i), 'my-bucket/photos');

    // Switch to S3
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Amazon S3/i));

    // Wait for connector field
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });

    // Select connector
    const connectorSelect = screen.getByLabelText(/Connector/i);
    await user.click(connectorSelect);
    await user.click(screen.getByText('S3 Connector 1'));

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify submit was called with correct data
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'My S3 Collection',
        type: 's3',
        location: 'my-bucket/photos',
        state: 'live',
        connector_id: 1,
        cache_ttl: '',
        metadata: {},
      });
    });
  });

  it('should reset connector_id when switching from remote to local', async () => {
    const user = userEvent.setup();

    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill name and location
    await user.type(screen.getByLabelText(/Collection Name/i), 'Test Collection');
    await user.type(screen.getByLabelText(/Location/i), '/photos');

    // Switch to S3
    let typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Amazon S3/i));

    // Select connector
    await waitFor(() => {
      expect(screen.getByLabelText(/Connector/i)).toBeInTheDocument();
    });

    const connectorSelect = screen.getByLabelText(/Connector/i);
    await user.click(connectorSelect);
    await user.click(screen.getByText('S3 Connector 1'));

    // Switch back to local
    typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Local Filesystem/i));

    // Connector field should disappear
    await waitFor(() => {
      expect(screen.queryByLabelText(/Connector/i)).not.toBeInTheDocument();
    });

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify connector_id is null
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      const submittedData = mockOnSubmit.mock.calls[0][0];
      expect(submittedData.connector_id).toBeNull();
    });
  });
});
