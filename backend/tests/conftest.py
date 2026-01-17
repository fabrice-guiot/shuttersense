"""
Pytest configuration and fixtures for backend tests.

Provides shared fixtures for:
- Test database sessions
- In-memory cache
- Mock encryptor
- Sample data factories
- Mocked storage adapters
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Generate a valid Fernet key for testing
from cryptography.fernet import Fernet
_TEST_MASTER_KEY = Fernet.generate_key().decode('utf-8')

# Set test environment variables before importing app modules
os.environ['PHOTO_ADMIN_MASTER_KEY'] = _TEST_MASTER_KEY
os.environ['PHOTO_ADMIN_DB_URL'] = 'sqlite:///:memory:'

# Allow temp directories for testing (covers both macOS and Linux paths)
# macOS: /private/var/folders (resolved) and /var/folders (symlink)
# Linux: /tmp
import tempfile
_temp_base = tempfile.gettempdir()
os.environ['PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS'] = f'{_temp_base},/tmp,/private/var,/var'

# Disable rate limiters at import time to prevent rate limit exhaustion during tests
from backend.src.main import limiter as _main_limiter
_main_limiter.enabled = False
from backend.src.api.tools import limiter as _tools_limiter
_tools_limiter.enabled = False
# Clear any existing rate limit state from previous runs
# The limiter uses limits library which stores state in _storage
try:
    if hasattr(_main_limiter, '_storage') and _main_limiter._storage is not None:
        _main_limiter._storage.reset()
    if hasattr(_tools_limiter, '_storage') and _tools_limiter._storage is not None:
        _tools_limiter._storage.reset()
except Exception:
    pass  # Ignore errors during cleanup

from backend.src.models import Base, Connector, Collection, AnalysisResult, Pipeline, Configuration, Team, User, UserStatus, UserType
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.cache import FileListingCache
from backend.src.utils.job_queue import JobQueue
from backend.src.utils.websocket import ConnectionManager
from backend.src.middleware.auth import TenantContext


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope='function')
def test_db_engine():
    """Create an in-memory SQLite database engine for testing."""
    from sqlalchemy import event

    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraints for SQLite
    # This must be set for each connection
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('pragma foreign_keys=ON')

    event.listen(engine, 'connect', _fk_pragma_on_connect)

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope='function')
def test_session_factory(test_db_engine):
    """Create a session factory bound to test database."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )


