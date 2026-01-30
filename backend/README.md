# ShutterSense Backend

FastAPI backend for the ShutterSense.ai web application. Provides a comprehensive REST API for photo collection management, analysis pipeline configuration, distributed agent coordination, calendar event management, multi-tenant authentication, and push notifications -- all backed by PostgreSQL with encrypted credential storage.

## Features

- **Remote Storage Connectors**: Manage S3, GCS, and SMB/CIFS connections with Fernet-encrypted credentials
- **Cloud Inventory Import**: S3 Inventory and GCS Storage Insights integration for large-scale bucket scanning
- **Photo Collections**: Track local and remote photo collections with accessibility monitoring and file listing cache
- **Analysis Pipelines**: Configure and manage validation rule pipelines with version history
- **Distributed Agent Execution**: Coordinate analysis jobs across lightweight ShutterSense agents with heartbeat monitoring, load balancing, and chunked result uploads
- **Calendar Events**: Full event management with categories, locations, organizers, performers, series, and deadline tracking
- **Trend Analytics**: Historical analysis data, storage metrics, and trend aggregation across collections
- **Push Notifications**: Web Push (VAPID) notifications for agent status changes, job completions, and event deadline reminders
- **OAuth 2.0 Authentication**: Google and Microsoft login with session-based cookies and JWT API tokens
- **Multi-Tenancy**: Team-based data isolation with tenant-scoped queries across all services
- **Security Hardening**: Rate limiting, request size limits, security headers (CSP, X-Frame-Options), and SQL injection prevention
- **SPA Serving**: Single-port deployment serving both the REST API and the React frontend from the same server
- **RESTful API**: Comprehensive REST API with OpenAPI/Swagger documentation and tagged endpoint groups

## Tech Stack

- **Python 3.10+** -- Required for match/case syntax and modern type hinting
- **FastAPI** -- Modern web framework with automatic OpenAPI documentation
- **PostgreSQL 12+** -- Primary database with JSONB support (SQLite for tests)
- **SQLAlchemy 2.0** -- ORM with connection pooling
- **Alembic** -- Database migrations
- **Pydantic v2** -- Data validation and serialization (with pydantic-settings)
- **Authlib** -- OAuth 2.0/OpenID Connect client (Google, Microsoft)
- **python-jose** -- JWT encoding/decoding for API tokens
- **slowapi** -- Rate limiting middleware
- **cryptography** -- Fernet encryption for credential storage
- **pywebpush** -- Web Push protocol with VAPID authentication
- **boto3** -- AWS S3 and S3 Inventory integration
- **google-cloud-storage** -- GCS and Storage Insights integration
- **smbprotocol** -- SMB/CIFS network share access
- **geopy / timezonefinder** -- Geocoding and timezone lookup for locations
- **Pytest** -- Testing framework with 2,475 tests across 110 test files

## Project Structure

