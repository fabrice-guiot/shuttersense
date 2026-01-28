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
from backend.src.schemas.inventory import (
    InventoryConfigRequest,
    InventoryStatusResponse,
    InventoryValidationResponse,
    InventoryFolderListResponse,
    InventoryFolderResponse,
    InventoryImportTriggerResponse,
)
from backend.src.services.connector_service import ConnectorService
from backend.src.services.inventory_service import InventoryService, InventoryValidationStatus
from backend.src.services.exceptions import ConflictError
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import get_logger
from backend.src.middleware.auth import require_auth, TenantContext


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


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    """Create InventoryService instance with dependencies."""
    return InventoryService(db=db)


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
    ctx: TenantContext = Depends(require_auth),
    connector_service: ConnectorService = Depends(get_connector_service)
) -> ConnectorStatsResponse:
    """
    Get aggregated statistics for team's connectors.

    Returns KPIs for the Connectors page topband.

    Returns:
        ConnectorStatsResponse with:
        - total_connectors: Count of team's connectors
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
        stats = connector_service.get_connector_stats(team_id=ctx.team_id)

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
    ctx: TenantContext = Depends(require_auth),
    type: Optional[ConnectorType] = Query(None, description="Filter by type (s3, gcs, smb)"),
    active_only: bool = Query(False, description="Only return active connectors"),
    connector_service: ConnectorService = Depends(get_connector_service)
) -> List[ConnectorResponse]:
    """
    List team's connectors with optional filters.

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
            team_id=ctx.team_id,
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
    ctx: TenantContext = Depends(require_auth),
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
            team_id=ctx.team_id,
            credential_location=connector.credential_location,
            credentials=connector.credentials,
            metadata=connector.metadata,
            is_active=connector.is_active
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
    ctx: TenantContext = Depends(require_auth),
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
        404 Not Found: If connector doesn't exist or belongs to different team

    Example:
        GET /api/connectors/con_01hgw2bbg0000000000000000
    """
    try:
        # Filter by team_id to ensure tenant isolation (cross-team access returns 404)
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

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
    ctx: TenantContext = Depends(require_auth),
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
        404 Not Found: If connector doesn't exist or belongs to different team
        409 Conflict: If name conflicts with existing connector

    Example:
        PUT /api/connectors/con_01hgw2bbg0000000000000000
        {
          "name": "Updated AWS Account",
          "is_active": false
        }
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for update: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        updated_connector = connector_service.update_connector(
            connector_id=connector.id,
            name=connector_update.name,
            credential_location=connector_update.credential_location,
            credentials=connector_update.credentials,
            update_credentials=connector_update.update_credentials,
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
    ctx: TenantContext = Depends(require_auth),
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
        404 Not Found: If connector doesn't exist or belongs to different team
        409 Conflict: If collections reference this connector

    Example:
        DELETE /api/connectors/con_01hgw2bbg0000000000000000

        Success (no collections): 204 No Content
        Error (has collections): 409 Conflict with message:
        "Cannot delete connector 'My AWS' because 3 collection(s) reference it.
         Delete or reassign collections first."
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

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
    ctx: TenantContext = Depends(require_auth),
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
        404 Not Found: If connector doesn't exist or belongs to different team

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
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

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


# ============================================================================
# Inventory Configuration Endpoints (Issue #107)
# ============================================================================

@router.put(
    "/{guid}/inventory/config",
    response_model=ConnectorResponse,
    summary="Configure inventory source",
    description="Set inventory configuration on a connector (S3 or GCS)"
)
async def update_inventory_config(
    guid: str,
    request: InventoryConfigRequest,
    ctx: TenantContext = Depends(require_auth),
    connector_service: ConnectorService = Depends(get_connector_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
) -> ConnectorResponse:
    """
    Configure inventory source on a connector.

    Sets S3 or GCS inventory configuration and triggers validation.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Request Body:
        InventoryConfigRequest with config and schedule

    Returns:
        ConnectorResponse with updated inventory configuration

    Raises:
        400 Bad Request: If connector type doesn't support inventory
        404 Not Found: If connector doesn't exist

    Example:
        PUT /api/connectors/con_01hgw2bbg.../inventory/config
        {
          "config": {
            "provider": "s3",
            "destination_bucket": "my-inventory-bucket",
            "source_bucket": "my-photo-bucket",
            "config_name": "daily-inventory"
          },
          "schedule": "weekly"
        }
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for inventory config: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        # Set inventory configuration
        updated_connector = inventory_service.set_inventory_config(
            connector_id=connector.id,
            config=request.config,
            schedule=request.schedule,
            team_id=ctx.team_id
        )

        logger.info(
            f"Set inventory config on connector",
            extra={
                "guid": guid,
                "provider": request.config.provider,
                "schedule": request.schedule
            }
        )

        return ConnectorResponse.model_validate(updated_connector)

    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Invalid inventory config: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error setting inventory config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set inventory configuration: {str(e)}"
        )


