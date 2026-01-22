/**
 * Integration tests for scheduled jobs functionality - T190
 *
 * Tests the scheduled jobs (upcoming) tab in Analytics including:
 * - Queue status includes scheduled_count
 * - Jobs can be filtered by scheduled status
 * - Scheduled jobs can be cancelled
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useTools, useQueueStatus } from '@/hooks/useTools'
import { resetMockData, addScheduledJob } from '../mocks/handlers'

describe('Scheduled Jobs Integration', () => {
  beforeEach(() => {
    resetMockData()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Queue Status with Scheduled Count', () => {
    it('should return scheduled_count of 0 when no scheduled jobs', async () => {
      const { result: queueResult } = renderHook(() =>
        useQueueStatus({ autoFetch: false, pollInterval: 0 })
      )

      await act(async () => {
        await queueResult.current.refetch()
      })

      await waitFor(() => {
        expect(queueResult.current.loading).toBe(false)
      })

      expect(queueResult.current.queueStatus).toBeDefined()
      expect(queueResult.current.queueStatus?.scheduled_count).toBe(0)
    })

    it('should return correct scheduled_count when scheduled jobs exist', async () => {
      // Add some scheduled jobs
      addScheduledJob('col_01hgw2bbg00000000000000001', 'photostats', 1)
      addScheduledJob('col_01hgw2bbg00000000000000001', 'photo_pairing', 2)
      addScheduledJob('col_01hgw2bbg00000000000000002', 'photostats', 3)

      const { result: queueResult } = renderHook(() =>
        useQueueStatus({ autoFetch: false, pollInterval: 0 })
      )

      await act(async () => {
        await queueResult.current.refetch()
      })

      await waitFor(() => {
        expect(queueResult.current.loading).toBe(false)
      })

      expect(queueResult.current.queueStatus?.scheduled_count).toBe(3)
    })

    it('should separate scheduled_count from queued_count', async () => {
      // Add scheduled jobs
      addScheduledJob('col_01hgw2bbg00000000000000001', 'photostats', 1)
      addScheduledJob('col_01hgw2bbg00000000000000001', 'photo_pairing', 2)

      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))
      const { result: queueResult } = renderHook(() =>
        useQueueStatus({ autoFetch: false, pollInterval: 0 })
      )

      // Run a regular job (will be queued)
      await act(async () => {
        await toolsResult.current.runTool({
          collection_guid: 'col_01hgw2bbg00000000000000002',
          tool: 'photostats'
        })
      })

      // Get queue status
      await act(async () => {
        await queueResult.current.refetch()
      })

      await waitFor(() => {
        expect(queueResult.current.loading).toBe(false)
      })

      // Should have 2 scheduled and 1 queued - these are separate counts
      expect(queueResult.current.queueStatus?.scheduled_count).toBe(2)
      expect(queueResult.current.queueStatus?.queued_count).toBe(1)
    })
  })

  describe('Job List Filtering by Scheduled Status', () => {
    it('should filter jobs by scheduled status', async () => {
      // Add scheduled jobs
      addScheduledJob('col_01hgw2bbg00000000000000001', 'photostats', 1)
      addScheduledJob('col_01hgw2bbg00000000000000002', 'photo_pairing', 2)

      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Run a regular job (will be queued)
      await act(async () => {
        await toolsResult.current.runTool({
          collection_guid: 'col_01hgw2bbg00000000000000001',
          tool: 'pipeline_validation'
        })
      })

      // Fetch jobs with scheduled status filter
      await act(async () => {
        await toolsResult.current.fetchJobs({ status: ['scheduled'] })
      })

      await waitFor(() => {
        expect(toolsResult.current.loading).toBe(false)
      })

      // Should only return scheduled jobs
      expect(toolsResult.current.jobs.length).toBe(2)
      expect(toolsResult.current.jobs.every(j => j.status === 'scheduled')).toBe(true)
    })

    it('should include scheduled_for timestamp in scheduled jobs', async () => {
      // Add a scheduled job
      const scheduledJob = addScheduledJob('col_01hgw2bbg00000000000000001', 'photostats', 1)

      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Fetch jobs
      await act(async () => {
        await toolsResult.current.fetchJobs({ status: ['scheduled'] })
      })

      await waitFor(() => {
        expect(toolsResult.current.loading).toBe(false)
      })

      // Should have scheduled_for timestamp
      expect(toolsResult.current.jobs.length).toBe(1)
      expect(toolsResult.current.jobs[0].scheduled_for).toBeDefined()
      expect(toolsResult.current.jobs[0].scheduled_for).not.toBeNull()
    })
  })

  describe('Scheduled Job Cancellation', () => {
    it('should cancel a scheduled job', async () => {
      // Add a scheduled job
      const scheduledJob = addScheduledJob('col_01hgw2bbg00000000000000001', 'photostats', 1)

      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Fetch jobs to populate state
      await act(async () => {
        await toolsResult.current.fetchJobs({ status: ['scheduled'] })
      })

      // Cancel the scheduled job
      await act(async () => {
        const cancelledJob = await toolsResult.current.cancelJob(scheduledJob.id)
        expect(cancelledJob.status).toBe('cancelled')
      })
    })

    it('should update queue status after cancelling scheduled job', async () => {
      // Add scheduled jobs
      addScheduledJob('col_01hgw2bbg00000000000000001', 'photostats', 1)
      const jobToCancel = addScheduledJob('col_01hgw2bbg00000000000000001', 'photo_pairing', 2)

      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))
      const { result: queueResult } = renderHook(() =>
        useQueueStatus({ autoFetch: false, pollInterval: 0 })
      )

      // Get initial queue status
      await act(async () => {
        await queueResult.current.refetch()
      })

      expect(queueResult.current.queueStatus?.scheduled_count).toBe(2)

      // Cancel one scheduled job
      await act(async () => {
        await toolsResult.current.cancelJob(jobToCancel.id)
      })

      // Refresh queue status
      await act(async () => {
        await queueResult.current.refetch()
      })

      // Should have one less scheduled job and one more cancelled job
      expect(queueResult.current.queueStatus?.scheduled_count).toBe(1)
      expect(queueResult.current.queueStatus?.cancelled_count).toBe(1)
    })
  })
})
