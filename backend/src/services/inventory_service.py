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
from typing import Dict, Any, List, Optional, Set, Tuple, Union

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
from backend.src.services.exceptions import NotFoundError, ValidationError, ConflictError
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
            success, message, latest_manifest = self._validate_manifest_access(
                connector.type, credentials, config, manifest_path
            )

            # Update status based on result
            if success:
                connector.inventory_validation_status = InventoryValidationStatus.VALIDATED
                connector.inventory_validation_error = None
                connector.inventory_latest_manifest = latest_manifest
            else:
                connector.inventory_validation_status = InventoryValidationStatus.FAILED
                connector.inventory_validation_error = message
                connector.inventory_latest_manifest = None

            self.db.commit()

            logger.info(
                "Completed inventory config validation (server-side)",
                extra={
                    "connector_id": connector_id,
                    "success": success,
                    "result_message": message,
                    "latest_manifest": latest_manifest
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
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate access to inventory manifest using storage adapter.

        Args:
            connector_type: Connector type (S3 or GCS)
            credentials: Decrypted credentials
            config: Inventory configuration dict
            manifest_prefix: Path prefix to search for manifest

        Returns:
            Tuple of (success, message, latest_manifest_display)
            latest_manifest_display is the timestamp/manifest.json portion for display
        """
        from backend.src.services.remote import S3Adapter, GCSAdapter

        destination_bucket = config.get("destination_bucket", "")

        try:
            if connector_type == ConnectorType.S3:
                adapter = S3Adapter(credentials)
                # List objects at the manifest prefix to find inventory folders
                location = f"{destination_bucket}/{manifest_prefix}"
                files = adapter.list_files(location)

                # Look for any manifest.json file, sort to get latest
                manifest_files = sorted(
                    [f for f in files if f.endswith("manifest.json")],
                    reverse=True  # Latest first (timestamp folders sort lexicographically)
                )
                if manifest_files:
                    # Extract just the timestamp/manifest.json part for display
                    latest_manifest = manifest_files[0]
                    manifest_parts = latest_manifest.split("/")
                    if len(manifest_parts) >= 2:
                        latest_manifest_display = "/".join(manifest_parts[-2:])
                    else:
                        latest_manifest_display = latest_manifest
                    return True, f"Found {len(manifest_files)} inventory manifest(s)", latest_manifest_display
                else:
                    return False, (
                        f"No manifest.json found at {location}. "
                        "Verify the inventory is enabled and has generated at least one report."
                    ), None

            else:  # GCS
                adapter = GCSAdapter(credentials)
                location = f"{destination_bucket}/{manifest_prefix}"
                files = adapter.list_files(location)

                manifest_files = sorted(
                    [f for f in files if f.endswith("manifest.json")],
                    reverse=True
                )
                if manifest_files:
                    latest_manifest = manifest_files[0]
                    manifest_parts = latest_manifest.split("/")
                    if len(manifest_parts) >= 2:
                        latest_manifest_display = "/".join(manifest_parts[-2:])
                    else:
                        latest_manifest_display = latest_manifest
                    return True, f"Found {len(manifest_files)} inventory manifest(s)", latest_manifest_display
                else:
                    return False, (
                        f"No manifest.json found at {location}. "
                        "Verify Storage Insights is enabled and has generated at least one report."
                    ), None

        except PermissionError as e:
            return False, f"Access denied: {str(e)}", None
        except ConnectionError as e:
            return False, f"Connection failed: {str(e)}", None
        except Exception as e:
            return False, f"Validation error: {str(e)}", None

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
        latest_manifest: Optional[str] = None,
        team_id: Optional[int] = None
    ) -> Connector:
        """
        Update inventory validation status from agent result.

        Called when an agent completes a validation job to report the result.

        Args:
            connector_id: Internal connector ID
            success: Whether validation succeeded
            error_message: Error message if validation failed
            latest_manifest: Path of the latest detected manifest.json
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
            connector.inventory_latest_manifest = latest_manifest
        else:
            connector.inventory_validation_status = InventoryValidationStatus.FAILED
            connector.inventory_validation_error = error_message
            connector.inventory_latest_manifest = None

        self.db.commit()
        self.db.refresh(connector)

        logger.info(
            "Updated inventory validation status from agent",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "success": success,
                "error": error_message,
                "latest_manifest": latest_manifest
            }
        )

        return connector

    def has_running_inventory_job(
        self,
        connector_id: int,
        team_id: int
    ) -> Optional[Job]:
        """
        Check if there's already a running inventory job for this connector.

        A job is considered "running" if it's in PENDING, ASSIGNED, or RUNNING status.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID

        Returns:
            The running Job if one exists, None otherwise
        """
        # Get the connector to find its GUID for matching
        connector = self._get_connector(connector_id, team_id)

        # Query all running inventory jobs for this team
        running_jobs = self.db.query(Job).filter(
            Job.team_id == team_id,
            Job.tool.in_(["inventory_import", "inventory_validate"]),
            Job.status.in_([JobStatus.PENDING, JobStatus.ASSIGNED, JobStatus.RUNNING])
        ).all()

        # Check each job to find one matching this connector
        for job in running_jobs:
            progress = job.progress or {}
            # Match by connector_id or connector_guid
            if progress.get("connector_id") == connector_id:
                return job
            if progress.get("connector_guid") == connector.guid:
                return job

        return None

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
            ConflictError: If an import job is already running for this connector
        """
        connector = self._get_connector(connector_id, team_id)

        if not connector.has_inventory_config:
            raise ValidationError("Connector has no inventory configuration")

        if connector.inventory_validation_status != InventoryValidationStatus.VALIDATED:
            raise ValidationError(
                f"Inventory configuration not validated. Current status: "
                f"{connector.inventory_validation_status or 'none'}"
            )

        # Check for existing running inventory job (T039: concurrent import prevention)
        existing_job = self.has_running_inventory_job(connector_id, team_id)
        if existing_job:
            raise ConflictError(
                message=f"An inventory job is already running for this connector",
                existing_job_id=existing_job.guid
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
            # Convert enum to string value
            job.required_capabilities = [connector.type.value if hasattr(connector.type, 'value') else str(connector.type)]

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
        # Note: team isolation is enforced via connector_id (connector belongs to team)
        existing_folders = {
            f.path: f for f in self.db.query(InventoryFolder).filter(
                InventoryFolder.connector_id == connector_id
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
                # Note: team isolation is enforced via connector_id (connector belongs to team)
                folder = InventoryFolder(
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

        # Count folders still eligible for mapping (not mapped and not eliminated by hierarchy)
        mappable_folder_count = self.db.query(func.count(InventoryFolder.id)).filter(
            InventoryFolder.connector_id == connector_id,
            InventoryFolder.is_mappable == True  # noqa: E712
        ).scalar() or 0

        # Get current active job for this connector (if any)
        running_jobs = self.db.query(Job).filter(
            Job.team_id == connector.team_id,
            Job.tool.in_(["inventory_validate", "inventory_import"]),
            Job.status.in_([JobStatus.PENDING, JobStatus.ASSIGNED, JobStatus.RUNNING])
        ).all()

        current_job_info = None
        # Find the job that matches this specific connector
        for job in running_jobs:
            progress = job.progress or {}
            if progress.get("connector_id") == connector_id or progress.get("connector_guid") == connector.guid:
                current_job_info = {
                    "guid": job.guid,
                    "status": job.status.value,
                    "phase": progress.get("phase", "unknown"),
                    "progress_percentage": progress.get("percentage", 0)
                }
                break

        return {
            "validation_status": connector.inventory_validation_status,
            "validation_error": connector.inventory_validation_error,
            "latest_manifest": connector.inventory_latest_manifest,
            "last_import_at": connector.inventory_last_import_at.isoformat() if connector.inventory_last_import_at else None,
            "next_scheduled_at": None,  # TODO: Calculate from schedule
            "folder_count": folder_count,
            "mapped_folder_count": mapped_folder_count,
            "mappable_folder_count": mappable_folder_count,
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

        Validates that:
        1. The folder exists and is accessible by the team
        2. The folder is currently mappable (not blocked by hierarchy)
        3. The collection exists and belongs to the same team

        Args:
            folder_id: Internal folder ID
            collection_guid: Collection GUID to map to
            team_id: Team ID for tenant isolation

        Returns:
            Updated InventoryFolder

        Raises:
            NotFoundError: If folder or collection not found
            ValidationError: If folder is not mappable or collection doesn't match tenant
        """
        from backend.src.models.collection import Collection

        folder = self.db.query(InventoryFolder).filter(
            InventoryFolder.id == folder_id
        ).first()

        if not folder:
            raise NotFoundError("InventoryFolder", str(folder_id))

        # Get the connector to verify team ownership
        connector = self.db.query(Connector).filter(
            Connector.id == folder.connector_id
        ).first()

        if not connector:
            raise NotFoundError("InventoryFolder", str(folder_id))

        # Verify connector belongs to team if team_id provided
        effective_team_id = team_id if team_id is not None else connector.team_id
        if team_id is not None and connector.team_id != team_id:
            raise NotFoundError("InventoryFolder", str(folder_id))

        # Check if folder is currently mappable
        if not folder.is_mappable:
            raise ValidationError(
                f"Folder '{folder.path}' is not mappable. "
                "A parent or child folder may already be mapped to a collection."
            )

        # Validate that the collection exists and belongs to the same team
        try:
            uuid_value = GuidService.parse_identifier(collection_guid, expected_prefix="col")
        except ValueError as e:
            raise ValidationError(f"Invalid collection GUID: {e}")

        collection = self.db.query(Collection).filter(
            Collection.uuid == uuid_value,
            Collection.team_id == effective_team_id
        ).first()

        if not collection:
            raise NotFoundError("Collection", collection_guid)

        # All validations passed - perform the mapping
        folder.collection_guid = collection_guid
        self.db.commit()
        self.db.refresh(folder)

        # Recalculate mappability for all folders of this connector
        self.recalculate_folder_mappability(folder.connector_id)

        logger.info(
            "Mapped inventory folder to collection",
            extra={
                "folder_id": folder_id,
                "folder_path": folder.path,
                "collection_guid": collection_guid,
                "collection_id": collection.id
            }
        )

        return folder

    def recalculate_folder_mappability(self, connector_id: int) -> int:
        """
        Recalculate is_mappable for all folders of a connector.

        A folder is NOT mappable if:
        1. It is directly mapped (collection_guid is set), OR
        2. An ancestor folder is mapped (parent path has collection_guid), OR
        3. A descendant folder is mapped (child path has collection_guid)

        Args:
            connector_id: Connector ID to recalculate folders for

        Returns:
            Number of folders marked as not mappable
        """
        # Get all folders for this connector
        folders = self.db.query(InventoryFolder).filter(
            InventoryFolder.connector_id == connector_id
        ).all()

        # Get paths of all mapped folders
        mapped_paths = {
            f.path for f in folders if f.collection_guid is not None
        }

        not_mappable_count = 0

        for folder in folders:
            # Check if this folder is mappable
            is_mappable = True

            # Rule 1: Directly mapped
            if folder.collection_guid is not None:
                is_mappable = False
            else:
                # Rule 2: Check if any ancestor is mapped
                # Ancestors have paths that are prefixes of this folder's path
                for mapped_path in mapped_paths:
                    if folder.path.startswith(mapped_path) and folder.path != mapped_path:
                        # mapped_path is an ancestor of folder.path
                        is_mappable = False
                        break

                # Rule 3: Check if any descendant is mapped
                if is_mappable:
                    for mapped_path in mapped_paths:
                        if mapped_path.startswith(folder.path) and mapped_path != folder.path:
                            # mapped_path is a descendant of folder.path
                            is_mappable = False
                            break

            folder.is_mappable = is_mappable
            if not is_mappable:
                not_mappable_count += 1

        self.db.commit()

        logger.info(
            "Recalculated folder mappability",
            extra={
                "connector_id": connector_id,
                "total_folders": len(folders),
                "not_mappable": not_mappable_count,
                "mapped_folders": len(mapped_paths)
            }
        )

        return not_mappable_count

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

    def get_folder_by_guid(
        self,
        guid: str,
        team_id: Optional[int] = None
    ) -> InventoryFolder:
        """
        Get inventory folder by GUID with optional team filtering.

        Args:
            guid: Folder GUID (fld_xxx)
            team_id: Team ID for tenant isolation (via connector)

        Returns:
            InventoryFolder instance

        Raises:
            NotFoundError: If folder not found
            ValueError: If GUID format is invalid
        """
        uuid_value = GuidService.parse_identifier(guid, expected_prefix="fld")
        query = self.db.query(InventoryFolder).filter(InventoryFolder.uuid == uuid_value)

        folder = query.first()

        if not folder:
            raise NotFoundError("InventoryFolder", guid)

        # Verify connector belongs to team if team_id provided
        if team_id is not None:
            connector = self.db.query(Connector).filter(
                Connector.id == folder.connector_id,
                Connector.team_id == team_id
            ).first()
            if not connector:
                raise NotFoundError("InventoryFolder", guid)

        return folder

    # =========================================================================
    # Collection Creation from Inventory
    # =========================================================================

    def validate_folder_mappings(
        self,
        connector_id: int,
        folder_guids: List[str],
        team_id: Optional[int] = None
    ) -> Tuple[List[InventoryFolder], List[Tuple[str, str]]]:
        """
        Validate folder mappings for collection creation.

        Checks:
        - All folders exist and belong to connector
        - No folders are already mapped to collections
        - No overlapping paths (ancestor/descendant relations)

        Args:
            connector_id: Internal connector ID
            folder_guids: List of folder GUIDs to validate
            team_id: Team ID for tenant isolation

        Returns:
            Tuple of (valid_folders, errors) where errors is list of (folder_guid, error_message)
        """
        connector = self._get_connector(connector_id, team_id)
        valid_folders: List[InventoryFolder] = []
        errors: List[Tuple[str, str]] = []

        # Parse all GUIDs and fetch folders
        folder_map: Dict[str, InventoryFolder] = {}
        for guid in folder_guids:
            try:
                folder = self.get_folder_by_guid(guid, team_id)

                # Check folder belongs to this connector
                if folder.connector_id != connector_id:
                    errors.append((guid, "Folder does not belong to this connector"))
                    continue

                # Check folder is not already mapped
                if folder.collection_guid is not None:
                    errors.append((guid, "Folder is already mapped to a collection"))
                    continue

                folder_map[guid] = folder
            except NotFoundError:
                errors.append((guid, "Folder not found"))
            except ValueError as e:
                errors.append((guid, str(e)))

        # Check for overlapping paths
        paths = [(guid, folder.path) for guid, folder in folder_map.items()]

        for i, (guid1, path1) in enumerate(paths):
            for guid2, path2 in paths[i + 1:]:
                if self._paths_overlap(path1, path2):
                    errors.append((guid1, f"Path overlaps with another selected folder: {path2}"))
                    # Remove from valid
                    if guid1 in folder_map:
                        del folder_map[guid1]
                    break

        valid_folders = list(folder_map.values())
        return valid_folders, errors

    def _paths_overlap(self, path1: str, path2: str) -> bool:
        """Check if two paths have an ancestor/descendant relationship."""
        # Normalize paths to end with /
        p1 = path1 if path1.endswith('/') else path1 + '/'
        p2 = path2 if path2.endswith('/') else path2 + '/'

        return p1.startswith(p2) or p2.startswith(p1)

    # =========================================================================
    # FileInfo Storage (Phase B - Issue #107)
    # =========================================================================

    def get_collections_for_connector(
        self,
        connector_id: int,
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get collections mapped to folders for a connector.

        Returns collections that have been created from inventory folders,
        along with their folder path for filtering.

        Args:
            connector_id: Internal connector ID
            team_id: Team ID for tenant isolation

        Returns:
            List of dicts with collection_guid, collection_id, folder_path
        """
        from backend.src.models.collection import Collection

        connector = self._get_connector(connector_id, team_id)

        # Get inventory folders that have been mapped to collections
        mapped_folders = self.db.query(InventoryFolder).filter(
            InventoryFolder.connector_id == connector_id,
            InventoryFolder.collection_guid.isnot(None)
        ).all()

        if not mapped_folders:
            return []

        # Get the collections for these mappings
        collection_guids = [f.collection_guid for f in mapped_folders]

        # Query collections by GUID (via UUID lookup)
        # Include tenant scoping to prevent cross-tenant data leakage
        from backend.src.services.guid import GuidService

        # Use provided team_id or fall back to connector's team_id
        effective_team_id = team_id if team_id is not None else connector.team_id

        collections_data = []
        for folder in mapped_folders:
            try:
                uuid_value = GuidService.parse_identifier(folder.collection_guid, expected_prefix="col")
                collection = self.db.query(Collection).filter(
                    Collection.uuid == uuid_value,
                    Collection.team_id == effective_team_id
                ).first()

                if collection:
                    collections_data.append({
                        "collection_guid": folder.collection_guid,
                        "collection_id": collection.id,
                        "folder_path": folder.path
                    })
            except ValueError:
                # Skip invalid GUIDs
                continue

        logger.info(
            "Retrieved collections for connector",
            extra={
                "connector_id": connector_id,
                "connector_guid": connector.guid,
                "collection_count": len(collections_data)
            }
        )

        return collections_data

    def store_file_info(
        self,
        collection_id: int,
        file_info: List[Dict[str, Any]],
        team_id: Optional[int] = None
    ) -> bool:
        """
        Store FileInfo on a collection from inventory import.

        Updates the collection's file_info JSONB, file_info_updated_at,
        and file_info_source fields.

        Args:
            collection_id: Internal collection ID
            file_info: List of FileInfo dicts (key, size, last_modified, etc.)
            team_id: Team ID for tenant isolation

        Returns:
            True if stored successfully

        Raises:
            NotFoundError: If collection not found
        """
        from backend.src.models.collection import Collection

        query = self.db.query(Collection).filter(Collection.id == collection_id)

        if team_id is not None:
            query = query.filter(Collection.team_id == team_id)

        collection = query.first()

        if not collection:
            raise NotFoundError("Collection", str(collection_id))

        # Store FileInfo
        collection.file_info = file_info
        collection.file_info_updated_at = datetime.utcnow()
        collection.file_info_source = "inventory"

        self.db.commit()

        logger.info(
            "Stored FileInfo on collection",
            extra={
                "collection_id": collection_id,
                "collection_guid": collection.guid,
                "file_count": len(file_info),
                "source": "inventory"
            }
        )

        return True

    def store_file_info_batch(
        self,
        collections_data: List[Dict[str, Any]],
        connector_id: Optional[int] = None,
        team_id: Optional[int] = None
    ) -> int:
        """
        Store FileInfo for multiple collections from inventory import.

        Only updates collections that are mapped to the specified connector
        via InventoryFolder mappings. This provides defense-in-depth against
        agents attempting to update arbitrary collections.

        Args:
            collections_data: List of dicts with collection_guid and file_info
            connector_id: Connector ID to validate mapping (required for security)
            team_id: Team ID for tenant isolation

        Returns:
            Number of collections updated
        """
        from backend.src.models.collection import Collection
        from backend.src.services.guid import GuidService

        updated_count = 0
        skipped_count = 0
        now = datetime.utcnow()

        # Build set of allowed collection GUIDs (collections mapped to this connector)
        allowed_guids: Optional[Set[str]] = None
        if connector_id is not None:
            mapped_folders = self.db.query(InventoryFolder).filter(
                InventoryFolder.connector_id == connector_id,
                InventoryFolder.collection_guid.isnot(None)
            ).all()
            allowed_guids = {f.collection_guid for f in mapped_folders if f.collection_guid}

        for data in collections_data:
            collection_guid = data.get("collection_guid")
            file_info = data.get("file_info", [])

            if not collection_guid:
                continue

            # Defensive check: ensure collection is mapped to the connector
            if allowed_guids is not None and collection_guid not in allowed_guids:
                logger.warning(
                    "Skipping collection not mapped to connector",
                    extra={
                        "collection_guid": collection_guid,
                        "connector_id": connector_id
                    }
                )
                skipped_count += 1
                continue

            try:
                uuid_value = GuidService.parse_identifier(collection_guid, expected_prefix="col")
                query = self.db.query(Collection).filter(Collection.uuid == uuid_value)

                if team_id is not None:
                    query = query.filter(Collection.team_id == team_id)

                collection = query.first()

                if collection:
                    # Additional check: verify mapping exists for this specific collection
                    if connector_id is not None:
                        mapping_exists = self.db.query(InventoryFolder).filter(
                            InventoryFolder.connector_id == connector_id,
                            InventoryFolder.collection_guid == collection_guid
                        ).first() is not None

                        if not mapping_exists:
                            logger.warning(
                                "Skipping collection with no folder mapping",
                                extra={
                                    "collection_guid": collection_guid,
                                    "connector_id": connector_id
                                }
                            )
                            skipped_count += 1
                            continue

                    collection.file_info = file_info
                    collection.file_info_updated_at = now
                    collection.file_info_source = "inventory"
                    updated_count += 1
            except ValueError:
                # Skip invalid GUIDs
                continue

        self.db.commit()

        logger.info(
            "Stored FileInfo batch",
            extra={
                "collections_updated": updated_count,
                "collections_skipped": skipped_count,
                "connector_id": connector_id,
                "source": "inventory"
            }
        )

        return updated_count
