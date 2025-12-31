import { http, HttpResponse } from 'msw';

// Mock data
let connectors = [
  {
    id: 1,
    name: 'Test S3 Connector',
    type: 's3',
    is_active: true,
    last_validated: '2025-01-01T10:00:00Z',
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T10:00:00Z',
  },
  {
    id: 2,
    name: 'Test GCS Connector',
    type: 'gcs',
    is_active: false,
    last_validated: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
];

let collections = [
  {
    id: 1,
    name: 'Test Collection',
    type: 'local',
    location: '/photos',
    state: 'live',
    connector_id: null,
    cache_ttl: 3600,
    is_accessible: true,
    last_error: null,
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
    last_error: null,
    created_at: '2025-01-01T09:00:00Z',
    updated_at: '2025-01-01T09:00:00Z',
  },
];

let nextConnectorId = 3;
let nextCollectionId = 3;

const BASE_URL = 'http://localhost:8000/api';

export const handlers = [
  // Connectors endpoints
  http.get(`${BASE_URL}/connectors`, () => {
    return HttpResponse.json(connectors);
  }),

  http.get(`${BASE_URL}/connectors/:id`, ({ params }) => {
    const connector = connectors.find((c) => c.id === Number(params.id));
    if (!connector) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(connector);
  }),

  http.post(`${BASE_URL}/connectors`, async ({ request }) => {
    const data = await request.json();
    const newConnector = {
      id: nextConnectorId++,
      ...data,
      is_active: data.is_active ?? true,
      last_validated: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    connectors.push(newConnector);
    return HttpResponse.json(newConnector, { status: 201 });
  }),

  http.put(`${BASE_URL}/connectors/:id`, async ({ params, request }) => {
    const data = await request.json();
    const index = connectors.findIndex((c) => c.id === Number(params.id));
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    connectors[index] = {
      ...connectors[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return HttpResponse.json(connectors[index]);
  }),

  http.delete(`${BASE_URL}/connectors/:id`, ({ params }) => {
    const id = Number(params.id);
    // Check if connector is referenced by collections (delete protection)
    const referencedBy = collections.filter((c) => c.connector_id === id);
    if (referencedBy.length > 0) {
      return HttpResponse.json(
        { detail: `Connector is referenced by ${referencedBy.length} collection(s)` },
        { status: 409 }
      );
    }
    const index = connectors.findIndex((c) => c.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    connectors.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${BASE_URL}/connectors/:id/test`, ({ params }) => {
    const connector = connectors.find((c) => c.id === Number(params.id));
    if (!connector) {
      return new HttpResponse(null, { status: 404 });
    }
    // Update last_validated
    const index = connectors.findIndex((c) => c.id === Number(params.id));
    connectors[index] = {
      ...connectors[index],
      last_validated: new Date().toISOString(),
    };
    return HttpResponse.json({ success: true, message: 'Connection successful' });
  }),

  // Collections endpoints
  http.get(`${BASE_URL}/collections`, () => {
    return HttpResponse.json(collections);
  }),

  http.get(`${BASE_URL}/collections/:id`, ({ params }) => {
    const collection = collections.find((c) => c.id === Number(params.id));
    if (!collection) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(collection);
  }),

  http.post(`${BASE_URL}/collections`, async ({ request }) => {
    const data = await request.json();
    // Validate connector exists for remote collections
    if (['s3', 'gcs', 'smb'].includes(data.type) && data.connector_id) {
      const connector = connectors.find((c) => c.id === data.connector_id);
      if (!connector) {
        return HttpResponse.json(
          { detail: 'Connector not found' },
          { status: 404 }
        );
      }
    }
    const newCollection = {
      id: nextCollectionId++,
      ...data,
      is_accessible: true,
      last_error: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    collections.push(newCollection);
    return HttpResponse.json(newCollection, { status: 201 });
  }),

  http.put(`${BASE_URL}/collections/:id`, async ({ params, request }) => {
    const data = await request.json();
    const index = collections.findIndex((c) => c.id === Number(params.id));
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    collections[index] = {
      ...collections[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return HttpResponse.json(collections[index]);
  }),

  http.delete(`${BASE_URL}/collections/:id`, ({ params, request }) => {
    const url = new URL(request.url);
    const forceDelete = url.searchParams.get('force_delete') === 'true';
    const id = Number(params.id);

    const index = collections.findIndex((c) => c.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
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
        );
      }
    }

    collections.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${BASE_URL}/collections/:id/test`, ({ params }) => {
    const collection = collections.find((c) => c.id === Number(params.id));
    if (!collection) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ success: true, message: 'Collection is accessible' });
  }),

  http.post(`${BASE_URL}/collections/:id/refresh`, ({ params, request }) => {
    const url = new URL(request.url);
    const confirm = url.searchParams.get('confirm') === 'true';
    const collection = collections.find((c) => c.id === Number(params.id));
    if (!collection) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      message: confirm ? 'Force refresh initiated' : 'Refresh initiated',
      task_id: 'mock-task-123',
    });
  }),
];

// Helper to reset mock data (useful for tests)
export function resetMockData() {
  connectors = [
    {
      id: 1,
      name: 'Test S3 Connector',
      type: 's3',
      is_active: true,
      last_validated: '2025-01-01T10:00:00Z',
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T10:00:00Z',
    },
    {
      id: 2,
      name: 'Test GCS Connector',
      type: 'gcs',
      is_active: false,
      last_validated: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ];
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
      last_error: null,
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
      last_error: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ];
  nextConnectorId = 3;
  nextCollectionId = 3;
}
