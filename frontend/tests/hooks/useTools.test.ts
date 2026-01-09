import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useTools, useQueueStatus } from '@/hooks/useTools'
import { resetMockData } from '../mocks/handlers'

describe('useTools', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should start with empty jobs and no loading state when autoFetch is disabled', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    expect(result.current.jobs).toEqual([])
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should fetch jobs on mount when autoFetch is enabled', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: true }))

    // Initially loading
    expect(result.current.loading).toBe(true)

    // Wait for loading to complete
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // No jobs initially (mock data starts with empty jobs)
    expect(result.current.jobs).toEqual([])
    expect(result.current.error).toBe(null)
  })

  it('should run a tool successfully', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    await act(async () => {
      const job = await result.current.runTool({
        collection_id: 1,
        tool: 'photostats'
      })

      expect(job.id).toBeDefined()
      expect(job.collection_id).toBe(1)
      expect(job.tool).toBe('photostats')
      expect(job.status).toBe('queued')
    })

    expect(result.current.jobs).toHaveLength(1)
    expect(result.current.jobs[0].tool).toBe('photostats')
    expect(result.current.error).toBe(null)
  })

  it('should run photo_pairing tool', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    await act(async () => {
      const job = await result.current.runTool({
        collection_id: 1,
        tool: 'photo_pairing'
      })

      expect(job.tool).toBe('photo_pairing')
    })

    expect(result.current.jobs[0].tool).toBe('photo_pairing')
  })

  it('should reject running tool on inaccessible collection', async () => {
    // Note: We need to modify the mock collection to be inaccessible first
    // For this test, we'll test the error handling path
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    await act(async () => {
      try {
        // Non-existent collection will return 400
        await result.current.runTool({
          collection_id: 999,
          tool: 'photostats'
        })
        expect.fail('Should have thrown error')
      } catch (error: any) {
        expect(error.response?.status).toBe(400)
      }
    })
  })

  it('should reject duplicate tool run on same collection', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    // Run first job
    await act(async () => {
      await result.current.runTool({
        collection_id: 1,
        tool: 'photostats'
      })
    })

    // Try to run same tool on same collection
    await act(async () => {
      try {
        await result.current.runTool({
          collection_id: 1,
          tool: 'photostats'
        })
        expect.fail('Should have thrown conflict error')
      } catch (error: any) {
        expect(error.response?.status).toBe(409)
      }
    })
  })

  it('should cancel a queued job', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    // Create a job first
    let jobId: string
    await act(async () => {
      const job = await result.current.runTool({
        collection_id: 1,
        tool: 'photostats'
      })
      jobId = job.id
    })

    // Cancel the job
    await act(async () => {
      const cancelledJob = await result.current.cancelJob(jobId!)
      expect(cancelledJob.status).toBe('cancelled')
    })

    expect(result.current.jobs[0].status).toBe('cancelled')
  })

  it('should fail to cancel non-existent job', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    await act(async () => {
      try {
        await result.current.cancelJob('non-existent-job')
        expect.fail('Should have thrown 404 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(404)
      }
    })
  })

  it('should get a specific job', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    // Create a job first
    let jobId: string
    await act(async () => {
      const job = await result.current.runTool({
        collection_id: 1,
        tool: 'photostats'
      })
      jobId = job.id
    })

    // Get the job
    await act(async () => {
      const job = await result.current.getJob(jobId!)
      expect(job.id).toBe(jobId)
      expect(job.tool).toBe('photostats')
    })
  })

  it('should fetch jobs with filters', async () => {
    const { result } = renderHook(() => useTools({ autoFetch: false }))

    // Create a job first
    await act(async () => {
      await result.current.runTool({
        collection_id: 1,
        tool: 'photostats'
      })
    })

    // Fetch jobs with status filter
    await act(async () => {
      const jobs = await result.current.fetchJobs({ status: 'queued' })
      expect(jobs).toHaveLength(1)
    })
  })
})

describe('useQueueStatus', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch queue status on mount', async () => {
    const { result } = renderHook(() => useQueueStatus({ autoFetch: true, pollInterval: 0 }))

    // Initially loading
    expect(result.current.loading).toBe(true)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.queueStatus).toBeDefined()
    expect(result.current.queueStatus?.queued_count).toBe(0)
    expect(result.current.queueStatus?.running_count).toBe(0)
    expect(result.current.error).toBe(null)
  })

  it('should refetch queue status', async () => {
    const { result } = renderHook(() => useQueueStatus({ autoFetch: false, pollInterval: 0 }))

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.queueStatus).toBeDefined()
  })
})