```
backend/
├── src/
│   ├── api/                           # FastAPI route handlers (20 files)
│   │   ├── collections.py            # Collection CRUD, accessibility, cache refresh
│   │   ├── connectors.py             # Connector CRUD, test connection, inventory
│   │   ├── pipelines.py              # Pipeline CRUD, activation, validation, preview
│   │   ├── events.py                 # Event CRUD, series, date range filters
│   │   ├── categories.py             # Event category taxonomy
│   │   ├── locations.py              # Event location/venue management
│   │   ├── organizers.py             # Event organizer management
│   │   ├── performers.py             # Event performer management
│   │   ├── tools.py                  # Job execution, queue status, WebSocket progress
│   │   ├── results.py                # Analysis result storage, download, stats
│   │   ├── trends.py                 # Trend data and aggregation
│   │   ├── analytics.py              # Storage metrics and usage analytics
│   │   ├── config.py                 # Application configuration (extensions, etc.)
│   │   ├── notifications.py          # Push subscriptions, notification CRUD, preferences
│   │   ├── auth.py                   # OAuth 2.0 login/callback/logout
│   │   ├── users.py                  # User profile, invite, deactivate/reactivate
│   │   ├── tokens.py                 # API token CRUD and revocation
│   │   ├── admin/
│   │   │   ├── teams.py              # Super admin: team management
│   │   │   └── release_manifests.py  # Super admin: agent binary attestation
│   │   └── agent/
│   │       ├── routes.py             # Agent registration, heartbeat, job claim/complete
│   │       ├── schemas.py            # Agent-specific Pydantic schemas
│   │       └── dependencies.py       # Agent authentication dependencies
│   ├── auth/
│   │   └── oauth_client.py           # OAuth 2.0 client configuration
│   ├── config/
│   │   ├── settings.py               # AppSettings (JWT, VAPID, job config)
│   │   ├── session.py                # SessionSettings (cookie config)
│   │   ├── oauth.py                  # OAuth provider configuration
│   │   └── super_admins.py           # Super admin email list
│   ├── db/
│   │   ├── database.py               # Database connection and session management
│   │   └── migrations/               # Alembic database migrations
│   ├── middleware/
│   │   ├── auth.py                   # Session + API token authentication
│   │   └── tenant.py                 # TenantContext and team_id scoping
│   ├── models/                        # SQLAlchemy ORM models (25 files)
│   │   ├── agent.py                  # Agent entity (status, heartbeat, capabilities)
│   │   ├── agent_registration_token.py  # Agent registration tokens
│   │   ├── analysis_result.py        # Analysis results with JSONB payload
│   │   ├── api_token.py              # JWT API tokens
│   │   ├── category.py               # Event categories
│   │   ├── collection.py             # Photo collections (local + remote)
│   │   ├── configuration.py          # Key-value configuration store
│   │   ├── connector.py              # Storage connectors (S3, GCS, SMB)
│   │   ├── event.py                  # Calendar events with deadlines
│   │   ├── event_performer.py        # Event-performer many-to-many
│   │   ├── event_series.py           # Recurring event series
│   │   ├── inventory_folder.py       # Cloud inventory folder tracking
│   │   ├── job.py                    # Job queue entries
│   │   ├── location.py              # Event locations with geocoding
│   │   ├── notification.py           # In-app notifications
│   │   ├── organizer.py              # Event organizers
│   │   ├── performer.py              # Event performers
│   │   ├── pipeline.py               # Validation pipelines
│   │   ├── pipeline_history.py       # Pipeline version history
│   │   ├── push_subscription.py      # Web Push subscriptions
│   │   ├── release_manifest.py       # Agent binary release manifests
│   │   ├── storage_metrics.py        # Storage usage tracking
│   │   ├── team.py                   # Multi-tenant teams
│   │   ├── user.py                   # User accounts
│   │   ├── types.py                  # Shared SQLAlchemy types/enums
│   │   └── mixins/
│   │       └── guid.py               # ExternalIdMixin for GUID generation
│   ├── schemas/                       # Pydantic request/response schemas (20 files)
│   │   ├── collection.py             # Collection schemas
│   │   ├── config.py                 # Configuration schemas
│   │   ├── category.py               # Category schemas
│   │   ├── event.py                  # Event schemas
│   │   ├── event_series.py           # Event series schemas
│   │   ├── guid.py                   # GUID validation schemas
│   │   ├── inventory.py              # Inventory import schemas
│   │   ├── location.py               # Location schemas
│   │   ├── notifications.py          # Notification/push schemas
│   │   ├── organizer.py              # Organizer schemas
│   │   ├── performer.py              # Performer schemas
│   │   ├── pipelines.py              # Pipeline schemas
│   │   ├── results.py                # Result schemas
│   │   ├── retention.py              # Data retention schemas
│   │   ├── team.py                   # Team schemas
│   │   ├── tools.py                  # Tool execution schemas
│   │   ├── trends.py                 # Trend schemas
│   │   └── user.py                   # User schemas
│   ├── services/                      # Business logic layer (31+ files)
│   │   ├── agent_service.py          # Agent registration, heartbeat, offline detection
│   │   ├── auth_service.py           # OAuth user resolution and session management
│   │   ├── category_service.py       # Category CRUD
│   │   ├── chunked_upload_service.py # Multi-part chunked result uploads
│   │   ├── cleanup_service.py        # Data cleanup and maintenance
│   │   ├── collection_service.py     # Collection CRUD, accessibility, binding
│   │   ├── config_loader.py          # YAML configuration loading
│   │   ├── config_service.py         # Configuration CRUD and seeding
│   │   ├── connector_service.py      # Connector CRUD, encryption, test connection
│   │   ├── event_service.py          # Event CRUD, series, stats
│   │   ├── exceptions.py             # Shared service exceptions
│   │   ├── geocoding_service.py      # Nominatim geocoding + timezone lookup
│   │   ├── guid.py                   # GuidService (UUIDv7 + Crockford Base32)
│   │   ├── input_state_service.py    # Form input state management
│   │   ├── inventory_service.py      # Cloud inventory import processing
│   │   ├── job_coordinator_service.py # Job creation, assignment, load balancing
│   │   ├── location_service.py       # Location CRUD with geocoding
│   │   ├── notification_service.py   # Notification creation, push delivery, deadlines
│   │   ├── organizer_service.py      # Organizer CRUD
│   │   ├── performer_service.py      # Performer CRUD
│   │   ├── pipeline_service.py       # Pipeline CRUD, activation, validation
│   │   ├── push_subscription_service.py # Web Push subscription management
│   │   ├── result_service.py         # Result storage, retrieval, report download
│   │   ├── retention_service.py      # Data retention policy enforcement
│   │   ├── seed_data_service.py      # Default data seeding for new teams
│   │   ├── storage_metrics_service.py # Storage analytics and metrics
│   │   ├── team_service.py           # Team CRUD and administration
│   │   ├── token_service.py          # API token generation and validation
│   │   ├── tool_service.py           # Tool execution orchestration
│   │   ├── trend_service.py          # Trend aggregation across tools
│   │   ├── user_service.py           # User management and invitation
│   │   └── remote/                   # Storage adapters
│   │       ├── base.py               # StorageAdapter abstract base class
│   │       ├── s3_adapter.py         # AWS S3 storage adapter
│   │       ├── gcs_adapter.py        # Google Cloud Storage adapter
│   │       └── smb_adapter.py        # SMB/CIFS storage adapter
│   ├── utils/
│   │   ├── cache.py                  # In-memory file listing cache with TTL
│   │   ├── crypto.py                 # Credential encryption/decryption (Fernet)
│   │   ├── file_listing.py           # File listing utilities
│   │   ├── formatting.py            # Output formatting helpers
│   │   ├── job_queue.py              # In-memory background job queue
│   │   ├── logging_config.py         # Structured logging configuration
│   │   ├── pipeline_adapter.py       # Pipeline rule adaptation
│   │   ├── security_settings.py      # SPA path validation and security
│   │   └── websocket.py              # WebSocket connection manager
│   ├── scripts/
│   │   └── seed_first_team.py        # Bootstrap script for first team setup
│   └── main.py                        # FastAPI application entry point
├── tests/
│   ├── unit/                          # Unit tests (~1,882 test functions)
│   │   ├── api/                      # API-level unit tests
│   │   ├── models/                   # Model-level unit tests
│   │   ├── schemas/                  # Schema validation tests
│   │   ├── services/                 # Service-level unit tests
│   │   └── test_*.py                 # Component tests (59 files)
│   ├── integration/                   # Integration tests (~578 test functions)
│   │   ├── api/                      # API integration tests
│   │   └── test_*.py                 # Workflow tests (39 files)
│   └── conftest.py                    # Shared pytest fixtures
├── requirements.txt                   # Python dependencies
├── alembic.ini                        # Alembic migration config
└── README.md                          # This file
```

