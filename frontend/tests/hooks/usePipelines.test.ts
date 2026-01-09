import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { usePipelines, usePipeline, usePipelineStats } from '@/hooks/usePipelines'
import { resetMockData } from '../mocks/handlers'

describe('usePipelines', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch pipelines on mount', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.pipelines).toEqual([])

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should have 3 mock pipelines
    expect(result.current.pipelines).toHaveLength(3)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is disabled', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: false }))

    expect(result.current.pipelines).toEqual([])
    expect(result.current.loading).toBe(false)
  })

  it('should fetch pipelines with active filter', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: false }))

    await act(async () => {
      await result.current.fetchPipelines({ is_active: true })
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // All returned pipelines should be active
    expect(result.current.pipelines.every((p) => p.is_active)).toBe(true)
  })

  it('should fetch pipelines with valid filter', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: false }))

    await act(async () => {
      await result.current.fetchPipelines({ is_valid: true })
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // All returned pipelines should be valid
    expect(result.current.pipelines.every((p) => p.is_valid)).toBe(true)
  })

  it('should create a new pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.pipelines.length

    await act(async () => {
      await result.current.createPipeline({
        name: 'New Test Pipeline',
        description: 'Test description',
        nodes: [
          { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
        ],
        edges: [],
      })
    })

    // Refetch to see the new pipeline
    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.pipelines.length).toBeGreaterThan(initialCount)
  })

  it('should fail to create duplicate pipeline name', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createPipeline({
          name: 'Standard RAW Workflow', // Already exists
          nodes: [{ id: 'done', type: 'termination', properties: {} }],
          edges: [],
        })
        expect.fail('Should have thrown 409 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(409)
      }
    })
  })

  it('should update a pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.updatePipeline(2, {
        description: 'Updated HDR description',
        change_summary: 'Updated description',
      })
    })

    // Refetch to see the update
    await act(async () => {
      await result.current.refetch()
    })

    const updated = result.current.pipelines.find((p) => p.id === 2)
    expect(updated?.description).toBe('Updated HDR description')
  })

  it('should delete a pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.pipelines.length
    const pipelineToDelete = result.current.pipelines.find((p) => !p.is_active)

    await act(async () => {
      await result.current.deletePipeline(pipelineToDelete!.id)
    })

    // Refetch to see the deletion
    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.pipelines.length).toBeLessThan(initialCount)
  })

  it('should fail to delete active pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const activePipeline = result.current.pipelines.find((p) => p.is_active)

    await act(async () => {
      try {
        await result.current.deletePipeline(activePipeline!.id)
        expect.fail('Should have thrown 409 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(409)
      }
    })
  })

  it('should activate a pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Find a valid but inactive pipeline
    const inactivePipeline = result.current.pipelines.find((p) => !p.is_active && p.is_valid)

    await act(async () => {
      await result.current.activatePipeline(inactivePipeline!.id)
    })

    // Refetch to see the activation
    await act(async () => {
      await result.current.refetch()
    })

    const activated = result.current.pipelines.find((p) => p.id === inactivePipeline!.id)
    expect(activated?.is_active).toBe(true)
  })

  it('should fail to activate invalid pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const invalidPipeline = result.current.pipelines.find((p) => !p.is_valid)

    await act(async () => {
      try {
        await result.current.activatePipeline(invalidPipeline!.id)
        expect.fail('Should have thrown 400 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(400)
      }
    })
  })

  it('should deactivate a pipeline', async () => {
    const { result } = renderHook(() => usePipelines({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const activePipeline = result.current.pipelines.find((p) => p.is_active)

    await act(async () => {
      await result.current.deactivatePipeline(activePipeline!.id)
    })

    // Refetch to see the deactivation
    await act(async () => {
      await result.current.refetch()
    })

    const deactivated = result.current.pipelines.find((p) => p.id === activePipeline!.id)
    expect(deactivated?.is_active).toBe(false)
  })
})

describe('usePipeline', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch single pipeline by ID', async () => {
    const { result } = renderHook(() => usePipeline(1))

    // Initially loading
    expect(result.current.loading).toBe(true)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.pipeline).toBeDefined()
    expect(result.current.pipeline?.id).toBe(1)
    expect(result.current.pipeline?.name).toBe('Standard RAW Workflow')
    expect(result.current.error).toBe(null)
  })

  it('should handle null pipelineId', async () => {
    const { result } = renderHook(() => usePipeline(null))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.pipeline).toBe(null)
  })

  it('should handle non-existent pipeline', async () => {
    const { result } = renderHook(() => usePipeline(999))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBeTruthy()
    expect(result.current.pipeline).toBe(null)
  })

  it('should include full pipeline details including nodes and edges', async () => {
    const { result } = renderHook(() => usePipeline(1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.pipeline?.nodes).toBeDefined()
    expect(result.current.pipeline?.nodes.length).toBeGreaterThan(0)
    expect(result.current.pipeline?.edges).toBeDefined()
  })

  it('should validate a pipeline', async () => {
    const { result } = renderHook(() => usePipeline(1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      const validationResult = await result.current.validate()
      expect(validationResult.is_valid).toBe(true)
      expect(validationResult.errors).toHaveLength(0)
    })
  })

  it('should get validation errors for invalid pipeline', async () => {
    const { result } = renderHook(() => usePipeline(3))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      const validationResult = await result.current.validate()
      expect(validationResult.is_valid).toBe(false)
      expect(validationResult.errors.length).toBeGreaterThan(0)
    })
  })

  it('should preview filenames for valid pipeline', async () => {
    const { result } = renderHook(() => usePipeline(1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      const preview = await result.current.preview({ camera_id: 'AB3D', counter: '0001' })
      expect(preview.base_filename).toBe('AB3D0001')
      expect(preview.expected_files.length).toBeGreaterThan(0)
    })
  })

  it('should fail to preview invalid pipeline', async () => {
    const { result } = renderHook(() => usePipeline(3))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.preview({ camera_id: 'AB3D', counter: '0001' })
        expect.fail('Should have thrown 400 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(400)
      }
    })
  })

  it('should get pipeline history', async () => {
    const { result } = renderHook(() => usePipeline(2))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      const history = await result.current.getHistory()
      expect(history.length).toBeGreaterThan(0)
      expect(history[0].version).toBeDefined()
    })
  })
})

describe('usePipelineStats', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch pipeline stats on mount', async () => {
    const { result } = renderHook(() => usePipelineStats(true))

    // Initially loading
    expect(result.current.loading).toBe(true)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toBeDefined()
    expect(result.current.stats?.total_pipelines).toBe(3)
    expect(result.current.stats?.valid_pipelines).toBe(2)
    expect(result.current.stats?.default_pipeline_id).toBe(1)
    expect(result.current.stats?.active_pipeline_count).toBe(1)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => usePipelineStats(false))

    expect(result.current.stats).toBe(null)
    expect(result.current.loading).toBe(false)
  })

  it('should include default pipeline name', async () => {
    const { result } = renderHook(() => usePipelineStats(true))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats?.default_pipeline_name).toBe('Standard RAW Workflow')
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => usePipelineStats(false))

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toBeDefined()
  })
})
