"""
Pydantic schemas for collection API request/response validation.

Provides data validation and serialization for:
- Connector credentials (S3, GCS, SMB)
- Collection creation requests
- Collection update requests
- Collection API responses

Design:
- Strict credential validation with field constraints
- Optional fields with sensible defaults
- Comprehensive metadata support
- DateTime serialization for API responses
"""

from datetime import datetime
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.src.models import CollectionType, CollectionState, ConnectorType
from backend.src.models.connector import CredentialLocation


# ============================================================================
# Connector Credential Schemas (T091)
# ============================================================================

class S3Credentials(BaseModel):
    """
    AWS S3 connector credentials.

    Required:
        aws_access_key_id: AWS access key ID
        aws_secret_access_key: AWS secret access key

    Optional:
        region: AWS region (defaults to us-east-1)

    Example:
        >>> creds = S3Credentials(
        ...     aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
        ...     aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ...     region="us-west-2"
        ... )
    """
    aws_access_key_id: str = Field(..., min_length=16, max_length=128, description="AWS access key ID")
    aws_secret_access_key: str = Field(..., min_length=40, description="AWS secret access key")
    region: Optional[str] = Field(default="us-east-1", description="AWS region")

    @field_validator('aws_access_key_id')
    @classmethod
    def validate_access_key(cls, v: str) -> str:
        """Validate access key format (must start with AKIA or ASIA)."""
        if not v.startswith(('AKIA', 'ASIA')):
            raise ValueError("AWS access key ID must start with AKIA or ASIA")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-west-2"
            }
        }
    }


class GCSCredentials(BaseModel):
    """
    Google Cloud Storage connector credentials.

    Required:
        service_account_json: GCS service account JSON string

    Example:
        >>> creds = GCSCredentials(
        ...     service_account_json='{"type": "service_account", "project_id": "my-project", ...}'
        ... )
    """
    service_account_json: str = Field(..., min_length=50, description="GCS service account JSON string")

    @field_validator('service_account_json')
    @classmethod
    def validate_json_format(cls, v: str) -> str:
        """Validate service account JSON contains required fields."""
        import json
        try:
            data = json.loads(v)
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise ValueError(f"Service account JSON missing required fields: {', '.join(missing)}")
            if data.get('type') != 'service_account':
                raise ValueError("Service account JSON must have type='service_account'")
            return v
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for service account")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service_account_json": '{"type": "service_account", "project_id": "my-project", "private_key_id": "key-id", "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n", "client_email": "service-account@my-project.iam.gserviceaccount.com"}'
            }
        }
    }


class SMBCredentials(BaseModel):
    """
    SMB/CIFS network share connector credentials.

    Required:
        server: SMB server hostname or IP address
        share: SMB share name
        username: SMB username
        password: SMB password

    Optional:
        port: SMB port (defaults to 445)

    Example:
        >>> creds = SMBCredentials(
        ...     server="nas.local",
        ...     share="photos",
        ...     username="user",
        ...     password="pass",
        ...     port=445
        ... )
    """
    server: str = Field(..., min_length=1, max_length=255, description="SMB server hostname or IP")
    share: str = Field(..., min_length=1, max_length=255, description="SMB share name")
    username: str = Field(..., min_length=1, max_length=255, description="SMB username")
    password: str = Field(..., min_length=1, description="SMB password")
    port: Optional[int] = Field(default=445, ge=1, le=65535, description="SMB port")

    model_config = {
        "json_schema_extra": {
            "example": {
                "server": "nas.local",
                "share": "photos",
                "username": "admin",
                "password": "securepass123",
                "port": 445
            }
        }
    }


# Union type for all credential types
ConnectorCredentials = Union[S3Credentials, GCSCredentials, SMBCredentials]


# ============================================================================
# Connector Schemas
# ============================================================================

