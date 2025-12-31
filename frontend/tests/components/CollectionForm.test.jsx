import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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

  it('should render the form with required fields', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/Collection Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Location/i)).toBeInTheDocument();
    expect(screen.getByText(/Create/i)).toBeInTheDocument();
    expect(screen.getByText(/Cancel/i)).toBeInTheDocument();
  });

  it('should hide connector field for local type by default', () => {
    render(
      <CollectionForm
        collection={null}
        connectors={mockConnectors}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Connector field should not be visible for local type (default)
    expect(screen.queryByLabelText(/Connector/i)).not.toBeInTheDocument();
  });

  it('should show validation error for empty name', async () => {
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
    expect(await screen.findByText(/Name is required/i)).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
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

  it('should show Update button when editing existing collection', () => {
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

    expect(screen.getByText(/Update/i)).toBeInTheDocument();
  });
});
