"""
Camera service for managing camera equipment records.

Provides CRUD operations, discovery, and statistics:
- List, get, update, delete cameras
- Discover cameras (batch idempotent create for agent use)
- Statistics for dashboard KPIs

Design:
- discover_cameras uses session.begin_nested() for SAVEPOINT
  to handle concurrent inserts gracefully
- DB-agnostic: no INSERT ON CONFLICT (works with SQLite tests)
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_

from backend.src.models.camera import Camera
from backend.src.schemas.camera import (
    CameraResponse, CameraListResponse, CameraStatsResponse,
    CameraDiscoverItem, CameraDiscoverResponse,
)
from backend.src.services.exceptions import NotFoundError, ConflictError
from backend.src.services.guid import GuidService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


class CameraService:
    """
    Service for managing camera equipment records.

    Handles CRUD operations, batch discovery, and statistics
    for camera entities scoped to a team.
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def list(
        self,
        team_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> CameraListResponse:
        """
        List cameras for a team with pagination and filtering.

        Args:
            team_id: Team ID for tenant isolation
            limit: Page size
            offset: Page offset
            status: Filter by status (temporary or confirmed)
            search: Search by camera_id, display_name, make, or model

        Returns:
            Paginated camera list with total count
        """
        query = self.db.query(Camera).filter(Camera.team_id == team_id)

        if status:
            query = query.filter(Camera.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Camera.camera_id.ilike(search_term),
                    Camera.display_name.ilike(search_term),
                    Camera.make.ilike(search_term),
                    Camera.model.ilike(search_term),
                )
            )

        total = query.count()
        cameras = query.order_by(Camera.camera_id).offset(offset).limit(limit).all()

        return CameraListResponse(
            items=[self._to_response(c) for c in cameras],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_by_guid(self, guid: str, team_id: int) -> CameraResponse:
        """
        Get camera by GUID.

        Args:
            guid: Camera GUID (cam_xxx)
            team_id: Team ID for tenant isolation

        Returns:
            Camera details

        Raises:
            ValueError: If GUID format is invalid
            NotFoundError: If camera not found or belongs to different team
        """
        camera = self._get_camera_by_guid(guid, team_id)
        return self._to_response(camera)

    def create(
        self,
        team_id: int,
        camera_id: str,
        status: str = "temporary",
        display_name: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        serial_number: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> CameraResponse:
        """
        Create a new camera record.

        Args:
            team_id: Team ID for tenant isolation
            camera_id: Short alphanumeric camera ID
            status: Camera status (temporary or confirmed)
            display_name: Optional friendly name
            make: Optional manufacturer
            model: Optional model name
            serial_number: Optional serial number
            notes: Optional notes
            user_id: User ID for audit

        Returns:
            Created camera details

        Raises:
            ConflictError: If camera_id already exists for this team
        """
        existing = self.db.query(Camera).filter(
            Camera.team_id == team_id,
            Camera.camera_id == camera_id,
        ).first()
        if existing:
            raise ConflictError(f"Camera with ID '{camera_id}' already exists")

        camera = Camera(
            team_id=team_id,
            camera_id=camera_id,
            status=status,
            display_name=display_name,
            make=make,
            model=model,
            serial_number=serial_number,
            notes=notes,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )

        self.db.add(camera)
        self.db.commit()
        self.db.refresh(camera)

        logger.info(f"Created camera '{camera_id}' (id={camera.id}, team_id={team_id})")
        return self._to_response(camera)

    def update(
        self,
        guid: str,
        team_id: int,
        status: Optional[str] = None,
        display_name: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        serial_number: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> CameraResponse:
        """
        Update camera details.

        Args:
            guid: Camera GUID (cam_xxx)
            team_id: Team ID for tenant isolation
            status: New status (temporary or confirmed)
            display_name: New display name
            make: New manufacturer
            model: New model name
            serial_number: New serial number
            notes: New notes
            user_id: User ID for audit

        Returns:
            Updated camera details

        Raises:
            ValueError: If GUID format is invalid
            NotFoundError: If camera not found
        """
        camera = self._get_camera_by_guid(guid, team_id)

        if status is not None:
            camera.status = status
        if display_name is not None:
            camera.display_name = display_name
        if make is not None:
            camera.make = make
        if model is not None:
            camera.model = model
        if serial_number is not None:
            camera.serial_number = serial_number
        if notes is not None:
            camera.notes = notes
        if user_id is not None:
            camera.updated_by_user_id = user_id

        self.db.commit()
        self.db.refresh(camera)

        logger.info(f"Updated camera {guid}")
        return self._to_response(camera)

    def delete(self, guid: str, team_id: int) -> str:
        """
        Delete a camera.

        Args:
            guid: Camera GUID (cam_xxx)
            team_id: Team ID for tenant isolation

        Returns:
            GUID of deleted camera

        Raises:
            ValueError: If GUID format is invalid
            NotFoundError: If camera not found
        """
        camera = self._get_camera_by_guid(guid, team_id)
        deleted_guid = camera.guid
        self.db.delete(camera)
        self.db.commit()

        logger.info(f"Deleted camera {deleted_guid}")
        return deleted_guid

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self, team_id: int) -> CameraStatsResponse:
        """
        Get camera statistics for dashboard KPIs.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Statistics including total, confirmed, and temporary counts
        """
        total = self.db.query(func.count(Camera.id)).filter(
            Camera.team_id == team_id
        ).scalar() or 0

        confirmed = self.db.query(func.count(Camera.id)).filter(
            Camera.team_id == team_id,
            Camera.status == "confirmed",
        ).scalar() or 0

        temporary = self.db.query(func.count(Camera.id)).filter(
            Camera.team_id == team_id,
            Camera.status == "temporary",
        ).scalar() or 0

        return CameraStatsResponse(
            total_cameras=total,
            confirmed_count=confirmed,
            temporary_count=temporary,
        )

    # =========================================================================
    # Discovery (Agent-facing)
    # =========================================================================

    def discover_cameras(
        self,
        team_id: int,
        camera_ids: List[str],
        user_id: Optional[int] = None,
    ) -> CameraDiscoverResponse:
        """
        Discover cameras: idempotent batch create.

        For each camera_id, checks if it already exists for this team.
        Creates new records with status "temporary" for unknown IDs.
        Uses SAVEPOINT (begin_nested) to handle concurrent inserts.

        Args:
            team_id: Team ID for tenant isolation
            camera_ids: List of camera IDs to discover
            user_id: Optional user ID for audit

        Returns:
            All cameras (existing + newly created) for the submitted IDs
        """
        if not camera_ids:
            return CameraDiscoverResponse(cameras=[])

        # Deduplicate
        unique_ids = list(dict.fromkeys(camera_ids))

        results: List[CameraDiscoverItem] = []

        for cam_id in unique_ids:
            # Check if already exists
            existing = self.db.query(Camera).filter(
                Camera.team_id == team_id,
                Camera.camera_id == cam_id,
            ).first()

            if existing:
                results.append(self._to_discover_item(existing))
                continue

            # Try to create with SAVEPOINT for concurrent safety
            try:
                nested = self.db.begin_nested()
                camera = Camera(
                    team_id=team_id,
                    camera_id=cam_id,
                    status="temporary",
                    display_name=None,
                    created_by_user_id=user_id,
                    updated_by_user_id=user_id,
                )
                self.db.add(camera)
                self.db.flush()
                nested.commit()
                results.append(self._to_discover_item(camera))
                logger.info(f"Discovered new camera '{cam_id}' for team {team_id}")
            except IntegrityError:
                nested.rollback()
                # Concurrent insert — camera was created between our check and insert
                existing = self.db.query(Camera).filter(
                    Camera.team_id == team_id,
                    Camera.camera_id == cam_id,
                ).first()
                if existing:
                    results.append(self._to_discover_item(existing))

        self.db.commit()

        return CameraDiscoverResponse(cameras=results)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_camera_by_guid(self, guid: str, team_id: int) -> Camera:
        """
        Get camera by GUID with team isolation.

        Args:
            guid: Camera GUID (cam_xxx)
            team_id: Team ID for tenant isolation

        Returns:
            Camera model

        Raises:
            ValueError: If GUID format is invalid
            NotFoundError: If camera not found or belongs to different team
        """
        uuid_value = GuidService.parse_identifier(guid, expected_prefix="cam")
        camera = self.db.query(Camera).filter(
            Camera.uuid == uuid_value,
            Camera.team_id == team_id,
        ).first()
        if not camera:
            raise NotFoundError("Camera", guid)
        return camera

    def _to_response(self, camera: Camera) -> CameraResponse:
        """Convert Camera model to CameraResponse."""
        return CameraResponse(
            guid=camera.guid,
            camera_id=camera.camera_id,
            status=camera.status,
            display_name=camera.display_name,
            make=camera.make,
            model=camera.model,
            serial_number=camera.serial_number,
            notes=camera.notes,
            metadata_json=camera.metadata_json,
            created_at=camera.created_at,
            updated_at=camera.updated_at,
            audit=camera.audit,
        )

    def _to_discover_item(self, camera: Camera) -> CameraDiscoverItem:
        """Convert Camera model to CameraDiscoverItem."""
        return CameraDiscoverItem(
            guid=camera.guid,
            camera_id=camera.camera_id,
            status=camera.status,
            display_name=camera.display_name,
        )