class ConnectorCreate(BaseModel):
    """
    Schema for creating a new connector.

    Fields:
        name: User-friendly connector name (must be unique)
        type: Connector type (S3, GCS, SMB)
        credential_location: Where credentials are stored (server/agent/pending)
        credentials: Type-specific credentials object (required when location=server)
        metadata: Optional user-defined metadata

    Credential Location Modes:
        - server: Credentials encrypted on server (default, current behavior)
        - agent: Credentials stored only on agent(s), server has none
        - pending: Placeholder connector awaiting credential configuration

    Example:
        >>> # Server credentials (default)
        >>> connector = ConnectorCreate(
        ...     name="My AWS Account",
        ...     type=ConnectorType.S3,
        ...     credentials={"aws_access_key_id": "...", "aws_secret_access_key": "..."},
        ... )
        >>> # Agent-only credentials
        >>> connector = ConnectorCreate(
        ...     name="NAS Storage",
        ...     type=ConnectorType.SMB,
        ...     credential_location=CredentialLocation.AGENT,
        ... )
    """
    name: str = Field(..., min_length=1, max_length=255, description="Unique connector name")
    type: ConnectorType = Field(..., description="Connector type")
    credential_location: CredentialLocation = Field(
        default=CredentialLocation.SERVER,
        description="Where credentials are stored (server/agent/pending)"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Connector credentials (required when credential_location=server)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="User-defined metadata")
    is_active: bool = Field(default=True, description="Whether connector is active")

    @model_validator(mode='after')
    def validate_credentials_match_type(self):
        """Validate credentials are required for server mode and match connector type."""
        # Cannot activate a connector with pending credentials
        if self.credential_location == CredentialLocation.PENDING and self.is_active:
            raise ValueError("Cannot activate connector with pending credentials. Configure credentials first.")

        # Credentials required when location is SERVER
        if self.credential_location == CredentialLocation.SERVER:
            if not self.credentials:
                raise ValueError("Credentials are required when credential_location is 'server'")

            # Validate credentials structure based on type
            try:
                if self.type == ConnectorType.S3:
                    S3Credentials(**self.credentials)
                elif self.type == ConnectorType.GCS:
                    GCSCredentials(**self.credentials)
                elif self.type == ConnectorType.SMB:
                    SMBCredentials(**self.credentials)
            except Exception as e:
                raise ValueError(f"Invalid credentials for {self.type.value}: {str(e)}")

        # For AGENT or PENDING, credentials should not be provided
        elif self.credentials:
            raise ValueError(
                f"Credentials should not be provided when credential_location is '{self.credential_location.value}'. "
                "For agent credentials, configure them on the agent using CLI."
            )

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Production AWS",
                    "type": "s3",
                    "credential_location": "server",
                    "credentials": {
                        "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                        "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                        "region": "us-west-2"
                    },
                    "metadata": {"team": "engineering", "environment": "production"}
                },
                {
                    "name": "Office NAS",
                    "type": "smb",
                    "credential_location": "agent",
                    "metadata": {"location": "office"}
                }
            ]
        }
    }