@router.delete(
    "/{guid}/inventory/config",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove inventory configuration",
    description="Clear inventory configuration from connector"
)
async def delete_inventory_config(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    connector_service: ConnectorService = Depends(get_connector_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
) -> None:
    """
    Remove inventory configuration from a connector.

    Clears config, validation status, and deletes associated inventory folders.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        204 No Content on success

    Raises:
        404 Not Found: If connector doesn't exist

    Example:
        DELETE /api/connectors/con_01hgw2bbg.../inventory/config
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for inventory config delete: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        inventory_service.clear_inventory_config(
            connector_id=connector.id,
            team_id=ctx.team_id
        )

        logger.info(
            f"Cleared inventory config from connector",
            extra={"guid": guid}
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error clearing inventory config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear inventory configuration: {str(e)}"
        )


@router.post(
    "/{guid}/inventory/validate",
    response_model=InventoryValidationResponse,
    summary="Validate inventory configuration",
    description="Validate inventory manifest.json accessibility"
)
async def validate_inventory_config(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    connector_service: ConnectorService = Depends(get_connector_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
) -> InventoryValidationResponse:
    """
    Validate inventory configuration by checking manifest.json accessibility.

    For connectors with server-side credentials, validation happens synchronously
    by checking if manifest.json exists at the configured inventory location.

    For connectors with agent-side credentials, a validation job is created
    for an agent to execute.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        InventoryValidationResponse with validation result

    Raises:
        400 Bad Request: If no inventory config exists
        404 Not Found: If connector doesn't exist

    Example:
        POST /api/connectors/con_01hgw2bbg.../inventory/validate

        Server-side credentials response:
        {
          "success": true,
          "message": "Found 3 inventory manifest(s)",
          "validation_status": "validated",
          "job_guid": null
        }

        Agent-side credentials response:
        {
          "success": true,
          "message": "Validation job created for agent",
          "validation_status": "pending",
          "job_guid": "job_01hgw2bbg..."
        }
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for inventory validation: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        if not connector.inventory_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connector has no inventory configuration to validate"
            )

        # Check if connector uses agent-side credentials
        if connector.requires_agent_credentials:
            # Create validation job for agent
            job = inventory_service.create_validation_job(
                connector_id=connector.id,
                team_id=ctx.team_id
            )

            logger.info(
                f"Created inventory validation job for agent",
                extra={
                    "guid": guid,
                    "job_guid": job.guid
                }
            )

            return InventoryValidationResponse(
                success=True,
                message="Validation job created for agent",
                validation_status="pending",
                job_guid=job.guid
            )

        # Server-side credentials: validate synchronously
        # Get connector with decrypted credentials for validation
        connector_with_creds = connector_service.get_connector(
            connector.id, decrypt_credentials=True
        )
        if not connector_with_creds:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        success, message = inventory_service.validate_inventory_config_server_side(
            connector_id=connector.id,
            team_id=ctx.team_id,
            credentials=connector_with_creds.decrypted_credentials
        )

        # Refresh connector to get updated validation status
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)
        if not connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        logger.info(
            f"Validated inventory config (server-side)",
            extra={
                "guid": guid,
                "success": success,
                "validation_status": connector.inventory_validation_status
            }
        )

        return InventoryValidationResponse(
            success=success,
            message=message,
            validation_status=connector.inventory_validation_status or "unknown",
            job_guid=None
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error validating inventory config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate inventory configuration: {str(e)}"
        )


