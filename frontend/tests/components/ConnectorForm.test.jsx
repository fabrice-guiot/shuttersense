import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConnectorForm from '../../src/components/connectors/ConnectorForm';

describe('ConnectorForm', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render the form with required fields', () => {
    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/Connector Name/i)).toBeInTheDocument();
    expect(screen.getByText(/Create/i)).toBeInTheDocument();
    expect(screen.getByText(/Cancel/i)).toBeInTheDocument();
  });

  it('should show S3 credential fields by default', () => {
    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // S3 credentials should be visible by default
    expect(screen.getByLabelText(/AWS Access Key ID/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/AWS Secret Access Key/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Region/i)).toBeInTheDocument();
  });

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    await user.click(screen.getByText(/Cancel/i));

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('should show Update button when editing existing connector', () => {
    const existingConnector = {
      id: 1,
      name: 'Existing Connector',
      type: 's3',
      is_active: true,
    };

    render(
      <ConnectorForm
        connector={existingConnector}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText(/Update/i)).toBeInTheDocument();
  });

  it('should show validation error for empty name', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Submit without filling form
    const submitButton = screen.getByText(/Create/i);
    await user.click(submitButton);

    // Should show validation error
    expect(await screen.findByText(/Name is required/i)).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
});