class ConnectorUpdate(BaseModel):
    """
    Schema for updating an existing connector.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New connector name
        credential_location: New credential storage location
        credentials: New credentials (will be re-encrypted, only when location=server)
        update_credentials: Whether to update credentials (false = keep existing)
        metadata: New metadata
        is_active: Active status

    Note:
        Changing credential_location from server to agent will clear server credentials.
        Changing from agent to server requires providing new credentials.
        When update_credentials=false, the credentials field is ignored.

    Example:
        >>> update = ConnectorUpdate(name="Updated AWS Account", is_active=False)
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    credential_location: Optional[CredentialLocation] = Field(
        default=None,
        description="New credential storage location"
    )
    credentials: Optional[Dict[str, Any]] = Field(default=None)
    update_credentials: bool = Field(
        default=True,
        description="Whether to update credentials (false = keep existing)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Connector Name",
                "credential_location": "server",
                "is_active": True,
                "update_credentials": False,
                "metadata": {"team": "platform"}
            }
        }
    }


class ConnectorResponse(BaseModel):
    """
    Schema for connector API responses.

    Includes all connector fields except encrypted credentials.

    Fields:
        guid: External identifier (con_xxx)
        name: Connector name
        type: ConnectorType
        credential_location: Where credentials are stored (server/agent/pending)
        metadata: User-defined metadata
        is_active: Active status
        last_validated: Last successful connection test
        last_error: Last connection error message
        inventory_config: Inventory configuration (S3/GCS)
        inventory_validation_status: Validation status (pending/validating/validated/failed)
        inventory_validation_error: Error message if validation failed
        inventory_last_import_at: Last successful import timestamp
        inventory_schedule: Import schedule (manual/daily/weekly)
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = ConnectorResponse.from_orm(connector_obj)
    """
    guid: str = Field(..., description="External identifier (con_xxx)")
    name: str
    type: ConnectorType
    credential_location: CredentialLocation = Field(
        description="Where credentials are stored (server/agent/pending)"
    )
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool
    last_validated: Optional[datetime]
    last_error: Optional[str]
    # Inventory configuration fields (Issue #107)
    inventory_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Inventory configuration (S3/GCS)"
    )
    inventory_validation_status: Optional[str] = Field(
        default=None, description="Validation status (pending/validating/validated/failed)"
    )
    inventory_validation_error: Optional[str] = Field(
        default=None, description="Error message if validation failed"
    )
    inventory_last_import_at: Optional[datetime] = Field(
        default=None, description="Last successful import timestamp"
    )
    inventory_schedule: Optional[str] = Field(
        default=None, description="Import schedule (manual/daily/weekly)"
    )
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='before')
    @classmethod
    def deserialize_metadata(cls, data):
        """Deserialize metadata_json field to metadata dict."""
        if isinstance(data, dict):
            # Already a dict (from JSON API request)
            return data
        # It's an ORM object
        if hasattr(data, 'metadata_json'):
            import json
            metadata_json = data.metadata_json
            if metadata_json:
                try:
                    data.metadata = json.loads(metadata_json)
                except (json.JSONDecodeError, TypeError):
                    data.metadata = None
            else:
                data.metadata = None
        return data

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "con_01hgw2bbg0000000000000001",
                "name": "Production AWS",
                "type": "s3",
                "metadata": {"team": "engineering"},
                "is_active": True,
                "last_validated": "2025-12-30T10:30:00",
                "last_error": None,
                "created_at": "2025-12-20T08:00:00",
                "updated_at": "2025-12-30T10:30:00"
            }
        }
    }


class ConnectorTestResponse(BaseModel):
    """
    Schema for connector connection test response.

    Fields:
        success: Test result
        message: Descriptive message

    Example:
        >>> response = ConnectorTestResponse(success=True, message="Connected successfully")
    """
    success: bool = Field(..., description="Test success status")
    message: str = Field(..., description="Descriptive message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Connected to S3 bucket. Found 1,234 objects."
            }
        }
    }


# ============================================================================
# Collection Schemas (T092-T094)
# ============================================================================

class CollectionCreate(BaseModel):
    """
    Schema for creating a new collection.

    Validates:
    - Remote collections (S3/GCS/SMB) require connector_guid
    - Local collections cannot have connector_guid
    - Local collections can optionally specify bound_agent_guid
    - Location format is reasonable
    - State defaults to LIVE

    Fields:
        name: Unique collection name
        type: Collection type (LOCAL, S3, GCS, SMB)
        location: File path or remote location
        state: Collection state (defaults to LIVE)
        connector_guid: Required for remote collections (con_xxx format)
        bound_agent_guid: Agent for LOCAL collections (agt_xxx format)
        pipeline_guid: Explicit pipeline assignment (NULL = use default at runtime)
        metadata: User-defined metadata

    Note:
        Cache TTL is derived from the collection state and team-level configuration.
        Configure TTL values in Settings > Configuration > Collection Cache TTL.

    Example:
        >>> collection = CollectionCreate(
        ...     name="Vacation 2024",
        ...     type=CollectionType.S3,
        ...     location="s3://my-bucket/photos/2024",
        ...     connector_guid="con_01hgw2bbg0000000000000001",
        ...     metadata={"year": 2024, "trip": "Hawaii"}
        ... )
    """
    name: str = Field(..., min_length=1, max_length=255, description="Unique collection name")
    type: CollectionType = Field(..., description="Collection type")
    location: str = Field(..., min_length=1, max_length=1024, description="File path or remote location")
    state: CollectionState = Field(default=CollectionState.LIVE, description="Collection state")
    connector_guid: Optional[str] = Field(default=None, description="Connector GUID (con_xxx, required for remote)")
    bound_agent_guid: Optional[str] = Field(default=None, description="Bound agent GUID (agt_xxx, for LOCAL collections)")
    pipeline_guid: Optional[str] = Field(default=None, description="Pipeline GUID (pip_xxx, NULL = use default)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="User-defined metadata")

    @model_validator(mode='after')
    def validate_connector_requirement(self):
        """Validate connector_guid is provided for remote collections and absent for local."""
        # Check collection type requirements first (more specific error messages)

        # Local collections require bound_agent_guid and cannot have connector_guid
        if self.type == CollectionType.LOCAL:
            if self.connector_guid is not None:
                raise ValueError("connector_guid must be null for LOCAL collections")
            if self.bound_agent_guid is None:
                raise ValueError("bound_agent_guid is required for LOCAL collections")

        # Remote collections require connector_guid and cannot have bound_agent_guid
        if self.type in [CollectionType.S3, CollectionType.GCS, CollectionType.SMB]:
            if self.connector_guid is None:
                raise ValueError(f"connector_guid is required for {self.type.value} collections")
            if self.bound_agent_guid is not None:
                raise ValueError("bound_agent_guid is only valid for LOCAL collections")

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Vacation Photos 2024",
                "type": "s3",
                "location": "s3://my-bucket/photos/2024/vacation",
                "state": "live",
                "connector_guid": "con_01hgw2bbg0000000000000001",
                "pipeline_guid": "pip_01hgw2bbg0000000000000001",
                "metadata": {"year": 2024, "season": "summer", "location": "Hawaii"}
            }
        }
    }


class CollectionUpdate(BaseModel):
    """
    Schema for updating an existing collection.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New collection name
        location: New location path
        state: New state (LIVE, CLOSED, ARCHIVED)
        pipeline_guid: New pipeline assignment (pip_xxx, set to explicit None to clear)
        bound_agent_guid: Bound agent for LOCAL collections (agt_xxx, set to None to unbind)
        metadata: New metadata

    Note:
        - Cannot change collection type or connector_guid after creation
        - Changing state invalidates cache (new TTL applies based on team config)
        - Setting pipeline_guid assigns a pipeline and pins the current version
        - Use clear_pipeline endpoint to explicitly remove assignment
        - bound_agent_guid can only be set for LOCAL collections
        - Cache TTL is derived from state and team config (Settings > Configuration)

    Example:
        >>> update = CollectionUpdate(state=CollectionState.ARCHIVED)
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    state: Optional[CollectionState] = Field(default=None)
    pipeline_guid: Optional[str] = Field(default=None, description="Pipeline GUID (pip_xxx, NULL = keep current)")
    bound_agent_guid: Optional[str] = Field(default=None, description="Bound agent GUID (agt_xxx, for LOCAL collections)")
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": "archived",
                "pipeline_guid": "pip_01hgw2bbg0000000000000002",
                "bound_agent_guid": "agt_01hgw2bbg0000000000000001",
                "metadata": {"archived_by": "admin", "reason": "project completed"}
            }
        }
    }


