"""
Collection service for managing photo collections (local and remote).

Provides business logic for creating, reading, updating, and deleting photo collections
with accessibility testing, file listing caching, and remote storage integration.

Design:
- Validates local paths are accessible before creation
- Tests remote collection accessibility via connectors
- Caches file listings with state-based TTL
- Invalidates cache on state changes
- Prevents deletion if analysis results or jobs exist (FR-005)
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.src.models import Collection, CollectionType, CollectionState, Connector
from backend.src.utils.cache import FileListingCache
from backend.src.utils.logging_config import get_logger
from backend.src.services.connector_service import ConnectorService


logger = get_logger("services")


class CollectionService:
    """
    Service for managing photo collections.

    Handles CRUD operations for collections with automatic accessibility testing,
    file listing caching, and remote storage integration via connectors.

    Usage:
        >>> service = CollectionService(db_session, file_cache, connector_service)
        >>> collection = service.create_collection(
        ...     name="Vacation 2024",
        ...     type=CollectionType.LOCAL,
        ...     location="/photos/2024/vacation",
        ...     state=CollectionState.LIVE
        ... )
    """

    def __init__(
        self,
        db: Session,
        file_cache: FileListingCache,
        connector_service: ConnectorService
    ):
        """
        Initialize collection service.

        Args:
            db: SQLAlchemy database session
            file_cache: File listing cache for remote storage
            connector_service: Connector service for remote storage access
        """
        self.db = db
        self.file_cache = file_cache
        self.connector_service = connector_service

    def create_collection(
        self,
        name: str,
        type: CollectionType,
        location: str,
        state: CollectionState = CollectionState.LIVE,
        connector_id: Optional[int] = None,
        cache_ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Collection:
        """
        Create a new collection with accessibility test.

        Validates:
        - Local collections: directory exists and is accessible
        - Remote collections: connector exists and connection succeeds

        Args:
            name: User-friendly collection name (must be unique)
            type: Collection type (LOCAL, S3, GCS, SMB)
            location: Storage location path/URI
            state: Collection lifecycle state (default: LIVE)
            connector_id: Connector ID (required for remote types, None for LOCAL)
            cache_ttl: Custom cache TTL override (seconds)
            metadata: Optional user-defined metadata

        Returns:
            Created Collection instance

        Raises:
            ValueError: If validation fails (name exists, location invalid, connector missing)
            Exception: If database operation fails

        Example:
            >>> # Local collection
            >>> collection = service.create_collection(
            ...     name="Local Photos",
            ...     type=CollectionType.LOCAL,
            ...     location="/photos/2024"
            ... )
            >>> # Remote collection
            >>> collection = service.create_collection(
            ...     name="S3 Bucket",
            ...     type=CollectionType.S3,
            ...     location="my-bucket/photos",
            ...     connector_id=1
            ... )
        """
        # Validate connector requirement
        if type != CollectionType.LOCAL and not connector_id:
            raise ValueError(f"Connector ID required for remote collection type: {type.value}")

        if type == CollectionType.LOCAL and connector_id:
            raise ValueError("Connector ID should not be provided for LOCAL collections")

        # Test accessibility before creation
        is_accessible, last_error = self._test_accessibility(type, location, connector_id)

        try:
            # Convert metadata to JSON string if provided
            metadata_json = json.dumps(metadata) if metadata else None

            # Create collection
            collection = Collection(
                name=name,
                type=type,
                location=location,
                state=state,
                connector_id=connector_id,
                cache_ttl=cache_ttl,
                is_accessible=is_accessible,
                last_error=last_error,
                metadata_json=metadata_json
            )

            self.db.add(collection)
            self.db.commit()
            self.db.refresh(collection)

            logger.info(
                f"Created collection: {name}",
                extra={
                    "collection_id": collection.id,
                    "type": type.value,
                    "accessible": is_accessible
                }
            )

            return collection

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Collection name already exists: {name}")
            raise ValueError(f"Collection with name '{name}' already exists")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create collection: {str(e)}", extra={"collection_name": name})
            raise

    def get_collection(self, collection_id: int) -> Optional[Collection]:
        """
        Get collection by ID with connector details.

        Args:
            collection_id: Collection ID

        Returns:
            Collection instance or None if not found

        Example:
            >>> collection = service.get_collection(1)
            >>> if collection.connector:
            ...     print(f"Uses connector: {collection.connector.name}")
        """
        return self.db.query(Collection).filter(Collection.id == collection_id).first()

    def list_collections(
        self,
        state_filter: Optional[CollectionState] = None,
        type_filter: Optional[CollectionType] = None,
        accessible_only: bool = False
    ) -> List[Collection]:
        """
        List collections with optional filtering, sorted by creation date (newest first).

        Args:
            state_filter: Filter by collection state (LIVE, CLOSED, ARCHIVED)
            type_filter: Filter by collection type (LOCAL, S3, GCS, SMB)
            accessible_only: If True, only return accessible collections

        Returns:
            List of Collection instances sorted by created_at DESC

        Example:
            >>> collections = service.list_collections(
            ...     state_filter=CollectionState.LIVE,
            ...     accessible_only=True
            ... )
        """
        query = self.db.query(Collection)

        if state_filter:
            query = query.filter(Collection.state == state_filter)

        if type_filter:
            query = query.filter(Collection.type == type_filter)

        if accessible_only:
            query = query.filter(Collection.is_accessible == True)

        collections = query.order_by(Collection.created_at.desc()).all()

        logger.info(
            f"Listed {len(collections)} collections",
            extra={
                "state_filter": state_filter.value if state_filter else None,
                "type_filter": type_filter.value if type_filter else None,
                "accessible_only": accessible_only
            }
        )

        return collections

    def update_collection(
        self,
        collection_id: int,
        name: Optional[str] = None,
        location: Optional[str] = None,
        state: Optional[CollectionState] = None,
        cache_ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Collection:
        """
        Update collection properties.

        Invalidates cache if state changes (different TTL applies).
        Only updates fields that are not None.

        Args:
            collection_id: Collection ID to update
            name: New name (must be unique if changed)
            location: New location path/URI
            state: New lifecycle state
            cache_ttl: New cache TTL override
            metadata: New metadata

        Returns:
            Updated Collection instance

        Raises:
            ValueError: If collection not found or name conflicts
            Exception: If database operation fails

        Example:
            >>> collection = service.update_collection(1, state=CollectionState.CLOSED)
            >>> # Cache invalidated due to state change
        """
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()

        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        try:
            # Track if state changes (requires cache invalidation)
            state_changed = False

            # Update fields
            if name is not None:
                collection.name = name

            if location is not None:
                collection.location = location

            if state is not None and state != collection.state:
                collection.state = state
                state_changed = True

            if cache_ttl is not None:
                collection.cache_ttl = cache_ttl

            if metadata is not None:
                collection.metadata_json = json.dumps(metadata)

            self.db.commit()
            self.db.refresh(collection)

            # Invalidate cache if state changed (different TTL applies)
            if state_changed:
                self.file_cache.invalidate(collection_id)
                logger.info(
                    f"Invalidated cache due to state change: {collection.name}",
                    extra={"collection_id": collection_id, "new_state": state.value}
                )

            logger.info(
                f"Updated collection: {collection.name}",
                extra={"collection_id": collection_id}
            )

            return collection

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Collection name conflict: {name}")
            raise ValueError(f"Collection with name '{name}' already exists")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update collection: {str(e)}", extra={"collection_id": collection_id})
            raise

    def delete_collection(self, collection_id: int, force: bool = False) -> None:
        """
        Delete collection.

        Checks for analysis results and active jobs before deletion (FR-005).
        Requires force=True if results/jobs exist.

        Args:
            collection_id: Collection ID to delete
            force: If True, delete even if results/jobs exist (cascade delete)

        Raises:
            ValueError: If collection not found or results/jobs exist without force
            Exception: If database operation fails

        Example:
            >>> service.delete_collection(1)  # Raises if results exist
            >>> service.delete_collection(1, force=True)  # Force delete
        """
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()

        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        # Check for analysis results (cascade delete relationship exists)
        # Note: analysis_results relationship will be available when AnalysisResult model is created
        # For now, we'll implement the check structure

        # TODO: Uncomment when AnalysisResult model is created
        # result_count = collection.analysis_results.count()
        result_count = 0  # Placeholder

        # TODO: Check for active jobs in job queue
        # job_count = count_active_jobs_for_collection(collection_id)
        job_count = 0  # Placeholder

        if (result_count > 0 or job_count > 0) and not force:
            logger.warning(
                f"Cannot delete collection without force flag",
                extra={
                    "collection_id": collection_id,
                    "result_count": result_count,
                    "job_count": job_count
                }
            )
            raise ValueError(
                f"Cannot delete collection '{collection.name}' because it has "
                f"{result_count} analysis result(s) and {job_count} active job(s). "
                f"Use force=True to delete anyway (this will cascade delete all results)."
            )

        try:
            # Invalidate cache
            self.file_cache.invalidate(collection_id)

            # Delete collection (cascade will delete results if they exist)
            self.db.delete(collection)
            self.db.commit()

            logger.info(
                f"Deleted collection: {collection.name}",
                extra={"collection_id": collection_id, "force": force}
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete collection: {str(e)}", extra={"collection_id": collection_id})
            raise

    def test_collection_accessibility(self, collection_id: int) -> tuple[bool, str]:
        """
        Test collection accessibility.

        For local collections: checks if directory exists and is readable.
        For remote collections: tests connection via connector adapter.

        Updates collection's is_accessible and last_error fields.

        Args:
            collection_id: Collection ID to test

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            ValueError: If collection not found

        Example:
            >>> success, message = service.test_collection_accessibility(1)
            >>> print(f"Accessible: {success}, {message}")
        """
        collection = self.get_collection(collection_id)

        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        is_accessible, last_error = self._test_accessibility(
            collection.type,
            collection.location,
            collection.connector_id
        )

        # Update collection fields
        collection.is_accessible = is_accessible
        collection.last_error = last_error
        self.db.commit()

        logger.info(
            f"Tested collection accessibility: {collection.name}",
            extra={"collection_id": collection_id, "accessible": is_accessible}
        )

        message = "Collection is accessible" if is_accessible else last_error
        return is_accessible, message

    def get_collection_files(
        self,
        collection_id: int,
        use_cache: bool = True
    ) -> List[str]:
        """
        Get list of files in collection.

        Implements cache hit/miss logic using FileListingCache.
        Cache TTL is determined by collection state or user override.

        Args:
            collection_id: Collection ID
            use_cache: If True, use cache; if False, force refresh

        Returns:
            List of file paths

        Raises:
            ValueError: If collection not found or not accessible
            ConnectionError: If remote storage fails

        Example:
            >>> files = service.get_collection_files(1)  # Uses cache
            >>> files = service.get_collection_files(1, use_cache=False)  # Force refresh
        """
        collection = self.get_collection(collection_id)

        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        if not collection.is_accessible:
            raise ValueError(
                f"Collection '{collection.name}' is not accessible. "
                f"Error: {collection.last_error or 'Unknown error'}"
            )

        # Check cache first
        if use_cache:
            cached_files = self.file_cache.get(collection_id)
            if cached_files is not None:
                logger.info(
                    f"Cache hit for collection files",
                    extra={"collection_id": collection_id, "file_count": len(cached_files)}
                )
                return cached_files

        # Cache miss or forced refresh - fetch files
        logger.info(
            f"Cache miss for collection files, fetching",
            extra={"collection_id": collection_id, "use_cache": use_cache}
        )

        files = self._fetch_collection_files(collection)

        # Update cache with collection's effective TTL
        ttl = collection.get_effective_cache_ttl()
        self.file_cache.set(collection_id, files, ttl)

        logger.info(
            f"Fetched and cached collection files",
            extra={"collection_id": collection_id, "file_count": len(files), "ttl": ttl}
        )

        return files

    def refresh_collection_cache(
        self,
        collection_id: int,
        confirm: bool = False,
        threshold: int = 100000
    ) -> tuple[bool, str, int]:
        """
        Refresh collection file listing cache.

        Implements file count warning logic (FR-013a).
        If file count exceeds threshold, requires confirm=True.

        Args:
            collection_id: Collection ID
            confirm: Confirmation to proceed with large refresh
            threshold: File count threshold for warning (default: 100K)

        Returns:
            Tuple of (success: bool, message: str, file_count: int)

        Raises:
            ValueError: If collection not found or confirmation required

        Example:
            >>> # First call - gets warning if large
            >>> success, msg, count = service.refresh_collection_cache(1)
            >>> # Returns: (False, "Confirm required: 150K files", 150000)

            >>> # Second call - with confirmation
            >>> success, msg, count = service.refresh_collection_cache(1, confirm=True)
            >>> # Returns: (True, "Cache refreshed", 150000)
        """
        collection = self.get_collection(collection_id)

        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        if not collection.is_accessible:
            return False, f"Collection not accessible: {collection.last_error}", 0

        # Fetch file count (lightweight operation for warning check)
        files = self._fetch_collection_files(collection)
        file_count = len(files)

        # Check threshold
        if file_count > threshold and not confirm:
            logger.warning(
                f"Cache refresh requires confirmation (large file count)",
                extra={"collection_id": collection_id, "file_count": file_count, "threshold": threshold}
            )
            return (
                False,
                f"Collection has {file_count:,} files (exceeds {threshold:,} threshold). "
                f"This may take significant time and API quota. Set confirm=True to proceed.",
                file_count
            )

        # Refresh cache
        ttl = collection.get_effective_cache_ttl()
        self.file_cache.invalidate(collection_id)
        self.file_cache.set(collection_id, files, ttl)

        logger.info(
            f"Refreshed cache for collection",
            extra={"collection_id": collection_id, "file_count": file_count}
        )

        return True, f"Cache refreshed successfully. {file_count:,} files cached.", file_count

    # Private helper methods

    def _test_accessibility(
        self,
        type: CollectionType,
        location: str,
        connector_id: Optional[int]
    ) -> tuple[bool, Optional[str]]:
        """
        Test collection accessibility (local or remote).

        Args:
            type: Collection type
            location: Storage location
            connector_id: Connector ID (for remote collections)

        Returns:
            Tuple of (is_accessible: bool, last_error: Optional[str])
        """
        if type == CollectionType.LOCAL:
            # Test local filesystem access
            if os.path.isdir(location) and os.access(location, os.R_OK):
                return True, None
            else:
                return False, f"Local directory not found or not readable: {location}"
        else:
            # Test remote access via connector
            if not connector_id:
                return False, "Remote collection missing connector"

            try:
                success, message = self.connector_service.test_connector(connector_id)
                if success:
                    return True, None
                else:
                    return False, f"Connector test failed: {message}"
            except Exception as e:
                return False, f"Connector test error: {str(e)}"

    def _fetch_collection_files(self, collection: Collection) -> List[str]:
        """
        Fetch file listing from collection (local or remote).

        Args:
            collection: Collection instance

        Returns:
            List of file paths

        Raises:
            ValueError: If collection type not supported
            ConnectionError: If remote fetch fails
        """
        if collection.type == CollectionType.LOCAL:
            # List local filesystem
            files = []
            for root, dirs, filenames in os.walk(collection.location):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(full_path, collection.location)
                    files.append(relative_path)
            return files
        else:
            # List remote storage via connector
            if not collection.connector_id:
                raise ValueError("Remote collection missing connector")

            connector = self.connector_service.get_connector(
                collection.connector_id,
                decrypt_credentials=True
            )

            if not connector:
                raise ValueError(f"Connector {collection.connector_id} not found")

            # Create appropriate adapter
            from backend.src.services.remote import S3Adapter, GCSAdapter, SMBAdapter
            from backend.src.models import ConnectorType

            if connector.type == ConnectorType.S3:
                adapter = S3Adapter(connector.decrypted_credentials)
            elif connector.type == ConnectorType.GCS:
                adapter = GCSAdapter(connector.decrypted_credentials)
            elif connector.type == ConnectorType.SMB:
                adapter = SMBAdapter(connector.decrypted_credentials)
            else:
                raise ValueError(f"Unsupported connector type: {connector.type}")

            return adapter.list_files(collection.location)