## Setup and Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12+ (for production) or SQLite (for testing)
- Virtual environment (recommended)

### Installation

1. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables** (see [Environment Variables](#environment-variables) for the full list):
   ```bash
   # Required
   export SHUSAI_MASTER_KEY="your-fernet-key-here"
   export SHUSAI_DB_URL="postgresql://user:password@localhost:5432/shuttersense"

   # Authentication (required for OAuth login)
   export SESSION_SECRET_KEY="your-session-secret-key"
   export JWT_SECRET_KEY="your-jwt-secret-key-at-least-32-chars"

   # Optional
   export SHUSAI_ENV="development"
   export SHUSAI_LOG_LEVEL="INFO"
   ```

   To generate a master encryption key:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   To generate a session/JWT secret key:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. **Run database migrations**:
   ```bash
   cd backend
   alembic upgrade head
   ```

5. **Seed the first team** (optional, for initial setup):
   ```bash
   python3 -m backend.src.scripts.seed_first_team
   ```

## Running the Application

### Development Server

```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000/api
- **OpenAPI docs (Swagger UI)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **Health check**: http://localhost:8000/health
- **Version**: http://localhost:8000/api/version

### Production Server

```bash
cd backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use Gunicorn with Uvicorn workers:
```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Background Tasks

The application automatically starts two background tasks on startup:

1. **Dead Agent Safety Net** -- Runs every 120 seconds, detecting agents with stale heartbeats and marking them offline. Triggers `pool_offline` notifications when a team loses all agents.
2. **Deadline Check Scheduler** -- Runs every hour, scanning for approaching event deadlines and sending push notification reminders based on user preferences.

## Testing

The backend has comprehensive test coverage with **2,475 tests** across **110 test files** (1,882 unit + 578 integration).

### Running Tests

#### Run all tests
```bash
cd backend
python -m pytest tests/ -v
```

#### Run unit tests only
```bash
python -m pytest tests/unit/ -v
```

#### Run integration tests only
```bash
python -m pytest tests/integration/ -v
```

#### Run specific test file
```bash
python -m pytest tests/unit/test_connector_service.py -v
```

#### Run specific test class or function
```bash
# Run a specific test class
python -m pytest tests/unit/test_connector_service.py::TestConnectorServiceCreate -v

# Run a specific test function
python -m pytest tests/unit/test_connector_service.py::TestConnectorServiceCreate::test_create_connector_with_encryption -v
```

#### Run tests matching a pattern
```bash
# Run all tests with "delete" in the name
python -m pytest tests/ -k "delete" -v

# Run all agent-related tests
python -m pytest tests/ -k "agent" -v

# Run all notification tests
python -m pytest tests/ -k "notification" -v
```

#### Run with detailed output
```bash
# Show print statements
python -m pytest tests/ -v -s

# Show local variables on failure
python -m pytest tests/ -v -l

# Stop on first failure
python -m pytest tests/ -v -x
```

### Coverage Reporting

#### Generate coverage report
```bash
# Run tests with coverage
python -m pytest tests/ --cov=backend.src --cov-report=term-missing

# Generate HTML coverage report
python -m pytest tests/ --cov=backend.src --cov-report=html

# Open HTML report (macOS)
open htmlcov/index.html

# Open HTML report (Linux)
xdg-open htmlcov/index.html
```

#### Coverage targets
- **Overall**: >80% (constitution requirement)
- **Core business logic**: >80% (services, models, utils)
- **API endpoints**: >80% (API route handlers)
- **Utilities**: >85% (cache, crypto, job queue)

#### Check coverage for specific module
```bash
# Coverage for connector service only
python -m pytest tests/unit/test_connector_service.py --cov=backend.src.services.connector_service --cov-report=term-missing

# Coverage for all services
python -m pytest tests/unit/test_*_service.py --cov=backend.src.services --cov-report=term-missing
```

### Test Organization

#### Unit Tests (`tests/unit/`)

Test individual components in isolation with mocked dependencies. Key test files include:

**Utilities:**
- `test_crypto.py` -- CredentialEncryptor (encryption/decryption, key validation)
- `test_cache.py` -- FileListingCache (get/set/invalidate, TTL expiry, concurrency)
- `test_job_queue.py` -- JobQueue (enqueue/dequeue, FIFO, status transitions)
- `test_file_listing.py` -- File listing utilities
- `test_security_settings.py` -- SPA path validation, security settings
- `test_security.py` -- Security headers, CORS, rate limiting
- `test_guid_service.py` -- GUID generation and validation

**Storage Adapters:**
- `test_s3_adapter.py` -- S3Adapter (list_files, test_connection, retry logic)
- `test_gcs_adapter.py` -- GCSAdapter (list_files, service account validation)
- `test_smb_adapter.py` -- SMBAdapter (list_files, credential validation)

**Core Services:**
- `test_connector_service.py` -- Connector CRUD, encryption, deletion protection
- `test_collection_service.py` -- Collection CRUD, accessibility, cache management
- `test_pipeline_service.py` -- Pipeline CRUD, activation, validation
- `test_result_service.py` -- Result storage and retrieval
- `test_trend_service.py` -- Trend aggregation
- `test_tool_service.py` -- Tool execution orchestration
- `test_config_service.py` -- Configuration management
- `test_storage_metrics_service.py` -- Storage analytics
- `test_retention_service.py` -- Data retention policies
- `test_cleanup_service.py` -- Cleanup operations

**Event Domain:**
- `test_category_service.py` -- Category CRUD
- `test_location_service.py` -- Location CRUD with geocoding
- `test_organizer_service.py` -- Organizer CRUD
- `test_performer_service.py` -- Performer CRUD
- `test_geocoding_service.py` -- Nominatim geocoding integration

**Authentication & Multi-Tenancy:**
- `test_auth_service.py` -- OAuth user resolution
- `test_user_service.py` -- User management
- `test_team_service.py` -- Team management
- `test_token_service.py` -- API token generation/validation
- `test_input_state_service.py` -- Form state management

**Agent & Job System:**
- `test_agent_service.py` -- Agent registration, heartbeat, status
- `test_agent_auth.py` -- Agent authentication
- `test_agent_collection_create.py` -- Agent collection creation
- `test_agent_notification_triggers.py` -- Agent notification triggers
- `test_job_cancellation.py` -- Job cancellation flows

**Notifications:**
- `test_notification_service.py` -- Notification creation and delivery
- `test_notification_triggers.py` -- Notification trigger conditions
- `test_notifications_api.py` -- Notification API endpoints
- `test_push_subscription_service.py` -- Push subscription management

**API Endpoints:**
- `test_api_collections.py` -- Collection API (HTTP status codes, validation)
- `test_api_connectors.py` -- Connector API (filters, CRUD)
- `test_api_pipelines.py` -- Pipeline API
- `test_api_results.py` -- Results API
- `test_api_trends.py` -- Trends API
- `test_api_tools.py` -- Tool execution API
- `test_api_config.py` -- Configuration API
- `test_api_analytics.py` -- Analytics API
- `test_api_tokens.py` -- Token API
- `test_api_guids.py` -- GUID validation in APIs

**Unit Test Subdirectories:**
- `api/test_admin_release_manifests.py` -- Release manifest admin API
- `models/` -- Model tests (agent, collection, connector, inventory, job, release manifest)
- `schemas/` -- Schema validation tests (inventory)
- `services/` -- Service tests (agent metrics, agent pool, chunked upload, config loader, inventory, job coordinator, load balancing, scheduled jobs)

#### Integration Tests (`tests/integration/`)

Test end-to-end workflows across multiple services and API endpoints. Key test files include:

**Core Workflows:**
- `test_connector_collection_flow.py` -- Connector-collection lifecycle
- `test_collection_accessibility_job.py` -- Collection accessibility checking
- `test_collection_binding.py` -- Collection-agent binding
- `test_tool_execution_flow.py` -- Full tool execution lifecycle
- `test_no_change_flow.py` -- No-change detection flow
- `test_trend_aggregation.py` -- Trend data aggregation
- `test_chunked_upload.py` -- Multi-part upload workflow

**Agent System:**
- `test_agent_registration.py` -- Agent registration flow
- `test_agent_heartbeat.py` -- Agent heartbeat protocol
- `test_agent_detail.py` -- Agent detail retrieval
- `test_agent_admin_api.py` -- Agent admin operations
- `test_agent_authorized_roots.py` -- Authorized root path validation
- `test_agent_connector_api.py` -- Agent connector access
- `test_agent_progress_ws.py` -- WebSocket progress streaming
- `test_attestation_flow.py` -- Binary attestation verification
- `test_multi_agent.py` -- Multi-agent coordination
- `test_pool_status_api.py` -- Agent pool status API
- `test_pool_status_ws.py` -- Agent pool status WebSocket

**Job System:**
- `test_job_claim.py` -- Job claiming protocol
- `test_job_complete.py` -- Job completion flow
- `test_job_management.py` -- Job lifecycle management
- `test_job_progress.py` -- Job progress tracking
- `test_scheduled_jobs.py` -- Scheduled job execution

**Events & Directory:**
- `test_events_api.py` -- Event CRUD and series
- `test_categories_api.py` -- Category management
- `test_locations_api.py` -- Location management
- `test_organizers_api.py` -- Organizer management
- `test_performers_api.py` -- Performer management

**Authentication & Administration:**
- `test_oauth_flow.py` -- OAuth login/callback flow
- `test_tenant_isolation.py` -- Multi-tenant data isolation
- `test_teams_api.py` -- Team administration
- `test_user_management.py` -- User lifecycle
- `test_seed_script.py` -- First team seeding

**Configuration & Inventory:**
- `test_config_api.py` -- Configuration API
- `test_config_import.py` -- Configuration import
- `test_cleanup_integration.py` -- Cleanup operations
- `api/test_inventory_api.py` -- Inventory import API
- `api/test_inventory_validation_flow.py` -- Inventory validation
- `test_guid.py` -- GUID generation integration

#### Fixtures (`tests/conftest.py`)

Shared pytest fixtures for consistent test setup:

- **Database fixtures**: `test_db_engine`, `test_db_session`
- **Utility fixtures**: `test_encryptor`, `test_cache`, `test_job_queue`
- **Service fixtures**: `test_connector_service`, `test_file_cache`
- **Sample data factories**: `sample_connector_data`, `sample_collection_data`
- **Mocked adapters**: `mock_s3_client`, `mock_gcs_client`, `mock_smb_connection`
- **FastAPI client**: `test_client` with dependency overrides
- **Tenant context**: Fixtures providing mock `TenantContext` with team isolation

### Test Dependencies

Test-specific dependencies (included in `requirements.txt`):

- **pytest** -- Testing framework
- **pytest-cov** -- Coverage reporting
- **pytest-mock** -- Mocking support
- **pytest-asyncio** -- Async test support
- **freezegun** -- Time mocking for cache TTL and deadline tests
- **httpx** -- Testing FastAPI endpoints (TestClient)

### Running Tests in CI/CD

Example GitHub Actions workflow:

```yaml
- name: Run tests with coverage
  run: |
    cd backend
    python -m pytest tests/ --cov=backend.src --cov-report=xml --cov-report=term-missing

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./backend/coverage.xml
```

## Database Migrations

### Create a new migration

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Migration best practices

- Review autogenerated migrations before applying
- Test migrations on a development database first
- Include both upgrade and downgrade operations
- Use descriptive migration messages
- Avoid data migrations in schema migrations when possible

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SHUSAI_MASTER_KEY` | Fernet encryption key for credential storage (44 chars, base64-encoded) |
| `SHUSAI_DB_URL` | PostgreSQL connection URL (e.g., `postgresql://user:pass@localhost:5432/shuttersense`) |

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SHUSAI_ENV` | `development` | Environment name (`development` or `production`) |
| `SHUSAI_LOG_LEVEL` | `INFO` | Logging level (`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`) |
| `SHUSAI_LOG_DIR` | (platform default) | Directory for log file output |
| `SHUSAI_SPA_DIST_PATH` | `frontend/dist` | Path to the built SPA distribution directory |
| `SHUSAI_AUTHORIZED_LOCAL_ROOTS` | (empty) | Comma-separated list of authorized root paths for local collections (security) |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated list of allowed CORS origins |

### Authentication (OAuth 2.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_SECRET_KEY` | (empty) | Secret key for signing session cookies (min 32 chars; required for OAuth) |
| `SESSION_MAX_AGE` | `86400` (24h) | Session duration in seconds (min 60, max 30 days) |
| `SESSION_COOKIE_NAME` | `shusai_session` | Name of the session cookie |
| `SESSION_SAME_SITE` | `lax` | SameSite cookie attribute (`lax`, `strict`, `none`) |
| `SESSION_HTTPS_ONLY` | `false` | Require HTTPS for session cookies (set `true` in production) |
| `SESSION_PATH` | `/` | Cookie path |

### API Tokens (JWT)

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | (empty) | Secret key for signing JWT API tokens (min 32 chars) |
| `JWT_TOKEN_EXPIRY_DAYS` | `90` | Default token expiry in days (1-365) |

### Web Push Notifications (VAPID)

| Variable | Default | Description |
|----------|---------|-------------|
| `VAPID_PUBLIC_KEY` | (empty) | Base64url-encoded VAPID public key |
| `VAPID_PRIVATE_KEY` | (empty) | Base64url-encoded VAPID private key |
| `VAPID_SUBJECT` | (empty) | VAPID subject identifier (`mailto:` or `https:` URL) |

### Job Execution

| Variable | Default | Description |
|----------|---------|-------------|
| `INMEMORY_JOB_TYPES` | (empty) | Comma-separated tool types to run in-memory on the server (e.g., `photostats,photo_pairing`). By default all jobs are dispatched to agents. |

### Example `.env` file

```bash
# backend/.env

# Required
SHUSAI_MASTER_KEY=your-fernet-key-here
SHUSAI_DB_URL=postgresql://shuttersense:password@localhost:5432/shuttersense

# Application
SHUSAI_ENV=development
SHUSAI_LOG_LEVEL=DEBUG
SHUSAI_AUTHORIZED_LOCAL_ROOTS=/home/user/photos,/mnt/storage

# Authentication
SESSION_SECRET_KEY=your-session-secret-key-at-least-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-at-least-32-chars

# CORS (for frontend dev server)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Web Push (optional -- generate with: npx web-push generate-vapid-keys)
VAPID_PUBLIC_KEY=BPubKeyBase64...
VAPID_PRIVATE_KEY=PrivKeyBase64...
VAPID_SUBJECT=mailto:admin@example.com
```

Load with:
```bash
source backend/.env  # Or use python-dotenv (automatically loaded by pydantic-settings)
```

## API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs (with Bearer token authorization)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Authentication

The API supports two authentication methods:

1. **Session cookies** -- For browser-based OAuth login (Google, Microsoft)
2. **Bearer tokens** -- For programmatic API access (`Authorization: Bearer <token>`)

Public endpoints (no auth required): `/health`, `/api/version`, `/api/auth/*`

### Endpoint Reference

All entity endpoints use GUIDs (e.g., `col_01hgw2bbg...`) as path parameters, never internal numeric IDs.

#### Collections
- `GET /api/collections` -- List collections (with filters)
- `POST /api/collections` -- Create collection
- `GET /api/collections/stats` -- Get collection statistics (KPIs)
- `GET /api/collections/{guid}` -- Get collection by GUID
- `PUT /api/collections/{guid}` -- Update collection
- `DELETE /api/collections/{guid}` -- Delete collection
- `POST /api/collections/{guid}/test` -- Test collection accessibility
- `POST /api/collections/{guid}/refresh` -- Refresh file listing cache

#### Connectors
- `GET /api/connectors` -- List connectors (with filters)
- `POST /api/connectors` -- Create connector
- `GET /api/connectors/stats` -- Get connector statistics
- `GET /api/connectors/{guid}` -- Get connector by GUID
- `PUT /api/connectors/{guid}` -- Update connector
- `DELETE /api/connectors/{guid}` -- Delete connector (protected if collections exist)
- `POST /api/connectors/{guid}/test` -- Test connector connection
- `GET /api/connectors/{guid}/inventory/*` -- S3 Inventory / GCS Storage Insights endpoints

#### Pipelines
- `GET /api/pipelines` -- List pipelines
- `POST /api/pipelines` -- Create pipeline
- `GET /api/pipelines/stats` -- Get pipeline statistics
- `GET /api/pipelines/{guid}` -- Get pipeline by GUID
- `PUT /api/pipelines/{guid}` -- Update pipeline
- `DELETE /api/pipelines/{guid}` -- Delete pipeline
- `POST /api/pipelines/{guid}/activate` -- Activate pipeline
- `POST /api/pipelines/{guid}/deactivate` -- Deactivate pipeline
- `POST /api/pipelines/{guid}/set-default` -- Set as default pipeline
- `POST /api/pipelines/{guid}/unset-default` -- Unset as default pipeline
- `POST /api/pipelines/{guid}/validate` -- Validate pipeline rules
- `POST /api/pipelines/{guid}/preview` -- Preview filenames against pipeline
- `GET /api/pipelines/{guid}/history` -- Get pipeline version history
- `GET /api/pipelines/{guid}/history/{version}` -- Get specific pipeline version

#### Events
- `GET /api/events` -- List events (with date range, category, status filters)
- `POST /api/events` -- Create standalone event
- `POST /api/events/series` -- Create event series (multiple dates)
- `GET /api/events/stats` -- Get event statistics (KPIs)
- `GET /api/events/{guid}` -- Get event details
- `PATCH /api/events/{guid}` -- Update event (supports series scope)
- `DELETE /api/events/{guid}` -- Soft-delete event

#### Categories
- `GET /api/categories` -- List categories
- `POST /api/categories` -- Create category
- `GET /api/categories/{guid}` -- Get category details
- `PATCH /api/categories/{guid}` -- Update category
- `DELETE /api/categories/{guid}` -- Delete category

#### Locations
- `GET /api/locations` -- List locations
- `POST /api/locations` -- Create location (with optional geocoding)
- `GET /api/locations/{guid}` -- Get location details
- `PATCH /api/locations/{guid}` -- Update location
- `DELETE /api/locations/{guid}` -- Delete location

#### Organizers
- `GET /api/organizers` -- List organizers
- `POST /api/organizers` -- Create organizer
- `GET /api/organizers/{guid}` -- Get organizer details
- `PATCH /api/organizers/{guid}` -- Update organizer
- `DELETE /api/organizers/{guid}` -- Delete organizer

#### Performers
- `GET /api/performers` -- List performers
- `POST /api/performers` -- Create performer
- `GET /api/performers/{guid}` -- Get performer details
- `PATCH /api/performers/{guid}` -- Update performer
- `DELETE /api/performers/{guid}` -- Delete performer
- `POST /api/events/{guid}/performers` -- Link performer to event
- `DELETE /api/events/{guid}/performers/{performer_guid}` -- Unlink performer

#### Tools (Job Execution)
- `POST /api/tools/run` -- Run analysis tool against a collection
- `POST /api/tools/run-all` -- Run all tools against a collection
- `GET /api/tools/jobs` -- List jobs (with status filters)
- `GET /api/tools/jobs/{guid}` -- Get job details
- `POST /api/tools/jobs/{guid}/cancel` -- Cancel a running job
- `POST /api/tools/jobs/{guid}/retry` -- Retry a failed job
- `GET /api/tools/queue-status` -- Get job queue status
- `WS /api/ws/jobs/all` -- WebSocket: global job progress stream
- `WS /api/ws/jobs/{job_id}` -- WebSocket: per-job progress stream

#### Results
- `GET /api/results` -- List analysis results (with filters)
- `GET /api/results/stats` -- Get result statistics
- `GET /api/results/{guid}` -- Get result details
- `DELETE /api/results/{guid}` -- Delete result
- `GET /api/results/{guid}/report` -- Download HTML report

#### Trends
- `GET /api/trends/photostats` -- PhotoStats trend data
- `GET /api/trends/photo-pairing` -- Photo Pairing trend data
- `GET /api/trends/pipeline-validation` -- Pipeline Validation trend data
- `GET /api/trends/display-graph` -- Display graph trend data
- `GET /api/trends/summary` -- Trend summary across all tools

#### Analytics
- `GET /api/analytics/storage` -- Storage usage metrics and statistics

#### Configuration
- `GET /api/config` -- Get current configuration
- `PUT /api/config` -- Update configuration

#### Notifications
- `POST /api/notifications/push/subscribe` -- Subscribe to Web Push notifications
- `DELETE /api/notifications/push/subscribe` -- Unsubscribe from push
- `GET /api/notifications/push/status` -- Get subscription status
- `GET /api/notifications/preferences` -- Get notification preferences
- `PUT /api/notifications/preferences` -- Update notification preferences
- `GET /api/notifications` -- List notifications (with pagination)
- `GET /api/notifications/stats` -- Get notification statistics
- `GET /api/notifications/unread-count` -- Get unread notification count
- `POST /api/notifications/{guid}/read` -- Mark notification as read
- `POST /api/notifications/check-deadlines` -- Trigger deadline check (admin)
- `GET /api/notifications/vapid-key` -- Get VAPID public key

#### Authentication
- `GET /api/auth/providers` -- List configured OAuth providers
- `GET /api/auth/login/{provider}` -- Initiate OAuth login
- `GET /api/auth/callback/{provider}` -- OAuth callback handler
- `GET /api/auth/me` -- Get current user profile
- `POST /api/auth/logout` -- Logout (clear session)
- `GET /api/auth/status` -- Check authentication status

#### Users
- `POST /api/users` -- Invite a new user
- `GET /api/users` -- List users
- `GET /api/users/stats` -- Get user statistics
- `GET /api/users/{guid}` -- Get user details
- `DELETE /api/users/{guid}` -- Delete pending user
- `POST /api/users/{guid}/deactivate` -- Deactivate user
- `POST /api/users/{guid}/reactivate` -- Reactivate user

#### API Tokens
- `POST /api/tokens` -- Create API token
- `GET /api/tokens` -- List API tokens
- `GET /api/tokens/stats` -- Get token statistics
- `GET /api/tokens/{guid}` -- Get token details
- `DELETE /api/tokens/{guid}` -- Revoke token

#### Agent API (Internal)
- `POST /api/agent/v1/register` -- Register new agent
- `POST /api/agent/v1/heartbeat` -- Send heartbeat
- `GET /api/agent/v1/me` -- Get current agent info
- `POST /api/agent/v1/disconnect` -- Disconnect agent
- `POST /api/agent/v1/jobs/claim` -- Claim next available job
- `POST /api/agent/v1/jobs/{guid}/progress` -- Report job progress
- `POST /api/agent/v1/jobs/{guid}/no-change` -- Complete job with no change
- `POST /api/agent/v1/jobs/{guid}/complete` -- Complete job with results
- `POST /api/agent/v1/jobs/{guid}/fail` -- Report job failure
- `GET /api/agent/v1/jobs/{guid}/config` -- Get job configuration
- `GET /api/agent/v1/config` -- Get team configuration for agent
- `POST /api/agent/v1/uploads/initiate` -- Initiate chunked upload
- `PUT /api/agent/v1/uploads/{upload_id}/chunks/{chunk_number}` -- Upload chunk
- `GET /api/agent/v1/uploads/{upload_id}/status` -- Get upload status
- `POST /api/agent/v1/uploads/{upload_id}/finalize` -- Finalize upload
- `DELETE /api/agent/v1/uploads/{upload_id}` -- Cancel upload
- `POST /api/agent/v1/registration-tokens` -- Create registration token
- `GET /api/agent/v1/registration-tokens` -- List registration tokens
- `DELETE /api/agent/v1/registration-tokens/{guid}` -- Delete registration token
- `GET /api/agent/v1/agents` -- List agents
- `GET /api/agent/v1/pool-status` -- Get agent pool status
- `GET /api/agent/v1/connectors` -- List connectors (agent view)

#### Admin API (Super Admin Only)
- `POST /api/admin/teams` -- Create team
- `GET /api/admin/teams` -- List teams
- `GET /api/admin/teams/stats` -- Get team statistics
- `GET /api/admin/teams/{guid}` -- Get team details
- `POST /api/admin/teams/{guid}/deactivate` -- Deactivate team
- `POST /api/admin/teams/{guid}/reactivate` -- Reactivate team
- `POST /api/admin/release-manifests` -- Create release manifest
- `GET /api/admin/release-manifests` -- List release manifests
- `GET /api/admin/release-manifests/stats` -- Get manifest statistics
- `GET /api/admin/release-manifests/{guid}` -- Get manifest details
- `PATCH /api/admin/release-manifests/{guid}` -- Update manifest
- `DELETE /api/admin/release-manifests/{guid}` -- Delete manifest

#### System
- `GET /health` -- Health check (no auth required)
- `GET /api/version` -- Application version (no auth required)

## Architecture

### Multi-Tenancy

All data is scoped to a team via `team_id`. Every service method receives a `TenantContext` (containing `team_id`, `user_id`, and role info) and filters queries accordingly. Cross-team access returns 404 (not 403) to prevent information leakage.

### Authentication Flow

1. **Browser users**: OAuth 2.0 login (Google/Microsoft) -> session cookie -> `TenantContext` from session
2. **Programmatic access**: API token (Bearer header) -> JWT validation -> `TenantContext` from token claims
3. **Agents**: Registration token -> agent credentials -> agent-specific authentication middleware

### GUID System

All entities exposed via API use GUIDs with entity-specific prefixes (e.g., `col_`, `con_`, `pip_`). GUIDs are generated using UUIDv7 + Crockford Base32 encoding. Internal numeric IDs are never exposed in API responses.

### Distributed Agent Execution

The server acts as a job coordinator. Analysis tools are executed by lightweight ShutterSense agents running on user machines:

1. Server creates jobs and queues them for execution
2. Agents poll `/api/agent/v1/jobs/claim` to claim available jobs
3. Agents execute tools locally and report progress via the agent API
4. Results are uploaded (optionally via chunked upload) and stored by the server
5. Dead agent detection runs as a background safety net

## Development Workflow

### Code Quality

```bash
# Format and lint with Ruff
ruff check backend/src backend/tests
ruff format backend/src backend/tests

# Type checking with mypy (if installed)
mypy backend/src
```

### API Development

1. **Define Pydantic schemas** in `src/schemas/`
2. **Create/update ORM models** in `src/models/`
3. **Generate migration**: `alembic revision --autogenerate -m "..."`
4. **Apply migration**: `alembic upgrade head`
5. **Implement business logic** in `src/services/`
6. **Create API endpoints** in `src/api/`
7. **Write tests** in `tests/unit/` and `tests/integration/`
8. **Run tests with coverage**: `pytest tests/ --cov=backend.src`
9. **Review OpenAPI docs**: http://localhost:8000/docs

### Adding a New Storage Adapter

1. Create adapter class in `src/services/remote/`:
   ```python
   class NewAdapter(StorageAdapter):
       def __init__(self, credentials: dict):
           # Validate and store credentials

       def list_files(self, location: str) -> List[str]:
           # Implement file listing

       def test_connection(self) -> tuple[bool, str]:
           # Implement connection test
   ```

2. Add credential schema to `src/schemas/collection.py`

3. Update `ConnectorType` enum in `src/models/connector.py`

4. Update `CollectionType` enum in `src/models/collection.py`

5. Add adapter selection in `src/services/connector_service.py`

6. Write tests in `tests/unit/test_new_adapter.py`

### Adding a New Domain Entity

1. Create ORM model with `ExternalIdMixin` in `src/models/`
2. Register GUID prefix in `src/services/guid.py`
3. Create Pydantic schemas in `src/schemas/`
4. Create service in `src/services/`
5. Create API router in `src/api/`
6. Register router in `src/main.py`
7. Add OpenAPI tag metadata in `src/main.py`
8. Generate and apply database migration
9. Write unit and integration tests

## Security

### Middleware Stack

The application applies the following security middleware (outermost first):

1. **SessionMiddleware** -- Signed cookie-based sessions for OAuth
2. **CORSMiddleware** -- Cross-origin request control
3. **SecurityHeadersMiddleware** -- X-Content-Type-Options, X-Frame-Options, CSP, Permissions-Policy
4. **RequestSizeLimitMiddleware** -- 10MB request body limit
5. **Rate Limiter** -- slowapi-based rate limiting per IP

### Credential Encryption

Remote storage credentials (S3 keys, GCS service accounts, SMB passwords) are encrypted at rest using Fernet symmetric encryption with the `SHUSAI_MASTER_KEY`.

### Authorized Local Roots

Local collection paths are restricted to directories listed in `SHUSAI_AUTHORIZED_LOCAL_ROOTS`. This prevents agents from accessing arbitrary filesystem paths.

## Troubleshooting

### Tests failing with database errors

```bash
# Ensure test environment variables are set
export SHUSAI_MASTER_KEY="test_key_12345678901234567890123456789012"
export SHUSAI_DB_URL="sqlite:///:memory:"

# Run tests
python -m pytest tests/
```

### Coverage reports not generated

```bash
# Install coverage dependencies
pip install pytest-cov

# Run with coverage
python -m pytest tests/ --cov=backend.src --cov-report=term-missing
```

### Import errors in tests

```bash
# Ensure you're running from the repository root
cd /path/to/shuttersense
python -m pytest backend/tests/
```

### Database connection errors

```bash
# Check PostgreSQL is running
pg_isready

# Verify connection URL
psql $SHUSAI_DB_URL

# Run migrations
cd backend
alembic upgrade head
```

### Session/OAuth not working

```bash
# Verify SESSION_SECRET_KEY is set (min 32 chars)
echo $SESSION_SECRET_KEY | wc -c

# Check OAuth provider configuration
# Ensure Google/Microsoft client IDs and secrets are set
```

### Push notifications not delivering

```bash
# Verify VAPID keys are configured
echo $VAPID_PUBLIC_KEY
echo $VAPID_PRIVATE_KEY
echo $VAPID_SUBJECT

# Check pywebpush is installed
python -c "import pywebpush; print('OK')"
```

## License

GNU Affero General Public License v3.0 (AGPL-3.0)

## Contributing

1. Create a feature branch
2. Write code with comprehensive tests (target >80% coverage)
3. Run tests: `pytest tests/ --cov=backend.src`
4. Update documentation as needed
5. Create pull request

## Support

For issues and questions, please use the GitHub issue tracker.