class BoundAgentSummary(BaseModel):
    """
    Summary schema for bound agent in collection responses.

    Fields:
        guid: Agent GUID (agt_xxx)
        name: Agent display name
        status: Current agent status

    Example:
        >>> summary = BoundAgentSummary(guid="agt_xxx", name="My Agent", status="online")
    """
    guid: str = Field(..., description="Agent GUID (agt_xxx)")
    name: str = Field(..., description="Agent display name")
    status: str = Field(..., description="Agent status (online, offline, error)")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "agt_01hgw2bbg0000000000000001",
                "name": "Home Mac Agent",
                "status": "online"
            }
        }
    }


class FileInfoSummary(BaseModel):
    """
    Summary of FileInfo cache on a collection.

    Fields:
        count: Number of cached FileInfo entries
        source: Source of FileInfo (api or inventory)
        updated_at: When FileInfo was last updated
        delta: Delta summary from last inventory import

    Example:
        >>> summary = FileInfoSummary(count=150, source="inventory")
    """
    count: int = Field(default=0, ge=0, description="Number of cached files")
    source: Optional[str] = Field(default=None, description="FileInfo source: api or inventory")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    delta: Optional[Dict[str, Any]] = Field(default=None, description="Delta summary")

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 150,
                "source": "inventory",
                "updated_at": "2026-01-25T10:00:00Z",
                "delta": {"new_count": 5, "modified_count": 2, "deleted_count": 0}
            }
        }
    }