@router.get(
    "/{guid}/inventory/status",
    response_model=InventoryStatusResponse,
    summary="Get inventory status",
    description="Get current inventory import status and statistics"
)
async def get_inventory_status(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    connector_service: ConnectorService = Depends(get_connector_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
) -> InventoryStatusResponse:
    """
    Get inventory status for a connector.

    Returns validation status, folder counts, and current job info.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        InventoryStatusResponse with status and statistics

    Raises:
        404 Not Found: If connector doesn't exist

    Example:
        GET /api/connectors/con_01hgw2bbg.../inventory/status

        Response:
        {
          "validation_status": "validated",
          "folder_count": 42,
          "mapped_folder_count": 15,
          "current_job": null
        }
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for inventory status: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        status_data = inventory_service.get_inventory_status(
            connector_id=connector.id,
            team_id=ctx.team_id
        )

        logger.info(
            f"Retrieved inventory status for connector",
            extra={"guid": guid, "validation_status": status_data.get("validation_status")}
        )

        return InventoryStatusResponse(**status_data)

    except ValueError as e:
        # Invalid GUID format
        logger.warning(f"Invalid GUID: {guid} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting inventory status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get inventory status: {str(e)}"
        )


@router.get(
    "/{guid}/inventory/folders",
    response_model=InventoryFolderListResponse,
    summary="List discovered folders",
    description="Get folders discovered from inventory import"
)
async def list_inventory_folders(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    path_prefix: Optional[str] = Query(None, description="Filter by path prefix"),
    unmapped_only: bool = Query(False, description="Only unmapped folders"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
    connector_service: ConnectorService = Depends(get_connector_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
) -> InventoryFolderListResponse:
    """
    List inventory folders discovered from a connector.

    Supports filtering by path prefix and mapping status.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Query Parameters:
        path_prefix: Filter by path prefix (e.g., "2020/")
        unmapped_only: If true, only return unmapped folders
        limit: Maximum results (default 1000, max 10000)
        offset: Skip first N results

    Returns:
        InventoryFolderListResponse with folders and pagination info

    Raises:
        404 Not Found: If connector doesn't exist

    Example:
        GET /api/connectors/con_01hgw2bbg.../inventory/folders?unmapped_only=true
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for inventory folders: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        folders, total_count, has_more = inventory_service.list_folders(
            connector_id=connector.id,
            team_id=ctx.team_id,
            path_prefix=path_prefix,
            unmapped_only=unmapped_only,
            limit=limit,
            offset=offset
        )

        # Convert to response models with suggested names
        folder_responses = []
        for folder in folders:
            folder_response = InventoryFolderResponse(
                guid=folder.guid,
                path=folder.path,
                object_count=folder.object_count or 0,
                total_size_bytes=folder.total_size_bytes or 0,
                deepest_modified=folder.deepest_modified,
                discovered_at=folder.discovered_at,
                collection_guid=folder.collection_guid,
                suggested_name=folder.name  # Use the name property as suggested name
            )
            folder_responses.append(folder_response)

        logger.info(
            f"Listed inventory folders",
            extra={
                "guid": guid,
                "total_count": total_count,
                "returned_count": len(folder_responses)
            }
        )

        return InventoryFolderListResponse(
            folders=folder_responses,
            total_count=total_count,
            has_more=has_more
        )

    except ValueError as e:
        # Invalid GUID format
        logger.warning(f"Invalid GUID: {guid} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error listing inventory folders: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list inventory folders: {str(e)}"
        )


@router.post(
    "/{guid}/inventory/import",
    response_model=InventoryImportTriggerResponse,
    summary="Trigger inventory import",
    description="Start an inventory import job to extract folders from cloud storage inventory"
)
async def trigger_inventory_import(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    connector_service: ConnectorService = Depends(get_connector_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
) -> InventoryImportTriggerResponse:
    """
    Trigger an inventory import job.

    Creates a job that will:
    1. Fetch the latest inventory manifest
    2. Parse data files (CSV/Parquet)
    3. Extract unique folder paths
    4. Store folders in the database

    The job is executed by an agent with the appropriate connector capability.

    Path Parameters:
        guid: Connector GUID (con_xxx format)

    Returns:
        InventoryImportTriggerResponse with job GUID

    Raises:
        400 Bad Request: If no inventory config or config not validated
        404 Not Found: If connector doesn't exist

    Example:
        POST /api/connectors/con_01hgw2bbg.../inventory/import

        Response:
        {
          "job_guid": "job_01hgw2bbg...",
          "message": "Inventory import job created"
        }
    """
    try:
        # Get connector by GUID with tenant filtering
        connector = connector_service.get_by_guid(guid, team_id=ctx.team_id)

        if not connector:
            logger.warning(f"Connector not found for inventory import: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector not found: {guid}"
            )

        if not connector.inventory_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connector has no inventory configuration. Configure inventory first."
            )

        # Check if inventory is validated
        if connector.inventory_validation_status != InventoryValidationStatus.VALIDATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory configuration not validated. Current status: {connector.inventory_validation_status or 'none'}"
            )

        # Create import job
        job = inventory_service.create_import_job(
            connector_id=connector.id,
            team_id=ctx.team_id
        )

        logger.info(
            f"Created inventory import job",
            extra={
                "guid": guid,
                "job_guid": job.guid
            }
        )

        return InventoryImportTriggerResponse(
            job_guid=job.guid,
            message="Inventory import job created"
        )

    except ConflictError as e:
        # T039: Concurrent import prevention - return 409 if job already running
        logger.warning(
            f"Inventory import conflict: {e.message}",
            extra={
                "guid": guid,
                "existing_job_guid": e.existing_job_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": e.message,
                "existing_job_guid": e.existing_job_id
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error triggering inventory import: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger inventory import: {str(e)}"
        )
