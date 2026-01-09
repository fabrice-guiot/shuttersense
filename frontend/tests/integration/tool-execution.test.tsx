/**
 * Integration tests for tool execution flow - T068
 *
 * Tests the complete workflow from running a tool to viewing results
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useTools, useQueueStatus } from '@/hooks/useTools'
import { useResults, useResult, useResultStats } from '@/hooks/useResults'
import { resetMockData } from '../mocks/handlers'

describe('Tool Execution Integration', () => {
  beforeEach(() => {
    resetMockData()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Run Tool to View Result Flow', () => {
    it('should run a tool, wait for completion, and view result', async () => {
      // Step 1: Initialize tools hook
      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Step 2: Run PhotoStats tool on collection 1
      let jobId: string
      await act(async () => {
        const job = await toolsResult.current.runTool({
          collection_id: 1,
          tool: 'photostats'
        })
        jobId = job.id
        expect(job.status).toBe('queued')
      })

      // Step 3: Verify job is in the jobs list
      expect(toolsResult.current.jobs).toHaveLength(1)
      expect(toolsResult.current.jobs[0].id).toBe(jobId!)

      // Step 4: Fetch results to see completed analysis
      const { result: resultsResult } = renderHook(() =>
        useResults({ autoFetch: true, debounceMs: 0 })
      )

      await waitFor(() => {
        expect(resultsResult.current.loading).toBe(false)
      })

      // Results should include the pre-existing mock results
      expect(resultsResult.current.results.length).toBeGreaterThan(0)
    })

    it('should get queue status during tool execution', async () => {
      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))
      const { result: queueResult } = renderHook(() =>
        useQueueStatus({ autoFetch: false, pollInterval: 0 })
      )

      // Run a tool
      await act(async () => {
        await toolsResult.current.runTool({
          collection_id: 1,
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

      expect(queueResult.current.queueStatus).toBeDefined()
      expect(queueResult.current.queueStatus?.queued_count).toBeGreaterThanOrEqual(0)
    })

    it('should cancel a queued job', async () => {
      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Run a tool
      let jobId: string
      await act(async () => {
        const job = await toolsResult.current.runTool({
          collection_id: 1,
          tool: 'photostats'
        })
        jobId = job.id
      })

      // Cancel the job
      await act(async () => {
        const cancelledJob = await toolsResult.current.cancelJob(jobId!)
        expect(cancelledJob.status).toBe('cancelled')
      })

      // Verify the job status was updated
      expect(toolsResult.current.jobs[0].status).toBe('cancelled')
    })
  })

  describe('Results Management Flow', () => {
    it('should list and filter results', async () => {
      const { result } = renderHook(() =>
        useResults({ autoFetch: false, debounceMs: 0 })
      )

      // Fetch all results
      await act(async () => {
        await result.current.fetchResults({})
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.results.length).toBe(4) // Mock has 4 results
      expect(result.current.total).toBe(4)

      // Filter by tool
      await act(async () => {
        await result.current.fetchResults({ tool: 'photostats' })
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Should only have photostats results
      expect(result.current.results.every(r => r.tool === 'photostats')).toBe(true)
    })

    it('should get single result with full details', async () => {
      const { result } = renderHook(() => useResult(1))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.result).toBeDefined()
      expect(result.current.result?.id).toBe(1)
      expect(result.current.result?.tool).toBe('photostats')
      expect(result.current.result?.results).toBeDefined()
      // Type narrow to PhotoStatsResults to access its properties
      const photoStatsResults = result.current.result?.results as { total_files: number }
      expect(photoStatsResults?.total_files).toBe(1000)
    })

    it('should delete a result', async () => {
      const { result } = renderHook(() =>
        useResults({ autoFetch: true, debounceMs: 0 })
      )

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const initialCount = result.current.results.length

      // Delete the first result
      const resultToDelete = result.current.results[0]
      await act(async () => {
        await result.current.deleteResult(resultToDelete.id)
      })

      // Result should be removed
      expect(result.current.results.length).toBe(initialCount - 1)
      expect(result.current.results.find(r => r.id === resultToDelete.id)).toBeUndefined()
    })

    it('should get result statistics', async () => {
      const { result } = renderHook(() => useResultStats(true))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.stats).toBeDefined()
      expect(result.current.stats?.total_results).toBe(4)
      expect(result.current.stats?.completed_count).toBe(3)
      expect(result.current.stats?.failed_count).toBe(1)
      expect(result.current.stats?.by_tool.photostats).toBe(2)
      expect(result.current.stats?.by_tool.photo_pairing).toBe(1)
      expect(result.current.stats?.by_tool.pipeline_validation).toBe(1)
    })
  })

  describe('Error Handling Flow', () => {
    it('should handle tool conflict error', async () => {
      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Run first job
      await act(async () => {
        await toolsResult.current.runTool({
          collection_id: 1,
          tool: 'photostats'
        })
      })

      // Try to run same tool on same collection
      await act(async () => {
        try {
          await toolsResult.current.runTool({
            collection_id: 1,
            tool: 'photostats'
          })
          expect.fail('Should have thrown conflict error')
        } catch (error: any) {
          expect(error.response?.status).toBe(409)
        }
      })
    })

    it('should handle non-existent result fetch', async () => {
      const { result } = renderHook(() => useResult(999))

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.error).toBeTruthy()
      expect(result.current.result).toBe(null)
    })

    it('should handle non-existent result deletion', async () => {
      const { result } = renderHook(() =>
        useResults({ autoFetch: false, debounceMs: 0 })
      )

      await act(async () => {
        try {
          await result.current.deleteResult(999)
          expect.fail('Should have thrown 404 error')
        } catch (error: any) {
          expect(error.response?.status).toBe(404)
        }
      })
    })
  })

  describe('Pagination Flow', () => {
    it('should handle pagination correctly', async () => {
      const { result } = renderHook(() =>
        useResults({ autoFetch: false, debounceMs: 0, defaultLimit: 2 })
      )

      // Fetch first page
      await act(async () => {
        await result.current.fetchResults({ limit: 2, offset: 0 })
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.results.length).toBe(2) // Only 2 results per page
      expect(result.current.total).toBe(4) // Total is 4

      // Set page to 2 and refetch
      act(() => {
        result.current.setPage(2)
      })

      // Wait for debounced fetch
      await waitFor(() => {
        expect(result.current.page).toBe(2)
      })
    })

    it('should reset page when filters change', async () => {
      const { result } = renderHook(() =>
        useResults({ autoFetch: false, debounceMs: 0 })
      )

      // Set to page 2
      act(() => {
        result.current.setPage(2)
      })

      expect(result.current.page).toBe(2)

      // Change filters - should reset to page 1
      act(() => {
        result.current.setFilters({ tool: 'photostats' })
      })

      expect(result.current.page).toBe(1)
    })
  })

  describe('Multiple Tools Flow', () => {
    it('should run different tools on same collection', async () => {
      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Run PhotoStats
      await act(async () => {
        const job = await toolsResult.current.runTool({
          collection_id: 1,
          tool: 'photostats'
        })
        expect(job.tool).toBe('photostats')
      })

      // Run Photo Pairing (different tool, same collection - should succeed)
      await act(async () => {
        const job = await toolsResult.current.runTool({
          collection_id: 1,
          tool: 'photo_pairing'
        })
        expect(job.tool).toBe('photo_pairing')
      })

      // Should have 2 jobs
      expect(toolsResult.current.jobs).toHaveLength(2)
      expect(toolsResult.current.jobs.map(j => j.tool)).toContain('photostats')
      expect(toolsResult.current.jobs.map(j => j.tool)).toContain('photo_pairing')
    })

    it('should run same tool on different collections', async () => {
      const { result: toolsResult } = renderHook(() => useTools({ autoFetch: false }))

      // Run PhotoStats on collection 1
      await act(async () => {
        const job = await toolsResult.current.runTool({
          collection_id: 1,
          tool: 'photostats'
        })
        expect(job.collection_id).toBe(1)
      })

      // Run PhotoStats on collection 2 (same tool, different collection - should succeed)
      await act(async () => {
        const job = await toolsResult.current.runTool({
          collection_id: 2,
          tool: 'photostats'
        })
        expect(job.collection_id).toBe(2)
      })

      // Should have 2 jobs
      expect(toolsResult.current.jobs).toHaveLength(2)
    })
  })
})
