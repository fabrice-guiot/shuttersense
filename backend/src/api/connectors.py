"""
Connectors API endpoints for managing remote storage connectors.

Provides CRUD operations and connection testing for storage connectors:
- List connectors with filtering
- Create new connectors with credential encryption
- Get connector details (without credentials)
- Update connector properties
- Delete connectors with protection against referenced collections
- Test connector connections

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- Query parameter validation
- Response models for type safety
- Credentials never exposed in responses
- All endpoints use GUID format (con_xxx) for identifiers
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.models import ConnectorType
from backend.src.schemas.collection import (
    ConnectorCreate,
    ConnectorUpdate,
    ConnectorResponse,
    ConnectorTestResponse,
    ConnectorStatsResponse,
)
from backend.src.services.connector_service import ConnectorService
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/connectors",
    tags=["Connectors"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_credential_encryptor(request: Request) -> CredentialEncryptor:
    """Get credential encryptor from application state."""
    return request.app.state.credential_encryptor


def get_connector_service(
    db: Session = Depends(get_db),
    encryptor: CredentialEncryptor = Depends(get_credential_encryptor)
) -> ConnectorService:
    """Create ConnectorService instance with dependencies."""
    return ConnectorService(db=db, encryptor=encryptor)


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/stats",
    response_model=ConnectorStatsResponse,
    summary="Get connector statistics",
    description="Get aggregated KPI statistics for all connectors (Issue #37)"
)
async def get_connector_stats(
    connector_service: ConnectorService = Depends(get_connector_service)
) -> ConnectorStatsResponse:
    """
    Get aggregated statistics for all connectors.

    Returns KPIs for the Connectors page topband.

    Returns:
        ConnectorStatsResponse with:
        - total_connectors: Count of all connectors
        - active_connectors: Count of active connectors (is_active=true)

    Example:
        GET /api/connectors/stats

        Response:
        {
          "total_connectors": 5,
          "active_connectors": 3
        }
    """
    try:
        stats = connector_service.get_connector_stats()

        logger.info(
            f"Retrieved connector stats",
            extra={"total_connectors": stats['total_connectors']}
        )

        return ConnectorStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting connector stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connector statistics: {str(e)}"
        )


@router.get(
    "",
    response_model=List[ConnectorResponse],
    summary="List connectors",
    description="List all connectors with optional filtering by type and active status"
)
async def list_connectors(
    type: Optional[ConnectorType] = Query(None, description="Filter by type (s3, gcs, smb)"),
    active_only: bool = Query(False, description="Only return active connectors"),
    connector_service: ConnectorService = Depends(get_connector_service)
) -> List[ConnectorResponse]:
    """
    List connectors with optional filters.

    Query Parameters:
        - type: Filter by connector type (S3, GCS, SMB)
        - active_only: If true, only return connectors with is_active=true

    Returns:
        List of ConnectorResponse objects (credentials are NOT included)

    Example:
        GET /api/connectors?type=s3&active_only=true
    """
    try:
        connectors = connector_service.list_connectors(
            type_filter=type,
            active_only=active_only
        )

        logger.info(
            f"Listed {len(connectors)} connectors",
            extra={
                "type_filter": type.value if type else None,
                "active_only": active_only,
                "count": len(connectors)
            }
        )

        return [ConnectorResponse.model_validate(c) for c in connectors]

    except Exception as e:
        logger.error(f"Error listing connectors: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connectors: {str(e)}"
        )


@router.post(
    "",
    response_model=ConnectorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create connector",
    description="Create a new connector with encrypted credentials"
)
async def create_connector(
    connector: ConnectorCreate,
    connector_service: ConnectorService = Depends(get_connector_service)
) -> ConnectorResponse:
    """
    Create a new connector.

    Validates:
    - Connector name is unique
    - Credentials match connector type (S3/GCS/SMB)
    - Credentials are valid (structure validation only, not connection test)

    Request Body:
        ConnectorCreate schema with name, type, credentials, metadata

    Returns:
        ConnectorResponse with created connector details (credentials encrypted, not returned)

    Raises:
        409 Conflict: If connector name already exists
        400 Bad Request: If credential validation fails
        500 Internal Server Error: If creation fails

    Example:
        POST /api/connectors
        {
          "name": "Production AWS",
          "type": "s3",
          "credentials": {
            "aws_access_key_id": "AKIA...",
            "aws_secret_access_key": "...",
            "region": "us-west-2"
          },
          "metadata": {"team": "engineering"}
        }
    """
    try:
        created_connector = connector_service.create_connector(
            name=connector.name,
            type=connector.type,
            credentials=connector.credentials,
            metadata=connector.metadata
        )

        logger.info(
            f"Created connector: {connector.name}",
            extra={
                "connector_id": created_connector.id,
                "type": connector.type.value
            }
        )

        return ConnectorResponse.model_validate(created_connector)

    except ValueError as e:
        error_msg = str(e)
        # Name conflict
        if "already exists" in error_msg:
            logger.warning(f"Connector name conflict: {connector.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        # Validation error
        else:
            logger.warning(f"Connector creation validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except Exception as e:
        logger.error(f"Error creating connector: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connector: {str(e)}"
        )


@router.get(
    "/{guid}",
    response_model=ConnectorResponse,
    summary="Get connector",
    description="Get a single connector by GUID (e.g., con_01hgw...)"
)
async def get_connector(
    guid: str,
    connector_service: ConnectorService = Depends(get_connector_service)
) -> ConnectorResponse:
    """
    Get connector by GUID.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        ConnectorResponse with connector details (credentials encrypted, not returned)

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If connector doesn't exist

    Example:
        GET /api/connectors/con_01hgw2bbg0000000000000000
    """
    try:
        connector = connector_service.get_by_guid(guid)

        if not connector:
            logger.warning(f"Connector not found: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        logger.info(
            f"Retrieved connector: {connector.name}",
            extra={"guid": guid}
        )

        return ConnectorResponse.model_validate(connector)

    except ValueError as e:
        # Invalid GUID format or prefix mismatch
        logger.warning(f"Invalid connector GUID: {guid} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{guid}",
    response_model=ConnectorResponse,
    summary="Update connector",
    description="Update connector properties (credentials will be re-encrypted if provided)"
)
async def update_connector(
    guid: str,
    connector_update: ConnectorUpdate,
    connector_service: ConnectorService = Depends(get_connector_service)
) -> ConnectorResponse:
    """
    Update connector properties by GUID.

    Only provided fields will be updated. If credentials are provided, they will be re-encrypted.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Request Body:
        ConnectorUpdate schema with optional fields

    Returns:
        ConnectorResponse with updated connector

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If connector doesn't exist
        409 Conflict: If name conflicts with existing connector

    Example:
        PUT /api/connectors/con_01hgw2bbg0000000000000000
        {
          "name": "Updated AWS Account",
          "is_active": false
        }
    """
    try:
        # Get connector by GUID
        connector = connector_service.get_by_guid(guid)

        if not connector:
            logger.warning(f"Connector not found for update: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        updated_connector = connector_service.update_connector(
            connector_id=connector.id,
            name=connector_update.name,
            credentials=connector_update.credentials,
            metadata=connector_update.metadata,
            is_active=connector_update.is_active
        )

        logger.info(
            f"Updated connector: {updated_connector.name}",
            extra={"guid": guid}
        )

        return ConnectorResponse.model_validate(updated_connector)

    except ValueError as e:
        error_msg = str(e)
        # Invalid GUID format or prefix mismatch
        if "prefix mismatch" in error_msg.lower() or "Invalid identifier" in error_msg or "Numeric IDs" in error_msg:
            logger.warning(f"Invalid GUID: {guid} - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        # Name conflict
        elif "already exists" in error_msg:
            logger.warning(f"Connector name conflict during update: {connector_update.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        # Other validation errors
        else:
            logger.warning(f"Connector update validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error updating connector: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update connector: {str(e)}"
        )


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete connector",
    description="Delete connector (protected: cannot delete if collections reference it)"
)
async def delete_connector(
    guid: str,
    connector_service: ConnectorService = Depends(get_connector_service)
) -> None:
    """
    Delete connector by GUID.

    PROTECTED OPERATION: Cannot delete if any collections reference this connector.
    This prevents orphaned collections and ensures data integrity.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        204 No Content on success

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If connector doesn't exist
        409 Conflict: If collections reference this connector

    Example:
        DELETE /api/connectors/con_01hgw2bbg0000000000000000

        Success (no collections): 204 No Content
        Error (has collections): 409 Conflict with message:
        "Cannot delete connector 'My AWS' because 3 collection(s) reference it.
         Delete or reassign collections first."
    """
    try:
        # Get connector by GUID
        connector = connector_service.get_by_guid(guid)

        if not connector:
            logger.warning(f"Connector not found for deletion: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        connector_service.delete_connector(connector.id)

        logger.info(
            f"Deleted connector",
            extra={"guid": guid}
        )

    except ValueError as e:
        error_msg = str(e)
        # Invalid GUID format or prefix mismatch
        if "prefix mismatch" in error_msg.lower() or "Invalid identifier" in error_msg or "Numeric IDs" in error_msg:
            logger.warning(f"Invalid GUID: {guid} - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        # Not found
        elif "not found" in error_msg:
            logger.warning(f"Connector not found for deletion: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        # Has collections (RESTRICT constraint)
        elif "collection(s) reference it" in error_msg:
            logger.warning(f"Cannot delete connector with collections: {guid}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        # Other validation errors
        else:
            logger.warning(f"Connector deletion validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deleting connector: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connector: {str(e)}"
        )


@router.post(
    "/{guid}/test",
    response_model=ConnectorTestResponse,
    summary="Test connector connection",
    description="Test connector connection and update last_validated/last_error fields"
)
async def test_connector(
    guid: str,
    connector_service: ConnectorService = Depends(get_connector_service)
) -> ConnectorTestResponse:
    """
    Test connector connection.

    Tests connectivity using the appropriate storage adapter (S3/GCS/SMB) and updates
    connector.last_validated and connector.last_error fields based on the result.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        ConnectorTestResponse with success status and message

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If connector doesn't exist

    Example:
        POST /api/connectors/con_01hgw2bbg0000000000000000/test

        Success Response:
        {
          "success": true,
          "message": "Connected to S3 bucket 'my-photos'. Found 1,234 objects."
        }

        Failure Response:
        {
          "success": false,
          "message": "Authentication failed. Check access key and secret key: InvalidAccessKeyId"
        }
    """
    try:
        # Get connector by GUID
        connector = connector_service.get_by_guid(guid)

        if not connector:
            logger.warning(f"Connector not found for test: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        success, message = connector_service.test_connector(connector.id)

        logger.info(
            f"Tested connector connection",
            extra={"guid": guid, "success": success}
        )

        return ConnectorTestResponse(success=success, message=message)

    except ValueError as e:
        error_msg = str(e)
        # Invalid GUID format or prefix mismatch
        if "prefix mismatch" in error_msg.lower() or "Invalid identifier" in error_msg or "Numeric IDs" in error_msg:
            logger.warning(f"Invalid GUID: {guid} - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        # Not found
        if "not found" in error_msg:
            logger.warning(f"Connector not found for test: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error testing connector: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connector: {str(e)}"
        )
