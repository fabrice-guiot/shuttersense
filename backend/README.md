# Photo Admin Backend

FastAPI backend for the photo-admin web application. Supports remote photo collection management, pipeline configuration, and analysis tool execution with persistent result storage.

## Features

- **Remote Storage Connectors**: Manage S3, GCS, and SMB/CIFS connections with encrypted credentials
- **Photo Collections**: Track local and remote photo collections with accessibility monitoring
- **File Listing Cache**: In-memory caching with state-based TTL for remote storage file listings
- **Calendar Events**: Full event management with categories, locations, organizers, and performers
- **RESTful API**: Comprehensive REST API with OpenAPI/Swagger documentation
- **PostgreSQL Storage**: Persistent storage with SQLAlchemy ORM and Alembic migrations
- **Credential Encryption**: Fernet-based encryption for remote storage credentials

## Tech Stack

- **Python 3.10+** - Required for match/case syntax and modern type hinting
- **FastAPI** - Modern web framework with automatic OpenAPI documentation
- **PostgreSQL 12+** - Primary database with JSONB support
- **SQLAlchemy 2.0** - ORM with connection pooling
- **Alembic** - Database migrations
- **Pytest** - Testing framework with 319 comprehensive tests

## Project Structure

```
backend/
├── src/
│   ├── api/                    # FastAPI route handlers
│   │   ├── connectors.py       # Connector CRUD endpoints
│   │   └── collections.py      # Collection CRUD endpoints
│   ├── db/
│   │   └── database.py         # Database connection and session management
│   ├── models/
│   │   ├── connector.py        # Connector ORM model
│   │   └── collection.py       # Collection ORM model
│   ├── schemas/
│   │   └── collection.py       # Pydantic request/response schemas
│   ├── services/
│   │   ├── connector_service.py    # Connector business logic
│   │   ├── collection_service.py   # Collection business logic
│   │   └── remote/
│   │       ├── s3_adapter.py       # AWS S3 storage adapter
│   │       ├── gcs_adapter.py      # Google Cloud Storage adapter
│   │       └── smb_adapter.py      # SMB/CIFS storage adapter
│   ├── utils/
│   │   ├── cache.py            # In-memory file listing cache
│   │   ├── crypto.py           # Credential encryption/decryption
│   │   ├── job_queue.py        # Background job queue
│   │   └── logging_config.py   # Structured logging configuration
│   ├── migrations/             # Alembic database migrations
│   └── main.py                 # FastAPI application entry point
├── tests/
│   ├── unit/                   # Unit tests (312 tests)
│   │   ├── test_crypto.py
│   │   ├── test_cache.py
│   │   ├── test_job_queue.py
│   │   ├── test_models.py
│   │   ├── test_s3_adapter.py
│   │   ├── test_gcs_adapter.py
│   │   ├── test_smb_adapter.py
│   │   ├── test_connector_service.py
│   │   ├── test_collection_service.py
│   │   ├── test_api_connectors.py
│   │   └── test_api_collections.py
│   ├── integration/            # Integration tests (7 tests)
│   │   └── test_connector_collection_flow.py
│   └── conftest.py             # Shared pytest fixtures
├── requirements.txt            # Python dependencies
├── .coveragerc                 # Coverage configuration
└── README.md                   # This file
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

3. **Set environment variables**:
   ```bash
   # Required
   export PHOTO_ADMIN_MASTER_KEY="your-fernet-key-here"
   export PHOTO_ADMIN_DB_URL="postgresql://user:password@localhost:5432/photo_admin"

   # Optional
   export PHOTO_ADMIN_ENV="development"  # or "production"
   export PHOTO_ADMIN_LOG_LEVEL="INFO"   # DEBUG/INFO/WARNING/ERROR/CRITICAL
   ```

   To generate a master key:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. **Run database migrations**:
   ```bash
   cd backend
   alembic upgrade head
   ```

## Running the Application

### Development Server

```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000/api
- **OpenAPI docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

### Production Server

```bash
cd backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use Gunicorn with Uvicorn workers:
```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Testing

The backend has comprehensive test coverage with 319 tests (312 unit + 7 integration).

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

# Run all tests with "s3" in the name
python -m pytest tests/ -k "s3" -v
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

Test individual components in isolation with mocked dependencies:

- **test_crypto.py** - CredentialEncryptor tests (encryption/decryption, key validation)
- **test_cache.py** - FileListingCache tests (get/set/invalidate, TTL expiry, concurrency)
- **test_job_queue.py** - JobQueue tests (enqueue/dequeue, FIFO, status transitions)
- **test_models.py** - ORM model tests (constraints, relationships, validation)
- **test_s3_adapter.py** - S3Adapter tests (list_files, test_connection, retry logic)
- **test_gcs_adapter.py** - GCSAdapter tests (list_files, service account validation)
- **test_smb_adapter.py** - SMBAdapter tests (list_files, credential validation)
- **test_connector_service.py** - ConnectorService tests (CRUD, encryption, deletion protection)
- **test_collection_service.py** - CollectionService tests (CRUD, accessibility, cache management)
- **test_api_connectors.py** - Connector API endpoint tests (HTTP status codes, validation)
- **test_api_collections.py** - Collection API endpoint tests (filters, cache refresh)

#### Integration Tests (`tests/integration/`)

Test end-to-end workflows across multiple services and API endpoints:

