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
        credentials: Type-specific credentials object
        metadata: Optional user-defined metadata

    Example:
        >>> connector = ConnectorCreate(
        ...     name="My AWS Account",
        ...     type=ConnectorType.S3,
        ...     credentials={"aws_access_key_id": "...", "aws_secret_access_key": "..."},
        ...     metadata={"team": "engineering", "cost_center": "123"}
        ... )
    """
    name: str = Field(..., min_length=1, max_length=255, description="Unique connector name")
    type: ConnectorType = Field(..., description="Connector type")
    credentials: Dict[str, Any] = Field(..., description="Connector credentials")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="User-defined metadata")

    @model_validator(mode='after')
    def validate_credentials_match_type(self):
        """Validate credentials structure matches connector type."""
        if not self.type or not self.credentials:
            return self

        # Validate credentials based on type
        try:
            if self.type == ConnectorType.S3:
                S3Credentials(**self.credentials)
            elif self.type == ConnectorType.GCS:
                GCSCredentials(**self.credentials)
            elif self.type == ConnectorType.SMB:
                SMBCredentials(**self.credentials)
        except Exception as e:
            raise ValueError(f"Invalid credentials for {self.type.value}: {str(e)}")

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Production AWS",
                "type": "s3",
                "credentials": {
                    "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    "region": "us-west-2"
                },
                "metadata": {"team": "engineering", "environment": "production"}
            }
        }
    }


class ConnectorUpdate(BaseModel):
    """
    Schema for updating an existing connector.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New connector name
        credentials: New credentials (will be re-encrypted)
        metadata: New metadata
        is_active: Active status

    Example:
        >>> update = ConnectorUpdate(name="Updated AWS Account", is_active=False)
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    credentials: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Connector Name",
                "is_active": True,
                "metadata": {"team": "platform"}
            }
        }
    }


class ConnectorResponse(BaseModel):
    """
    Schema for connector API responses.

    Includes all connector fields except encrypted credentials.

    Fields:
        id: Connector ID
        name: Connector name
        type: ConnectorType
        metadata: User-defined metadata
        is_active: Active status
        last_validated: Last successful connection test
        last_error: Last connection error message
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = ConnectorResponse.from_orm(connector_obj)
    """
    id: int
    name: str
    type: ConnectorType
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool
    last_validated: Optional[datetime]
    last_error: Optional[str]
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
                "id": 1,
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
    - Remote collections (S3/GCS/SMB) require connector_id
    - Local collections cannot have connector_id
    - Location format is reasonable
    - State defaults to LIVE

    Fields:
        name: Unique collection name
        type: Collection type (LOCAL, S3, GCS, SMB)
        location: File path or remote location
        state: Collection state (defaults to LIVE)
        connector_id: Required for remote collections
        cache_ttl: Override default cache TTL (seconds)
        metadata: User-defined metadata

    Example:
        >>> collection = CollectionCreate(
        ...     name="Vacation 2024",
        ...     type=CollectionType.S3,
        ...     location="s3://my-bucket/photos/2024",
        ...     connector_id=1,
        ...     metadata={"year": 2024, "trip": "Hawaii"}
        ... )
    """
    name: str = Field(..., min_length=1, max_length=255, description="Unique collection name")
    type: CollectionType = Field(..., description="Collection type")
    location: str = Field(..., min_length=1, max_length=1024, description="File path or remote location")
    state: CollectionState = Field(default=CollectionState.LIVE, description="Collection state")
    connector_id: Optional[int] = Field(default=None, description="Connector ID (required for remote)")
    cache_ttl: Optional[int] = Field(default=None, ge=0, le=604800, description="Cache TTL in seconds (max 7 days)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="User-defined metadata")

    @model_validator(mode='after')
    def validate_connector_requirement(self):
        """Validate connector_id is provided for remote collections and absent for local."""
        # Check collection type requirements first (more specific error messages)

        # Local collections cannot have connector_id
        if self.type == CollectionType.LOCAL:
            if self.connector_id is not None:
                raise ValueError("connector_id must be null for LOCAL collections")

        # Remote collections require connector_id
        if self.type in [CollectionType.S3, CollectionType.GCS, CollectionType.SMB]:
            if self.connector_id is None:
                raise ValueError(f"connector_id is required for {self.type.value} collections")
            # Validate connector_id value for remote collections
            if self.connector_id < 1:
                raise ValueError(f"connector_id must be a positive integer (>= 1), got {self.connector_id}")

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Vacation Photos 2024",
                "type": "s3",
                "location": "s3://my-bucket/photos/2024/vacation",
                "state": "live",
                "connector_id": 1,
                "cache_ttl": 7200,
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
        cache_ttl: New cache TTL override
        metadata: New metadata

    Note:
        - Cannot change collection type or connector_id after creation
        - Changing state invalidates cache (new TTL applies)

    Example:
        >>> update = CollectionUpdate(state=CollectionState.ARCHIVED, cache_ttl=86400)
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    state: Optional[CollectionState] = Field(default=None)
    cache_ttl: Optional[int] = Field(default=None, ge=0, le=604800)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": "archived",
                "cache_ttl": 86400,
                "metadata": {"archived_by": "admin", "reason": "project completed"}
            }
        }
    }


class CollectionResponse(BaseModel):
    """
    Schema for collection API responses.

    Includes all collection fields and connector information.

    Fields:
        id: Collection ID
        name: Collection name
        type: Collection type
        location: File path or remote location
        state: Collection state
        connector_id: Connector ID (null for local)
        cache_ttl: Cache TTL override
        is_accessible: Accessibility flag
        last_error: Last error message
        metadata: User-defined metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
        connector: Optional connector details

    Example:
        >>> response = CollectionResponse.from_orm(collection_obj)
    """
    id: int
    name: str
    type: CollectionType
    location: str
    state: CollectionState
    connector_id: Optional[int]
    cache_ttl: Optional[int]
    is_accessible: bool
    last_error: Optional[str]
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    connector: Optional[ConnectorResponse] = None

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
                "id": 1,
                "name": "Vacation Photos 2024",
                "type": "s3",
                "location": "s3://my-bucket/photos/2024/vacation",
                "state": "live",
                "connector_id": 1,
                "cache_ttl": 7200,
                "is_accessible": True,
                "last_error": None,
                "metadata": {"year": 2024, "location": "Hawaii"},
                "created_at": "2025-12-20T08:00:00",
                "updated_at": "2025-12-30T10:30:00",
                "connector": {
                    "id": 1,
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

    Fields:
        success: Test result
        message: Descriptive message

    Example:
        >>> response = CollectionTestResponse(success=True, message="Collection is accessible")
    """
    success: bool = Field(..., description="Test success status")
    message: str = Field(..., description="Descriptive message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Collection is accessible. Found 1,234 files."
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
        collection_id: Collection ID
        files: List of file paths
        cached: Whether result came from cache
        file_count: Total file count

    Example:
        >>> response = CollectionFilesResponse(collection_id=1, files=["photo1.jpg", "photo2.dng"], cached=True, file_count=2)
    """
    collection_id: int = Field(..., description="Collection ID")
    files: list[str] = Field(..., description="List of file paths")
    cached: bool = Field(..., description="Whether result is from cache")
    file_count: int = Field(..., ge=0, description="Total file count")

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_id": 1,
                "files": ["2024/vacation/IMG_001.jpg", "2024/vacation/IMG_002.dng"],
                "cached": True,
                "file_count": 2
            }
        }
    }
