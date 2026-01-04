import { http, HttpResponse } from 'msw'
import type { Connector } from '@/contracts/api/connector-api'
import type { Collection } from '@/contracts/api/collection-api'
import type { JobResponse, JobStatus, ToolType, QueueStatusResponse } from '@/contracts/api/tools-api'
import type { AnalysisResult, AnalysisResultSummary, ResultStatsResponse } from '@/contracts/api/results-api'

// Mock data
let jobs: JobResponse[] = []
let nextJobId = 1

let results: AnalysisResult[] = [
  {
    id: 1,
    collection_id: 1,
    collection_name: 'Test Collection',
    tool: 'photostats',
    pipeline_id: null,
    pipeline_name: null,
    status: 'COMPLETED',
    started_at: '2025-01-01T10:00:00Z',
    completed_at: '2025-01-01T10:05:00Z',
    duration_seconds: 300,
    files_scanned: 1000,
    issues_found: 5,
    error_message: null,
    has_report: true,
    results: {
      total_files: 1000,
      total_size: 5000000000,
      file_counts: { '.jpg': 800, '.cr3': 200 },
      orphaned_images: ['orphan1.jpg', 'orphan2.jpg'],
      orphaned_xmp: ['orphan1.xmp', 'orphan2.xmp', 'orphan3.xmp'],
    },
    created_at: '2025-01-01T10:00:00Z',
  },
  {
    id: 2,
    collection_id: 1,
    collection_name: 'Test Collection',
    tool: 'photo_pairing',
    pipeline_id: null,
    pipeline_name: null,
    status: 'COMPLETED',
    started_at: '2025-01-01T11:00:00Z',
    completed_at: '2025-01-01T11:03:00Z',
    duration_seconds: 180,
    files_scanned: 800,
    issues_found: 2,
    error_message: null,
    has_report: true,
    results: {
      group_count: 400,
      image_count: 800,
      camera_usage: {
        'ABC1': { name: 'Canon EOS R5', image_count: 500, group_count: 250, serial_number: '12345' },
        'XYZ2': { name: 'Sony A7R', image_count: 300, group_count: 150, serial_number: '67890' },
      },
    },
    created_at: '2025-01-01T11:00:00Z',
  },
  {
    id: 3,
    collection_id: 2,
    collection_name: 'Remote S3 Collection',
    tool: 'photostats',
    pipeline_id: null,
    pipeline_name: null,
    status: 'FAILED',
    started_at: '2025-01-01T12:00:00Z',
    completed_at: '2025-01-01T12:00:30Z',
    duration_seconds: 30,
    files_scanned: 0,
    issues_found: 0,
    error_message: 'Connection timeout to S3 bucket',
    has_report: false,
    results: {},
    created_at: '2025-01-01T12:00:00Z',
  },
]
let nextResultId = 4

