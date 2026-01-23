/**
 * Tests for ReportStorageTab component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Stats display
 * - Header stats integration
 *
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { describe, test, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { ReportStorageTab } from './ReportStorageTab'
import { HeaderStatsProvider } from '@/contexts/HeaderStatsContext'

// Mock storage stats data
const mockStorageStats = {
  total_reports_generated: 150,
  completed_jobs_purged: 25,
  failed_jobs_purged: 10,
  completed_results_purged_original: 20,
  completed_results_purged_copy: 30,
  estimated_bytes_purged: 5242880,
  total_results_retained: 100,
  original_results_retained: 60,
  copy_results_retained: 40,
  preserved_results_count: 15,
  reports_retained_json_bytes: 1048576,
  reports_retained_html_bytes: 4194304,
  deduplication_ratio: 40.0,
  storage_savings_bytes: 2097152
}

// Helper to render component with required providers
function renderWithProviders() {
  return render(
    <HeaderStatsProvider>
      <ReportStorageTab />
    </HeaderStatsProvider>
  )
}

describe('ReportStorageTab', () => {
  beforeEach(() => {
    // Reset MSW handlers
    server.resetHandlers()
  })

  describe('loading state', () => {
    test('shows loading spinner initially', async () => {
      // Override handler to delay response
      server.use(
        http.get('*/api/analytics/storage', async () => {
          await new Promise(resolve => setTimeout(resolve, 100))
          return HttpResponse.json(mockStorageStats)
        })
      )

      renderWithProviders()

      // Should show loading spinner
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('Total Results')).toBeInTheDocument()
      })
    })
  })

  describe('error state', () => {
    test('shows error message on API failure', async () => {
      server.use(
        http.get('*/api/analytics/storage', () => {
          return HttpResponse.json(
            { detail: 'Database connection failed' },
            { status: 500 }
          )
        })
      )

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Database connection failed')).toBeInTheDocument()
      })
    })
  })

  describe('stats display', () => {
    beforeEach(() => {
      server.use(
        http.get('*/api/analytics/storage', () => {
          return HttpResponse.json(mockStorageStats)
        })
      )
    })

    test('displays current storage section', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Current Storage')).toBeInTheDocument()
      })

      // Check KPI cards
      expect(screen.getByText('Total Results')).toBeInTheDocument()
      expect(screen.getByText('100')).toBeInTheDocument() // total_results_retained

      expect(screen.getByText('Original Results')).toBeInTheDocument()
      expect(screen.getByText('60')).toBeInTheDocument() // original_results_retained

      expect(screen.getByText('Deduplicated Copies')).toBeInTheDocument()
      expect(screen.getByText('40')).toBeInTheDocument() // copy_results_retained

      expect(screen.getByText('Protected Results')).toBeInTheDocument()
      expect(screen.getByText('15')).toBeInTheDocument() // preserved_results_count
    })

    test('displays storage usage section', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Storage Usage')).toBeInTheDocument()
      })

      // Storage breakdown
      expect(screen.getByText('JSON Data')).toBeInTheDocument()
      expect(screen.getByText('HTML Reports')).toBeInTheDocument()
      expect(screen.getByText('Total Storage')).toBeInTheDocument()

      // Deduplication ratio
      expect(screen.getByText('Deduplication Ratio')).toBeInTheDocument()
      expect(screen.getByText('40.0%')).toBeInTheDocument()
    })

    test('displays cleanup statistics section', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Cleanup Statistics (All Time)')).toBeInTheDocument()
      })

      expect(screen.getByText('Total Reports Generated')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument() // total_reports_generated

      expect(screen.getByText('Jobs Purged')).toBeInTheDocument()
      expect(screen.getByText('35')).toBeInTheDocument() // 25 + 10

      expect(screen.getByText('Results Purged')).toBeInTheDocument()
      expect(screen.getByText('50')).toBeInTheDocument() // 20 + 30
    })

    test('displays detailed breakdown section', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Detailed Breakdown')).toBeInTheDocument()
      })

      expect(screen.getByText('Completed Jobs Purged')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()

      expect(screen.getByText('Failed Jobs Purged')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()

      expect(screen.getByText('Original Results Purged')).toBeInTheDocument()
      expect(screen.getByText('20')).toBeInTheDocument()

      expect(screen.getByText('Copy Results Purged')).toBeInTheDocument()
      expect(screen.getByText('30')).toBeInTheDocument()
    })
  })

  describe('formatting', () => {
    test('formats bytes correctly', async () => {
      server.use(
        http.get('*/api/analytics/storage', () => {
          return HttpResponse.json(mockStorageStats)
        })
      )

      renderWithProviders()

      await waitFor(() => {
        // Total storage = 1MB + 4MB = 5MB (appears twice - in storage section and estimated freed)
        const fiveMBElements = screen.getAllByText('5 MB')
        expect(fiveMBElements.length).toBeGreaterThanOrEqual(1)
      })

      // JSON bytes = 1MB
      expect(screen.getByText('1 MB')).toBeInTheDocument()

      // HTML bytes = 4MB
      expect(screen.getByText('4 MB')).toBeInTheDocument()

      // Storage savings = 2MB
      expect(screen.getByText(/2 MB saved/)).toBeInTheDocument()
    })
  })
})
