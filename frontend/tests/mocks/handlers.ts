import { http, HttpResponse, ws } from 'msw'
import type { Connector } from '@/contracts/api/connector-api'
import type { Collection } from '@/contracts/api/collection-api'
import type { JobResponse, JobStatus, ToolType, ToolMode, QueueStatusResponse, ToolRunRequest } from '@/contracts/api/tools-api'
import type { AnalysisResult, AnalysisResultSummary, ResultStatsResponse } from '@/contracts/api/results-api'
import type { Pipeline, PipelineSummary, PipelineStatsResponse, ValidationResult, PipelineHistoryEntry, FilenamePreviewResponse } from '@/contracts/api/pipelines-api'
import type {
  PhotoStatsTrendResponse,
  PhotoPairingTrendResponse,
  PipelineValidationTrendResponse,
  DisplayGraphTrendResponse,
  TrendSummaryResponse
} from '@/contracts/api/trends-api'
import type {
  ConfigurationResponse,
  CategoryConfigResponse,
  ConfigValueResponse,
  ConfigStatsResponse,
  ImportSessionResponse,
  ImportResultResponse,
  ConfigCategory,
  ConfigItem
} from '@/contracts/api/config-api'
import type {
  Category,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  CategoryStatsResponse
} from '@/contracts/api/category-api'
import type {
  Event,
  EventDetail,
  EventStatsResponse
} from '@/contracts/api/event-api'
import type {
  Location,
  LocationCreateRequest,
  LocationUpdateRequest,
  LocationStatsResponse,
  GeocodeResponse
} from '@/contracts/api/location-api'
import type {
  Performer,
  PerformerCreateRequest,
  PerformerUpdateRequest,
  PerformerStatsResponse
} from '@/contracts/api/performer-api'
import type {
  Organizer,
  OrganizerCreateRequest,
  OrganizerUpdateRequest,
  OrganizerStatsResponse
} from '@/contracts/api/organizer-api'

// Mock data
let jobs: JobResponse[] = []
let nextJobNum = 1

// Helper to generate job GUIDs in proper format
function generateJobGuid(): string {
  const num = nextJobNum++
  // Pad to 26 chars with the format job_01hgw2bbg0000000000000000X
  // Base: 01hgw2bbg = 9 chars, then 17 zeros/digits to reach 26 total
  const paddedNum = String(num).padStart(1, '0')
  return `job_01hgw2bbg0000000000000000${paddedNum}`
}

