"""
Inventory service for managing cloud storage bucket inventory import.

Provides business logic for:
- Configuring S3/GCS inventory sources on connectors
- Validating inventory configuration (server-side or agent-side credentials)
- Managing inventory folders (CRUD operations)
- Triggering inventory import jobs

Issue #107: Cloud Storage Bucket Inventory Import
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.src.models import Connector, ConnectorType
from backend.src.models.connector import CredentialLocation
from backend.src.models.inventory_folder import InventoryFolder
from backend.src.models.job import Job, JobStatus
from backend.src.schemas.inventory import (
    S3InventoryConfig,
    GCSInventoryConfig,
    InventoryFolderResponse,
)
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.services.guid import GuidService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


# Inventory validation status constants
class InventoryValidationStatus:
    """Inventory validation status values."""
    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    FAILED = "failed"


class InventoryService:
    """
    Service for managing cloud storage inventory imports.

    Handles inventory configuration, validation, and folder management
    for S3 and GCS connectors.

    Usage:
        >>> service = InventoryService(db_session)
        >>> config = S3InventoryConfig(
        ...     destination_bucket="inventory-bucket",
        ...     source_bucket="photo-bucket",
        ...     config_name="daily"
        ... )
        >>> connector = service.set_inventory_config(
        ...     connector_id=1, config=config, schedule="daily"
        ... )
    """

    def __init__(self, db: Session):
        """
        Initialize inventory service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # =========================================================================
    # Inventory Configuration
    # =========================================================================

    def set_inventory_config(
        self,
        connector_id: int,
        config: Union[S3InventoryConfig, GCSInventoryConfig],
        schedule: str = "manual",
        team_id: Optional[int] = None
    ) -> Connector:
        """
        Set inventory configuration on a connector.

        Args:
            connector_id: Internal connector ID
            config: S3 or GCS inventory configuration
            schedule: Import schedule (manual/daily/weekly)
            team_id: Team ID for tenant isolation

        Returns:
            Updated Connector with inventory config set

        Raises:
            NotFoundError: If connector not found
            ValidationError: If connector type doesn't support inventory
        """
        connector = self._get_connector(connector_id, team_id)

        # Validate connector supports inventory
        if not connector.supports_inventory:
            raise ValidationError(
                f"Connector type '{connector.type.value}' does not support inventory. "
                "Only S3 and GCS connectors support bucket inventory."
            )

        # Validate config matches connector type
        if connector.type == ConnectorType.S3 and config.provider != "s3":
            raise ValidationError(
                f"Configuration provider '{config.provider}' doesn't match "
                f"connector type '{connector.type.value}'"
            )
        if connector.type == ConnectorType.GCS and config.provider != "gcs":
            raise ValidationError(
                f"Configuration provider '{config.provider}' doesn't match "
                f"connector type '{connector.type.value}'"
            )

        # Store config as JSONB
        connector.inventory_config = config.model_dump()
        connector.inventory_schedule = schedule
        connector.inventory_validation_status = InventoryValidationStatus.PENDING
        connector.inventory_validation_error = None

        self.db.commit()
        self.db.refresh(connector)

        logger.info(
            "Set inventory configuration on connector",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "provider": config.provider,
                "schedule": schedule
            }
        )

        return connector

    def clear_inventory_config(
        self,
        connector_id: int,
        team_id: Optional[int] = None
    ) -> Connector:
        """
        Clear inventory configuration from a connector.

        Also clears validation status and removes associated inventory folders.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID for tenant isolation

        Returns:
            Updated Connector with inventory config cleared

        Raises:
            NotFoundError: If connector not found
        """
        connector = self._get_connector(connector_id, team_id)

        # Clear inventory config and status
        connector.inventory_config = None
        connector.inventory_schedule = "manual"
        connector.inventory_validation_status = None
        connector.inventory_validation_error = None
        connector.inventory_last_import_at = None

        # Delete associated inventory folders
        deleted_count = self.db.query(InventoryFolder).filter(
            InventoryFolder.connector_id == connector_id
        ).delete()

        self.db.commit()
        self.db.refresh(connector)

        logger.info(
            "Cleared inventory configuration from connector",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "deleted_folders": deleted_count
            }
        )

        return connector

    # =========================================================================
    # Inventory Validation (Server-Side Credentials)
    # =========================================================================

    def validate_inventory_config_server_side(
        self,
        connector_id: int,
        team_id: Optional[int] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Validate inventory configuration using server-side credentials.

        Attempts to fetch the manifest.json file from the configured
        inventory location to verify accessibility.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID for tenant isolation
            credentials: Decrypted credentials (must be provided for validation)

        Returns:
            Tuple of (success, message)

        Raises:
            NotFoundError: If connector not found
            ValidationError: If connector has no inventory config or requires agent credentials
        """
        connector = self._get_connector(connector_id, team_id)

        if not connector.has_inventory_config:
            raise ValidationError("Connector has no inventory configuration")

        if connector.requires_agent_credentials:
            raise ValidationError(
                "Cannot validate server-side: connector uses agent credentials. "
                "Use create_validation_job() instead."
            )

        if not credentials:
            raise ValidationError("Credentials required for server-side validation")

        # Set status to validating
        connector.inventory_validation_status = InventoryValidationStatus.VALIDATING
        self.db.commit()

        try:
            # Get inventory manifest path
            config = connector.inventory_config
            manifest_path = self._get_manifest_path(connector.type, config)

            # Validate using appropriate adapter
            success, message = self._validate_manifest_access(
                connector.type, credentials, config, manifest_path
            )

            # Update status based on result
            if success:
                connector.inventory_validation_status = InventoryValidationStatus.VALIDATED
                connector.inventory_validation_error = None
            else:
                connector.inventory_validation_status = InventoryValidationStatus.FAILED
                connector.inventory_validation_error = message

            self.db.commit()

            logger.info(
                "Completed inventory config validation (server-side)",
                extra={
                    "connector_id": connector_id,
                    "success": success,
                    "result_message": message
                }
            )

            return success, message

        except Exception as e:
            # Handle unexpected errors
            connector.inventory_validation_status = InventoryValidationStatus.FAILED
            connector.inventory_validation_error = str(e)
            self.db.commit()

            logger.error(
                "Inventory config validation failed with exception",
                extra={
                    "connector_id": connector_id,
                    "error": str(e)
                }
            )

            return False, f"Validation failed: {str(e)}"

    def _get_manifest_path(
        self,
        connector_type: ConnectorType,
        config: Dict[str, Any]
    ) -> str:
        """
        Get the expected manifest path for inventory configuration.

        Args:
            connector_type: Connector type (S3 or GCS)
            config: Inventory configuration dict

        Returns:
            Path to manifest.json (relative to destination bucket)
        """
        if connector_type == ConnectorType.S3:
            # S3: {destination_prefix}/{source-bucket}/{config-name}/
            # Note: Full path requires finding latest timestamp folder
            destination_prefix = config.get("destination_prefix", "").strip("/")
            source_bucket = config.get("source_bucket", "")
            config_name = config.get("config_name", "")
            if destination_prefix:
                return f"{destination_prefix}/{source_bucket}/{config_name}/"
            return f"{source_bucket}/{config_name}/"
        else:
            # GCS: {report_config_name}/
            # Note: Full path requires finding latest snapshot date folder
            report_config_name = config.get("report_config_name", "")
            return f"{report_config_name}/"

    def _validate_manifest_access(
        self,
        connector_type: ConnectorType,
        credentials: Dict[str, Any],
        config: Dict[str, Any],
        manifest_prefix: str
    ) -> Tuple[bool, str]:
        """
        Validate access to inventory manifest using storage adapter.

        Args:
            connector_type: Connector type (S3 or GCS)
            credentials: Decrypted credentials
            config: Inventory configuration dict
            manifest_prefix: Path prefix to search for manifest

        Returns:
            Tuple of (success, message)
        """
        from backend.src.services.remote import S3Adapter, GCSAdapter

        destination_bucket = config.get("destination_bucket", "")

        try:
            if connector_type == ConnectorType.S3:
                adapter = S3Adapter(credentials)
                # List objects at the manifest prefix to find inventory folders
                location = f"{destination_bucket}/{manifest_prefix}"
                files = adapter.list_files(location)

                # Look for any manifest.json file
                manifest_files = [f for f in files if f.endswith("manifest.json")]
                if manifest_files:
                    return True, f"Found {len(manifest_files)} inventory manifest(s)"
                else:
                    return False, (
                        f"No manifest.json found at {location}. "
                        "Verify the inventory is enabled and has generated at least one report."
                    )

            else:  # GCS
                adapter = GCSAdapter(credentials)
                location = f"{destination_bucket}/{manifest_prefix}"
                files = adapter.list_files(location)

                manifest_files = [f for f in files if f.endswith("manifest.json")]
                if manifest_files:
                    return True, f"Found {len(manifest_files)} inventory manifest(s)"
                else:
                    return False, (
                        f"No manifest.json found at {location}. "
                        "Verify Storage Insights is enabled and has generated at least one report."
                    )

        except PermissionError as e:
            return False, f"Access denied: {str(e)}"
        except ConnectionError as e:
            return False, f"Connection failed: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    # =========================================================================
    # Inventory Validation (Agent-Side Credentials)
    # =========================================================================

    def create_validation_job(
        self,
        connector_id: int,
        team_id: int
    ) -> Job:
        """
        Create a validation job for agent-side credential path.

        When connector credentials are stored on the agent, the server
        cannot directly validate the inventory config. This creates a
        lightweight job for an agent to validate manifest accessibility.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID

        Returns:
            Created validation Job

        Raises:
            NotFoundError: If connector not found
            ValidationError: If connector has no inventory config
        """
        connector = self._get_connector(connector_id, team_id)

        if not connector.has_inventory_config:
            raise ValidationError("Connector has no inventory configuration to validate")

        # Set status to pending (will become validating when agent claims job)
        connector.inventory_validation_status = InventoryValidationStatus.PENDING
        self.db.commit()

        # Create validation job
        job = Job(
            team_id=team_id,
            collection_id=None,  # No collection for validation jobs
            tool="inventory_validate",
            mode="validation",
            status=JobStatus.PENDING,
            priority=5,  # Higher priority for quick validation
        )

        # Store connector_id in job metadata for agent to use
        job.progress = {
            "connector_id": connector_id,
            "connector_guid": connector.guid,
            "config": connector.inventory_config
        }

        # If connector uses agent credentials, job requires that agent
        if connector.requires_agent_credentials:
            # Add connector capability requirement
            job.required_capabilities = [f"connector:{connector.guid}"]

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(
            "Created inventory validation job",
            extra={
                "job_guid": job.guid,
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "requires_agent_credentials": connector.requires_agent_credentials
            }
        )

        return job

    def update_validation_status(
        self,
        connector_id: int,
        success: bool,
        error_message: Optional[str] = None,
        team_id: Optional[int] = None
    ) -> Connector:
        """
        Update inventory validation status from agent result.

        Called when an agent completes a validation job to report the result.

        Args:
            connector_id: Internal connector ID
            success: Whether validation succeeded
            error_message: Error message if validation failed
            team_id: Team ID for tenant isolation

        Returns:
            Updated Connector

        Raises:
            NotFoundError: If connector not found
        """
        connector = self._get_connector(connector_id, team_id)

        if success:
            connector.inventory_validation_status = InventoryValidationStatus.VALIDATED
            connector.inventory_validation_error = None
        else:
            connector.inventory_validation_status = InventoryValidationStatus.FAILED
            connector.inventory_validation_error = error_message

        self.db.commit()
        self.db.refresh(connector)

        logger.info(
            "Updated inventory validation status from agent",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "success": success,
                "error": error_message
            }
        )

        return connector

    def create_import_job(
        self,
        connector_id: int,
        team_id: int
    ) -> Job:
        """
        Create an inventory import job.

        Creates a job for an agent to:
        1. Fetch the latest inventory manifest
        2. Parse data files (CSV/Parquet)
        3. Extract unique folder paths
        4. Report folders to the server

        Args:
            connector_id: Internal connector ID
            team_id: Team ID

        Returns:
            Created import Job

        Raises:
            NotFoundError: If connector not found
            ValidationError: If connector has no inventory config or not validated
        """
        connector = self._get_connector(connector_id, team_id)

        if not connector.has_inventory_config:
            raise ValidationError("Connector has no inventory configuration")

        if connector.inventory_validation_status != InventoryValidationStatus.VALIDATED:
            raise ValidationError(
                f"Inventory configuration not validated. Current status: "
                f"{connector.inventory_validation_status or 'none'}"
            )

        # Create import job
        job = Job(
            team_id=team_id,
            collection_id=None,  # No collection for import jobs
            tool="inventory_import",
            mode="import",
            status=JobStatus.PENDING,
            priority=3,  # Normal priority
        )

        # Store connector info in job metadata for agent to use
        job.progress = {
            "connector_id": connector_id,
            "connector_guid": connector.guid,
            "config": connector.inventory_config
        }

        # If connector uses agent credentials, job requires that agent
        if connector.requires_agent_credentials:
            job.required_capabilities = [f"connector:{connector.guid}"]
        else:
            # For server credentials, job needs the cloud capability (s3/gcs)
            job.required_capabilities = [connector.type]

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(
            "Created inventory import job",
            extra={
                "job_guid": job.guid,
                "connector_id": connector_id,
                "connector_guid": connector.guid
            }
        )

        return job

    def store_folders(
        self,
        connector_id: int,
        team_id: int,
        folders: List[str],
        folder_stats: Dict[str, Dict[str, Any]],
        total_files: int,
        total_size: int
    ) -> int:
        """
        Store discovered folders from inventory import.

        Creates InventoryFolder records for newly discovered paths
        and updates statistics for existing folders.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID
            folders: List of folder paths
            folder_stats: Dict mapping path to stats (file_count, total_size)
            total_files: Total files processed in inventory
            total_size: Total size of all files in bytes

        Returns:
            Number of folders stored/updated

        Raises:
            NotFoundError: If connector not found
        """
        from backend.src.models.inventory_folder import InventoryFolder

        connector = self._get_connector(connector_id, team_id)

        # Get existing folders for this connector
        existing_folders = {
            f.path: f for f in self.db.query(InventoryFolder).filter(
                InventoryFolder.connector_id == connector_id,
                InventoryFolder.team_id == team_id
            ).all()
        }

        stored_count = 0
        now = datetime.utcnow()

        for path in folders:
            stats = folder_stats.get(path, {})
            file_count = stats.get("file_count", 0)
            size = stats.get("total_size", 0)

            if path in existing_folders:
                # Update existing folder
                folder = existing_folders[path]
                folder.object_count = file_count
                folder.total_size_bytes = size
                folder.discovered_at = now
            else:
                # Create new folder
                folder = InventoryFolder(
                    team_id=team_id,
                    connector_id=connector_id,
                    path=path,
                    object_count=file_count,
                    total_size_bytes=size,
                    discovered_at=now
                )
                self.db.add(folder)

            stored_count += 1

        # Update connector's last import timestamp
        connector.inventory_last_import_at = now
        self.db.commit()

        logger.info(
            "Stored inventory folders",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "folder_count": stored_count,
                "total_files": total_files,
                "total_size": total_size
            }
        )

        return stored_count

    # =========================================================================
    # Inventory Status
    # =========================================================================

    def get_inventory_status(
        self,
        connector_id: int,
        team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get inventory status for a connector.

        Returns validation status, folder counts, and current job info.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID for tenant isolation

        Returns:
            Dictionary with inventory status information

        Raises:
            NotFoundError: If connector not found
        """
        connector = self._get_connector(connector_id, team_id)

        # Count folders
        folder_count = self.db.query(func.count(InventoryFolder.id)).filter(
            InventoryFolder.connector_id == connector_id
        ).scalar() or 0

        mapped_folder_count = self.db.query(func.count(InventoryFolder.id)).filter(
            InventoryFolder.connector_id == connector_id,
            InventoryFolder.collection_guid.isnot(None)
        ).scalar() or 0

        # Get current active job (if any)
        current_job = self.db.query(Job).filter(
            Job.team_id == connector.team_id,
            Job.tool.in_(["inventory_validate", "inventory_import"]),
            Job.status.in_([JobStatus.PENDING, JobStatus.ASSIGNED, JobStatus.RUNNING])
        ).first()

        current_job_info = None
        if current_job:
            progress = current_job.progress or {}
            # Check if job is for this connector
            if progress.get("connector_id") == connector_id or progress.get("connector_guid") == connector.guid:
                current_job_info = {
                    "guid": current_job.guid,
                    "status": current_job.status.value,
                    "phase": progress.get("phase", "unknown"),
                    "progress_percentage": progress.get("percentage", 0)
                }

        return {
            "validation_status": connector.inventory_validation_status,
            "validation_error": connector.inventory_validation_error,
            "last_import_at": connector.inventory_last_import_at.isoformat() if connector.inventory_last_import_at else None,
            "next_scheduled_at": None,  # TODO: Calculate from schedule
            "folder_count": folder_count,
            "mapped_folder_count": mapped_folder_count,
            "current_job": current_job_info
        }

    # =========================================================================
    # Inventory Folders
    # =========================================================================

    def list_folders(
        self,
        connector_id: int,
        team_id: Optional[int] = None,
        path_prefix: Optional[str] = None,
        unmapped_only: bool = False,
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[List[InventoryFolder], int, bool]:
        """
        List inventory folders for a connector.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID for tenant isolation
            path_prefix: Filter by path prefix
            unmapped_only: Only return folders not mapped to collections
            limit: Maximum number of folders to return
            offset: Number of folders to skip

        Returns:
            Tuple of (folders, total_count, has_more)

        Raises:
            NotFoundError: If connector not found
        """
        # Verify connector exists
        self._get_connector(connector_id, team_id)

        # Build query
        query = self.db.query(InventoryFolder).filter(
            InventoryFolder.connector_id == connector_id
        )

        if path_prefix:
            query = query.filter(InventoryFolder.path.startswith(path_prefix))

        if unmapped_only:
            query = query.filter(InventoryFolder.collection_guid.is_(None))

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination and ordering
        folders = query.order_by(InventoryFolder.path).offset(offset).limit(limit + 1).all()

        # Check if there are more results
        has_more = len(folders) > limit
        if has_more:
            folders = folders[:limit]

        return folders, total_count, has_more

    def upsert_folders(
        self,
        connector_id: int,
        folders_data: List[Dict[str, Any]],
        team_id: Optional[int] = None
    ) -> int:
        """
        Upsert inventory folders from import results.

        Creates new folders or updates existing ones based on path.

        Args:
            connector_id: Internal connector ID
            folders_data: List of folder dictionaries with path, object_count, total_size_bytes, etc.
            team_id: Team ID for tenant isolation

        Returns:
            Number of folders upserted

        Raises:
            NotFoundError: If connector not found
        """
        connector = self._get_connector(connector_id, team_id)

        upserted_count = 0
        now = datetime.utcnow()

        for folder_data in folders_data:
            path = folder_data.get("path", "")
            if not path:
                continue

            # Check if folder exists
            existing = self.db.query(InventoryFolder).filter(
                InventoryFolder.connector_id == connector_id,
                InventoryFolder.path == path
            ).first()

            if existing:
                # Update existing folder
                existing.object_count = folder_data.get("object_count", existing.object_count)
                existing.total_size_bytes = folder_data.get("total_size_bytes", existing.total_size_bytes)
                if "deepest_modified" in folder_data and folder_data["deepest_modified"]:
                    existing.deepest_modified = folder_data["deepest_modified"]
            else:
                # Create new folder
                folder = InventoryFolder(
                    connector_id=connector_id,
                    path=path,
                    object_count=folder_data.get("object_count", 0),
                    total_size_bytes=folder_data.get("total_size_bytes", 0),
                    deepest_modified=folder_data.get("deepest_modified"),
                    discovered_at=now
                )
                self.db.add(folder)

            upserted_count += 1

        # Update connector's last import timestamp
        connector.inventory_last_import_at = now

        self.db.commit()

        logger.info(
            "Upserted inventory folders",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "upserted_count": upserted_count
            }
        )

        return upserted_count

    def map_folder_to_collection(
        self,
        folder_id: int,
        collection_guid: str,
        team_id: Optional[int] = None
    ) -> InventoryFolder:
        """
        Map an inventory folder to a collection.

        Args:
            folder_id: Internal folder ID
            collection_guid: Collection GUID to map to
            team_id: Team ID for tenant isolation

        Returns:
            Updated InventoryFolder

        Raises:
            NotFoundError: If folder not found
        """
        folder = self.db.query(InventoryFolder).filter(
            InventoryFolder.id == folder_id
        ).first()

        if not folder:
            raise NotFoundError("InventoryFolder", str(folder_id))

        # Verify connector belongs to team if team_id provided
        if team_id is not None:
            connector = self.db.query(Connector).filter(
                Connector.id == folder.connector_id,
                Connector.team_id == team_id
            ).first()
            if not connector:
                raise NotFoundError("InventoryFolder", str(folder_id))

        folder.collection_guid = collection_guid
        self.db.commit()
        self.db.refresh(folder)

        logger.info(
            "Mapped inventory folder to collection",
            extra={
                "folder_id": folder_id,
                "folder_path": folder.path,
                "collection_guid": collection_guid
            }
        )

        return folder

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_connector(
        self,
        connector_id: int,
        team_id: Optional[int] = None
    ) -> Connector:
        """
        Get connector by ID with optional team filtering.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID for tenant isolation

        Returns:
            Connector instance

        Raises:
            NotFoundError: If connector not found
        """
        query = self.db.query(Connector).filter(Connector.id == connector_id)

        if team_id is not None:
            query = query.filter(Connector.team_id == team_id)

        connector = query.first()

        if not connector:
            raise NotFoundError("Connector", str(connector_id))

        return connector

    def get_connector_by_guid(
        self,
        guid: str,
        team_id: Optional[int] = None
    ) -> Connector:
        """
        Get connector by GUID with optional team filtering.

        Args:
            guid: Connector GUID (con_xxx)
            team_id: Team ID for tenant isolation

        Returns:
            Connector instance

        Raises:
            NotFoundError: If connector not found
            ValueError: If GUID format is invalid
        """
        uuid_value = GuidService.parse_identifier(guid, expected_prefix="con")
        query = self.db.query(Connector).filter(Connector.uuid == uuid_value)

        if team_id is not None:
            query = query.filter(Connector.team_id == team_id)

        connector = query.first()

        if not connector:
            raise NotFoundError("Connector", guid)

        return connector