class CollectionResponse(BaseModel):
    """
    Schema for collection API responses.

    Includes all collection fields, connector information, and pipeline assignment.

    Fields:
        guid: External identifier (col_xxx)
        name: Collection name
        type: Collection type
        location: File path or remote location
        state: Collection state
        connector_guid: Connector GUID (con_xxx, null for LOCAL collections)
        pipeline_guid: Pipeline GUID (pip_xxx, null = use default)
        pipeline_version: Pinned pipeline version (null if using default)
        pipeline_name: Name of assigned pipeline (null if using default)
        bound_agent: Bound agent details for LOCAL collections (null for remote)
        cache_ttl: Cache TTL override
        is_accessible: Accessibility flag (True=accessible, False=not accessible, None=pending/testing)
        last_error: Last error message
        metadata: User-defined metadata
        file_info: FileInfo cache summary (Issue #107)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        connector: Optional connector details (full object)

    Example:
        >>> response = CollectionResponse.from_orm(collection_obj)
    """
    guid: str = Field(..., description="External identifier (col_xxx)")
    name: str
    type: CollectionType
    location: str
    state: CollectionState
    connector_guid: Optional[str] = Field(default=None, description="Connector GUID (con_xxx)")
    pipeline_guid: Optional[str] = Field(default=None, description="Pipeline GUID (pip_xxx)")
    pipeline_version: Optional[int] = None
    pipeline_name: Optional[str] = None
    bound_agent: Optional[BoundAgentSummary] = Field(default=None, description="Bound agent for LOCAL collections")
    cache_ttl: Optional[int]
    is_accessible: Optional[bool] = Field(
        default=None,
        description="Accessibility flag: True=accessible, False=not accessible, None=pending/testing"
    )
    accessibility_message: Optional[str] = Field(default=None, description="Accessibility error message")
    last_scanned_at: Optional[datetime] = Field(default=None, description="Last completed scan timestamp")
    metadata: Optional[Dict[str, Any]] = None
    file_info: Optional[FileInfoSummary] = Field(default=None, description="FileInfo cache summary")
    created_at: datetime
    updated_at: datetime
    connector: Optional[ConnectorResponse] = None

    @model_validator(mode='before')
    @classmethod
    def deserialize_metadata_and_pipeline(cls, data):
        """Deserialize metadata_json and extract pipeline info from relationship."""
        if isinstance(data, dict):
            # Already a dict (from JSON API request)
            return data
        # It's an ORM object - convert to dict to avoid modifying the ORM
        result = {}

        # Copy basic attributes
        for attr in ['guid', 'name', 'type', 'location', 'state', 'pipeline_version',
                     'is_accessible', 'created_at', 'updated_at']:
            if hasattr(data, attr):
                result[attr] = getattr(data, attr)

        # Get effective cache TTL (uses state-based defaults if no override)
        if hasattr(data, 'get_effective_cache_ttl'):
            result['cache_ttl'] = data.get_effective_cache_ttl()
        elif hasattr(data, 'cache_ttl'):
            result['cache_ttl'] = getattr(data, 'cache_ttl')

        # Map last_error (DB field) to accessibility_message (API field)
        if hasattr(data, 'last_error'):
            result['accessibility_message'] = getattr(data, 'last_error')

        # Map last_refresh_at (DB field) to last_scanned_at (API field)
        if hasattr(data, 'last_refresh_at'):
            result['last_scanned_at'] = getattr(data, 'last_refresh_at')

        # Deserialize metadata_json
        if hasattr(data, 'metadata_json'):
            import json
            metadata_json = data.metadata_json
            if metadata_json:
                try:
                    result['metadata'] = json.loads(metadata_json)
                except (json.JSONDecodeError, TypeError):
                    result['metadata'] = None
            else:
                result['metadata'] = None

        # Extract pipeline_guid and pipeline_name from relationship
        if hasattr(data, 'pipeline') and data.pipeline:
            result['pipeline_guid'] = data.pipeline.guid
            result['pipeline_name'] = data.pipeline.name
        else:
            result['pipeline_guid'] = None
            result['pipeline_name'] = None

        # Extract bound_agent info from relationship
        if hasattr(data, 'bound_agent') and data.bound_agent:
            result['bound_agent'] = BoundAgentSummary(
                guid=data.bound_agent.guid,
                name=data.bound_agent.name,
                status=data.bound_agent.status.value if hasattr(data.bound_agent.status, 'value') else str(data.bound_agent.status)
            )
        else:
            result['bound_agent'] = None

        # Extract connector_guid and connector from relationship
        if hasattr(data, 'connector') and data.connector:
            result['connector_guid'] = data.connector.guid
            result['connector'] = data.connector
        else:
            result['connector_guid'] = None
            result['connector'] = None

        # Extract FileInfo summary (Issue #107)
        if hasattr(data, 'file_info') and data.file_info is not None:
            result['file_info'] = FileInfoSummary(
                count=len(data.file_info) if data.file_info else 0,
                source=getattr(data, 'file_info_source', None),
                updated_at=getattr(data, 'file_info_updated_at', None),
                delta=getattr(data, 'file_info_delta', None)
            )
        else:
            result['file_info'] = None

        return result

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "col_01hgw2bbg0000000000000000",
                "name": "Vacation Photos 2024",
                "type": "s3",
                "location": "s3://my-bucket/photos/2024/vacation",
                "state": "live",
                "connector_guid": "con_01hgw2bbg0000000000000001",
                "pipeline_guid": "pip_01hgw2bbg0000000000000001",
                "pipeline_version": 3,
                "pipeline_name": "Standard RAW Workflow",
                "bound_agent": None,
                "cache_ttl": 7200,
                "is_accessible": True,
                "last_error": None,
                "metadata": {"year": 2024, "location": "Hawaii"},
                "created_at": "2025-12-20T08:00:00",
                "updated_at": "2025-12-30T10:30:00",
                "connector": {
                    "guid": "con_01hgw2bbg0000000000000001",
                    "name": "Production AWS",
                    "type": "s3",
                    "is_active": True
                }
            }
        }
    }


