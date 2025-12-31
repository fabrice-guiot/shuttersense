import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConnectorForm from '../../src/components/connectors/ConnectorForm';

describe('ConnectorForm', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render the form with default S3 type', () => {
    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/Connector Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Type/i)).toBeInTheDocument();
    expect(screen.getByText(/Create/i)).toBeInTheDocument();
    expect(screen.getByText(/Cancel/i)).toBeInTheDocument();

    // S3 credentials should be visible by default
    expect(screen.getByLabelText(/AWS Access Key ID/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/AWS Secret Access Key/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Region/i)).toBeInTheDocument();
  });

  it('should show S3 credential fields when S3 type is selected', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // S3 is default, fields should be visible
    expect(screen.getByLabelText(/AWS Access Key ID/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/AWS Secret Access Key/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Region/i)).toBeInTheDocument();
  });

  it('should show GCS credential fields when GCS type is selected', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Click on type dropdown and select GCS
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Google Cloud Storage/i));

    // GCS credentials should now be visible
    await waitFor(() => {
      expect(screen.getByLabelText(/Service Account JSON/i)).toBeInTheDocument();
    });

    // S3 fields should not be visible
    expect(screen.queryByLabelText(/AWS Access Key ID/i)).not.toBeInTheDocument();
  });

  it('should show SMB credential fields when SMB type is selected', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Click on type dropdown and select SMB
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/SMB\/CIFS/i));

    // SMB credentials should now be visible
    await waitFor(() => {
      expect(screen.getByLabelText(/Server/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Share/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    });
  });

  it('should validate required fields', async () => {
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

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText(/Name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/AWS Access Key ID is required/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should validate minimum length for credentials', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill name
    await user.type(screen.getByLabelText(/Connector Name/i), 'Test Connector');

    // Fill AWS Access Key ID with too short value (< 16 chars)
    await user.type(screen.getByLabelText(/AWS Access Key ID/i), 'SHORTKEY');

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Should show validation error for minimum length
    await waitFor(() => {
      expect(screen.getByText(/Minimum 16 characters/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
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

  it('should disable type selection when editing existing connector', () => {
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

    const typeSelect = screen.getByLabelText(/Type/i);
    expect(typeSelect).toBeDisabled();
    expect(screen.getByText(/Update/i)).toBeInTheDocument();
  });

  // Integration test: fill form and submit
  it('should successfully submit valid S3 connector form', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill form
    await user.type(screen.getByLabelText(/Connector Name/i), 'My S3 Connector');
    await user.type(screen.getByLabelText(/AWS Access Key ID/i), 'AKIAIOSFODNN7EXAMPLE');
    await user.type(
      screen.getByLabelText(/AWS Secret Access Key/i),
      'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    );
    await user.type(screen.getByLabelText(/Region/i), 'us-east-1');

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify submit was called with correct data
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'My S3 Connector',
        type: 's3',
        credentials: {
          aws_access_key_id: 'AKIAIOSFODNN7EXAMPLE',
          aws_secret_access_key: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
          region: 'us-east-1',
        },
        metadata: {},
      });
    });
  });

  it('should successfully submit valid GCS connector form', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill name
    await user.type(screen.getByLabelText(/Connector Name/i), 'My GCS Connector');

    // Switch to GCS
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/Google Cloud Storage/i));

    // Fill GCS credentials
    await waitFor(() => {
      expect(screen.getByLabelText(/Service Account JSON/i)).toBeInTheDocument();
    });

    const serviceAccountJson = '{"type":"service_account","project_id":"my-project"}';
    await user.type(screen.getByLabelText(/Service Account JSON/i), serviceAccountJson);

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify submit was called with correct data
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'My GCS Connector',
        type: 'gcs',
        credentials: {
          service_account_json: serviceAccountJson,
        },
        metadata: {},
      });
    });
  });

  it('should successfully submit valid SMB connector form', async () => {
    const user = userEvent.setup();

    render(
      <ConnectorForm
        connector={null}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Fill name
    await user.type(screen.getByLabelText(/Connector Name/i), 'My SMB Connector');

    // Switch to SMB
    const typeSelect = screen.getByLabelText(/Type/i);
    await user.click(typeSelect);
    await user.click(screen.getByText(/SMB\/CIFS/i));

    // Fill SMB credentials
    await waitFor(() => {
      expect(screen.getByLabelText(/Server/i)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/Server/i), 'nas.local');
    await user.type(screen.getByLabelText(/Share/i), 'photos');
    await user.type(screen.getByLabelText(/Username/i), 'admin');
    await user.type(screen.getByLabelText(/Password/i), 'password123');

    // Submit
    await user.click(screen.getByText(/Create/i));

    // Verify submit was called with correct data
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'My SMB Connector',
        type: 'smb',
        credentials: {
          server: 'nas.local',
          share: 'photos',
          username: 'admin',
          password: 'password123',
        },
        metadata: {},
      });
    });
  });
});