let pipelines: Pipeline[] = [
  {
    guid: 'pip_01hgw2bbg00000000000000001',
    name: 'Standard RAW Workflow',
    description: 'RAW capture to processed TIFF export',
    nodes: [
      { id: 'capture', type: 'capture', properties: { camera_id_pattern: '[A-Z0-9]{4}' } },
      { id: 'raw', type: 'file', properties: { extension: '.dng' } },
      { id: 'xmp', type: 'file', properties: { extension: '.xmp' } },
      { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
    ],
    edges: [
      { from: 'capture', to: 'raw' },
      { from: 'capture', to: 'xmp' },
      { from: 'raw', to: 'done' },
    ],
    version: 1,
    is_active: true,
    is_default: true,
    is_valid: true,
    validation_errors: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
  {
    guid: 'pip_01hgw2bbg00000000000000002',
    name: 'HDR Workflow',
    description: 'HDR processing pipeline',
    nodes: [
      { id: 'capture', type: 'capture', properties: { camera_id_pattern: '[A-Z0-9]{4}' } },
      { id: 'raw', type: 'file', properties: { extension: '.cr3' } },
      { id: 'hdr', type: 'process', properties: { suffix: '-HDR' } },
      { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
    ],
    edges: [
      { from: 'capture', to: 'raw' },
      { from: 'raw', to: 'hdr' },
      { from: 'hdr', to: 'done' },
    ],
    version: 2,
    is_active: false,
    is_default: false,
    is_valid: true,
    validation_errors: null,
    created_at: '2025-01-01T10:00:00Z',
    updated_at: '2025-01-01T11:00:00Z',
  },
  {
    guid: 'pip_01hgw2bbg00000000000000003',
    name: 'Invalid Pipeline',
    description: 'Pipeline with validation errors',
    nodes: [
      { id: 'capture', type: 'capture', properties: {} },
      { id: 'orphan', type: 'file', properties: { extension: '.dng' } },
    ],
    edges: [],
    version: 1,
    is_active: false,
    is_default: false,
    is_valid: false,
    validation_errors: ['Orphaned node: orphan'],
    created_at: '2025-01-01T12:00:00Z',
    updated_at: '2025-01-01T12:00:00Z',
  },
]
let nextPipelineId = 4

let pipelineHistory: PipelineHistoryEntry[] = [
  {
    version: 1,
    change_summary: 'Initial version',
    changed_by: null,
    created_at: '2025-01-01T10:00:00Z',
  },
  {
    version: 2,
    change_summary: 'Updated HDR settings',
    changed_by: null,
    created_at: '2025-01-01T11:00:00Z',
  },
]

let results: AnalysisResult[] = [
  {
    guid: 'res_01hgw2bbg00000000000000001',
    external_id: 'res_01hgw2bbg00000000000000001',
    collection_guid: 'col_01hgw2bbg00000000000000001',
    collection_name: 'Test Collection',
    tool: 'photostats',
    pipeline_guid: null,
    pipeline_version: null,
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
    guid: 'res_01hgw2bbg00000000000000002',
    external_id: 'res_01hgw2bbg00000000000000002',
    collection_guid: 'col_01hgw2bbg00000000000000001',
    collection_name: 'Test Collection',
    tool: 'photo_pairing',
    pipeline_guid: null,
    pipeline_version: null,
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
    guid: 'res_01hgw2bbg00000000000000003',
    external_id: 'res_01hgw2bbg00000000000000003',
    collection_guid: 'col_01hgw2bbg00000000000000002',
    collection_name: 'Remote S3 Collection',
    tool: 'photostats',
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    status: 'FAILED',
    started_at: '2025-01-01T12:00:00Z',
    completed_at: '2025-01-01T12:00:30Z',
    duration_seconds: 30,
    files_scanned: 0,
    issues_found: 0,
    error_message: 'Connection timeout to S3 bucket',
    has_report: false,
    results: {
      total_size: 0,
      total_files: 0,
      file_counts: {},
      orphaned_images: [],
      orphaned_xmp: [],
    },
    created_at: '2025-01-01T12:00:00Z',
  },
  {
    guid: 'res_01hgw2bbg00000000000000004',
    external_id: 'res_01hgw2bbg00000000000000004',
    collection_guid: 'col_01hgw2bbg00000000000000002',
    collection_name: 'Remote S3 Collection',
    tool: 'pipeline_validation',
    pipeline_guid: 'pip_01hgw2bbg00000000000000001',
    pipeline_version: 1,
    pipeline_name: 'Standard RAW Workflow',
    status: 'COMPLETED',
    started_at: '2025-01-01T13:00:00Z',
    completed_at: '2025-01-01T13:05:00Z',
    duration_seconds: 300,
    files_scanned: 500,
    issues_found: 3,
    error_message: null,
    has_report: true,
    results: {
      consistency_counts: { CONSISTENT: 400, PARTIAL: 50, INCONSISTENT: 50 },
    },
    created_at: '2025-01-01T13:00:00Z',
  },
]
let nextResultId = 5

let connectors: Connector[] = [
  {
    guid: 'con_01hgw2bbg00000000000000001',
    name: 'Test S3 Connector',
    type: 's3',
    is_active: true,
    last_validated: '2025-01-01T10:00:00Z',
    last_error: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T10:00:00Z',
  },
  {
    guid: 'con_01hgw2bbg00000000000000002',
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
    guid: 'col_01hgw2bbg00000000000000001',
    name: 'Test Collection',
    type: 'local',
    location: '/photos',
    state: 'live',
    connector_guid: null,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    cache_ttl: 3600,
    is_accessible: true,
    accessibility_message: null,
    last_scanned_at: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
  {
    guid: 'col_01hgw2bbg00000000000000002',
    name: 'Remote S3 Collection',
    type: 's3',
    location: 'my-bucket/photos',
    state: 'closed',
    connector_guid: 'con_01hgw2bbg00000000000000001',
    pipeline_guid: 'pip_01hgw2bbg00000000000000001',
    pipeline_version: 1,
    pipeline_name: 'Standard RAW Workflow',
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

// Category mock data
let categories: Category[] = [
  {
    guid: 'cat_01hgw2bbg00000000000000001',
    name: 'Airshow',
    icon: 'plane',
    color: '#3B82F6',
    display_order: 0,
    is_active: true,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
  {
    guid: 'cat_01hgw2bbg00000000000000002',
    name: 'Wildlife',
    icon: 'bird',
    color: '#22C55E',
    display_order: 1,
    is_active: true,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
  {
    guid: 'cat_01hgw2bbg00000000000000003',
    name: 'Wedding',
    icon: 'heart',
    color: '#EC4899',
    display_order: 2,
    is_active: false,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
]
let nextCategoryNum = 4

// Events mock data
let events: Event[] = [
  {
    guid: 'evt_01hgw2bbg00000000000000001',
    title: 'Oshkosh Airshow Day 1',
    event_date: '2026-07-27',
    start_time: '08:00:00',
    end_time: '18:00:00',
    is_all_day: false,
    input_timezone: 'America/Chicago',
    status: 'future',
    attendance: 'planned',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
    },
    location: null,
    series_guid: 'ser_01hgw2bbg00000000000000001',
    sequence_number: 1,
    series_total: 3,
    ticket_required: true,
    ticket_status: 'purchased',
    timeoff_required: true,
    timeoff_status: 'approved',
    travel_required: true,
    travel_status: 'booked',
    is_deadline: false,
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  },
  {
    guid: 'evt_01hgw2bbg00000000000000002',
    title: 'Oshkosh Airshow Day 2',
    event_date: '2026-07-28',
    start_time: '08:00:00',
    end_time: '18:00:00',
    is_all_day: false,
    input_timezone: 'America/Chicago',
    status: 'future',
    attendance: 'planned',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
    },
    location: null,
    series_guid: 'ser_01hgw2bbg00000000000000001',
    sequence_number: 2,
    series_total: 3,
    ticket_required: true,
    ticket_status: 'purchased',
    timeoff_required: true,
    timeoff_status: 'approved',
    travel_required: true,
    travel_status: 'booked',
    is_deadline: false,
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  },
  {
    guid: 'evt_01hgw2bbg00000000000000003',
    title: 'Wildlife Photography Workshop',
    event_date: '2026-03-15',
    start_time: '10:00:00',
    end_time: '16:00:00',
    is_all_day: false,
    input_timezone: 'America/New_York',
    status: 'future',
    attendance: 'planned',
    category: {
      guid: 'cat_01hgw2bbg00000000000000002',
      name: 'Wildlife',
      icon: 'bird',
      color: '#22C55E',
    },
    location: null,
    series_guid: null,
    sequence_number: null,
    series_total: null,
    ticket_required: false,
    ticket_status: null,
    timeoff_required: false,
    timeoff_status: null,
    travel_required: false,
    travel_status: null,
    is_deadline: false,
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  },
]
let nextEventNum = 4

// Locations mock data
let locations: Location[] = [
  {
    guid: 'loc_01hgw2bbg00000000000000001',
    name: 'EAA Grounds',
    address: '3000 Poberezny Road',
    city: 'Oshkosh',
    state: 'Wisconsin',
    country: 'USA',
    postal_code: '54902',
    latitude: 43.9844,
    longitude: -88.5564,
    timezone: 'America/Chicago',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
    },
    rating: 5,
    timeoff_required_default: true,
    travel_required_default: true,
    notes: 'Annual EAA AirVenture event location',
    is_known: true,
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  },
  {
    guid: 'loc_01hgw2bbg00000000000000002',
    name: 'Yellowstone National Park',
    address: null,
    city: 'Yellowstone',
    state: 'Wyoming',
    country: 'USA',
    postal_code: null,
    latitude: 44.4280,
    longitude: -110.5885,
    timezone: 'America/Denver',
    category: {
      guid: 'cat_01hgw2bbg00000000000000002',
      name: 'Wildlife',
      icon: 'bird',
      color: '#22C55E',
    },
    rating: 5,
    timeoff_required_default: true,
    travel_required_default: true,
    notes: 'Great for wildlife photography',
    is_known: true,
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  },
]
let nextLocationNum = 3

// Performer mock data
let performers: Performer[] = [
  {
    guid: 'prf_01hgw2bbg00000000000000001',
    name: 'Blue Angels',
    website: 'https://blueangels.navy.mil',
    instagram_handle: 'usabordo_blueangels',
    instagram_url: 'https://instagram.com/usabordo_blueangels',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
    },
    additional_info: 'US Navy Flight Demonstration Squadron',
    created_at: '2026-01-10T09:00:00Z',
    updated_at: '2026-01-10T09:00:00Z',
  },
  {
    guid: 'prf_01hgw2bbg00000000000000002',
    name: 'Thunderbirds',
    website: 'https://thunderbirds.airforce.com',
    instagram_handle: 'afthunderbirds',
    instagram_url: 'https://instagram.com/afthunderbirds',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
    },
    additional_info: 'US Air Force Air Demonstration Squadron',
    created_at: '2026-01-10T09:00:00Z',
    updated_at: '2026-01-10T09:00:00Z',
  },
  {
    guid: 'prf_01hgw2bbg00000000000000003',
    name: 'Wildlife Photography Guide',
    website: null,
    instagram_handle: null,
    instagram_url: null,
    category: {
      guid: 'cat_01hgw2bbg00000000000000002',
      name: 'Wildlife',
      icon: 'bird',
      color: '#22C55E',
    },
    additional_info: 'Expert wildlife guide',
    created_at: '2026-01-10T09:00:00Z',
    updated_at: '2026-01-10T09:00:00Z',
  },
]
let nextPerformerNum = 4

// Organizers mock data
let organizers: Organizer[] = [
  {
    guid: 'org_01hgw2bbg00000000000000001',
    name: 'USAF Demonstration Teams',
    website: 'https://usaf.com/demo',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
    },
    rating: 5,
    ticket_required_default: true,
    notes: 'Military demonstration team organizer',
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  },
  {
    guid: 'org_01hgw2bbg00000000000000002',
    name: 'National Wildlife Federation',
    website: 'https://nwf.org',
    category: {
      guid: 'cat_01hgw2bbg00000000000000002',
      name: 'Wildlife',
      icon: 'bird',
      color: '#22C55E',
    },
    rating: 4,
    ticket_required_default: false,
    notes: 'Conservation organization',
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
  },
]
let nextOrganizerNum = 3

// Config mock data
let configData = {
  extensions: {
    photo_extensions: ['.dng', '.cr3', '.arw'],
    metadata_extensions: ['.xmp'],
    require_sidecar: ['.cr3'],
  },
  cameras: {
    'AB3D': { name: 'Canon EOS R5', serial_number: '12345' },
    'XY7Z': { name: 'Sony A7R IV', serial_number: '67890' },
  } as Record<string, { name: string; serial_number: string }>,
  processing_methods: {
    'HDR': 'High Dynamic Range',
    'BW': 'Black and White',
  } as Record<string, string>,
  event_statuses: {
    'future': { label: 'Future', display_order: 0 },
    'confirmed': { label: 'Confirmed', display_order: 1 },
    'completed': { label: 'Completed', display_order: 2 },
    'cancelled': { label: 'Cancelled', display_order: 3 },
  } as Record<string, { label: string; display_order: number }>,
  importSessions: {} as Record<string, ImportSessionResponse>,
  lastImport: null as string | null,
}

const BASE_URL = 'http://localhost:8000/api'

// WebSocket handler for job updates
const jobsWebSocket = ws.link('ws://localhost:8000/api/tools/ws/jobs/*')

export const handlers = [
  // WebSocket handler for all job channels
  jobsWebSocket.addEventListener('connection', ({ client }) => {
    // Send initial connection acknowledgment
    client.send(JSON.stringify({ type: 'connected', message: 'WebSocket connected' }))
  }),

  // Version endpoint
  http.get(`${BASE_URL}/version`, () => {
    return HttpResponse.json({ version: 'v1.0.0' })
  }),

  // Connectors endpoints
  http.get(`${BASE_URL}/connectors`, () => {
    return HttpResponse.json(connectors)
  }),

  http.get(`${BASE_URL}/connectors/:guid`, ({ params }) => {
    const connector = connectors.find((c) => c.guid === params.guid)
    if (!connector) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(connector)
  }),

  http.post(`${BASE_URL}/connectors`, async ({ request }) => {
    const data = await request.json() as Partial<Connector>
    const newConnector: Connector = {
      guid: `con_01hgw2bbg000000000000000${nextConnectorId++}`,
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

  http.put(`${BASE_URL}/connectors/:guid`, async ({ params, request }) => {
    const data = await request.json() as Partial<Connector>
    const index = connectors.findIndex((c) => c.guid === params.guid)
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

  http.delete(`${BASE_URL}/connectors/:guid`, ({ params }) => {
    const guid = params.guid as string
    // Check if connector is referenced by collections (delete protection)
    const referencedBy = collections.filter((c) => c.connector_guid === guid)
    if (referencedBy.length > 0) {
      return HttpResponse.json(
        { detail: `Connector is referenced by ${referencedBy.length} collection(s)` },
        { status: 409 }
      )
    }
    const index = connectors.findIndex((c) => c.guid === guid)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    connectors.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${BASE_URL}/connectors/:guid/test`, ({ params }) => {
    const connector = connectors.find((c) => c.guid === params.guid)
    if (!connector) {
      return new HttpResponse(null, { status: 404 })
    }
    // Update last_validated
    const index = connectors.findIndex((c) => c.guid === params.guid)
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

  http.get(`${BASE_URL}/collections/:guid`, ({ params }) => {
    const collection = collections.find((c) => c.guid === params.guid)
    if (!collection) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(collection)
  }),

  http.post(`${BASE_URL}/collections`, async ({ request }) => {
    const data = await request.json() as Partial<Collection>
    // Validate connector exists for remote collections
    if (['s3', 'gcs', 'smb'].includes(data.type!) && data.connector_guid) {
      const connector = connectors.find((c) => c.guid === data.connector_guid)
      if (!connector) {
        return HttpResponse.json(
          { detail: 'Connector not found' },
          { status: 404 }
        )
      }
    }
    // Look up pipeline if pipeline_guid is provided
    let pipelineGuid: string | null = null
    let pipelineVersion: number | null = null
    let pipelineName: string | null = null
    if (data.pipeline_guid) {
      const pipeline = pipelines.find((p) => p.guid === data.pipeline_guid)
      if (pipeline && pipeline.is_active) {
        pipelineGuid = pipeline.guid
        pipelineVersion = pipeline.version
        pipelineName = pipeline.name
      }
    }
    const newCollection: Collection = {
      guid: `col_01hgw2bbg000000000000000${nextCollectionId++}`,
      name: data.name!,
      type: data.type!,
      location: data.location!,
      state: data.state!,
      connector_guid: data.connector_guid ?? null,
      pipeline_guid: pipelineGuid,
      pipeline_version: pipelineVersion,
      pipeline_name: pipelineName,
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

  http.put(`${BASE_URL}/collections/:guid`, async ({ params, request }) => {
    const data = await request.json() as Partial<Collection>
    const index = collections.findIndex((c) => c.guid === params.guid)
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

  http.delete(`${BASE_URL}/collections/:guid`, ({ params, request }) => {
    const url = new URL(request.url)
    const forceDelete = url.searchParams.get('force_delete') === 'true'
    const guid = params.guid as string

    const index = collections.findIndex((c) => c.guid === guid)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }

    // Simulate delete protection check (would normally check for results/jobs)
    if (!forceDelete) {
      // For testing, collection GUID 2 has results
      if (guid === 'col_01hgw2bbg00000000000000002') {
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

  http.post(`${BASE_URL}/collections/:guid/test`, ({ params }) => {
    const collection = collections.find((c) => c.guid === params.guid)
    if (!collection) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json({ success: true, message: 'Collection is accessible' })
  }),

  http.post(`${BASE_URL}/collections/:guid/refresh`, ({ params, request }) => {
    const url = new URL(request.url)
    const confirm = url.searchParams.get('confirm') === 'true'
    const collection = collections.find((c) => c.guid === params.guid)
    if (!collection) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json({
      message: confirm ? 'Force refresh initiated' : 'Refresh initiated',
      task_id: 'mock-task-123',
    })
  }),

  http.post(`${BASE_URL}/collections/:guid/assign-pipeline`, ({ params, request }) => {
    const url = new URL(request.url)
    const pipelineGuidParam = url.searchParams.get('pipeline_guid')
    if (!pipelineGuidParam) {
      return HttpResponse.json(
        { detail: 'pipeline_guid query parameter is required' },
        { status: 400 }
      )
    }
    const collectionIndex = collections.findIndex((c) => c.guid === params.guid)
    if (collectionIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    const pipeline = pipelines.find((p) => p.guid === pipelineGuidParam)
    if (!pipeline) {
      return HttpResponse.json(
        { detail: `Pipeline ${pipelineGuidParam} not found` },
        { status: 404 }
      )
    }
    if (!pipeline.is_active) {
      return HttpResponse.json(
        { detail: `Pipeline '${pipeline.name}' is not active` },
        { status: 400 }
      )
    }
    collections[collectionIndex] = {
      ...collections[collectionIndex],
      pipeline_guid: pipeline.guid,
      pipeline_version: pipeline.version,
      pipeline_name: pipeline.name,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(collections[collectionIndex])
  }),

  http.post(`${BASE_URL}/collections/:guid/clear-pipeline`, ({ params }) => {
    const collectionIndex = collections.findIndex((c) => c.guid === params.guid)
    if (collectionIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    collections[collectionIndex] = {
      ...collections[collectionIndex],
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(collections[collectionIndex])
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
    const data = await request.json() as ToolRunRequest

    // Handle display_graph mode (pipeline validation without collection)
    if (data.mode === 'display_graph') {
      if (!data.pipeline_guid) {
        return HttpResponse.json(
          { detail: 'pipeline_guid is required for display_graph mode' },
          { status: 400 }
        )
      }

      // Look up the pipeline to get numeric ID for the Job response
      const pipeline = pipelines.find((p) => p.guid === data.pipeline_guid)
      const pipelineId = pipeline ? pipelines.indexOf(pipeline) + 1 : null

      // Check for duplicate display_graph job
      const existingJob = jobs.find(
        (j) => j.pipeline_id === pipelineId && j.mode === 'display_graph' &&
               (j.status === 'queued' || j.status === 'running')
      )
      if (existingJob) {
        return HttpResponse.json(
          {
            detail: {
              message: `Display graph already running on pipeline ${data.pipeline_guid}`,
              existing_job_id: existingJob.id,
            }
          },
          { status: 409 }
        )
      }

      const newJob: JobResponse = {
        id: generateJobGuid(),
        collection_id: null,
        tool: data.tool,
        pipeline_id: pipelineId,
        mode: 'display_graph',
        status: 'queued',
        position: jobs.filter((j) => j.status === 'queued').length + 1,
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        progress: null,
        error_message: null,
        result_id: null,
      }
      jobs.push(newJob)
      return HttpResponse.json(newJob, { status: 202 })
    }

    // Collection mode - check if collection exists and is accessible
    if (!data.collection_guid) {
      return HttpResponse.json(
        { detail: 'collection_guid is required for collection mode' },
        { status: 400 }
      )
    }

    const collection = collections.find((c) => c.guid === data.collection_guid)
    if (!collection) {
      return HttpResponse.json(
        { detail: `Collection ${data.collection_guid} not found` },
        { status: 400 }
      )
    }
    if (!collection.is_accessible) {
      return HttpResponse.json(
        {
          detail: {
            message: `Collection '${collection.name}' is not accessible.`,
            collection_guid: collection.guid,
            collection_name: collection.name,
          }
        },
        { status: 422 }
      )
    }

    // Get numeric ID for Job response
    const collectionId = collections.indexOf(collection) + 1

    // Check for duplicate job
    const existingJob = jobs.find(
      (j) => j.collection_id === collectionId && j.tool === data.tool &&
             (j.status === 'queued' || j.status === 'running')
    )
    if (existingJob) {
      return HttpResponse.json(
        {
          detail: {
            message: `Tool ${data.tool} is already running on collection ${data.collection_guid}`,
            existing_job_id: existingJob.id,
          }
        },
        { status: 409 }
      )
    }

    // Look up pipeline if provided
    const pipeline = data.pipeline_guid ? pipelines.find((p) => p.guid === data.pipeline_guid) : null
    const pipelineId = pipeline ? pipelines.indexOf(pipeline) + 1 : null

    const newJob: JobResponse = {
      id: generateJobGuid(),
      collection_id: collectionId,
      tool: data.tool,
      pipeline_id: pipelineId,
      mode: data.mode ?? null,
      status: 'queued',
      position: jobs.filter((j) => j.status === 'queued').length + 1,
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
      progress: null,
      error_message: null,
      result_id: null,
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
    if (job.status !== 'queued') {
      return HttpResponse.json(
        { detail: 'Only queued jobs can be cancelled' },
        { status: 400 }
      )
    }
    job.status = 'cancelled'
    job.completed_at = new Date().toISOString()
    return HttpResponse.json(job)
  }),

  http.get(`${BASE_URL}/tools/queue/status`, () => {
    const queueStatus: QueueStatusResponse = {
      queued_count: jobs.filter((j) => j.status === 'queued').length,
      running_count: jobs.filter((j) => j.status === 'running').length,
      completed_count: jobs.filter((j) => j.status === 'completed').length,
      failed_count: jobs.filter((j) => j.status === 'failed').length,
      cancelled_count: jobs.filter((j) => j.status === 'cancelled').length,
      current_job_id: jobs.find((j) => j.status === 'running')?.id ?? null,
    }
    return HttpResponse.json(queueStatus)
  }),

  // ============================================================================
  // Results API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/results`, ({ request }) => {
    const url = new URL(request.url)
    const collectionGuid = url.searchParams.get('collection_guid')
    const tool = url.searchParams.get('tool')
    const status = url.searchParams.get('status')
    const limit = parseInt(url.searchParams.get('limit') ?? '50', 10)
    const offset = parseInt(url.searchParams.get('offset') ?? '0', 10)

    let filteredResults = [...results]
    if (collectionGuid) {
      filteredResults = filteredResults.filter((r) => r.collection_guid === collectionGuid)
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
        guid: r.guid,
        external_id: r.external_id,
        collection_guid: r.collection_guid,
        collection_name: r.collection_name,
        tool: r.tool,
        pipeline_guid: r.pipeline_guid,
        pipeline_version: r.pipeline_version,
        pipeline_name: r.pipeline_name,
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

  http.get(`${BASE_URL}/results/:identifier`, ({ params }) => {
    // Support lookup by external ID (res_xxx) or guid
    const identifier = params.identifier as string
    const result = results.find((r) => r.guid === identifier || r.external_id === identifier)
    if (!result) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(result)
  }),

  http.delete(`${BASE_URL}/results/:identifier`, ({ params }) => {
    // Support lookup by external ID (res_xxx) or guid
    const identifier = params.identifier as string
    const index = results.findIndex((r) => r.guid === identifier || r.external_id === identifier)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    const deletedGuid = results[index].guid
    results.splice(index, 1)
    return HttpResponse.json({ message: 'Result deleted successfully', deleted_guid: deletedGuid })
  }),

  http.get(`${BASE_URL}/results/:identifier/report`, ({ params }) => {
    // Support lookup by external ID (res_xxx) or guid
    const identifier = params.identifier as string
    const result = results.find((r) => r.guid === identifier || r.external_id === identifier)
    if (!result) {
      return new HttpResponse(null, { status: 404 })
    }
    if (!result.has_report) {
      return HttpResponse.json(
        { detail: `Report for result ${identifier} not found` },
        { status: 404 }
      )
    }
    const filename = `${result.tool}_report_${result.collection_name}_${result.collection_guid}_2025-01-01_10-00-00.html`
    return new HttpResponse('<html><body>Mock Report</body></html>', {
      headers: {
        'Content-Type': 'text/html',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })
  }),

  // ============================================================================
  // Pipelines API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/pipelines`, ({ request }) => {
    const url = new URL(request.url)
    const isActive = url.searchParams.get('is_active')
    const isValid = url.searchParams.get('is_valid')

    let filteredPipelines = [...pipelines]
    if (isActive !== null) {
      filteredPipelines = filteredPipelines.filter((p) => p.is_active === (isActive === 'true'))
    }
    if (isValid !== null) {
      filteredPipelines = filteredPipelines.filter((p) => p.is_valid === (isValid === 'true'))
    }

    const items: PipelineSummary[] = filteredPipelines.map((p) => ({
      guid: p.guid,
      name: p.name,
      description: p.description,
      version: p.version,
      is_active: p.is_active,
      is_default: p.is_default,
      is_valid: p.is_valid,
      node_count: p.nodes.length,
      created_at: p.created_at,
      updated_at: p.updated_at,
    }))

    return HttpResponse.json({ items })
  }),

  http.get(`${BASE_URL}/pipelines/stats`, () => {
    const defaultPipeline = pipelines.find((p) => p.is_default)
    const stats: PipelineStatsResponse = {
      total_pipelines: pipelines.length,
      valid_pipelines: pipelines.filter((p) => p.is_valid).length,
      active_pipeline_count: pipelines.filter((p) => p.is_active).length,
      default_pipeline_guid: defaultPipeline?.guid ?? null,
      default_pipeline_name: defaultPipeline?.name ?? null,
    }
    return HttpResponse.json(stats)
  }),

  http.get(`${BASE_URL}/pipelines/:id`, ({ params }) => {
    const pipeline = pipelines.find((p) => p.guid === params.id)
    if (!pipeline) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(pipeline)
  }),

  http.post(`${BASE_URL}/pipelines`, async ({ request }) => {
    const data = await request.json() as { name: string; description?: string; nodes: Pipeline['nodes']; edges: Pipeline['edges'] }

    // Check for duplicate name
    if (pipelines.some((p) => p.name === data.name)) {
      return HttpResponse.json(
        { detail: `Pipeline with name '${data.name}' already exists` },
        { status: 409 }
      )
    }

    const newPipelineNum = nextPipelineId++
    const newPipeline: Pipeline = {
      guid: `pip_01hgw2bbg000000000000000${newPipelineNum}`,
      name: data.name,
      description: data.description ?? null,
      nodes: data.nodes,
      edges: data.edges,
      version: 1,
      is_active: false,
      is_default: false,
      is_valid: true,
      validation_errors: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    pipelines.push(newPipeline)
    return HttpResponse.json(newPipeline, { status: 201 })
  }),

  http.put(`${BASE_URL}/pipelines/:id`, async ({ params, request }) => {
    const data = await request.json() as { name?: string; description?: string; nodes?: Pipeline['nodes']; edges?: Pipeline['edges']; change_summary?: string }
    const index = pipelines.findIndex((p) => p.guid === params.id)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }

    // Check for duplicate name (excluding current pipeline)
    if (data.name && pipelines.some((p) => p.name === data.name && p.guid !== params.id)) {
      return HttpResponse.json(
        { detail: `Pipeline with name '${data.name}' already exists` },
        { status: 409 }
      )
    }

    // Save to history
    const historyEntry: PipelineHistoryEntry = {
      version: pipelines[index].version,
      change_summary: data.change_summary ?? null,
      changed_by: null,
      created_at: new Date().toISOString(),
    }
    pipelineHistory.push(historyEntry)

    pipelines[index] = {
      ...pipelines[index],
      ...data,
      version: pipelines[index].version + 1,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(pipelines[index])
  }),

  http.delete(`${BASE_URL}/pipelines/:id`, ({ params }) => {
    const index = pipelines.findIndex((p) => p.guid === params.id)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    if (pipelines[index].is_active) {
      return HttpResponse.json(
        { detail: 'Cannot delete active pipeline' },
        { status: 409 }
      )
    }
    const deletedGuid = pipelines[index].guid
    pipelines.splice(index, 1)
    return HttpResponse.json({ message: 'Pipeline deleted successfully', deleted_guid: deletedGuid })
  }),

  http.post(`${BASE_URL}/pipelines/:id/activate`, ({ params }) => {
    const index = pipelines.findIndex((p) => p.guid === params.id)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    if (!pipelines[index].is_valid) {
      return HttpResponse.json(
        { detail: 'Cannot activate invalid pipeline' },
        { status: 400 }
      )
    }

    // Deactivate other pipelines
    pipelines.forEach((p) => { p.is_active = false })
    pipelines[index].is_active = true
    pipelines[index].updated_at = new Date().toISOString()

    return HttpResponse.json(pipelines[index])
  }),

  http.post(`${BASE_URL}/pipelines/:id/deactivate`, ({ params }) => {
    const index = pipelines.findIndex((p) => p.guid === params.id)
    if (index === -1) {
      return new HttpResponse(null, { status: 404 })
    }

    pipelines[index].is_active = false
    pipelines[index].updated_at = new Date().toISOString()

    return HttpResponse.json(pipelines[index])
  }),

  http.post(`${BASE_URL}/pipelines/:id/validate`, ({ params }) => {
    const pipeline = pipelines.find((p) => p.guid === params.id)
    if (!pipeline) {
      return new HttpResponse(null, { status: 404 })
    }

    const result: ValidationResult = {
      is_valid: pipeline.is_valid,
      errors: pipeline.validation_errors
        ? pipeline.validation_errors.map((msg) => ({
            type: 'orphaned_node' as const,
            message: msg,
            node_id: null,
            suggestion: null,
          }))
        : [],
    }
    return HttpResponse.json(result)
  }),

  http.post(`${BASE_URL}/pipelines/:id/preview`, async ({ params, request }) => {
    const pipeline = pipelines.find((p) => p.guid === params.id)
    if (!pipeline) {
      return new HttpResponse(null, { status: 404 })
    }
    if (!pipeline.is_valid) {
      return HttpResponse.json(
        { detail: 'Cannot preview invalid pipeline' },
        { status: 400 }
      )
    }

    const data = await request.json() as { camera_id?: string; counter?: string }
    const cameraId = data.camera_id ?? 'AB3D'
    const counter = data.counter ?? '0001'
    const baseFilename = `${cameraId}${counter}`

    const preview: FilenamePreviewResponse = {
      base_filename: baseFilename,
      expected_files: pipeline.nodes
        .filter((n) => n.type === 'file')
        .map((n) => ({
          path: `capture -> ${n.id}`,
          filename: `${baseFilename}${n.properties.extension || '.unknown'}`,
          optional: n.properties.optional === true,
        })),
    }
    return HttpResponse.json(preview)
  }),

  http.get(`${BASE_URL}/pipelines/:id/history`, ({ params }) => {
    const pipeline = pipelines.find((p) => p.guid === params.id)
    if (!pipeline) {
      return new HttpResponse(null, { status: 404 })
    }

    // Return history entries for the pipeline (mock just returns the global history)
    return HttpResponse.json(pipelineHistory)
  }),

  http.get(`${BASE_URL}/pipelines/:id/export`, ({ params }) => {
    const pipeline = pipelines.find((p) => p.guid === params.id)
    if (!pipeline) {
      return new HttpResponse(null, { status: 404 })
    }

    const yamlContent = `name: ${pipeline.name}
description: ${pipeline.description ?? ''}
nodes:
${pipeline.nodes.map((n) => `  - id: ${n.id}
    type: ${n.type}
    properties: ${JSON.stringify(n.properties)}`).join('\n')}
edges:
${pipeline.edges.map((e) => `  - from: ${e.from}
    to: ${e.to}`).join('\n')}
`

    return new HttpResponse(yamlContent, {
      headers: {
        'Content-Type': 'application/x-yaml',
        'Content-Disposition': `attachment; filename="${pipeline.name.replace(/\s+/g, '_')}.yaml"`,
      },
    })
  }),

  http.post(`${BASE_URL}/pipelines/import`, async ({ request }) => {
    // For simplicity, just create a new pipeline with default values
    const formData = await request.formData()
    const file = formData.get('file') as File
    if (!file) {
      return HttpResponse.json(
        { detail: 'No file provided' },
        { status: 400 }
      )
    }

    const newPipelineNum = nextPipelineId++
    const newPipeline: Pipeline = {
      guid: `pip_01hgw2bbg000000000000000${newPipelineNum}`,
      name: `Imported Pipeline ${newPipelineNum}`,
      description: 'Imported from YAML',
      nodes: [
        { id: 'capture', type: 'capture', properties: { camera_id_pattern: '[A-Z0-9]{4}' } },
        { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
      ],
      edges: [{ from: 'capture', to: 'done' }],
      version: 1,
      is_active: false,
      is_default: false,
      is_valid: true,
      validation_errors: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    pipelines.push(newPipeline)
    return HttpResponse.json(newPipeline, { status: 201 })
  }),

  // ============================================================================
  // Trends API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/trends/photostats`, ({ request }) => {
    const url = new URL(request.url)
    const collectionIds = url.searchParams.get('collection_ids')

    // Determine mode based on collection_ids parameter
    const parsedIds = collectionIds ? collectionIds.split(',').map(Number).filter(n => !isNaN(n)) : []
    const isComparisonMode = parsedIds.length >= 1 && parsedIds.length <= 5

    if (isComparisonMode) {
      // Comparison mode: return per-collection data
      const response: PhotoStatsTrendResponse = {
        mode: 'comparison',
        data_points: [],
        collections: parsedIds.map(id => {
          return {
            collection_id: id,
            collection_name: `Collection ${id}`,
            data_points: [
              {
                date: '2025-01-01T10:00:00Z',
                result_id: 1,
                orphaned_images_count: 5,
                orphaned_xmp_count: 3,
                total_files: 1000,
                total_size: 5000000000,
              },
              {
                date: '2025-01-02T10:00:00Z',
                result_id: 2,
                orphaned_images_count: 3,
                orphaned_xmp_count: 2,
                total_files: 1050,
                total_size: 5250000000,
              },
            ],
          }
        }),
      }
      return HttpResponse.json(response)
    }

    // Aggregated mode: return summed data
    const response: PhotoStatsTrendResponse = {
      mode: 'aggregated',
      data_points: [
        {
          date: '2025-01-01T00:00:00Z',
          orphaned_images: 10,
          orphaned_metadata: 5,
          collections_included: 2,
        },
        {
          date: '2025-01-02T00:00:00Z',
          orphaned_images: 8,
          orphaned_metadata: 4,
          collections_included: 2,
        },
        {
          date: '2025-01-03T00:00:00Z',
          orphaned_images: 6,
          orphaned_metadata: 3,
          collections_included: 2,
        },
      ],
      collections: [],
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/trends/photo-pairing`, ({ request }) => {
    const url = new URL(request.url)
    const collectionIds = url.searchParams.get('collection_ids')

    // Determine mode based on collection_ids parameter
    const parsedIds = collectionIds ? collectionIds.split(',').map(Number).filter(n => !isNaN(n)) : []
    const isComparisonMode = parsedIds.length >= 1 && parsedIds.length <= 5

    if (isComparisonMode) {
      // Comparison mode: return per-collection data
      const response: PhotoPairingTrendResponse = {
        mode: 'comparison',
        data_points: [],
        collections: parsedIds.map(id => {
          return {
            collection_id: id,
            collection_name: `Collection ${id}`,
            cameras: ['ABC1', 'XYZ2'],
            data_points: [
              {
                date: '2025-01-01T11:00:00Z',
                result_id: 2,
                group_count: 400,
                image_count: 800,
                camera_usage: { ABC1: 500, XYZ2: 300 },
              },
              {
                date: '2025-01-02T11:00:00Z',
                result_id: 3,
                group_count: 420,
                image_count: 840,
                camera_usage: { ABC1: 520, XYZ2: 320 },
              },
            ],
          }
        }),
      }
      return HttpResponse.json(response)
    }

    // Aggregated mode: return summed data (no camera breakdown)
    const response: PhotoPairingTrendResponse = {
      mode: 'aggregated',
      data_points: [
        {
          date: '2025-01-01T00:00:00Z',
          group_count: 800,
          image_count: 1600,
          collections_included: 2,
        },
        {
          date: '2025-01-02T00:00:00Z',
          group_count: 840,
          image_count: 1680,
          collections_included: 2,
        },
        {
          date: '2025-01-03T00:00:00Z',
          group_count: 880,
          image_count: 1760,
          collections_included: 2,
        },
      ],
      collections: [],
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/trends/pipeline-validation`, ({ request }) => {
    const url = new URL(request.url)
    const collectionIds = url.searchParams.get('collection_ids')

    // Determine mode based on collection_ids parameter
    const parsedIds = collectionIds ? collectionIds.split(',').map(Number).filter(n => !isNaN(n)) : []
    const isComparisonMode = parsedIds.length >= 1 && parsedIds.length <= 5

    if (isComparisonMode) {
      // Comparison mode: return per-collection data
      const response: PipelineValidationTrendResponse = {
        mode: 'comparison',
        data_points: [],
        collections: parsedIds.map(id => {
          return {
            collection_id: id,
            collection_name: `Collection ${id}`,
            data_points: [
              {
                date: '2025-01-01T13:00:00Z',
                result_id: 4,
                pipeline_id: 1,
                pipeline_name: 'Standard RAW Workflow',
                consistent_count: 400,
                partial_count: 50,
                inconsistent_count: 50,
                consistent_ratio: 80,
                partial_ratio: 10,
                inconsistent_ratio: 10,
              },
              {
                date: '2025-01-02T13:00:00Z',
                result_id: 5,
                pipeline_id: 1,
                pipeline_name: 'Standard RAW Workflow',
                consistent_count: 420,
                partial_count: 45,
                inconsistent_count: 35,
                consistent_ratio: 84,
                partial_ratio: 9,
                inconsistent_ratio: 7,
              },
            ],
          }
        }),
      }
      return HttpResponse.json(response)
    }

    // Aggregated mode: return percentage data
    const response: PipelineValidationTrendResponse = {
      mode: 'aggregated',
      data_points: [
        {
          date: '2025-01-01T00:00:00Z',
          overall_consistency_pct: 80,
          overall_inconsistent_pct: 10,
          black_box_consistency_pct: 85,
          browsable_consistency_pct: 75,
          total_images: 1000,
          consistent_count: 800,
          inconsistent_count: 100,
          collections_included: 2,
        },
        {
          date: '2025-01-02T00:00:00Z',
          overall_consistency_pct: 82,
          overall_inconsistent_pct: 8,
          black_box_consistency_pct: 87,
          browsable_consistency_pct: 77,
          total_images: 1050,
          consistent_count: 861,
          inconsistent_count: 84,
          collections_included: 2,
        },
        {
          date: '2025-01-03T00:00:00Z',
          overall_consistency_pct: 85,
          overall_inconsistent_pct: 6,
          black_box_consistency_pct: 90,
          browsable_consistency_pct: 80,
          total_images: 1100,
          consistent_count: 935,
          inconsistent_count: 66,
          collections_included: 2,
        },
      ],
      collections: [],
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/trends/display-graph`, () => {
    const response: DisplayGraphTrendResponse = {
      data_points: [
        {
          date: '2025-01-01T00:00:00Z',
          total_paths: 100,
          valid_paths: 90,
          black_box_archive_paths: 50,
          browsable_archive_paths: 40,
        },
        {
          date: '2025-01-02T00:00:00Z',
          total_paths: 110,
          valid_paths: 100,
          black_box_archive_paths: 55,
          browsable_archive_paths: 45,
        },
      ],
      pipelines_included: [
        { pipeline_id: 1, pipeline_name: 'Standard RAW Workflow', result_count: 2 },
      ],
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/trends/summary`, ({ request }) => {
    const url = new URL(request.url)
    const collectionId = url.searchParams.get('collection_id')

    const response: TrendSummaryResponse = {
      collection_id: collectionId ? Number(collectionId) : null,
      orphaned_trend: 'improving',
      consistency_trend: 'stable',
      last_photostats: '2025-01-03T10:00:00Z',
      last_photo_pairing: '2025-01-03T11:00:00Z',
      last_pipeline_validation: '2025-01-03T13:00:00Z',
      data_points_available: {
        photostats: 3,
        photo_pairing: 3,
        pipeline_validation: 3,
      },
    }
    return HttpResponse.json(response)
  }),

  // ============================================================================
  // Config API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/config`, () => {
    const response: ConfigurationResponse = {
      extensions: configData.extensions,
      cameras: configData.cameras,
      processing_methods: configData.processing_methods,
      event_statuses: configData.event_statuses,
    }
    return HttpResponse.json(response)
  }),

  // GET /api/config/event_statuses - Get event statuses
  http.get(`${BASE_URL}/config/event_statuses`, () => {
    const statuses = Object.entries(configData.event_statuses)
      .map(([key, value]) => ({
        key,
        label: value.label,
        display_order: value.display_order,
      }))
      .sort((a, b) => a.display_order - b.display_order)

    return HttpResponse.json({ statuses })
  }),

  http.get(`${BASE_URL}/config/stats`, () => {
    const camerasCount = Object.keys(configData.cameras).length
    const methodsCount = Object.keys(configData.processing_methods).length
    const extensionsCount = 3 // photo_extensions, metadata_extensions, require_sidecar

    const response: ConfigStatsResponse = {
      total_items: camerasCount + methodsCount + extensionsCount,
      cameras_configured: camerasCount,
      processing_methods_configured: methodsCount,
      last_import: configData.lastImport,
      source_breakdown: {
        database: camerasCount + methodsCount + extensionsCount,
        yaml_import: 0,
      },
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/config/export`, () => {
    const yamlContent = `# Photo Admin Configuration
extensions:
  photo_extensions: ${JSON.stringify(configData.extensions.photo_extensions)}
  metadata_extensions: ${JSON.stringify(configData.extensions.metadata_extensions)}
  require_sidecar: ${JSON.stringify(configData.extensions.require_sidecar)}
cameras:
${Object.entries(configData.cameras).map(([id, cam]) => `  ${id}:
    - name: ${cam.name}
      serial_number: "${cam.serial_number}"`).join('\n')}
processing_methods:
${Object.entries(configData.processing_methods).map(([key, desc]) => `  ${key}: "${desc}"`).join('\n')}
`
    return new HttpResponse(yamlContent, {
      headers: {
        'Content-Type': 'application/x-yaml',
        'Content-Disposition': 'attachment; filename="photo-admin-config.yaml"',
      },
    })
  }),

  http.get(`${BASE_URL}/config/:category`, ({ params }) => {
    const category = params.category as ConfigCategory
    let items: ConfigItem[] = []

    if (category === 'extensions') {
      items = [
        { key: 'photo_extensions', value: configData.extensions.photo_extensions, description: null, source: 'database', updated_at: '2025-01-01T09:00:00Z' },
        { key: 'metadata_extensions', value: configData.extensions.metadata_extensions, description: null, source: 'database', updated_at: '2025-01-01T09:00:00Z' },
        { key: 'require_sidecar', value: configData.extensions.require_sidecar, description: null, source: 'database', updated_at: '2025-01-01T09:00:00Z' },
      ]
    } else if (category === 'cameras') {
      items = Object.entries(configData.cameras).map(([key, value]) => ({
        key,
        value: [value],
        description: null,
        source: 'database' as const,
        updated_at: '2025-01-01T09:00:00Z',
      }))
    } else if (category === 'processing_methods') {
      items = Object.entries(configData.processing_methods).map(([key, value]) => ({
        key,
        value,
        description: null,
        source: 'database' as const,
        updated_at: '2025-01-01T09:00:00Z',
      }))
    }

    const response: CategoryConfigResponse = { category, items }
    return HttpResponse.json(response)
  }),

  // Import handlers MUST come before generic :category/:key handlers
  // to prevent import/sessionId from matching as category=import, key=sessionId
  http.post(`${BASE_URL}/config/import`, async ({ request }) => {
    const formData = await request.formData()
    const file = formData.get('file') as File

    const sessionId = `test-session-${Date.now()}`
    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString() // 15 minutes from now
    const session: ImportSessionResponse = {
      session_id: sessionId,
      status: 'pending',
      expires_at: expiresAt,
      file_name: file?.name || 'config.yaml',
      total_items: 5,
      new_items: 3,
      conflicts: [
        {
          category: 'cameras',
          key: 'AB3D',
          database_value: { name: 'Canon EOS R5', serial_number: '12345' },
          yaml_value: { name: 'Canon EOS R5 Updated', serial_number: '12345' },
          resolved: false,
          resolution: null,
        },
      ],
    }
    configData.importSessions[sessionId] = session
    return HttpResponse.json(session)
  }),

  http.get(`${BASE_URL}/config/import/:sessionId`, ({ params }) => {
    const session = configData.importSessions[params.sessionId as string]
    if (!session) {
      return HttpResponse.json({ detail: 'Import session not found' }, { status: 404 })
    }
    return HttpResponse.json(session)
  }),

  http.post(`${BASE_URL}/config/import/:sessionId/resolve`, async ({ params, request }) => {
    const session = configData.importSessions[params.sessionId as string]
    if (!session) {
      return HttpResponse.json({ detail: 'Import session not found' }, { status: 404 })
    }

    const data = await request.json() as { resolutions: Array<{ category: string; key: string; use_yaml: boolean }> }

    // Apply resolutions
    session.status = 'applied'
    configData.lastImport = new Date().toISOString()

    const response: ImportResultResponse = {
      success: true,
      items_imported: data.resolutions.filter(r => r.use_yaml).length + session.new_items,
      items_skipped: data.resolutions.filter(r => !r.use_yaml).length,
      message: 'Import completed successfully',
    }
    return HttpResponse.json(response)
  }),

  http.post(`${BASE_URL}/config/import/:sessionId/cancel`, ({ params }) => {
    const session = configData.importSessions[params.sessionId as string]
    if (!session) {
      return HttpResponse.json({ detail: 'Import session not found' }, { status: 404 })
    }
    session.status = 'cancelled'
    return HttpResponse.json({ message: 'Import cancelled' })
  }),

  http.get(`${BASE_URL}/config/:category/:key`, ({ params }) => {
    const category = params.category as ConfigCategory
    const key = params.key as string

    let value: unknown = null
    if (category === 'cameras' && configData.cameras[key]) {
      value = [configData.cameras[key]]
    } else if (category === 'processing_methods' && configData.processing_methods[key]) {
      value = configData.processing_methods[key]
    } else if (category === 'extensions') {
      value = configData.extensions[key as keyof typeof configData.extensions]
    }

    if (value === null || value === undefined) {
      return HttpResponse.json({ detail: 'Configuration not found' }, { status: 404 })
    }

    const response: ConfigValueResponse = {
      category,
      key,
      value,
      description: null,
      source: 'database',
      updated_at: '2025-01-01T09:00:00Z',
    }
    return HttpResponse.json(response)
  }),

  http.post(`${BASE_URL}/config/:category/:key`, async ({ params, request }) => {
    const category = params.category as ConfigCategory
    const key = params.key as string
    const data = await request.json() as { value: unknown; description?: string }

    if (category === 'cameras') {
      const cameraArray = data.value as Array<{ name: string; serial_number: string }>
      configData.cameras[key] = cameraArray[0]
    } else if (category === 'processing_methods') {
      configData.processing_methods[key] = data.value as string
    }

    const response: ConfigValueResponse = {
      category,
      key,
      value: data.value,
      description: data.description ?? null,
      source: 'database',
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(response, { status: 201 })
  }),

  http.put(`${BASE_URL}/config/:category/:key`, async ({ params, request }) => {
    const category = params.category as ConfigCategory
    const key = params.key as string
    const data = await request.json() as { value: unknown; description?: string }

    if (category === 'cameras') {
      const cameraArray = data.value as Array<{ name: string; serial_number: string }>
      configData.cameras[key] = cameraArray[0]
    } else if (category === 'processing_methods') {
      configData.processing_methods[key] = data.value as string
    } else if (category === 'extensions') {
      configData.extensions[key as keyof typeof configData.extensions] = data.value as string[]
    }

    const response: ConfigValueResponse = {
      category,
      key,
      value: data.value,
      description: data.description ?? null,
      source: 'database',
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(response)
  }),

  http.delete(`${BASE_URL}/config/:category/:key`, ({ params }) => {
    const category = params.category as ConfigCategory
    const key = params.key as string

    if (category === 'cameras') {
      delete configData.cameras[key]
    } else if (category === 'processing_methods') {
      delete configData.processing_methods[key]
    }

    return HttpResponse.json({ message: 'Configuration deleted successfully' })
  }),

  // ============================================================================
  // Categories API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/categories`, ({ request }) => {
    const url = new URL(request.url)
    const isActive = url.searchParams.get('is_active')

    let filteredCategories = [...categories]
    if (isActive !== null) {
      filteredCategories = filteredCategories.filter((c) => c.is_active === (isActive === 'true'))
    }

    // Sort by display_order
    filteredCategories.sort((a, b) => a.display_order - b.display_order)

    return HttpResponse.json(filteredCategories)
  }),

  http.get(`${BASE_URL}/categories/stats`, () => {
    const stats: CategoryStatsResponse = {
      total_count: categories.length,
      active_count: categories.filter((c) => c.is_active).length,
      inactive_count: categories.filter((c) => !c.is_active).length,
    }
    return HttpResponse.json(stats)
  }),

  http.get(`${BASE_URL}/categories/:guid`, ({ params }) => {
    const category = categories.find((c) => c.guid === params.guid)
    if (!category) {
      return HttpResponse.json(
        { detail: `Category ${params.guid} not found` },
        { status: 404 }
      )
    }
    return HttpResponse.json(category)
  }),

  http.post(`${BASE_URL}/categories`, async ({ request }) => {
    const data = await request.json() as CategoryCreateRequest

    // Check for duplicate name
    if (categories.some((c) => c.name.toLowerCase() === data.name.toLowerCase())) {
      return HttpResponse.json(
        { detail: `Category with name '${data.name}' already exists` },
        { status: 409 }
      )
    }

    const newCategory: Category = {
      guid: `cat_01hgw2bbg000000000000000${nextCategoryNum++}`,
      name: data.name,
      icon: data.icon ?? null,
      color: data.color ?? null,
      display_order: categories.length,
      is_active: data.is_active ?? true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    categories.push(newCategory)
    return HttpResponse.json(newCategory, { status: 201 })
  }),

  http.patch(`${BASE_URL}/categories/:guid`, async ({ params, request }) => {
    const data = await request.json() as CategoryUpdateRequest
    const index = categories.findIndex((c) => c.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Category ${params.guid} not found` },
        { status: 404 }
      )
    }

    // Check for duplicate name (excluding current category)
    if (data.name && categories.some((c) => c.name.toLowerCase() === data.name!.toLowerCase() && c.guid !== params.guid)) {
      return HttpResponse.json(
        { detail: `Category with name '${data.name}' already exists` },
        { status: 409 }
      )
    }

    categories[index] = {
      ...categories[index],
      ...data,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(categories[index])
  }),

  http.delete(`${BASE_URL}/categories/:guid`, ({ params }) => {
    const index = categories.findIndex((c) => c.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Category ${params.guid} not found` },
        { status: 404 }
      )
    }
    categories.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${BASE_URL}/categories/reorder`, async ({ request }) => {
    const data = await request.json() as { ordered_guids: string[] }

    // Reorder categories based on the provided order
    const reorderedCategories: Category[] = []
    data.ordered_guids.forEach((guid, index) => {
      const category = categories.find((c) => c.guid === guid)
      if (category) {
        category.display_order = index
        category.updated_at = new Date().toISOString()
        reorderedCategories.push(category)
      }
    })

    // Add any categories not in the list at the end
    categories.forEach((c) => {
      if (!data.ordered_guids.includes(c.guid)) {
        c.display_order = reorderedCategories.length
        reorderedCategories.push(c)
      }
    })

    categories = reorderedCategories
    return HttpResponse.json(categories)
  }),

  // ============================================================================
  // Events API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/events`, ({ request }) => {
    const url = new URL(request.url)
    const startDate = url.searchParams.get('start_date')
    const endDate = url.searchParams.get('end_date')
    const categoryGuid = url.searchParams.get('category_guid')
    const status = url.searchParams.get('status')
    const attendance = url.searchParams.get('attendance')

    let filteredEvents = [...events]

    if (startDate) {
      filteredEvents = filteredEvents.filter((e) => e.event_date >= startDate)
    }
    if (endDate) {
      filteredEvents = filteredEvents.filter((e) => e.event_date <= endDate)
    }
    if (categoryGuid) {
      filteredEvents = filteredEvents.filter((e) => e.category?.guid === categoryGuid)
    }
    if (status) {
      filteredEvents = filteredEvents.filter((e) => e.status === status)
    }
    if (attendance) {
      filteredEvents = filteredEvents.filter((e) => e.attendance === attendance)
    }

    // Sort by date
    filteredEvents.sort((a, b) => a.event_date.localeCompare(b.event_date))

    return HttpResponse.json(filteredEvents)
  }),

  http.get(`${BASE_URL}/events/stats`, () => {
    const today = new Date().toISOString().split('T')[0]
    const currentMonth = today.slice(0, 7)

    const stats: EventStatsResponse = {
      total_count: events.length,
      upcoming_count: events.filter((e) => e.event_date >= today && (e.status === 'future' || e.status === 'confirmed')).length,
      this_month_count: events.filter((e) => e.event_date.startsWith(currentMonth)).length,
      attended_count: events.filter((e) => e.attendance === 'attended').length,
    }
    return HttpResponse.json(stats)
  }),

  http.get(`${BASE_URL}/events/:guid`, ({ params }) => {
    const event = events.find((e) => e.guid === params.guid)
    if (!event) {
      return HttpResponse.json(
        { detail: `Event ${params.guid} not found` },
        { status: 404 }
      )
    }

    // Build detail response
    const detailResponse: EventDetail = {
      ...event,
      description: 'Event description goes here',
      location: null,
      organizer: null,
      performers: [],
      series: event.series_guid ? {
        guid: event.series_guid,
        title: 'Oshkosh Airshow 2026',
        total_events: event.series_total || 3,
        deadline_date: null,
        deadline_time: null,
        deadline_entry_guid: null,
      } : null,
      ticket_required: true,
      ticket_status: 'purchased',
      ticket_purchase_date: '2026-01-15',
      timeoff_required: true,
      timeoff_status: 'approved',
      timeoff_booking_date: '2026-01-10',
      travel_required: true,
      travel_status: 'booked',
      travel_booking_date: '2026-02-01',
      deadline_date: null,
      deleted_at: null,
    }

    return HttpResponse.json(detailResponse)
  }),

  // ============================================================================
  // Locations API endpoints
  // ============================================================================

  http.get(`${BASE_URL}/locations`, ({ request }) => {
    const url = new URL(request.url)
    const categoryGuid = url.searchParams.get('category_guid')
    const knownOnly = url.searchParams.get('known_only')
    const search = url.searchParams.get('search')
    const limit = parseInt(url.searchParams.get('limit') ?? '100', 10)
    const offset = parseInt(url.searchParams.get('offset') ?? '0', 10)

    let filteredLocations = [...locations]

    if (categoryGuid) {
      filteredLocations = filteredLocations.filter((l) => l.category.guid === categoryGuid)
    }
    if (knownOnly === 'true') {
      filteredLocations = filteredLocations.filter((l) => l.is_known)
    }
    if (search) {
      const searchLower = search.toLowerCase()
      filteredLocations = filteredLocations.filter(
        (l) =>
          l.name.toLowerCase().includes(searchLower) ||
          l.city?.toLowerCase().includes(searchLower) ||
          l.address?.toLowerCase().includes(searchLower)
      )
    }

    const total = filteredLocations.length
    const items = filteredLocations.slice(offset, offset + limit)

    return HttpResponse.json({ items, total })
  }),

  http.get(`${BASE_URL}/locations/stats`, () => {
    const stats: LocationStatsResponse = {
      total_count: locations.length,
      known_count: locations.filter((l) => l.is_known).length,
      with_coordinates_count: locations.filter((l) => l.latitude !== null && l.longitude !== null).length,
    }
    return HttpResponse.json(stats)
  }),

  http.get(`${BASE_URL}/locations/by-category/:categoryGuid`, ({ params, request }) => {
    const url = new URL(request.url)
    const knownOnly = url.searchParams.get('known_only') !== 'false'
    const categoryGuid = params.categoryGuid as string

    let filteredLocations = locations.filter((l) => l.category.guid === categoryGuid)
    if (knownOnly) {
      filteredLocations = filteredLocations.filter((l) => l.is_known)
    }

    return HttpResponse.json(filteredLocations)
  }),

  http.get(`${BASE_URL}/locations/:guid`, ({ params }) => {
    const location = locations.find((l) => l.guid === params.guid)
    if (!location) {
      return HttpResponse.json(
        { detail: `Location ${params.guid} not found` },
        { status: 404 }
      )
    }
    return HttpResponse.json(location)
  }),

  http.post(`${BASE_URL}/locations`, async ({ request }) => {
    const data = await request.json() as LocationCreateRequest

    // Find category
    const category = categories.find((c) => c.guid === data.category_guid)
    if (!category) {
      return HttpResponse.json(
        { detail: `Category ${data.category_guid} not found` },
        { status: 404 }
      )
    }

    const newLocation: Location = {
      guid: `loc_01hgw2bbg00000000000000${nextLocationNum++}`,
      name: data.name,
      address: data.address ?? null,
      city: data.city ?? null,
      state: data.state ?? null,
      country: data.country ?? null,
      postal_code: data.postal_code ?? null,
      latitude: data.latitude ?? null,
      longitude: data.longitude ?? null,
      timezone: data.timezone ?? null,
      category: {
        guid: category.guid,
        name: category.name,
        icon: category.icon,
        color: category.color,
      },
      rating: data.rating ?? null,
      timeoff_required_default: data.timeoff_required_default ?? false,
      travel_required_default: data.travel_required_default ?? false,
      notes: data.notes ?? null,
      is_known: data.is_known ?? true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    locations.push(newLocation)
    return HttpResponse.json(newLocation, { status: 201 })
  }),

  http.patch(`${BASE_URL}/locations/:guid`, async ({ params, request }) => {
    const data = await request.json() as LocationUpdateRequest
    const index = locations.findIndex((l) => l.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Location ${params.guid} not found` },
        { status: 404 }
      )
    }

    // If category is being updated, find it
    let category = locations[index].category
    if (data.category_guid) {
      const newCategory = categories.find((c) => c.guid === data.category_guid)
      if (!newCategory) {
        return HttpResponse.json(
          { detail: `Category ${data.category_guid} not found` },
          { status: 404 }
        )
      }
      category = {
        guid: newCategory.guid,
        name: newCategory.name,
        icon: newCategory.icon,
        color: newCategory.color,
      }
    }

    locations[index] = {
      ...locations[index],
      ...data,
      category,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(locations[index])
  }),

  http.delete(`${BASE_URL}/locations/:guid`, ({ params }) => {
    const index = locations.findIndex((l) => l.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Location ${params.guid} not found` },
        { status: 404 }
      )
    }
    locations.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${BASE_URL}/locations/geocode`, async ({ request }) => {
    const data = await request.json() as { address: string }

    // Mock geocoding response
    const response: GeocodeResponse = {
      address: '123 Main St',
      city: 'Test City',
      state: 'Test State',
      country: 'USA',
      postal_code: '12345',
      latitude: 40.7128,
      longitude: -74.0060,
      timezone: 'America/New_York',
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/locations/:guid/validate-category/:eventCategoryGuid`, ({ params }) => {
    const location = locations.find((l) => l.guid === params.guid)
    if (!location) {
      return HttpResponse.json(
        { detail: `Location ${params.guid} not found` },
        { status: 404 }
      )
    }

    const matches = location.category.guid === params.eventCategoryGuid
    return HttpResponse.json({ matches })
  }),

  // ============================================================================
  // Performer Handlers (Phase 11)
  // ============================================================================

  http.get(`${BASE_URL}/performers`, ({ request }) => {
    const url = new URL(request.url)
    const categoryGuid = url.searchParams.get('category_guid')
    const search = url.searchParams.get('search')
    const limit = parseInt(url.searchParams.get('limit') ?? '100', 10)
    const offset = parseInt(url.searchParams.get('offset') ?? '0', 10)

    let filteredPerformers = [...performers]

    if (categoryGuid) {
      filteredPerformers = filteredPerformers.filter((p) => p.category.guid === categoryGuid)
    }
    if (search) {
      const searchLower = search.toLowerCase()
      filteredPerformers = filteredPerformers.filter(
        (p) =>
          p.name.toLowerCase().includes(searchLower) ||
          p.instagram_handle?.toLowerCase().includes(searchLower) ||
          p.additional_info?.toLowerCase().includes(searchLower)
      )
    }

    const total = filteredPerformers.length
    const items = filteredPerformers.slice(offset, offset + limit)

    return HttpResponse.json({ items, total })
  }),

  http.get(`${BASE_URL}/performers/stats`, () => {
    const stats: PerformerStatsResponse = {
      total_count: performers.length,
      with_instagram_count: performers.filter((p) => p.instagram_handle !== null).length,
      with_website_count: performers.filter((p) => p.website !== null).length,
    }
    return HttpResponse.json(stats)
  }),

  http.get(`${BASE_URL}/performers/by-category/:categoryGuid`, ({ params, request }) => {
    const url = new URL(request.url)
    const search = url.searchParams.get('search')
    const categoryGuid = params.categoryGuid as string

    let filteredPerformers = performers.filter((p) => p.category.guid === categoryGuid)
    if (search) {
      const searchLower = search.toLowerCase()
      filteredPerformers = filteredPerformers.filter(
        (p) => p.name.toLowerCase().includes(searchLower)
      )
    }

    return HttpResponse.json(filteredPerformers)
  }),

  http.get(`${BASE_URL}/performers/:guid`, ({ params }) => {
    const performer = performers.find((p) => p.guid === params.guid)
    if (!performer) {
      return HttpResponse.json(
        { detail: `Performer ${params.guid} not found` },
        { status: 404 }
      )
    }
    return HttpResponse.json(performer)
  }),

  http.post(`${BASE_URL}/performers`, async ({ request }) => {
    const data = await request.json() as PerformerCreateRequest

    // Find category
    const category = categories.find((c) => c.guid === data.category_guid)
    if (!category) {
      return HttpResponse.json(
        { detail: `Category ${data.category_guid} not found` },
        { status: 404 }
      )
    }

    // Check if category is inactive
    if (!category.is_active) {
      return HttpResponse.json(
        { detail: 'Cannot create performer in inactive category' },
        { status: 400 }
      )
    }

    const newPerformer: Performer = {
      guid: `prf_01hgw2bbg0000000000000000${nextPerformerNum++}`,
      name: data.name,
      website: data.website ?? null,
      instagram_handle: data.instagram_handle?.replace(/^@/, '') ?? null,
      instagram_url: data.instagram_handle
        ? `https://instagram.com/${data.instagram_handle.replace(/^@/, '')}`
        : null,
      category: {
        guid: category.guid,
        name: category.name,
        icon: category.icon,
        color: category.color,
      },
      additional_info: data.additional_info ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    performers.push(newPerformer)
    return HttpResponse.json(newPerformer, { status: 201 })
  }),

  http.patch(`${BASE_URL}/performers/:guid`, async ({ params, request }) => {
    const data = await request.json() as PerformerUpdateRequest
    const index = performers.findIndex((p) => p.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Performer ${params.guid} not found` },
        { status: 404 }
      )
    }

    // If category is being updated, find it
    let category = performers[index].category
    if (data.category_guid) {
      const newCategory = categories.find((c) => c.guid === data.category_guid)
      if (!newCategory) {
        return HttpResponse.json(
          { detail: `Category ${data.category_guid} not found` },
          { status: 404 }
        )
      }
      category = {
        guid: newCategory.guid,
        name: newCategory.name,
        icon: newCategory.icon,
        color: newCategory.color,
      }
    }

    // Handle instagram URL
    let instagram_url = performers[index].instagram_url
    if (data.instagram_handle !== undefined) {
      if (data.instagram_handle) {
        const handle = data.instagram_handle.replace(/^@/, '')
        instagram_url = `https://instagram.com/${handle}`
      } else {
        instagram_url = null
      }
    }

    performers[index] = {
      ...performers[index],
      ...data,
      instagram_handle: data.instagram_handle?.replace(/^@/, '') ?? performers[index].instagram_handle,
      instagram_url,
      category,
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(performers[index])
  }),

  http.delete(`${BASE_URL}/performers/:guid`, ({ params }) => {
    const index = performers.findIndex((p) => p.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Performer ${params.guid} not found` },
        { status: 404 }
      )
    }
    performers.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${BASE_URL}/performers/:guid/validate-category/:eventCategoryGuid`, ({ params }) => {
    const performer = performers.find((p) => p.guid === params.guid)
    if (!performer) {
      return HttpResponse.json(
        { detail: `Performer ${params.guid} not found` },
        { status: 404 }
      )
    }

    const matches = performer.category.guid === params.eventCategoryGuid
    return HttpResponse.json({ matches })
  }),

  // ============================================================================
  // Organizers API
  // ============================================================================

  http.get(`${BASE_URL}/organizers`, ({ request }) => {
    const url = new URL(request.url)
    const categoryGuid = url.searchParams.get('category_guid')
    const search = url.searchParams.get('search')

    let filteredOrganizers = [...organizers]

    if (categoryGuid) {
      filteredOrganizers = filteredOrganizers.filter((o) => o.category.guid === categoryGuid)
    }

    if (search) {
      const searchLower = search.toLowerCase()
      filteredOrganizers = filteredOrganizers.filter(
        (o) =>
          o.name.toLowerCase().includes(searchLower) ||
          o.website?.toLowerCase().includes(searchLower) ||
          o.notes?.toLowerCase().includes(searchLower)
      )
    }

    return HttpResponse.json({ items: filteredOrganizers, total: filteredOrganizers.length })
  }),

  http.get(`${BASE_URL}/organizers/stats`, () => {
    return HttpResponse.json({
      total_count: organizers.length,
      with_rating_count: organizers.filter((o) => o.rating !== null).length,
      avg_rating: organizers.length > 0
        ? organizers.filter((o) => o.rating !== null).reduce((sum, o) => sum + (o.rating || 0), 0) / organizers.filter((o) => o.rating !== null).length
        : null,
    })
  }),

  http.get(`${BASE_URL}/organizers/by-category/:categoryGuid`, ({ params }) => {
    const categoryGuid = params.categoryGuid as string
    const filteredOrganizers = organizers.filter((o) => o.category.guid === categoryGuid)
    return HttpResponse.json(filteredOrganizers)
  }),

  http.get(`${BASE_URL}/organizers/:guid`, ({ params }) => {
    const organizer = organizers.find((o) => o.guid === params.guid)
    if (!organizer) {
      return HttpResponse.json(
        { detail: `Organizer ${params.guid} not found` },
        { status: 404 }
      )
    }
    return HttpResponse.json(organizer)
  }),

  http.post(`${BASE_URL}/organizers`, async ({ request }) => {
    const data = (await request.json()) as OrganizerCreateRequest
    const category = categories.find((c) => c.guid === data.category_guid)
    if (!category) {
      return HttpResponse.json(
        { detail: `Category ${data.category_guid} not found` },
        { status: 404 }
      )
    }

    const newOrganizer: Organizer = {
      guid: `org_01hgw2bbg0000000000000000${nextOrganizerNum++}`,
      name: data.name,
      website: data.website ?? null,
      category: {
        guid: category.guid,
        name: category.name,
        icon: category.icon,
        color: category.color,
      },
      rating: data.rating ?? null,
      ticket_required_default: data.ticket_required_default ?? true,
      notes: data.notes ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    organizers.push(newOrganizer)
    return HttpResponse.json(newOrganizer, { status: 201 })
  }),

  http.patch(`${BASE_URL}/organizers/:guid`, async ({ params, request }) => {
    const data = (await request.json()) as OrganizerUpdateRequest
    const index = organizers.findIndex((o) => o.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Organizer ${params.guid} not found` },
        { status: 404 }
      )
    }

    let category = organizers[index].category
    if (data.category_guid) {
      const newCategory = categories.find((c) => c.guid === data.category_guid)
      if (!newCategory) {
        return HttpResponse.json(
          { detail: `Category ${data.category_guid} not found` },
          { status: 404 }
        )
      }
      category = {
        guid: newCategory.guid,
        name: newCategory.name,
        icon: newCategory.icon,
        color: newCategory.color,
      }
    }

    organizers[index] = {
      ...organizers[index],
      ...data,
      category,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(organizers[index])
  }),

  http.delete(`${BASE_URL}/organizers/:guid`, ({ params }) => {
    const index = organizers.findIndex((o) => o.guid === params.guid)
    if (index === -1) {
      return HttpResponse.json(
        { detail: `Organizer ${params.guid} not found` },
        { status: 404 }
      )
    }

    organizers.splice(index, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${BASE_URL}/organizers/:guid/validate-category/:eventCategoryGuid`, ({ params }) => {
    const organizer = organizers.find((o) => o.guid === params.guid)
    if (!organizer) {
      return HttpResponse.json(
        { detail: `Organizer ${params.guid} not found` },
        { status: 404 }
      )
    }

    const matches = organizer.category.guid === params.eventCategoryGuid
    return HttpResponse.json({ matches })
  }),
]

// Helper to reset mock data (useful for tests)
export function resetMockData(): void {
  pipelines = [
    {
      guid: 'pip_01hgw2bbg00000000000000001',
      name: 'Standard RAW Workflow',
      description: 'RAW capture to processed TIFF export',
      nodes: [
        { id: 'capture', type: 'capture', properties: { camera_id_pattern: '[A-Z0-9]{4}' } },
        { id: 'raw', type: 'file', properties: { extension: '.dng' } },
        { id: 'xmp', type: 'file', properties: { extension: '.xmp' } },
        { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
      ],
      edges: [
        { from: 'capture', to: 'raw' },
        { from: 'capture', to: 'xmp' },
        { from: 'raw', to: 'done' },
      ],
      version: 1,
      is_active: true,
      is_default: true,
      is_valid: true,
      validation_errors: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'pip_01hgw2bbg00000000000000002',
      name: 'HDR Workflow',
      description: 'HDR processing pipeline',
      nodes: [
        { id: 'capture', type: 'capture', properties: { camera_id_pattern: '[A-Z0-9]{4}' } },
        { id: 'raw', type: 'file', properties: { extension: '.cr3' } },
        { id: 'hdr', type: 'process', properties: { suffix: '-HDR' } },
        { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
      ],
      edges: [
        { from: 'capture', to: 'raw' },
        { from: 'raw', to: 'hdr' },
        { from: 'hdr', to: 'done' },
      ],
      version: 2,
      is_active: false,
      is_default: false,
      is_valid: true,
      validation_errors: null,
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-01T11:00:00Z',
    },
    {
      guid: 'pip_01hgw2bbg00000000000000003',
      name: 'Invalid Pipeline',
      description: 'Pipeline with validation errors',
      nodes: [
        { id: 'capture', type: 'capture', properties: {} },
        { id: 'orphan', type: 'file', properties: { extension: '.dng' } },
      ],
      edges: [],
      version: 1,
      is_active: false,
      is_default: false,
      is_valid: false,
      validation_errors: ['Orphaned node: orphan'],
      created_at: '2025-01-01T12:00:00Z',
      updated_at: '2025-01-01T12:00:00Z',
    },
  ]
  nextPipelineId = 4
  pipelineHistory = [
    {
      version: 1,
      change_summary: 'Initial version',
      changed_by: null,
      created_at: '2025-01-01T10:00:00Z',
    },
    {
      version: 2,
      change_summary: 'Updated HDR settings',
      changed_by: null,
      created_at: '2025-01-01T11:00:00Z',
    },
  ]
  connectors = [
    {
      guid: 'con_01hgw2bbg00000000000000001',
      name: 'Test S3 Connector',
      type: 's3',
      is_active: true,
      last_validated: '2025-01-01T10:00:00Z',
      last_error: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T10:00:00Z',
    },
    {
      guid: 'con_01hgw2bbg00000000000000002',
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
      guid: 'col_01hgw2bbg00000000000000001',
      name: 'Test Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
      connector_guid: null,
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      cache_ttl: 3600,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'col_01hgw2bbg00000000000000002',
      name: 'Remote S3 Collection',
      type: 's3',
      location: 'my-bucket/photos',
      state: 'closed',
      connector_guid: 'con_01hgw2bbg00000000000000001',
      pipeline_guid: 'pip_01hgw2bbg00000000000000001',
      pipeline_version: 1,
      pipeline_name: 'Standard RAW Workflow',
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
      guid: 'res_01hgw2bbg00000000000000001',
      external_id: 'res_01hgw2bbg00000000000000001',
      collection_guid: 'col_01hgw2bbg00000000000000001',
      collection_name: 'Test Collection',
      tool: 'photostats',
      pipeline_guid: null,
      pipeline_version: null,
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
      guid: 'res_01hgw2bbg00000000000000002',
      external_id: 'res_01hgw2bbg00000000000000002',
      collection_guid: 'col_01hgw2bbg00000000000000001',
      collection_name: 'Test Collection',
      tool: 'photo_pairing',
      pipeline_guid: null,
      pipeline_version: null,
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
      guid: 'res_01hgw2bbg00000000000000003',
      external_id: 'res_01hgw2bbg00000000000000003',
      collection_guid: 'col_01hgw2bbg00000000000000002',
      collection_name: 'Remote S3 Collection',
      tool: 'photostats',
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      status: 'FAILED',
      started_at: '2025-01-01T12:00:00Z',
      completed_at: '2025-01-01T12:00:30Z',
      duration_seconds: 30,
      files_scanned: 0,
      issues_found: 0,
      error_message: 'Connection timeout to S3 bucket',
      has_report: false,
      results: {
        total_size: 0,
        total_files: 0,
        file_counts: {},
        orphaned_images: [],
        orphaned_xmp: [],
      },
      created_at: '2025-01-01T12:00:00Z',
    },
    {
      guid: 'res_01hgw2bbg00000000000000004',
      external_id: 'res_01hgw2bbg00000000000000004',
      collection_guid: 'col_01hgw2bbg00000000000000002',
      collection_name: 'Remote S3 Collection',
      tool: 'pipeline_validation',
      pipeline_guid: 'pip_01hgw2bbg00000000000000001',
      pipeline_version: 1,
      pipeline_name: 'Standard RAW Workflow',
      status: 'COMPLETED',
      started_at: '2025-01-01T13:00:00Z',
      completed_at: '2025-01-01T13:05:00Z',
      duration_seconds: 300,
      files_scanned: 500,
      issues_found: 3,
      error_message: null,
      has_report: true,
      results: {
        consistency_counts: { CONSISTENT: 400, PARTIAL: 50, INCONSISTENT: 50 },
      },
      created_at: '2025-01-01T13:00:00Z',
    },
  ]
  nextConnectorId = 3
  nextCollectionId = 3
  nextJobNum = 1
  nextResultId = 5
  // Reset config data
  configData = {
    extensions: {
      photo_extensions: ['.dng', '.cr3', '.arw'],
      metadata_extensions: ['.xmp'],
      require_sidecar: ['.cr3'],
    },
    cameras: {
      'AB3D': { name: 'Canon EOS R5', serial_number: '12345' },
      'XY7Z': { name: 'Sony A7R IV', serial_number: '67890' },
    },
    processing_methods: {
      'HDR': 'High Dynamic Range',
      'BW': 'Black and White',
    },
    event_statuses: {
      'future': { label: 'Future', display_order: 0 },
      'confirmed': { label: 'Confirmed', display_order: 1 },
      'completed': { label: 'Completed', display_order: 2 },
      'cancelled': { label: 'Cancelled', display_order: 3 },
    },
    importSessions: {},
    lastImport: null,
  }
  // Reset categories
  categories = [
    {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Airshow',
      icon: 'plane',
      color: '#3B82F6',
      display_order: 0,
      is_active: true,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'cat_01hgw2bbg00000000000000002',
      name: 'Wildlife',
      icon: 'bird',
      color: '#22C55E',
      display_order: 1,
      is_active: true,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'cat_01hgw2bbg00000000000000003',
      name: 'Wedding',
      icon: 'heart',
      color: '#EC4899',
      display_order: 2,
      is_active: false,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ]
  nextCategoryNum = 4
  // Reset events
  events = [
    {
      guid: 'evt_01hgw2bbg00000000000000001',
      title: 'Oshkosh Airshow Day 1',
      event_date: '2026-07-27',
      start_time: '08:00:00',
      end_time: '18:00:00',
      is_all_day: false,
      input_timezone: 'America/Chicago',
      status: 'future',
      attendance: 'planned',
      category: {
        guid: 'cat_01hgw2bbg00000000000000001',
        name: 'Airshow',
        icon: 'plane',
        color: '#3B82F6',
      },
      location: null,
      series_guid: 'ser_01hgw2bbg00000000000000001',
      sequence_number: 1,
      series_total: 3,
      ticket_required: true,
      ticket_status: 'purchased',
      timeoff_required: true,
      timeoff_status: 'approved',
      travel_required: true,
      travel_status: 'booked',
      is_deadline: false,
      created_at: '2026-01-01T09:00:00Z',
      updated_at: '2026-01-01T09:00:00Z',
    },
    {
      guid: 'evt_01hgw2bbg00000000000000002',
      title: 'Oshkosh Airshow Day 2',
      event_date: '2026-07-28',
      start_time: '08:00:00',
      end_time: '18:00:00',
      is_all_day: false,
      input_timezone: 'America/Chicago',
      status: 'future',
      attendance: 'planned',
      category: {
        guid: 'cat_01hgw2bbg00000000000000001',
        name: 'Airshow',
        icon: 'plane',
        color: '#3B82F6',
      },
      location: null,
      series_guid: 'ser_01hgw2bbg00000000000000001',
      sequence_number: 2,
      series_total: 3,
      ticket_required: true,
      ticket_status: 'purchased',
      timeoff_required: true,
      timeoff_status: 'approved',
      travel_required: true,
      travel_status: 'booked',
      is_deadline: false,
      created_at: '2026-01-01T09:00:00Z',
      updated_at: '2026-01-01T09:00:00Z',
    },
    {
      guid: 'evt_01hgw2bbg00000000000000003',
      title: 'Wildlife Photography Workshop',
      event_date: '2026-03-15',
      start_time: '10:00:00',
      end_time: '16:00:00',
      is_all_day: false,
      input_timezone: 'America/New_York',
      status: 'future',
      attendance: 'planned',
      category: {
        guid: 'cat_01hgw2bbg00000000000000002',
        name: 'Wildlife',
        icon: 'bird',
        color: '#22C55E',
      },
      location: null,
      series_guid: null,
      sequence_number: null,
      series_total: null,
      ticket_required: false,
      ticket_status: null,
      timeoff_required: false,
      timeoff_status: null,
      travel_required: false,
      travel_status: null,
      is_deadline: false,
      created_at: '2026-01-01T09:00:00Z',
      updated_at: '2026-01-01T09:00:00Z',
    },
  ]
  nextEventNum = 4
  // Reset locations
  locations = [
    {
      guid: 'loc_01hgw2bbg00000000000000001',
      name: 'EAA Grounds',
      address: '3000 Poberezny Road',
      city: 'Oshkosh',
      state: 'Wisconsin',
      country: 'USA',
      postal_code: '54902',
      latitude: 43.9844,
      longitude: -88.5564,
      timezone: 'America/Chicago',
      category: {
        guid: 'cat_01hgw2bbg00000000000000001',
        name: 'Airshow',
        icon: 'plane',
        color: '#3B82F6',
      },
      rating: 5,
      timeoff_required_default: true,
      travel_required_default: true,
      notes: 'Annual EAA AirVenture event location',
      is_known: true,
      created_at: '2026-01-01T09:00:00Z',
      updated_at: '2026-01-01T09:00:00Z',
    },
    {
      guid: 'loc_01hgw2bbg00000000000000002',
      name: 'Yellowstone National Park',
      address: null,
      city: 'Yellowstone',
      state: 'Wyoming',
      country: 'USA',
      postal_code: null,
      latitude: 44.4280,
      longitude: -110.5885,
      timezone: 'America/Denver',
      category: {
        guid: 'cat_01hgw2bbg00000000000000002',
        name: 'Wildlife',
        icon: 'bird',
        color: '#22C55E',
      },
      rating: 5,
      timeoff_required_default: true,
      travel_required_default: true,
      notes: 'Great for wildlife photography',
      is_known: true,
      created_at: '2026-01-01T09:00:00Z',
      updated_at: '2026-01-01T09:00:00Z',
    },
  ]
  nextLocationNum = 3

  // Reset performers
  performers = [
    {
      guid: 'prf_01hgw2bbg00000000000000001',
      name: 'Blue Angels',
      website: 'https://blueangels.navy.mil',
      instagram_handle: 'usabordo_blueangels',
      instagram_url: 'https://instagram.com/usabordo_blueangels',
      category: {
        guid: 'cat_01hgw2bbg00000000000000001',
        name: 'Airshow',
        icon: 'plane',
        color: '#3B82F6',
      },
      additional_info: 'US Navy Flight Demonstration Squadron',
      created_at: '2026-01-10T09:00:00Z',
      updated_at: '2026-01-10T09:00:00Z',
    },
    {
      guid: 'prf_01hgw2bbg00000000000000002',
      name: 'Thunderbirds',
      website: 'https://thunderbirds.airforce.com',
      instagram_handle: 'afthunderbirds',
      instagram_url: 'https://instagram.com/afthunderbirds',
      category: {
        guid: 'cat_01hgw2bbg00000000000000001',
        name: 'Airshow',
        icon: 'plane',
        color: '#3B82F6',
      },
      additional_info: 'US Air Force Air Demonstration Squadron',
      created_at: '2026-01-10T09:00:00Z',
      updated_at: '2026-01-10T09:00:00Z',
    },
    {
      guid: 'prf_01hgw2bbg00000000000000003',
      name: 'Wildlife Photography Guide',
      website: null,
      instagram_handle: null,
      instagram_url: null,
      category: {
        guid: 'cat_01hgw2bbg00000000000000002',
        name: 'Wildlife',
        icon: 'bird',
        color: '#22C55E',
      },
      additional_info: 'Expert wildlife guide',
      created_at: '2026-01-10T09:00:00Z',
      updated_at: '2026-01-10T09:00:00Z',
    },
  ]
  nextPerformerNum = 4

  // Reset organizers
  organizers = [
    {
      guid: 'org_01hgw2bbg00000000000000001',
      name: 'USAF Demonstration Teams',
      website: 'https://usaf.com/demo',
      category: {
        guid: 'cat_01hgw2bbg00000000000000001',
        name: 'Airshow',
        icon: 'plane',
        color: '#3B82F6',
      },
      rating: 5,
      ticket_required_default: true,
      notes: 'Military demonstration team organizer',
      created_at: '2026-01-01T09:00:00Z',
      updated_at: '2026-01-01T09:00:00Z',
    },
    {
      guid: 'org_01hgw2bbg00000000000000002',
      name: 'National Wildlife Federation',
      website: 'https://nwf.org',
      category: {
        guid: 'cat_01hgw2bbg00000000000000002',
        name: 'Wildlife',
        icon: 'bird',
        color: '#22C55E',
      },
      rating: 4,
      ticket_required_default: false,
      notes: 'Conservation organization',
      created_at: '2026-01-01T10:00:00Z',
      updated_at: '2026-01-01T10:00:00Z',
    },
  ]
  nextOrganizerNum = 3
}