# ============================================================================
# Additional Response Schemas
# ============================================================================

class CollectionTestResponse(BaseModel):
    """
    Schema for collection accessibility test response.

    For LOCAL collections bound to agents, the test is performed asynchronously
    by the agent. The response includes a job_guid that can be used to track
    the test progress. The collection's is_accessible will be updated when
    the agent completes the test.

    Fields:
        success: Test result (for async tests: False until agent completes)
        message: Descriptive message
        collection: Updated collection with new accessibility status
        job_guid: Job GUID for async accessibility tests (LOCAL collections)

    Example:
        >>> response = CollectionTestResponse(success=True, message="Collection is accessible", collection=...)
    """
    success: bool = Field(..., description="Test success status")
    message: str = Field(..., description="Descriptive message")
    collection: Optional["CollectionResponse"] = Field(
        default=None,
        description="Updated collection with new accessibility status"
    )
    job_guid: Optional[str] = Field(
        default=None,
        description="Job GUID for async accessibility tests (job_xxx, only for LOCAL collections)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Collection is accessible. Found 1,234 files.",
                "collection": {
                    "guid": "col_01hgw2bbg0000000000000000",
                    "name": "Vacation Photos",
                    "type": "local",
                    "is_accessible": True,
                    "last_error": None
                },
                "job_guid": None
            }
        }
    }