let connectors: Connector[] = [
  {
    id: 1,
    name: 'Test S3 Connector',
    type: 's3',
    is_active: true,
    last_validated: '2025-01-01T10:00:00Z',
    last_error: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T10:00:00Z',
  },
  {
    id: 2,
    name: 'Test GCS Connector',
    type: 'gcs',
    is_active: false,
    last_validated: null,
    last_error: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
]

let collections: Collection[] = [
  {
    id: 1,
    name: 'Test Collection',
    type: 'local',
    location: '/photos',
    state: 'live',
    connector_id: null,
    cache_ttl: 3600,
    is_accessible: true,
    accessibility_message: null,
    last_scanned_at: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
  {
    id: 2,
    name: 'Remote S3 Collection',
    type: 's3',
    location: 'my-bucket/photos',
    state: 'closed',
    connector_id: 1,
    cache_ttl: 86400,
    is_accessible: true,
    accessibility_message: null,
    last_scanned_at: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
]

let nextConnectorId = 3
let nextCollectionId = 3

const BASE_URL = 'http://localhost:8000/api'

export const handlers = [
  // Version endpoint
  http.get(`${BASE_URL}/version`, () => {
    return HttpResponse.json({ version: 'v1.0.0' })
  }),

  // Connectors endpoints
  http.get(`${BASE_URL}/connectors`, () => {
    return HttpResponse.json(connectors)
  }),

  http.get(`${BASE_URL}/connectors/:id`, ({ params }) => {
    const connector = connectors.find((c) => c.id === Number(params.id))
    if (!connector) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(connector)
  }),

  http.post(`${BASE_URL}/connectors`, async ({ request }) => {
    const data = await request.json() as Partial<Connector>
    const newConnector: Connector = {
      id: nextConnectorId++,
      name: data.name!,
      type: data.type!,
      is_active: data.is_active ?? true,
      last_validated: null,
      last_error: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    connectors.push(newConnector)
    return HttpResponse.json(newConnector, { status: 201 })
  }),

  http.put(`${BASE_URL}/connectors/:id`, async ({ params, request }) => {
    const data = await request.json() as Partial<Connector>
    const index = connectors.findIndex((c) => c.id === Number(params.id))
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    connectors[index] = {
      ...connectors[index],
      ...data,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(connectors[index])
  }),

  http.delete(`${BASE_URL}/connectors/:id`, ({ params }) => {
    const id = Number(params.id)
    // Check if connector is referenced by collections (delete protection)
    const referencedBy = collections.filter((c) => c.connector_id === id)
    if (referencedBy.length > 0) {
      return HttpResponse.json(
        { detail: `Connector is referenced by ${referencedBy.length} collection(s)` },
        { status: 409 }
      )
    }
    const index = connectors.findIndex((c) => c.id === id)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    connectors.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${BASE_URL}/connectors/:id/test`, ({ params }) => {
    const connector = connectors.find((c) => c.id === Number(params.id))
    if (!connector) {
      return new HttpResponse(null, { status: 404 })
    }
    // Update last_validated
    const index = connectors.findIndex((c) => c.id === Number(params.id))
    connectors[index] = {
      ...connectors[index],
      last_validated: new Date().toISOString(),
    }
    return HttpResponse.json({ success: true, message: 'Connection successful' })
  }),

  // Collections endpoints
  http.get(`${BASE_URL}/collections`, () => {
    return HttpResponse.json(collections)
  }),

  http.get(`${BASE_URL}/collections/:id`, ({ params }) => {
    const collection = collections.find((c) => c.id === Number(params.id))
    if (!collection) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(collection)
  }),

  http.post(`${BASE_URL}/collections`, async ({ request }) => {
    const data = await request.json() as Partial<Collection>
    // Validate connector exists for remote collections
    if (['s3', 'gcs', 'smb'].includes(data.type!) && data.connector_id) {
      const connector = connectors.find((c) => c.id === data.connector_id)
      if (!connector) {
        return HttpResponse.json(
          { detail: 'Connector not found' },
          { status: 404 }
        )
      }
    }
    const newCollection: Collection = {
      id: nextCollectionId++,
      name: data.name!,
      type: data.type!,
      location: data.location!,
      state: data.state!,
      connector_id: data.connector_id ?? null,
      cache_ttl: data.cache_ttl ?? null,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    collections.push(newCollection)
    return HttpResponse.json(newCollection, { status: 201 })
  }),

  http.put(`${BASE_URL}/collections/:id`, async ({ params, request }) => {
    const data = await request.json() as Partial<Collection>
    const index = collections.findIndex((c) => c.id === Number(params.id))
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    collections[index] = {
      ...collections[index],
      ...data,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(collections[index])
  }),

  http.delete(`${BASE_URL}/collections/:id`, ({ params, request }) => {
    const url = new URL(request.url)
    const forceDelete = url.searchParams.get('force_delete') === 'true'
    const id = Number(params.id)

    const index = collections.findIndex((c) => c.id === id)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }

    // Simulate delete protection check (would normally check for results/jobs)
    if (!forceDelete) {
      // For testing, collection ID 2 has results
      if (id === 2) {
        return HttpResponse.json(
          {
            has_results: true,
            result_count: 5,
            has_jobs: false,
            job_count: 0,
          },
          { status: 200 }
        )
      }
    }

    collections.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${BASE_URL}/collections/:id/test`, ({ params }) => {
    const collection = collections.find((c) => c.id === Number(params.id))
    if (!collection) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json({ success: true, message: 'Collection is accessible' })
  }),

  http.post(`${BASE_URL}/collections/:id/refresh`, ({ params, request }) => {
    const url = new URL(request.url)
    const confirm = url.searchParams.get('confirm') === 'true'
    const collection = collections.find((c) => c.id === Number(params.id))
    if (!collection) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json({
      message: confirm ? 'Force refresh initiated' : 'Refresh initiated',
      task_id: 'mock-task-123',
    })
  }),

  // Collection stats endpoint
  http.get(`${BASE_URL}/collections/stats`, () => {
    return HttpResponse.json({
      total_collections: collections.length,
      storage_used_bytes: 5000000000,
      storage_used_formatted: '4.66 GB',
      file_count: 1000,
      image_count: 800,
    })
  }),

  // ============================================================================
  // Tools API endpoints
  // ============================================================================

  http.post(`${BASE_URL}/tools/run`, async ({ request }) => {
    const data = await request.json() as { collection_id: number; tool: ToolType; pipeline_id?: number }

    // Check if collection exists and is accessible
    const collection = collections.find((c) => c.id === data.collection_id)
    if (!collection) {
      return HttpResponse.json(
        { detail: `Collection ${data.collection_id} not found` },
        { status: 400 }
      )
    }
    if (!collection.is_accessible) {
      return HttpResponse.json(
        {
          detail: {
            message: `Collection '${collection.name}' is not accessible.`,
            collection_id: collection.id,
            collection_name: collection.name,
          }
        },
        { status: 422 }
      )
    }

    // Check for duplicate job
    const existingJob = jobs.find(
      (j) => j.collection_id === data.collection_id && j.tool === data.tool &&
             (j.status === 'QUEUED' || j.status === 'RUNNING')
    )
    if (existingJob) {
      return HttpResponse.json(
        {
          detail: {
            message: `Tool ${data.tool} is already running on collection ${data.collection_id}`,
            existing_job_id: existingJob.id,
          }
        },
        { status: 409 }
      )
    }

    const newJob: JobResponse = {
      id: `job-${nextJobId++}`,
      collection_id: data.collection_id,
      tool: data.tool,
      pipeline_id: data.pipeline_id ?? null,
      status: 'QUEUED',
      position: jobs.filter((j) => j.status === 'QUEUED').length + 1,
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
      progress: null,
    }
    jobs.push(newJob)
    return HttpResponse.json(newJob, { status: 202 })
  }),

  http.get(`${BASE_URL}/tools/jobs`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status') as JobStatus | null

    let filteredJobs = jobs
    if (status) {
      filteredJobs = jobs.filter((j) => j.status === status)
    }
    return HttpResponse.json(filteredJobs)
  }),

  http.get(`${BASE_URL}/tools/jobs/:id`, ({ params }) => {
    const job = jobs.find((j) => j.id === params.id)
    if (!job) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(job)
  }),

  http.post(`${BASE_URL}/tools/jobs/:id/cancel`, ({ params }) => {
    const job = jobs.find((j) => j.id === params.id)
    if (!job) {
      return new HttpResponse(null, { status: 404 })
    }
    if (job.status !== 'QUEUED') {
      return HttpResponse.json(
        { detail: 'Only queued jobs can be cancelled' },
        { status: 400 }
      )
    }
    job.status = 'CANCELLED'
    job.completed_at = new Date().toISOString()
    return HttpResponse.json(job)
  }),

  http.get(`${BASE_URL}/tools/queue/status`, () => {
    const queueStatus: QueueStatusResponse = {
      queued_count: jobs.filter((j) => j.status === 'QUEUED').length,
      running_count: jobs.filter((j) => j.status === 'RUNNING').length,
      completed_count: jobs.filter((j) => j.status === 'COMPLETED').length,
      failed_count: jobs.filter((j) => j.status === 'FAILED').length,
      cancelled_count: jobs.filter((j) => j.status === 'CANCELLED').length,
      current_job_id: jobs.find((j) => j.status === 'RUNNING')?.id ?? null,
    }
    return HttpResponse.json(queueStatus)
  }),

  // ============================================================================
  // Results API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/results`, ({ request }) => {
    const url = new URL(request.url)
    const collectionId = url.searchParams.get('collection_id')
    const tool = url.searchParams.get('tool')
    const status = url.searchParams.get('status')
    const limit = parseInt(url.searchParams.get('limit') ?? '50', 10)
    const offset = parseInt(url.searchParams.get('offset') ?? '0', 10)

    let filteredResults = [...results]
    if (collectionId) {
      filteredResults = filteredResults.filter((r) => r.collection_id === Number(collectionId))
    }
    if (tool) {
      filteredResults = filteredResults.filter((r) => r.tool === tool)
    }
    if (status) {
      filteredResults = filteredResults.filter((r) => r.status === status)
    }

    const total = filteredResults.length
    const items: AnalysisResultSummary[] = filteredResults
      .slice(offset, offset + limit)
      .map((r) => ({
        id: r.id,
        collection_id: r.collection_id,
        collection_name: r.collection_name,
        tool: r.tool,
        status: r.status,
        started_at: r.started_at,
        completed_at: r.completed_at,
        duration_seconds: r.duration_seconds,
        files_scanned: r.files_scanned,
        issues_found: r.issues_found,
        has_report: r.has_report,
      }))

    return HttpResponse.json({ items, total, limit, offset })
  }),

  http.get(`${BASE_URL}/results/stats`, () => {
    const stats: ResultStatsResponse = {
      total_results: results.length,
      completed_count: results.filter((r) => r.status === 'COMPLETED').length,
      failed_count: results.filter((r) => r.status === 'FAILED').length,
      by_tool: {
        photostats: results.filter((r) => r.tool === 'photostats').length,
        photo_pairing: results.filter((r) => r.tool === 'photo_pairing').length,
        pipeline_validation: results.filter((r) => r.tool === 'pipeline_validation').length,
      },
      last_run: results.length > 0 ? results[results.length - 1].completed_at : null,
    }
    return HttpResponse.json(stats)
  }),

  http.get(`${BASE_URL}/results/:id`, ({ params }) => {
    const result = results.find((r) => r.id === Number(params.id))
    if (!result) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(result)
  }),

  http.delete(`${BASE_URL}/results/:id`, ({ params }) => {
    const index = results.findIndex((r) => r.id === Number(params.id))
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    const deletedId = results[index].id
    results.splice(index, 1)
    return HttpResponse.json({ message: 'Result deleted successfully', deleted_id: deletedId })
  }),

  http.get(`${BASE_URL}/results/:id/report`, ({ params }) => {
    const result = results.find((r) => r.id === Number(params.id))
    if (!result) {
      return new HttpResponse(null, { status: 404 })
    }
    if (!result.has_report) {
      return HttpResponse.json(
        { detail: `Report for result ${params.id} not found` },
        { status: 404 }
      )
    }
    const filename = `${result.tool}_report_${result.collection_name}_${result.collection_id}_2025-01-01_10-00-00.html`
    return new HttpResponse('<html><body>Mock Report</body></html>', {
      headers: {
        'Content-Type': 'text/html',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })
  }),
]

// Helper to reset mock data (useful for tests)
export function resetMockData(): void {
  connectors = [
    {
      id: 1,
      name: 'Test S3 Connector',
      type: 's3',
      is_active: true,
      last_validated: '2025-01-01T10:00:00Z',
      last_error: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T10:00:00Z',
    },
    {
      id: 2,
      name: 'Test GCS Connector',
      type: 'gcs',
      is_active: false,
      last_validated: null,
      last_error: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ]
  collections = [
    {
      id: 1,
      name: 'Test Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
      connector_id: null,
      cache_ttl: 3600,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      id: 2,
      name: 'Remote S3 Collection',
      type: 's3',
      location: 'my-bucket/photos',
      state: 'closed',
      connector_id: 1,
      cache_ttl: 86400,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ]
  jobs = []
  results = [
    {
      id: 1,
      collection_id: 1,
      collection_name: 'Test Collection',
      tool: 'photostats',
      pipeline_id: null,
      pipeline_name: null,
      status: 'COMPLETED',
      started_at: '2025-01-01T10:00:00Z',
      completed_at: '2025-01-01T10:05:00Z',
      duration_seconds: 300,
      files_scanned: 1000,
      issues_found: 5,
      error_message: null,
      has_report: true,
      results: {
        total_files: 1000,
        total_size: 5000000000,
        file_counts: { '.jpg': 800, '.cr3': 200 },
        orphaned_images: ['orphan1.jpg', 'orphan2.jpg'],
        orphaned_xmp: ['orphan1.xmp', 'orphan2.xmp', 'orphan3.xmp'],
      },
      created_at: '2025-01-01T10:00:00Z',
    },
    {
      id: 2,
      collection_id: 1,
      collection_name: 'Test Collection',
      tool: 'photo_pairing',
      pipeline_id: null,
      pipeline_name: null,
      status: 'COMPLETED',
      started_at: '2025-01-01T11:00:00Z',
      completed_at: '2025-01-01T11:03:00Z',
      duration_seconds: 180,
      files_scanned: 800,
      issues_found: 2,
      error_message: null,
      has_report: true,
      results: {
        group_count: 400,
        image_count: 800,
        camera_usage: {
          'ABC1': { name: 'Canon EOS R5', image_count: 500, group_count: 250, serial_number: '12345' },
          'XYZ2': { name: 'Sony A7R', image_count: 300, group_count: 150, serial_number: '67890' },
        },
      },
      created_at: '2025-01-01T11:00:00Z',
    },
    {
      id: 3,
      collection_id: 2,
      collection_name: 'Remote S3 Collection',
      tool: 'photostats',
      pipeline_id: null,
      pipeline_name: null,
      status: 'FAILED',
      started_at: '2025-01-01T12:00:00Z',
      completed_at: '2025-01-01T12:00:30Z',
      duration_seconds: 30,
      files_scanned: 0,
      issues_found: 0,
      error_message: 'Connection timeout to S3 bucket',
      has_report: false,
      results: {},
      created_at: '2025-01-01T12:00:00Z',
    },
  ]
  nextConnectorId = 3
  nextCollectionId = 3
  nextJobId = 1
  nextResultId = 4
}
