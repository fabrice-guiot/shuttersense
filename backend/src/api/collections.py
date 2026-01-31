"""
Collections API endpoints for managing photo collections.

Provides CRUD operations and management functions for photo collections:
- List collections with filtering
- Create new collections with accessibility testing
- Get collection details
- Update collection properties
- Delete collections with force flag
- Test collection accessibility
- Refresh collection file cache

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- Query parameter validation
- Response models for type safety
- All endpoints use GUID format (col_xxx) for identifiers
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.models import CollectionType, CollectionState, Pipeline, Connector
from backend.src.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionTestResponse,
    CollectionRefreshResponse,
    CollectionClearCacheResponse,
    CollectionStatsResponse,
)
from backend.src.schemas.inventory import (
    CreateCollectionsFromInventoryRequest,
    CreateCollectionsFromInventoryResponse,
    CollectionCreatedSummary,
    CollectionCreationError,
)
from backend.src.services.inventory_service import InventoryService
from backend.src.services.collection_service import CollectionService
from backend.src.services.config_service import ConfigService
from backend.src.services.connector_service import ConnectorService
from backend.src.services.guid import GuidService
from backend.src.utils.cache import FileListingCache
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import get_logger
from backend.src.middleware.auth import require_auth, TenantContext


logger = get_logger("api")

router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_file_cache(request: Request) -> FileListingCache:
    """Get file listing cache from application state."""
    return request.app.state.file_cache


def get_credential_encryptor(request: Request) -> CredentialEncryptor:
    """Get credential encryptor from application state."""
    return request.app.state.credential_encryptor


def get_connector_service(
    db: Session = Depends(get_db),
    encryptor: CredentialEncryptor = Depends(get_credential_encryptor)
) -> ConnectorService:
    """Create ConnectorService instance with dependencies."""
    return ConnectorService(db=db, encryptor=encryptor)


def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    """Create ConfigService instance with dependencies."""
    return ConfigService(db=db)


def get_collection_service(
    db: Session = Depends(get_db),
    file_cache: FileListingCache = Depends(get_file_cache),
    connector_service: ConnectorService = Depends(get_connector_service),
    config_service: ConfigService = Depends(get_config_service)
) -> CollectionService:
    """Create CollectionService instance with dependencies."""
    return CollectionService(
        db=db,
        file_cache=file_cache,
        connector_service=connector_service,
        config_service=config_service
    )


# ============================================================================
# API Endpoints (T096-T102)
# ============================================================================

@router.get(
    "/stats",
    response_model=CollectionStatsResponse,
    summary="Get collection statistics",
    description="Get aggregated KPI statistics for team's collections (Issue #37)"
)
async def get_collection_stats(
    ctx: TenantContext = Depends(require_auth),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionStatsResponse:
    """
    Get aggregated statistics for team's collections.

    Returns KPIs for the Collections page topband. These values are NOT affected
    by any filter parameters - shows team-wide totals.

    Returns:
        CollectionStatsResponse with:
        - total_collections: Count of team's collections
        - storage_used_bytes: Total storage in bytes
        - storage_used_formatted: Human-readable storage (e.g., "2.5 TB")
        - file_count: Total number of files
        - image_count: Total number of images after grouping

    Example:
        GET /api/collections/stats

        Response:
        {
          "total_collections": 42,
          "storage_used_bytes": 2748779069440,
          "storage_used_formatted": "2.5 TB",
          "file_count": 125000,
          "image_count": 98500
        }
    """
    try:
        stats = collection_service.get_collection_stats(team_id=ctx.team_id)

        logger.info(
            f"Retrieved collection stats",
            extra={"total_collections": stats['total_collections']}
        )

        return CollectionStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting collection stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection statistics: {str(e)}"
        )


@router.get(
    "",
    response_model=List[CollectionResponse],
    summary="List collections",
    description="List team's collections with optional filtering by state, type, accessibility, and name search"
)
async def list_collections(
    ctx: TenantContext = Depends(require_auth),
    state: Optional[CollectionState] = Query(None, description="Filter by state (live, closed, archived)"),
    type: Optional[CollectionType] = Query(None, description="Filter by type (local, s3, gcs, smb)"),
    accessible_only: bool = Query(False, description="Only return accessible collections"),
    search: Optional[str] = Query(None, max_length=100, description="Search by collection name (case-insensitive partial match)"),
    collection_service: CollectionService = Depends(get_collection_service)
) -> List[CollectionResponse]:
    """
    List collections with optional filters.

    Query Parameters:
        - state: Filter by collection state (LIVE, CLOSED, ARCHIVED)
        - type: Filter by collection type (LOCAL, S3, GCS, SMB)
        - accessible_only: If true, only return collections with is_accessible=true
        - search: Case-insensitive partial match on collection name (max 100 chars)

    Returns:
        List of CollectionResponse objects sorted by created_at descending

    Example:
        GET /api/collections?state=live&type=s3&accessible_only=true&search=vacation
    """
    try:
        collections = collection_service.list_collections(
            team_id=ctx.team_id,
            state_filter=state,
            type_filter=type,
            accessible_only=accessible_only,
            search=search
        )

        logger.info(
            f"Listed {len(collections)} collections",
            extra={
                "state_filter": state.value if state else None,
                "type_filter": type.value if type else None,
                "accessible_only": accessible_only,
                "search": search[:20] + "..." if search and len(search) > 20 else search,
                "count": len(collections)
            }
        )

        return [CollectionResponse.model_validate(c) for c in collections]

    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}"
        )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create collection",
    description="Create a new collection with automatic accessibility testing"
)
async def create_collection(
    collection: CollectionCreate,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionResponse:
    """
    Create a new collection.

    Validates:
    - Collection name is unique
    - Remote collections have valid connector_guid
    - Local collections don't specify connector_guid
    - Collection is accessible before creation

    Request Body:
        CollectionCreate schema with name, type, location, etc.

    Returns:
        CollectionResponse with created collection details

    Raises:
        409 Conflict: If collection name already exists
        400 Bad Request: If accessibility test fails, validation fails, or invalid GUID
        500 Internal Server Error: If creation fails

    Example:
        POST /api/collections
        {
          "name": "Vacation 2024",
          "type": "s3",
          "location": "s3://bucket/photos",
          "connector_guid": "con_01hgw2bbg0000000000000001",
          "state": "live"
        }
    """
    try:
        # Resolve connector_guid to internal ID using injected db session
        connector_id = None
        if collection.connector_guid:
            connector_uuid = GuidService.parse_identifier(
                collection.connector_guid, expected_prefix="con"
            )
            connector = db.query(Connector).filter(
                Connector.uuid == connector_uuid
            ).first()
            if not connector:
                raise ValueError(
                    f"Connector not found: {collection.connector_guid}"
                )
            connector_id = connector.id

        # Resolve pipeline_guid to internal ID using injected db session
        pipeline_id = None
        if collection.pipeline_guid:
            pipeline_uuid = GuidService.parse_identifier(
                collection.pipeline_guid, expected_prefix="pip"
            )
            pipeline = db.query(Pipeline).filter(
                Pipeline.uuid == pipeline_uuid
            ).first()
            if not pipeline:
                raise ValueError(
                    f"Pipeline not found: {collection.pipeline_guid}"
                )
            pipeline_id = pipeline.id

        # Resolve bound_agent_guid to internal ID for LOCAL collections
        bound_agent_id = None
        if collection.bound_agent_guid:
            from backend.src.models.agent import Agent
            bound_agent_uuid = GuidService.parse_identifier(
                collection.bound_agent_guid, expected_prefix="agt"
            )
            agent = db.query(Agent).filter(
                Agent.uuid == bound_agent_uuid
            ).first()
            if not agent:
                raise ValueError(
                    f"Agent not found: {collection.bound_agent_guid}"
                )
            bound_agent_id = agent.id

        created_collection = collection_service.create_collection(
            name=collection.name,
            type=collection.type,
            location=collection.location,
            team_id=ctx.team_id,
            state=collection.state,
            connector_id=connector_id,
            bound_agent_id=bound_agent_id,
            pipeline_id=pipeline_id,
            metadata=collection.metadata,
            user_id=ctx.user_id
        )

        logger.info(
            f"Created collection: {collection.name}",
            extra={
                "collection_guid": created_collection.guid,
                "type": collection.type.value,
                "location": collection.location
            }
        )

        # For LOCAL collections with bound agent, auto-trigger accessibility test job
        if collection.type == CollectionType.LOCAL and created_collection.bound_agent_id:
            from backend.src.models.job import Job, JobStatus as PersistentJobStatus

            test_job = Job(
                team_id=ctx.team_id,
                collection_id=created_collection.id,
                tool="collection_test",
                mode="collection",
                status=PersistentJobStatus.PENDING,
                bound_agent_id=created_collection.bound_agent_id,
                required_capabilities=["local_filesystem"],
            )
            db.add(test_job)
            db.commit()
            db.refresh(test_job)
            db.refresh(created_collection)

            logger.info(
                f"Auto-created collection_test job for new LOCAL collection",
                extra={
                    "collection_guid": created_collection.guid,
                    "job_guid": test_job.guid,
                    "agent_id": created_collection.bound_agent_id
                }
            )

        return CollectionResponse.model_validate(created_collection)

    except ValueError as e:
        error_msg = str(e)
        # Name conflict
        if "already exists" in error_msg:
            logger.warning(f"Collection name conflict: {collection.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        # Accessibility or validation error
        else:
            logger.warning(f"Collection creation validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except Exception as e:
        logger.error(f"Error creating collection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}"
        )


@router.get(
    "/{guid}",
    response_model=CollectionResponse,
    summary="Get collection",
    description="Get a single collection by GUID (e.g., col_01hgw...)"
)
async def get_collection(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionResponse:
    """
    Get collection by GUID.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Returns:
        CollectionResponse with collection details and connector info

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If collection doesn't exist or belongs to different team

    Example:
        GET /api/collections/col_01hgw2bbg0000000000000000
    """
    try:
        # Filter by team_id to ensure tenant isolation (cross-team access returns 404)
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        logger.info(
            f"Retrieved collection: {collection.name}",
            extra={"guid": guid}
        )

        return CollectionResponse.model_validate(collection)

    except ValueError as e:
        # Invalid GUID format or prefix mismatch
        logger.warning(f"Invalid collection GUID: {guid} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{guid}",
    response_model=CollectionResponse,
    summary="Update collection",
    description="Update collection properties with cache invalidation on state changes"
)
async def update_collection(
    guid: str,
    collection_update: CollectionUpdate,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionResponse:
    """
    Update collection properties by GUID.

    Only provided fields will be updated. Changing state invalidates cache.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Request Body:
        CollectionUpdate schema with optional fields

    Returns:
        CollectionResponse with updated collection

    Raises:
        400 Bad Request: If GUID format is invalid, prefix mismatch, or invalid pipeline_guid
        404 Not Found: If collection doesn't exist
        409 Conflict: If name conflicts with existing collection

    Example:
        PUT /api/collections/col_01hgw2bbg0000000000000000
        {
          "state": "archived",
          "cache_ttl": 86400
        }
    """
    try:
        # Get collection by GUID with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for update: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        # Resolve pipeline_guid to internal ID if provided using injected db session
        pipeline_id = None
        if collection_update.pipeline_guid:
            pipeline_uuid = GuidService.parse_identifier(
                collection_update.pipeline_guid, expected_prefix="pip"
            )
            pipeline = db.query(Pipeline).filter(
                Pipeline.uuid == pipeline_uuid
            ).first()
            if not pipeline:
                raise ValueError(
                    f"Pipeline not found: {collection_update.pipeline_guid}"
                )
            pipeline_id = pipeline.id

        # Resolve bound_agent_guid to internal ID if provided (LOCAL collections only)
        # Use sentinel ... to differentiate None (unbind) from not provided
        bound_agent_id = ...  # Sentinel default (ellipsis)
        if collection_update.bound_agent_guid is not None:
            from backend.src.models.agent import Agent
            bound_agent_uuid = GuidService.parse_identifier(
                collection_update.bound_agent_guid, expected_prefix="agt"
            )
            agent = db.query(Agent).filter(
                Agent.uuid == bound_agent_uuid
            ).first()
            if not agent:
                raise ValueError(
                    f"Agent not found: {collection_update.bound_agent_guid}"
                )
            bound_agent_id = agent.id
        elif hasattr(collection_update, 'bound_agent_guid') and collection_update.model_fields_set and 'bound_agent_guid' in collection_update.model_fields_set:
            # Explicitly set to null means unbind
            bound_agent_id = None

        updated_collection = collection_service.update_collection(
            collection_id=collection.id,
            name=collection_update.name,
            location=collection_update.location,
            state=collection_update.state,
            pipeline_id=pipeline_id,
            bound_agent_id=bound_agent_id,
            metadata=collection_update.metadata,
            user_id=ctx.user_id
        )

        logger.info(
            f"Updated collection: {updated_collection.name}",
            extra={"guid": guid}
        )

        # For LOCAL collections, if accessibility is pending (connectivity changed),
        # auto-trigger a test job
        if (
            updated_collection.type == CollectionType.LOCAL and
            updated_collection.bound_agent_id is not None and
            updated_collection.is_accessible is None
        ):
            from backend.src.models.job import Job, JobStatus as PersistentJobStatus

            test_job = Job(
                team_id=ctx.team_id,
                collection_id=updated_collection.id,
                tool="collection_test",
                mode="collection",
                status=PersistentJobStatus.PENDING,
                bound_agent_id=updated_collection.bound_agent_id,
                required_capabilities=["local_filesystem"],
            )
            db.add(test_job)
            db.commit()
            db.refresh(test_job)
            db.refresh(updated_collection)

            logger.info(
                f"Auto-created collection_test job after connectivity change",
                extra={
                    "collection_guid": updated_collection.guid,
                    "job_guid": test_job.guid,
                    "agent_id": updated_collection.bound_agent_id
                }
            )

        return CollectionResponse.model_validate(updated_collection)

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
            logger.warning(f"Collection name conflict during update: {collection_update.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        # Other validation errors (pipeline not found, etc.)
        else:
            logger.warning(f"Collection update validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error updating collection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update collection: {str(e)}"
        )


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete collection",
    description="Delete collection with optional force flag to bypass result/job checks"
)
async def delete_collection(
    guid: str,
    force: bool = Query(False, description="Force delete even if results/jobs exist"),
    ctx: TenantContext = Depends(require_auth),
    collection_service: CollectionService = Depends(get_collection_service)
) -> None:
    """
    Delete collection by GUID.

    Checks for analysis results and active jobs. Requires force=true if they exist.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Query Parameters:
        force: If true, delete even if results/jobs exist

    Returns:
        204 No Content on success

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If collection doesn't exist
        409 Conflict: If results/jobs exist and force=false

    Example:
        DELETE /api/collections/col_01hgw2bbg0000000000000000?force=true
    """
    try:
        # Get collection by GUID with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for deletion: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        collection_service.delete_collection(
            collection_id=collection.id,
            force=force
        )

        logger.info(
            f"Deleted collection",
            extra={"guid": guid, "force": force}
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
            logger.warning(f"Collection not found for deletion: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        # Results/jobs exist
        elif "force=True" in error_msg:
            logger.warning(f"Collection has results/jobs: {guid}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        # Other validation errors
        else:
            logger.warning(f"Collection deletion validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deleting collection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}"
        )


@router.post(
    "/{guid}/test",
    response_model=CollectionTestResponse,
    summary="Test collection accessibility",
    description="Test if collection is accessible and update is_accessible flag"
)
async def test_collection(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionTestResponse:
    """
    Test collection accessibility.

    For LOCAL collections bound to agents, creates an async job that the agent
    will execute. The collection's is_accessible field will be updated when
    the agent completes the job.

    For remote collections with agent-based credentials (credential_location=agent),
    creates an async job that can be claimed by any agent with credentials for
    that connector. The job's required_capabilities includes "connector:{guid}".

    For remote collections with server-based credentials (credential_location=server),
    tests connectivity synchronously via the connector and updates is_accessible immediately.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Returns:
        CollectionTestResponse with:
        - success: True for sync tests that pass, False for async or failed tests
        - message: Descriptive message
        - collection: Updated collection with accessibility status
        - job_guid: Job GUID for async tests (LOCAL or agent-credential collections)

    Raises:
        400 Bad Request: If GUID format is invalid, prefix mismatch, or LOCAL collection has no bound agent
        404 Not Found: If collection doesn't exist

    Example (remote collection with server credentials):
        POST /api/collections/col_01hgw2bbg0000000000000000/test

        Response:
        {
          "success": true,
          "message": "Collection is accessible. Found 1,234 files.",
          "collection": { "guid": "col_01hgw2bbg0000000000000000", "is_accessible": true, ... },
          "job_guid": null
        }

    Example (LOCAL collection with agent or remote with agent credentials):
        POST /api/collections/col_01hgw2bbg0000000000000001/test

        Response:
        {
          "success": false,
          "message": "Accessibility test job created. Result will update when agent completes.",
          "collection": { "guid": "col_01hgw2bbg0000000000000001", ... },
          "job_guid": "job_01hgw2bbg0000000000000001"
        }
    """
    try:
        # Get collection by GUID with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for test: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        # For LOCAL collections with a bound agent, create an async job
        if collection.type == CollectionType.LOCAL and collection.bound_agent_id:
            from backend.src.models.job import Job, JobStatus as PersistentJobStatus

            # Create a collection_test job for the bound agent
            # Parameters (collection_path) are derived from the job.collection relationship
            job = Job(
                team_id=ctx.team_id,
                collection_id=collection.id,
                tool="collection_test",
                mode="collection",
                status=PersistentJobStatus.PENDING,
                bound_agent_id=collection.bound_agent_id,
                required_capabilities=["local_filesystem"],
            )

            db.add(job)

            # Set accessibility to pending (NULL) while job is running
            collection.is_accessible = None
            collection.last_error = None

            db.commit()
            db.refresh(job)
            db.refresh(collection)

            logger.info(
                f"Created collection_test job for LOCAL collection",
                extra={
                    "collection_guid": guid,
                    "job_guid": job.guid,
                    "agent_id": collection.bound_agent_id
                }
            )

            return CollectionTestResponse(
                success=False,
                message="Accessibility test job created. Result will update when agent completes.",
                collection=CollectionResponse.model_validate(collection),
                job_guid=job.guid
            )

        # For remote collections with agent-based credentials, create an async job
        # that can be claimed by any agent with credentials for that connector
        from backend.src.models.connector import CredentialLocation
        if (collection.connector and
            collection.connector.credential_location == CredentialLocation.AGENT):
            from backend.src.models.job import Job, JobStatus as PersistentJobStatus

            connector_guid = collection.connector.guid

            # Create a collection_test job requiring connector credentials
            # Any agent with "connector:{guid}" capability can claim this job
            job = Job(
                team_id=ctx.team_id,
                collection_id=collection.id,
                tool="collection_test",
                mode="collection",
                status=PersistentJobStatus.PENDING,
                bound_agent_id=None,  # Not bound - any capable agent can claim
                required_capabilities=[f"connector:{connector_guid}"],
            )

            db.add(job)

            # Set accessibility to pending (NULL) while job is running
            collection.is_accessible = None
            collection.last_error = None

            db.commit()
            db.refresh(job)
            db.refresh(collection)

            logger.info(
                f"Created collection_test job for agent-credential connector",
                extra={
                    "collection_guid": guid,
                    "job_guid": job.guid,
                    "connector_guid": connector_guid,
                    "required_capability": f"connector:{connector_guid}"
                }
            )

            return CollectionTestResponse(
                success=False,
                message="Accessibility test job created. An agent with connector credentials will execute it.",
                collection=CollectionResponse.model_validate(collection),
                job_guid=job.guid
            )

        # For remote collections with server credentials or LOCAL without agent, test synchronously
        success, message, updated_collection = collection_service.test_collection_accessibility(collection.id)

        logger.info(
            f"Tested collection accessibility",
            extra={"guid": guid, "success": success}
        )

        return CollectionTestResponse(
            success=success,
            message=message,
            collection=CollectionResponse.model_validate(updated_collection),
            job_guid=None
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
        if "not found" in error_msg:
            logger.warning(f"Collection not found for test: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error testing collection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test collection: {str(e)}"
        )


@router.post(
    "/{guid}/refresh",
    response_model=CollectionRefreshResponse,
    summary="Refresh collection cache",
    description="Refresh file listing cache with optional confirmation for large collections"
)
async def refresh_collection_cache(
    guid: str,
    confirm: bool = Query(False, description="Confirm refresh for large collections (>100K files)"),
    threshold: int = Query(100000, ge=1000, le=1000000, description="File count warning threshold"),
    ctx: TenantContext = Depends(require_auth),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionRefreshResponse:
    """
    Refresh collection file listing cache.

    For collections with >threshold files (default 100K), requires confirm=true.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Query Parameters:
        confirm: Confirm refresh for large collections
        threshold: File count warning threshold (default: 100,000)

    Returns:
        CollectionRefreshResponse with success, message, and file_count

    Raises:
        400 Bad Request: If GUID format is invalid, prefix mismatch, or file count exceeds threshold and confirm=false
        404 Not Found: If collection doesn't exist

    Example:
        POST /api/collections/col_01hgw2bbg0000000000000000/refresh?confirm=true&threshold=50000

        Response:
        {
          "success": true,
          "message": "Cache refreshed successfully",
          "file_count": 1234
        }
    """
    try:
        # Get collection by GUID with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for refresh: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        success, message, file_count = collection_service.refresh_collection_cache(
            collection_id=collection.id,
            confirm=confirm,
            threshold=threshold
        )

        # Threshold exceeded without confirmation
        if not success and file_count > threshold:
            logger.warning(
                f"Collection refresh requires confirmation",
                extra={"guid": guid, "file_count": file_count, "threshold": threshold}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        logger.info(
            f"Refreshed collection cache",
            extra={"guid": guid, "file_count": file_count}
        )

        return CollectionRefreshResponse(
            success=success,
            message=message,
            file_count=file_count
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
        if "not found" in error_msg:
            logger.warning(f"Collection not found for refresh: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise

    except HTTPException:
        # Re-raise HTTP exceptions (threshold confirmation)
        raise

    except Exception as e:
        logger.error(f"Error refreshing collection cache: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh collection cache: {str(e)}"
        )


@router.post(
    "/{guid}/assign-pipeline",
    response_model=CollectionResponse,
    summary="Assign pipeline to collection",
    description="Assign a specific pipeline to a collection with version pinning"
)
async def assign_pipeline(
    guid: str,
    pipeline_guid: str = Query(..., description="Pipeline GUID to assign (pip_xxx format)"),
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionResponse:
    """
    Assign a pipeline to a collection.

    The pipeline's current version will be stored as the pinned version.
    The collection will use this specific version until manually reassigned.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Query Parameters:
        pipeline_guid: Pipeline GUID to assign (pip_xxx format)

    Returns:
        CollectionResponse with updated collection including pipeline info

    Raises:
        400 Bad Request: If GUID format is invalid, prefix mismatch, or pipeline is not active
        404 Not Found: If collection or pipeline doesn't exist

    Example:
        POST /api/collections/col_01hgw2bbg0000000000000001/assign-pipeline?pipeline_guid=pip_01hgw2bbg0000000000000002

        Response:
        {
          "guid": "col_01hgw2bbg0000000000000001",
          "name": "Vacation 2024",
          "pipeline_guid": "pip_01hgw2bbg0000000000000002",
          "pipeline_version": 3,
          "pipeline_name": "Standard RAW Workflow",
          ...
        }
    """
    try:
        # Get collection by GUID with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for pipeline assignment: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        # Resolve pipeline_guid to internal ID using injected db session
        pipeline_uuid = GuidService.parse_identifier(pipeline_guid, expected_prefix="pip")
        pipeline = db.query(Pipeline).filter(Pipeline.uuid == pipeline_uuid).first()
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_guid}")
        pipeline_id = pipeline.id

        updated_collection = collection_service.assign_pipeline(
            collection_id=collection.id,
            pipeline_id=pipeline_id
        )

        logger.info(
            f"Assigned pipeline to collection",
            extra={
                "collection_guid": guid,
                "pipeline_guid": pipeline_guid,
                "pipeline_version": updated_collection.pipeline_version
            }
        )

        return CollectionResponse.model_validate(updated_collection)

    except ValueError as e:
        error_msg = str(e)
        # Invalid GUID format or prefix mismatch
        if "prefix mismatch" in error_msg.lower() or "Invalid identifier" in error_msg or "Numeric IDs" in error_msg:
            logger.warning(f"Invalid GUID: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        if "not found" in error_msg:
            logger.warning(f"Not found for pipeline assignment: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "not active" in error_msg:
            logger.warning(f"Pipeline not active: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.warning(f"Pipeline assignment validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error assigning pipeline: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign pipeline: {str(e)}"
        )


@router.post(
    "/{guid}/clear-pipeline",
    response_model=CollectionResponse,
    summary="Clear pipeline assignment from collection",
    description="Remove explicit pipeline assignment, collection will use default pipeline at runtime"
)
async def clear_pipeline(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionResponse:
    """
    Clear pipeline assignment from a collection.

    After clearing, the collection will use the default pipeline at runtime
    for Pipeline Validation operations.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Returns:
        CollectionResponse with updated collection (pipeline_guid and pipeline_version are null)

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If collection doesn't exist

    Example:
        POST /api/collections/col_01hgw2bbg0000000000000000/clear-pipeline

        Response:
        {
          "guid": "col_01hgw2bbg0000000000000000",
          "name": "Vacation 2024",
          "pipeline_guid": null,
          "pipeline_version": null,
          "pipeline_name": null,
          ...
        }
    """
    try:
        # Get collection by GUID with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for clear pipeline: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        updated_collection = collection_service.clear_pipeline(collection_id=collection.id)

        logger.info(
            f"Cleared pipeline assignment from collection",
            extra={"guid": guid}
        )

        return CollectionResponse.model_validate(updated_collection)

    except ValueError as e:
        error_msg = str(e)
        # Invalid GUID format or prefix mismatch
        if "prefix mismatch" in error_msg.lower() or "Invalid identifier" in error_msg or "Numeric IDs" in error_msg:
            logger.warning(f"Invalid GUID: {guid} - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        if "not found" in error_msg:
            logger.warning(f"Collection not found for clear pipeline: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        else:
            logger.warning(f"Clear pipeline validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error clearing pipeline: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear pipeline: {str(e)}"
        )


# ============================================================================
# Inventory-based Collection Creation (Issue #107)
# ============================================================================

@router.post(
    "/from-inventory",
    response_model=CreateCollectionsFromInventoryResponse,
    summary="Create collections from inventory folders",
    description="Batch create collections from selected inventory folders"
)
async def create_collections_from_inventory(
    request: CreateCollectionsFromInventoryRequest,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CreateCollectionsFromInventoryResponse:
    """
    Create multiple collections from inventory folders.

    This endpoint supports the two-step wizard for mapping folders to collections:
    1. User selects folders from the folder tree (enforced in frontend)
    2. User configures name/state for each and submits here

    Request Body:
        connector_guid: GUID of the connector
        folders: List of folder mappings with name, state, and optional pipeline

    Returns:
        CreateCollectionsFromInventoryResponse with created list and errors list

    Example:
        POST /api/collections/from-inventory
        {
            "connector_guid": "con_01hgw...",
            "folders": [
                {"folder_guid": "fld_01hgw...", "name": "Vacation 2020", "state": "archived"}
            ]
        }
    """
    inventory_service = InventoryService(db)
    created: list[CollectionCreatedSummary] = []
    errors: list[CollectionCreationError] = []

    try:
        # Resolve connector
        connector = inventory_service.get_connector_by_guid(
            request.connector_guid, team_id=ctx.team_id
        )

        # Validate all folder mappings first
        folder_guids = [m.folder_guid for m in request.folders]
        valid_folders, validation_errors = inventory_service.validate_folder_mappings(
            connector_id=connector.id,
            folder_guids=folder_guids,
            team_id=ctx.team_id
        )

        # Add validation errors
        for folder_guid, error_msg in validation_errors:
            errors.append(CollectionCreationError(
                folder_guid=folder_guid,
                error=error_msg
            ))

        # Map folder GUIDs to folder objects for easy lookup
        folder_map = {f.guid: f for f in valid_folders}

        # Create collections for valid folders
        for mapping in request.folders:
            if mapping.folder_guid not in folder_map:
                continue  # Already reported in validation errors

            folder = folder_map[mapping.folder_guid]

            try:
                # Resolve pipeline if provided
                pipeline_id = None
                if mapping.pipeline_guid:
                    pipeline_uuid = GuidService.parse_identifier(
                        mapping.pipeline_guid, expected_prefix="pip"
                    )
                    pipeline = db.query(Pipeline).filter(
                        Pipeline.uuid == pipeline_uuid
                    ).first()
                    if not pipeline:
                        errors.append(CollectionCreationError(
                            folder_guid=mapping.folder_guid,
                            error=f"Pipeline not found: {mapping.pipeline_guid}"
                        ))
                        continue
                    pipeline_id = pipeline.id

                # Map state string to enum
                state = CollectionState[mapping.state.upper()]

                # Map connector type to collection type (S3 -> S3, GCS -> GCS)
                collection_type = CollectionType(connector.type.value)

                # Build full location URI from connector's source bucket + folder path
                # S3: s3://bucket/path/  GCS: gs://bucket/path/
                # URL decode the path (inventory stores URL-encoded paths like "Spring%20Training")
                from urllib.parse import unquote
                decoded_path = unquote(folder.path)

                source_bucket = connector.inventory_config.get("source_bucket", "")
                if connector.type.value == "s3":
                    location = f"s3://{source_bucket}/{decoded_path}"
                elif connector.type.value == "gcs":
                    location = f"gs://{source_bucket}/{decoded_path}"
                else:
                    location = decoded_path  # Fallback

                # Create the collection
                collection = collection_service.create_collection(
                    name=mapping.name,
                    type=collection_type,
                    location=location,
                    team_id=ctx.team_id,
                    state=state,
                    connector_id=connector.id,
                    pipeline_id=pipeline_id,
                    user_id=ctx.user_id
                )

                # Map folder to collection
                inventory_service.map_folder_to_collection(
                    folder_id=folder.id,
                    collection_guid=collection.guid,
                    team_id=ctx.team_id
                )

                created.append(CollectionCreatedSummary(
                    collection_guid=collection.guid,
                    folder_guid=mapping.folder_guid,
                    name=mapping.name
                ))

                logger.info(
                    "Created collection from inventory folder",
                    extra={
                        "collection_guid": collection.guid,
                        "folder_guid": mapping.folder_guid,
                        "folder_path": folder.path,
                        "collection_name": mapping.name
                    }
                )

                # Auto-trigger accessibility test for collections with agent-side credentials
                # This follows the tool-implementation-pattern.md documented pattern
                from backend.src.models.connector import CredentialLocation
                from backend.src.models.job import Job, JobStatus as PersistentJobStatus

                if connector.credential_location == CredentialLocation.AGENT:
                    # Create collection_test job requiring connector credentials
                    test_job = Job(
                        team_id=ctx.team_id,
                        collection_id=collection.id,
                        tool="collection_test",
                        mode="collection",
                        status=PersistentJobStatus.PENDING,
                        bound_agent_id=None,  # Any agent with connector credentials
                        required_capabilities=[f"connector:{connector.guid}"],
                    )
                    db.add(test_job)
                    db.flush()  # Flush to persist job and generate GUID

                    # Set collection accessibility to pending while job runs
                    collection.is_accessible = None
                    db.commit()

                    logger.info(
                        "Auto-created collection_test job for inventory collection",
                        extra={
                            "collection_guid": collection.guid,
                            "job_guid": test_job.guid,
                            "connector_guid": connector.guid
                        }
                    )

            except ValueError as e:
                errors.append(CollectionCreationError(
                    folder_guid=mapping.folder_guid,
                    error=str(e)
                ))
            except Exception as e:
                logger.error(
                    f"Error creating collection from folder: {str(e)}",
                    extra={"folder_guid": mapping.folder_guid}
                )
                errors.append(CollectionCreationError(
                    folder_guid=mapping.folder_guid,
                    error=f"Internal error: {str(e)}"
                ))

        return CreateCollectionsFromInventoryResponse(
            created=created,
            errors=errors
        )

    except ValueError as e:
        logger.warning(f"Invalid request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Error creating collections from inventory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collections: {str(e)}"
        )


@router.post(
    "/{guid}/clear-inventory-cache",
    response_model=CollectionClearCacheResponse,
    summary="Clear inventory cache (Issue #107 - T075)",
    description="Clear cached FileInfo from bucket inventory to force fresh cloud API listing"
)
async def clear_inventory_cache(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionClearCacheResponse:
    """
    Clear cached FileInfo from a collection's inventory import.

    This endpoint is used before running analysis tools when fresh file listings
    from the cloud API are needed (bypassing cached inventory data).

    The operation clears:
    - file_info: Cached FileInfo array
    - file_info_source: Source indicator ("api" or "inventory")
    - file_info_updated_at: Last update timestamp
    - file_info_delta: Import delta summary

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Returns:
        CollectionClearCacheResponse with success status and cleared entry count

    Raises:
        400 Bad Request: If GUID format is invalid, prefix mismatch, or collection is LOCAL type
        404 Not Found: If collection doesn't exist

    Example:
        POST /api/collections/col_01hgw2bbg0000000000000001/clear-inventory-cache

        Response:
        {
          "success": true,
          "message": "Inventory cache cleared. Tools will fetch fresh file listings from cloud.",
          "cleared_count": 12345
        }
    """
    try:
        # Validate GUID format
        try:
            GuidService.parse_identifier(guid, expected_prefix="col")
        except ValueError as e:
            logger.warning(f"Invalid collection GUID format: {guid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Get collection with tenant filtering
        collection = collection_service.get_by_guid(guid, team_id=ctx.team_id)

        if not collection:
            logger.warning(f"Collection not found for clear-inventory-cache: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        # Local collections don't have inventory cache
        if collection.type == CollectionType.LOCAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Local collections do not have inventory cache"
            )

        # Count entries before clearing
        cleared_count = collection.file_info_count

        # Clear the cached FileInfo
        collection.file_info = None
        collection.file_info_source = None
        collection.file_info_updated_at = None
        collection.file_info_delta = None

        db.commit()

        logger.info(
            f"Cleared inventory cache for collection {guid}",
            extra={
                "collection_guid": guid,
                "cleared_count": cleared_count
            }
        )

        return CollectionClearCacheResponse(
            success=True,
            message="Inventory cache cleared. Tools will fetch fresh file listings from cloud.",
            cleared_count=cleared_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing inventory cache: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear inventory cache: {str(e)}"
        )
