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

from backend.src.models import Base, Connector, Collection
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.cache import FileListingCache
from backend.src.utils.job_queue import JobQueue


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
def test_db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


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


# ============================================================================
# Sample Data Factories
# ============================================================================

@pytest.fixture
def sample_connector_data():
    """Factory for creating sample connector data."""
    def _create(
        name='Test S3 Connector',
        connector_type='s3',
        credentials=None,
        is_active=True,
        metadata=None
    ):
        if credentials is None:
            credentials = {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-east-1'
            }
        return {
            'name': name,
            'type': connector_type,
            'credentials': credentials,
            'is_active': is_active,
            'metadata': metadata or {}
        }
    return _create


@pytest.fixture
def sample_connector(test_db_session, test_encryptor, sample_connector_data):
    """Factory for creating sample Connector models in the database."""
    def _create(**kwargs):
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
            metadata_json=json.dumps(data['metadata']) if data['metadata'] else None
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)
        return connector
    return _create


@pytest.fixture
def sample_collection_data():
    """Factory for creating sample collection data."""
    def _create(
        name='Test Collection',
        collection_type='local',
        location='/photos',
        state='live',
        connector_id=None,
        cache_ttl=None,
        metadata=None
    ):
        return {
            'name': name,
            'type': collection_type,
            'location': location,
            'state': state,
            'connector_id': connector_id,
            'cache_ttl': cache_ttl,
            'metadata': metadata or {}
        }
    return _create


@pytest.fixture
def sample_collection(test_db_session, sample_collection_data):
    """Factory for creating sample Collection models in the database."""
    def _create(**kwargs):
        import json
        data = sample_collection_data(**kwargs)

        collection = Collection(
            name=data['name'],
            type=data['type'],
            location=data['location'],
            state=data['state'],
            connector_id=data['connector_id'],
            cache_ttl=data['cache_ttl'],
            is_accessible=True,
            last_error=None,
            metadata_json=json.dumps(data['metadata']) if data['metadata'] else None
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)
        return collection
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
def test_client(test_db_session, test_cache, test_job_queue, test_encryptor):
    """Create a test client for FastAPI application."""
    from fastapi.testclient import TestClient
    from backend.src.main import app

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

    # Import and override dependencies
    from backend.src.db.database import get_db
    from backend.src.dependencies import get_cache, get_job_queue, get_encryptor

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_cache] = get_test_cache
    app.dependency_overrides[get_job_queue] = get_test_queue
    app.dependency_overrides[get_encryptor] = get_test_encryptor

    with TestClient(app) as client:
        yield client

    # Clear overrides
    app.dependency_overrides.clear()
