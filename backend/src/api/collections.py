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
    CollectionStatsResponse,
)
from backend.src.services.collection_service import CollectionService
from backend.src.services.connector_service import ConnectorService
from backend.src.services.guid import GuidService
from backend.src.utils.cache import FileListingCache
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import get_logger


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


def get_collection_service(
    db: Session = Depends(get_db),
    file_cache: FileListingCache = Depends(get_file_cache),
    connector_service: ConnectorService = Depends(get_connector_service)
) -> CollectionService:
    """Create CollectionService instance with dependencies."""
    return CollectionService(
        db=db,
        file_cache=file_cache,
        connector_service=connector_service
    )


# ============================================================================
# API Endpoints (T096-T102)
# ============================================================================

@router.get(
    "/stats",
    response_model=CollectionStatsResponse,
    summary="Get collection statistics",
    description="Get aggregated KPI statistics for all collections (Issue #37)"
)
async def get_collection_stats(
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionStatsResponse:
    """
    Get aggregated statistics for all collections.

    Returns KPIs for the Collections page topband. These values are NOT affected
    by any filter parameters - always shows system-wide totals.

    Returns:
        CollectionStatsResponse with:
        - total_collections: Count of all collections
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
        stats = collection_service.get_collection_stats()

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
    description="List all collections with optional filtering by state, type, accessibility, and name search"
)
async def list_collections(
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

        created_collection = collection_service.create_collection(
            name=collection.name,
            type=collection.type,
            location=collection.location,
            state=collection.state,
            connector_id=connector_id,
            pipeline_id=pipeline_id,
            cache_ttl=collection.cache_ttl,
            metadata=collection.metadata
        )

        logger.info(
            f"Created collection: {collection.name}",
            extra={
                "collection_guid": created_collection.guid,
                "type": collection.type.value,
                "location": collection.location
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
        404 Not Found: If collection doesn't exist

    Example:
        GET /api/collections/col_01hgw2bbg0000000000000000
    """
    try:
        collection = collection_service.get_by_guid(guid)

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
        # Get collection by GUID
        collection = collection_service.get_by_guid(guid)

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

        updated_collection = collection_service.update_collection(
            collection_id=collection.id,
            name=collection_update.name,
            location=collection_update.location,
            state=collection_update.state,
            pipeline_id=pipeline_id,
            cache_ttl=collection_update.cache_ttl,
            metadata=collection_update.metadata
        )

        logger.info(
            f"Updated collection: {updated_collection.name}",
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
        # Get collection by GUID
        collection = collection_service.get_by_guid(guid)

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
    collection_service: CollectionService = Depends(get_collection_service)
) -> CollectionTestResponse:
    """
    Test collection accessibility.

    Tests local filesystem or remote storage connectivity and updates
    collection.is_accessible and collection.last_error fields.

    Path Parameters:
        guid: Collection GUID (col_xxx format)

    Returns:
        CollectionTestResponse with success status, message, and updated collection

    Raises:
        400 Bad Request: If GUID format is invalid or prefix mismatch
        404 Not Found: If collection doesn't exist

    Example:
        POST /api/collections/col_01hgw2bbg0000000000000000/test

        Response:
        {
          "success": true,
          "message": "Collection is accessible. Found 1,234 files.",
          "collection": { "guid": "col_01hgw2bbg0000000000000000", "is_accessible": true, ... }
        }
    """
    try:
        # Get collection by GUID
        collection = collection_service.get_by_guid(guid)

        if not collection:
            logger.warning(f"Collection not found for test: {guid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection not found: {guid}"
            )

        success, message, updated_collection = collection_service.test_collection_accessibility(collection.id)

        logger.info(
            f"Tested collection accessibility",
            extra={"guid": guid, "success": success}
        )

        return CollectionTestResponse(
            success=success,
            message=message,
            collection=CollectionResponse.model_validate(updated_collection)
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
        # Get collection by GUID
        collection = collection_service.get_by_guid(guid)

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
        # Get collection by GUID
        collection = collection_service.get_by_guid(guid)

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
        # Get collection by GUID
        collection = collection_service.get_by_guid(guid)

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