- **test_connector_collection_flow.py** - Full workflows testing:
  - Connector deletion protection with referential integrity
  - Multiple collections and incremental deletion
  - Remote collection accessibility validation
  - State transitions (accessible → inaccessible)

#### Fixtures (`tests/conftest.py`)

Shared pytest fixtures for consistent test setup:

- **Database fixtures**: `test_db_engine`, `test_db_session`
- **Utility fixtures**: `test_encryptor`, `test_cache`, `test_job_queue`
- **Service fixtures**: `test_connector_service`, `test_file_cache`
- **Sample data factories**: `sample_connector_data`, `sample_collection_data`
- **Mocked adapters**: `mock_s3_client`, `mock_gcs_client`, `mock_smb_connection`
- **FastAPI client**: `test_client` with dependency overrides

### Test Dependencies

Test-specific dependencies (included in `requirements.txt`):

- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking support
- **pytest-asyncio** - Async test support
- **freezegun** - Time mocking for cache TTL tests

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

- `PHOTO_ADMIN_MASTER_KEY` - Fernet encryption key for credential storage (44 chars, base64)
- `PHOTO_ADMIN_DB_URL` - PostgreSQL connection URL

### Optional

- `PHOTO_ADMIN_ENV` - Environment name (default: `development`)
- `PHOTO_ADMIN_LOG_LEVEL` - Logging level (default: `INFO`)

### Example `.env` file

```bash
# backend/.env
PHOTO_ADMIN_MASTER_KEY=your-fernet-key-here
PHOTO_ADMIN_DB_URL=postgresql://photo_admin:password@localhost:5432/photo_admin
PHOTO_ADMIN_ENV=development
PHOTO_ADMIN_LOG_LEVEL=DEBUG
```

Load with:
```bash
source backend/.env  # Or use python-dotenv
```

## Development Workflow

### Code Quality

```bash
# Format code with Black (if installed)
black backend/src backend/tests

# Lint with Ruff (if installed)
ruff check backend/src backend/tests

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

2. Add credential schema to `src/schemas/collection.py`:
   ```python
   class NewCredentials(BaseModel):
       # Define required fields with validation
   ```

3. Update `ConnectorType` enum in `src/models/connector.py`

4. Update `CollectionType` enum in `src/models/collection.py`

5. Add adapter selection in `src/services/connector_service.py`

6. Write tests in `tests/unit/test_new_adapter.py`

## API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Main Endpoints

#### Connectors
- `GET /api/connectors` - List connectors (with filters)
- `POST /api/connectors` - Create connector
- `GET /api/connectors/{id}` - Get connector by ID
- `PUT /api/connectors/{id}` - Update connector
- `DELETE /api/connectors/{id}` - Delete connector (protected)
- `POST /api/connectors/{id}/test` - Test connector connection

#### Collections
- `GET /api/collections` - List collections (with filters)
- `POST /api/collections` - Create collection
- `GET /api/collections/{id}` - Get collection by ID
- `PUT /api/collections/{id}` - Update collection
- `DELETE /api/collections/{id}` - Delete collection
- `POST /api/collections/{id}/test` - Test collection accessibility
- `POST /api/collections/{id}/refresh` - Refresh file listing cache

#### Events (Issue #39)
- `GET /api/events` - List events (with date range, category, status filters)
- `POST /api/events` - Create standalone event
- `POST /api/events/series` - Create event series (multiple dates)
- `GET /api/events/{guid}` - Get event details
- `PATCH /api/events/{guid}` - Update event (supports series scope)
- `DELETE /api/events/{guid}` - Soft-delete event
- `GET /api/events/stats` - Get event statistics (KPIs)

#### Categories
- `GET /api/categories` - List categories
- `POST /api/categories` - Create category
- `GET /api/categories/{guid}` - Get category details
- `PATCH /api/categories/{guid}` - Update category
- `DELETE /api/categories/{guid}` - Delete category

#### Locations
- `GET /api/locations` - List locations
- `POST /api/locations` - Create location
- `GET /api/locations/{guid}` - Get location details
- `PATCH /api/locations/{guid}` - Update location
- `DELETE /api/locations/{guid}` - Delete location

#### Organizers
- `GET /api/organizers` - List organizers
- `POST /api/organizers` - Create organizer
- `GET /api/organizers/{guid}` - Get organizer details
- `PATCH /api/organizers/{guid}` - Update organizer
- `DELETE /api/organizers/{guid}` - Delete organizer

#### Performers
- `GET /api/performers` - List performers
- `POST /api/performers` - Create performer
- `GET /api/performers/{guid}` - Get performer details
- `PATCH /api/performers/{guid}` - Update performer
- `DELETE /api/performers/{guid}` - Delete performer
- `POST /api/events/{guid}/performers` - Link performer to event
- `DELETE /api/events/{guid}/performers/{performer_guid}` - Unlink performer

## Troubleshooting

### Tests failing with database errors

```bash
# Ensure test environment variables are set
export PHOTO_ADMIN_MASTER_KEY="test_key_12345678901234567890123456789012"
export PHOTO_ADMIN_DB_URL="sqlite:///:memory:"

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
cd /path/to/photo-admin
python -m pytest backend/tests/
```

### Database connection errors

```bash
# Check PostgreSQL is running
pg_isready

# Verify connection URL
psql $PHOTO_ADMIN_DB_URL

# Run migrations
cd backend
alembic upgrade head
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
