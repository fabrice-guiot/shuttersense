/**
 * InventoryConfigForm Component Tests
 *
 * Tests for the inventory configuration form component.
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { InventoryConfigForm } from '@/components/inventory/InventoryConfigForm'
import type { InventoryConfig } from '@/contracts/api/inventory-api'

describe('InventoryConfigForm', () => {
  const mockOnSubmit = vi.fn()
  const mockOnCancel = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('S3 Connector Form', () => {
    it('should render S3-specific fields', () => {
      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/source bucket/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/destination bucket/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/inventory configuration name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/inventory format/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/import schedule/i)).toBeInTheDocument()
    })

    it('should show S3 Inventory description', () => {
      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Use a more specific text that only appears in the description
      expect(screen.getByText(/import file metadata from your S3 bucket/i)).toBeInTheDocument()
    })

    it('should have ORC format option for S3', async () => {
      const user = userEvent.setup()

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the format select
      const formatSelect = screen.getByLabelText(/inventory format/i)
      await user.click(formatSelect)

      // ORC should be available for S3 - use getAllByRole to find in dropdown
      const options = screen.getAllByRole('option')
      const optionTexts = options.map(opt => opt.textContent)
      expect(optionTexts).toContain('ORC')
    })

    it('should submit S3 config correctly', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in form fields
      await user.type(screen.getByLabelText(/source bucket/i), 'my-photos-bucket')
      await user.type(screen.getByLabelText(/destination bucket/i), 'my-inventory-bucket')
      await user.type(screen.getByLabelText(/inventory configuration name/i), 'daily-inventory')

      // Submit form
      await user.click(screen.getByRole('button', { name: /save configuration/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            provider: 's3',
            source_bucket: 'my-photos-bucket',
            destination_bucket: 'my-inventory-bucket',
            config_name: 'daily-inventory',
            format: 'CSV'
          }),
          'manual'
        )
      })
    })
  })

  describe('GCS Connector Form', () => {
    it('should render GCS-specific fields', () => {
      render(
        <InventoryConfigForm
          connectorType="gcs"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/destination bucket/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/report configuration name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/report format/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/import schedule/i)).toBeInTheDocument()
    })

    it('should show GCS Storage Insights description', () => {
      render(
        <InventoryConfigForm
          connectorType="gcs"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Use a more specific text
      expect(screen.getByText(/import file metadata from your Cloud Storage bucket/i)).toBeInTheDocument()
    })

    it('should NOT have ORC format option for GCS', async () => {
      const user = userEvent.setup()

      render(
        <InventoryConfigForm
          connectorType="gcs"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the format select
      const formatSelect = screen.getByLabelText(/report format/i)
      await user.click(formatSelect)

      // Get all options from dropdown
      const options = screen.getAllByRole('option')
      const optionTexts = options.map(opt => opt.textContent)

      // ORC should NOT be available for GCS
      expect(optionTexts).not.toContain('ORC')
      // But CSV and Parquet should be
      expect(optionTexts).toContain('CSV')
      expect(optionTexts).toContain('Parquet')
    })

    it('should submit GCS config correctly', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <InventoryConfigForm
          connectorType="gcs"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill in form fields
      await user.type(screen.getByLabelText(/destination bucket/i), 'my-inventory-bucket')
      await user.type(screen.getByLabelText(/report configuration name/i), 'photo-inventory')

      // Submit form
      await user.click(screen.getByRole('button', { name: /save configuration/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            provider: 'gcs',
            destination_bucket: 'my-inventory-bucket',
            report_config_name: 'photo-inventory',
            format: 'CSV'
          }),
          'manual'
        )
      })
    })
  })

  describe('Schedule Selection', () => {
    it('should have all schedule options', async () => {
      const user = userEvent.setup()

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Click the schedule select
      const scheduleSelect = screen.getByLabelText(/import schedule/i)
      await user.click(scheduleSelect)

      // Get all options from dropdown
      const options = screen.getAllByRole('option')
      const optionTexts = options.map(opt => opt.textContent)

      expect(optionTexts).toContain('Manual only')
      expect(optionTexts).toContain('Daily')
      expect(optionTexts).toContain('Weekly')
    })

    it('should submit with selected schedule', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValue(undefined)

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Fill required fields
      await user.type(screen.getByLabelText(/source bucket/i), 'source')
      await user.type(screen.getByLabelText(/destination bucket/i), 'dest')
      await user.type(screen.getByLabelText(/inventory configuration name/i), 'config')

      // Select daily schedule - find the option by role
      const scheduleSelect = screen.getByLabelText(/import schedule/i)
      await user.click(scheduleSelect)
      const dailyOption = screen.getByRole('option', { name: 'Daily' })
      await user.click(dailyOption)

      // Submit
      await user.click(screen.getByRole('button', { name: /save configuration/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.any(Object),
          'daily'
        )
      })
    })
  })

  describe('Form Validation', () => {
    it('should show validation errors for empty required fields', async () => {
      const user = userEvent.setup()

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Submit without filling required fields
      await user.click(screen.getByRole('button', { name: /save configuration/i }))

      await waitFor(() => {
        // Should show validation errors
        expect(screen.getAllByText(/required/i).length).toBeGreaterThan(0)
      })

      // onSubmit should not have been called
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('should validate bucket name minimum length', async () => {
      const user = userEvent.setup()

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      // Enter too-short bucket name
      await user.type(screen.getByLabelText(/source bucket/i), 'ab')
      await user.type(screen.getByLabelText(/destination bucket/i), 'dest-bucket')
      await user.type(screen.getByLabelText(/inventory configuration name/i), 'config')

      // Submit
      await user.click(screen.getByRole('button', { name: /save configuration/i }))

      // Should not submit with invalid bucket name
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Cancel Action', () => {
    it('should call onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      expect(mockOnCancel).toHaveBeenCalled()
    })
  })

  describe('Edit Mode', () => {
    it('should show "Update Configuration" button when editing', () => {
      const existingConfig: InventoryConfig = {
        provider: 's3',
        destination_bucket: 'existing-inventory',
        source_bucket: 'existing-photos',
        config_name: 'existing-config',
        format: 'CSV'
      }

      render(
        <InventoryConfigForm
          connectorType="s3"
          existingConfig={existingConfig}
          existingSchedule="weekly"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /update configuration/i })).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('should disable buttons when loading', () => {
      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          loading={true}
        />
      )

      expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
    })
  })

  describe('Error Display', () => {
    it('should display error message', () => {
      render(
        <InventoryConfigForm
          connectorType="s3"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          error="Failed to save configuration"
        />
      )

      expect(screen.getByText(/failed to save configuration/i)).toBeInTheDocument()
    })
  })
})