class CollectionRefreshResponse(BaseModel):
    """
    Schema for collection cache refresh response.

    Fields:
        success: Refresh result
        message: Descriptive message
        file_count: Number of files found

    Example:
        >>> response = CollectionRefreshResponse(success=True, message="Cache refreshed", file_count=1234)
    """
    success: bool = Field(..., description="Refresh success status")
    message: str = Field(..., description="Descriptive message")
    file_count: int = Field(..., ge=0, description="Number of files found")


class CollectionClearCacheResponse(BaseModel):
    """
    Schema for collection inventory cache clear response (Issue #107 - T075).

    Used when clearing cached FileInfo from bucket inventory imports,
    typically before running tools with fresh cloud API data.

    Fields:
        success: Clear operation result
        message: Descriptive message
        cleared_count: Number of cached FileInfo entries that were cleared

    Example:
        >>> response = CollectionClearCacheResponse(
        ...     success=True,
        ...     message="Inventory cache cleared",
        ...     cleared_count=12345
        ... )
    """
    success: bool = Field(..., description="Clear operation success status")
    message: str = Field(..., description="Descriptive message")
    cleared_count: int = Field(..., ge=0, description="Number of cached entries cleared")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Cache refreshed successfully",
                "file_count": 1234
            }
        }
    }


class CollectionFilesResponse(BaseModel):
    """
    Schema for collection file listing response.

    Fields:
        collection_guid: Collection GUID (col_xxx)
        files: List of file paths
        cached: Whether result came from cache
        file_count: Total file count

    Example:
        >>> response = CollectionFilesResponse(collection_guid="col_01hgw2bbg0000000000000000", files=["photo1.jpg", "photo2.dng"], cached=True, file_count=2)
    """
    collection_guid: str = Field(..., description="Collection GUID (col_xxx)")
    files: list[str] = Field(..., description="List of file paths")
    cached: bool = Field(..., description="Whether result is from cache")
    file_count: int = Field(..., ge=0, description="Total file count")

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_guid": "col_01hgw2bbg0000000000000000",
                "files": ["2024/vacation/IMG_001.jpg", "2024/vacation/IMG_002.dng"],
                "cached": True,
                "file_count": 2
            }
        }
    }


# ============================================================================
# KPI Statistics Schemas (Issue #37)
# ============================================================================

class CollectionStatsResponse(BaseModel):
    """
    Aggregated statistics for all collections (KPI endpoint).

    These values are NOT affected by any filter parameters - always shows system-wide totals.

    Fields:
        total_collections: Count of all collections
        storage_used_bytes: Sum of storage_bytes across all collections
        storage_used_formatted: Human-readable storage (e.g., "2.5 TB")
        file_count: Sum of file_count across all collections
        image_count: Sum of image_count across all collections

    Example:
        >>> response = CollectionStatsResponse(
        ...     total_collections=42,
        ...     storage_used_bytes=2748779069440,
        ...     storage_used_formatted="2.5 TB",
        ...     file_count=125000,
        ...     image_count=98500
        ... )
    """
    total_collections: int = Field(..., ge=0, description="Total number of collections")
    storage_used_bytes: int = Field(..., ge=0, description="Total storage used in bytes")
    storage_used_formatted: str = Field(..., description="Human-readable storage amount")
    file_count: int = Field(..., ge=0, description="Total number of files")
    image_count: int = Field(..., ge=0, description="Total number of images after grouping")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_collections": 42,
                "storage_used_bytes": 2748779069440,
                "storage_used_formatted": "2.5 TB",
                "file_count": 125000,
                "image_count": 98500
            }
        }
    }


class ConnectorStatsResponse(BaseModel):
    """
    Aggregated statistics for all connectors (KPI endpoint).

    Fields:
        total_connectors: Count of all connectors
        active_connectors: Count of connectors where is_active=true

    Example:
        >>> response = ConnectorStatsResponse(total_connectors=5, active_connectors=3)
    """
    total_connectors: int = Field(..., ge=0, description="Total number of connectors")
    active_connectors: int = Field(..., ge=0, description="Number of active connectors")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_connectors": 5,
                "active_connectors": 3
            }
        }
    }


# Rebuild models to resolve forward references
CollectionTestResponse.model_rebuild()