@pytest.fixture(scope='function')
def test_db_session(test_session_factory):
    """Create a test database session."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# Test Team and User Fixtures
# ============================================================================

@pytest.fixture(scope='function')
def test_team(test_db_session):
    """Create a test team for tenant isolation testing."""
    team = Team(
        name='Test Team',
        slug='test-team',
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture(scope='function')
def test_user(test_db_session, test_team):
    """Create a test user for authentication testing."""
    user = User(
        team_id=test_team.id,
        email='test@example.com',
        display_name='Test User',
        status=UserStatus.ACTIVE,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope='function')
def test_system_user(test_db_session, test_team):
    """Create a test system user for API token testing."""
    user = User(
        team_id=test_team.id,
        email='system-token-1@system.local',
        display_name='System Token User',
        status=UserStatus.ACTIVE,
        user_type=UserType.SYSTEM,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope='function')
def test_tenant_context(test_team, test_user):
    """Create a TenantContext for authenticated tests."""
    return TenantContext(
        team_id=test_team.id,
        team_guid=test_team.guid,
        user_id=test_user.id,
        user_guid=test_user.guid,
        user_email=test_user.email,
        is_super_admin=False,
        is_api_token=False,
    )


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture(scope='function')
def test_encryptor():
    """Create a CredentialEncryptor with test master key."""
    return CredentialEncryptor(_TEST_MASTER_KEY)


@pytest.fixture(scope='function')
def test_cache():
    """Create an in-memory FileListingCache for testing."""
    return FileListingCache()


@pytest.fixture(scope='function')
def test_job_queue():
    """Create a JobQueue for testing."""
    return JobQueue()


@pytest.fixture(scope='function')
def test_websocket_manager():
    """Create a ConnectionManager for testing."""
    return ConnectionManager()


# ============================================================================
# Service Layer Fixtures
# ============================================================================

@pytest.fixture
def test_file_cache():
    """Create a FileListingCache for testing."""
    from backend.src.utils.cache import FileListingCache
    return FileListingCache()


@pytest.fixture
def test_connector_service(test_db_session, test_encryptor):
    """Create a ConnectorService for testing."""
    from backend.src.services.connector_service import ConnectorService
    return ConnectorService(test_db_session, test_encryptor)


# ============================================================================
# Sample Data Factories
# ============================================================================

@pytest.fixture
def sample_connector_data():
    """Factory for creating sample connector data."""
    def _create(
        name='Test S3 Connector',
        connector_type='s3',
        type=None,  # Allow 'type' as alias for consistency
        credentials=None,
        is_active=True,
        metadata=None
    ):
        # Use 'type' if provided, otherwise use 'connector_type'
        actual_type = type if type is not None else connector_type

        if credentials is None:
            credentials = {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-east-1'
            }
        return {
            'name': name,
            'type': actual_type,
            'credentials': credentials,
            'is_active': is_active,
            'metadata': metadata or {}
        }
    return _create


@pytest.fixture
def sample_connector(test_db_session, test_encryptor, sample_connector_data, test_team):
    """Factory for creating sample Connector models in the database."""
    def _create(team_id=None, **kwargs):
        import json
        data = sample_connector_data(**kwargs)
        # Convert credentials dict to JSON string before encryption
        creds_json = json.dumps(data['credentials'])
        encrypted_creds = test_encryptor.encrypt(creds_json)

        connector = Connector(
            name=data['name'],
            type=data['type'],
            credentials=encrypted_creds,
            is_active=data['is_active'],
            metadata_json=json.dumps(data['metadata']) if data['metadata'] else None,
            team_id=team_id if team_id is not None else test_team.id,
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)
        return connector
    return _create


@pytest.fixture
def sample_collection_data():
    """Factory for creating sample collection data for API requests."""
    def _create(
        name='Test Collection',
        collection_type='local',
        type=None,  # Allow 'type' as alias for consistency
        location='/photos',
        state='live',
        connector_guid=None,  # API now uses connector_guid
        connector_id=None,  # Legacy: accepts internal ID for test convenience
        cache_ttl=None,
        is_accessible=True,
        last_error=None,
        metadata=None
    ):
        # Use 'type' if provided, otherwise use 'collection_type'
        actual_type = type if type is not None else collection_type

        data = {
            'name': name,
            'type': actual_type,
            'location': location,
            'state': state,
            'cache_ttl': cache_ttl,
            'is_accessible': is_accessible,
            'last_error': last_error,
            'metadata': metadata or {}
        }
        if connector_guid:
            data['connector_guid'] = connector_guid
        # Legacy support: connector_id passed through for model tests
        if connector_id:
            data['connector_id'] = connector_id
        return data
    return _create


@pytest.fixture
def sample_collection(test_db_session, sample_collection_data, test_team):
    """Factory for creating sample Collection models in the database."""
    def _create(connector_guid=None, connector_id=None, team_id=None, **kwargs):
        import json
        from backend.src.services.guid import GuidService

        # Handle connector_guid to connector_id translation for DB model
        resolved_connector_id = connector_id  # Direct ID takes precedence
        if connector_guid and not connector_id:
            connector_uuid = GuidService.parse_identifier(connector_guid, expected_prefix="con")
            connector = test_db_session.query(Connector).filter(Connector.uuid == connector_uuid).first()
            if connector:
                resolved_connector_id = connector.id

        data = sample_collection_data(**kwargs)

        collection = Collection(
            name=data['name'],
            type=data['type'],
            location=data['location'],
            state=data['state'],
            connector_id=resolved_connector_id,
            cache_ttl=data['cache_ttl'],
            is_accessible=data['is_accessible'],
            last_error=data['last_error'],
            metadata_json=json.dumps(data['metadata']) if data['metadata'] else None,
            team_id=team_id if team_id is not None else test_team.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)
        return collection
    return _create


@pytest.fixture
def sample_pipeline_data():
    """Factory for creating sample pipeline data."""
    def _create(
        name='Test Pipeline',
        description='Test pipeline description',
        nodes=None,
        edges=None,
        is_active=False,
        is_default=False,
        is_valid=True,
    ):
        if nodes is None:
            nodes = [
                {"id": "capture", "type": "capture", "properties": {
                    "sample_filename": "AB3D0001",
                    "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
                    "camera_id_group": "1"
                }},
                {"id": "raw", "type": "file", "properties": {"extension": ".dng"}},
                {"id": "termination", "type": "termination", "properties": {}}
            ]
        if edges is None:
            edges = [
                {"from": "capture", "to": "raw"},
                {"from": "raw", "to": "termination"}
            ]
        return {
            'name': name,
            'description': description,
            'nodes': nodes,
            'edges': edges,
            'is_active': is_active,
            'is_default': is_default,
            'is_valid': is_valid,
        }
    return _create


@pytest.fixture
def sample_pipeline(test_db_session, sample_pipeline_data, test_team):
    """Factory for creating sample Pipeline models in the database."""
    def _create(team_id=None, **kwargs):
        data = sample_pipeline_data(**kwargs)

        pipeline = Pipeline(
            name=data['name'],
            description=data['description'],
            nodes_json=data['nodes'],
            edges_json=data['edges'],
            version=1,
            is_active=data['is_active'],
            is_default=data['is_default'],
            is_valid=data['is_valid'],
            team_id=team_id if team_id is not None else test_team.id,
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        test_db_session.refresh(pipeline)
        return pipeline
    return _create


# ============================================================================
# Mocked Storage Adapter Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_client(mocker):
    """Mock boto3 S3 client for testing S3Adapter."""
    mock_client = MagicMock()

    # Mock successful list_objects_v2 response
    mock_client.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'photo1.jpg', 'Size': 1024, 'LastModified': datetime.now()},
            {'Key': 'photo2.jpg', 'Size': 2048, 'LastModified': datetime.now()},
        ],
        'IsTruncated': False
    }

    # Mock successful head_bucket (connection test)
    mock_client.head_bucket.return_value = {}

    mocker.patch('boto3.client', return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_gcs_client(mocker):
    """Mock google-cloud-storage client for testing GCSAdapter."""
    mock_storage_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob1 = MagicMock()
    mock_blob1.name = 'photo1.jpg'
    mock_blob1.size = 1024
    mock_blob1.updated = datetime.now()

    mock_blob2 = MagicMock()
    mock_blob2.name = 'photo2.jpg'
    mock_blob2.size = 2048
    mock_blob2.updated = datetime.now()

    mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
    mock_storage_client.bucket.return_value = mock_bucket

    mocker.patch('google.cloud.storage.Client', return_value=mock_storage_client)
    return mock_storage_client


@pytest.fixture
def mock_smb_connection(mocker):
    """Mock smbprotocol connection for testing SMBAdapter."""
    mock_connection = MagicMock()

    # Mock directory listing
    mock_file1 = MagicMock()
    mock_file1.file_name.get_value.return_value = 'photo1.jpg'
    mock_file1.end_of_file.get_value.return_value = 1024
    mock_file1.last_write_time.get_value.return_value = datetime.now()

    mock_file2 = MagicMock()
    mock_file2.file_name.get_value.return_value = 'photo2.jpg'
    mock_file2.end_of_file.get_value.return_value = 2048
    mock_file2.last_write_time.get_value.return_value = datetime.now()

    mock_connection.query_directory.return_value = [mock_file1, mock_file2]

    mocker.patch('smbclient.register_session', return_value=None)
    mocker.patch('smbclient.scandir', return_value=[mock_file1, mock_file2])

    return mock_connection


# ============================================================================
# FastAPI Test Client Fixture
# ============================================================================

@pytest.fixture
def test_client(test_db_session, test_session_factory, test_cache, test_job_queue, test_encryptor, test_websocket_manager, test_team, test_user):
    """Create a test client for FastAPI application with mocked authentication."""
    from fastapi.testclient import TestClient
    from backend.src.main import app

    # Create test tenant context for authentication
    test_ctx = TenantContext(
        team_id=test_team.id,
        team_guid=test_team.guid,
        user_id=test_user.id,
        user_guid=test_user.guid,
        user_email=test_user.email,
        is_super_admin=False,
        is_api_token=False,
    )

    # Override dependencies
    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    def get_test_cache():
        return test_cache

    def get_test_queue():
        return test_job_queue

    def get_test_encryptor():
        return test_encryptor

    def get_test_websocket_manager():
        return test_websocket_manager

    def get_test_auth():
        """Return mock TenantContext for authenticated tests."""
        return test_ctx

    def get_test_tool_service():
        """Create ToolService with test session factory for background tasks."""
        from backend.src.services.tool_service import ToolService
        return ToolService(
            db=test_db_session,
            websocket_manager=test_websocket_manager,
            job_queue=test_job_queue,
            session_factory=test_session_factory
        )

    # Import and override dependencies
    from backend.src.db.database import get_db
    from backend.src.api.connectors import get_credential_encryptor as get_connector_encryptor
    from backend.src.api.collections import (
        get_file_cache,
        get_credential_encryptor as get_collection_encryptor
    )
    from backend.src.api.tools import get_websocket_manager, get_tool_service
    from backend.src.middleware.auth import require_auth

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_file_cache] = get_test_cache
    app.dependency_overrides[get_connector_encryptor] = get_test_encryptor
    app.dependency_overrides[get_collection_encryptor] = get_test_encryptor
    app.dependency_overrides[get_websocket_manager] = get_test_websocket_manager
    app.dependency_overrides[get_tool_service] = get_test_tool_service
    app.dependency_overrides[require_auth] = get_test_auth

    with TestClient(app) as client:
        yield client

    # Clear overrides
    app.dependency_overrides.clear()
