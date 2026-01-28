/**
 * InventoryStatusDisplay Component Tests
 *
 * Tests for the inventory status display component including:
 * - Validation status display
 * - T099a: "Import Now" guidance when validated but no import yet
 * - T100a: Stale inventory warning when data > 7 days old
 * - Job progress display
 * - Timestamp formatting
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T099a, T100a
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../../utils/test-utils'
import { InventoryStatusDisplay } from '@/components/inventory/InventoryStatusDisplay'
import type { InventoryStatus } from '@/contracts/api/inventory-api'

// ============================================================================
// Test Data
// ============================================================================

const baseStatus: InventoryStatus = {
  validation_status: 'validated',
  validation_error: null,
  latest_manifest: '2024-01-15/manifest.json',
  folder_count: 25,
  mapped_folder_count: 10,
  mappable_folder_count: 15,
  last_import_at: null,
  next_scheduled_at: null,
  current_job: null
}

// ============================================================================
// Tests
// ============================================================================

describe('InventoryStatusDisplay', () => {
  beforeEach(() => {
    // Mock Date.now() to a fixed date for stale inventory tests
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-20T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Loading State', () => {
    it('should show loading spinner when loading', () => {
      render(<InventoryStatusDisplay status={null} loading={true} />)

      expect(screen.getByText(/loading status/i)).toBeInTheDocument()
    })
  })

  describe('No Configuration', () => {
    it('should show "No inventory configuration" when status is null', () => {
      render(<InventoryStatusDisplay status={null} loading={false} />)

      expect(screen.getByText(/no inventory configuration/i)).toBeInTheDocument()
    })
  })

  describe('Validation Status', () => {
    it('should show "Validated" badge when validated', () => {
      render(<InventoryStatusDisplay status={baseStatus} />)

      expect(screen.getByText('Validated')).toBeInTheDocument()
    })

    it('should show "Pending" badge when pending', () => {
      render(
        <InventoryStatusDisplay
          status={{ ...baseStatus, validation_status: 'pending' }}
        />
      )

      expect(screen.getByText('Pending')).toBeInTheDocument()
    })

    it('should show "Validation Failed" badge and error when failed', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            validation_status: 'failed',
            validation_error: 'Could not access manifest.json'
          }}
        />
      )

      expect(screen.getByText('Validation Failed')).toBeInTheDocument()
      expect(screen.getByText(/could not access manifest\.json/i)).toBeInTheDocument()
    })

    it('should show "Validating" badge when validating', () => {
      render(
        <InventoryStatusDisplay
          status={{ ...baseStatus, validation_status: 'validating' }}
        />
      )

      expect(screen.getByText('Validating')).toBeInTheDocument()
    })
  })

  describe('T099a: Inventory Not Yet Generated Guidance', () => {
    it('should show guidance message when validated but no import yet', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            validation_status: 'validated',
            last_import_at: null,
            current_job: null
          }}
        />
      )

      expect(
        screen.getByText(/click "import now" to fetch inventory data and discover folders/i)
      ).toBeInTheDocument()
    })

    it('should NOT show guidance when import has been done', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            validation_status: 'validated',
            last_import_at: '2024-01-15T10:00:00Z'
          }}
        />
      )

      expect(
        screen.queryByText(/click "import now" to fetch inventory data/i)
      ).not.toBeInTheDocument()
    })

    it('should NOT show guidance when job is currently running', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            validation_status: 'validated',
            last_import_at: null,
            current_job: {
              guid: 'job_123',
              status: 'running',
              phase: 'folder_extraction',
              progress_percentage: 50
            }
          }}
        />
      )

      expect(
        screen.queryByText(/click "import now" to fetch inventory data/i)
      ).not.toBeInTheDocument()
    })

    it('should NOT show guidance when validation is not complete', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            validation_status: 'pending',
            last_import_at: null
          }}
        />
      )

      expect(
        screen.queryByText(/click "import now" to fetch inventory data/i)
      ).not.toBeInTheDocument()
    })
  })

  describe('T100a: Stale Inventory Warning', () => {
    it('should show stale warning when last import > 7 days ago', () => {
      // Current time is 2024-01-20, import was on 2024-01-10 (10 days ago)
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            last_import_at: '2024-01-10T10:00:00Z'
          }}
        />
      )

      expect(
        screen.getByText(/inventory data is more than 7 days old/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/consider running a new import/i)
      ).toBeInTheDocument()
    })

    it('should NOT show stale warning when last import <= 7 days ago', () => {
      // Current time is 2024-01-20, import was on 2024-01-15 (5 days ago)
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            last_import_at: '2024-01-15T10:00:00Z'
          }}
        />
      )

      expect(
        screen.queryByText(/inventory data is more than 7 days old/i)
      ).not.toBeInTheDocument()
    })

    it('should NOT show stale warning when no import has been done', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            last_import_at: null
          }}
        />
      )

      expect(
        screen.queryByText(/inventory data is more than 7 days old/i)
      ).not.toBeInTheDocument()
    })

    it('should show stale warning exactly at 7 days boundary', () => {
      // Current time is 2024-01-20 12:00, import was on 2024-01-13 11:00 (7 days + 1 hour ago)
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            last_import_at: '2024-01-13T11:00:00Z'
          }}
        />
      )

      expect(
        screen.getByText(/inventory data is more than 7 days old/i)
      ).toBeInTheDocument()
    })
  })

  describe('Job Progress', () => {
    it('should show progress when job is running', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            current_job: {
              guid: 'job_123',
              status: 'running',
              phase: 'folder_extraction',
              progress_percentage: 45
            }
          }}
        />
      )

      expect(screen.getByText(/extracting folders/i)).toBeInTheDocument()
      expect(screen.getByText('45%')).toBeInTheDocument()
    })

    it('should show file info population phase', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            current_job: {
              guid: 'job_123',
              status: 'running',
              phase: 'file_info_population',
              progress_percentage: 75
            }
          }}
        />
      )

      expect(screen.getByText(/populating file info/i)).toBeInTheDocument()
    })

    it('should show delta detection phase', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            current_job: {
              guid: 'job_123',
              status: 'running',
              phase: 'delta_detection',
              progress_percentage: 90
            }
          }}
        />
      )

      expect(screen.getByText(/detecting changes/i)).toBeInTheDocument()
    })
  })

  describe('Statistics', () => {
    it('should show folder counts when validated', () => {
      render(<InventoryStatusDisplay status={baseStatus} />)

      expect(screen.getByText('25')).toBeInTheDocument() // Total folders
      expect(screen.getByText('10')).toBeInTheDocument() // Mapped folders
    })

    it('should show latest manifest when validated', () => {
      render(<InventoryStatusDisplay status={baseStatus} />)

      expect(screen.getByText('2024-01-15/manifest.json')).toBeInTheDocument()
    })
  })

  describe('Timestamps', () => {
    it('should show last import timestamp when available', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            last_import_at: '2024-01-15T10:00:00Z'
          }}
        />
      )

      expect(screen.getByText(/last import/i)).toBeInTheDocument()
    })

    it('should show next scheduled import when available', () => {
      render(
        <InventoryStatusDisplay
          status={{
            ...baseStatus,
            next_scheduled_at: '2024-01-25T00:00:00Z'
          }}
        />
      )

      expect(screen.getByText(/next scheduled/i)).toBeInTheDocument()
    })
  })
})
