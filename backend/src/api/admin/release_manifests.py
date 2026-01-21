"""
Admin Release Manifests API endpoints for managing agent binary attestation.

Provides endpoints for creating, listing, and managing release manifests.
Release manifests store known-good checksums for agent binaries.
All endpoints require super admin privileges.

Part of Issue #90 - Distributed Agent Architecture (Phase 14)
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_super_admin, TenantContext
from backend.src.models.release_manifest import ReleaseManifest
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(prefix="/release-manifests", tags=["Admin - Release Manifests"])


# ============================================================================
# Schemas
# ============================================================================


class ReleaseManifestCreateRequest(BaseModel):
    """Request schema for creating a release manifest."""

    version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Semantic version (e.g., '1.0.0', '1.2.3-beta')"
    )
    platform: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Platform identifier (e.g., 'darwin-arm64', 'linux-amd64')"
    )
    checksum: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r'^[0-9a-fA-F]{64}$',
        description="SHA-256 checksum of the binary (64 hex characters)"
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional notes about this release"
    )
    is_active: bool = Field(
        True,
        description="Whether this manifest is active (allows registration)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": "1.0.0",
                "platform": "darwin-arm64",
                "checksum": "a" * 64,
                "notes": "Initial release for macOS Apple Silicon",
                "is_active": True,
            }
        }
    }


class ReleaseManifestUpdateRequest(BaseModel):
    """Request schema for updating a release manifest."""

    is_active: Optional[bool] = Field(
        None,
        description="Whether this manifest is active"
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional notes about this release"
    )


class ReleaseManifestResponse(BaseModel):
    """Response schema for a release manifest."""

    guid: str = Field(..., description="Release manifest GUID (rel_xxx)")
    version: str = Field(..., description="Semantic version")
    platform: str = Field(..., description="Platform identifier")
    checksum: str = Field(..., description="SHA-256 checksum")
    is_active: bool = Field(..., description="Whether manifest is active")
    notes: Optional[str] = Field(None, description="Optional notes")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class ReleaseManifestListResponse(BaseModel):
    """Response schema for listing release manifests."""

    manifests: List[ReleaseManifestResponse]
    total_count: int
    active_count: int


class ReleaseManifestStatsResponse(BaseModel):
    """Response schema for release manifest statistics."""

    total_count: int
    active_count: int
    platforms: List[str]
    versions: List[str]


# ============================================================================
# Helper Functions
# ============================================================================


def manifest_to_response(manifest: ReleaseManifest) -> ReleaseManifestResponse:
    """Convert ReleaseManifest model to response schema."""
    return ReleaseManifestResponse(
        guid=manifest.guid,
        version=manifest.version,
        platform=manifest.platform,
        checksum=manifest.checksum,
        is_active=manifest.is_active,
        notes=manifest.notes,
        created_at=manifest.created_at.isoformat(),
        updated_at=manifest.updated_at.isoformat(),
    )


# ============================================================================
# Release Manifest Endpoints (Super Admin Only)
# ============================================================================


@router.post("", response_model=ReleaseManifestResponse, status_code=201)
async def create_release_manifest(
    request: ReleaseManifestCreateRequest,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new release manifest.

    Creates a manifest entry for a known-good agent binary checksum.
    Agents with this checksum will be allowed to register.

    **Requires super admin privileges.**

    - **version**: Semantic version string
    - **platform**: Target platform (darwin-arm64, linux-amd64, etc.)
    - **checksum**: SHA-256 hash of the binary (64 hex chars)
    - **notes**: Optional notes about this release
    - **is_active**: Whether to allow registration with this checksum
    """
    try:
        # Check for duplicate (version, platform)
        existing = db.query(ReleaseManifest).filter(
            ReleaseManifest.version == request.version.strip(),
            ReleaseManifest.platform == request.platform.lower(),
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Manifest already exists for version {request.version} on {request.platform}"
            )

        manifest = ReleaseManifest(
            version=request.version,
            platform=request.platform,
            checksum=request.checksum,
            notes=request.notes,
            is_active=request.is_active,
        )

        db.add(manifest)
        db.commit()
        db.refresh(manifest)

        logger.info(
            "Super admin created release manifest",
            extra={
                "event": "admin.release_manifest.created",
                "admin_email": ctx.user_email,
                "admin_guid": ctx.user_guid,
                "manifest_guid": manifest.guid,
                "version": manifest.version,
                "platform": manifest.platform,
                "is_active": manifest.is_active,
            }
        )

        return manifest_to_response(manifest)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ReleaseManifestListResponse)
async def list_release_manifests(
    active_only: bool = Query(False, description="Only return active manifests"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    version: Optional[str] = Query(None, description="Filter by version"),
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    List all release manifests.

    **Requires super admin privileges.**

    Query parameters:
    - **active_only**: If true, only return active manifests
    - **platform**: Filter by platform identifier
    - **version**: Filter by version string
    """
    query = db.query(ReleaseManifest)

    if active_only:
        query = query.filter(ReleaseManifest.is_active == True)

    if platform:
        query = query.filter(ReleaseManifest.platform == platform.lower())

    if version:
        query = query.filter(ReleaseManifest.version == version)

    manifests = query.order_by(
        ReleaseManifest.version.desc(),
        ReleaseManifest.platform,
    ).all()

    # Count active
    active_count = sum(1 for m in manifests if m.is_active)

    return ReleaseManifestListResponse(
        manifests=[manifest_to_response(m) for m in manifests],
        total_count=len(manifests),
        active_count=active_count,
    )


@router.get("/stats", response_model=ReleaseManifestStatsResponse)
async def get_release_manifest_stats(
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Get release manifest statistics.

    Returns aggregate statistics about release manifests.

    **Requires super admin privileges.**
    """
    total_count = db.query(func.count(ReleaseManifest.id)).scalar() or 0
    active_count = db.query(func.count(ReleaseManifest.id)).filter(
        ReleaseManifest.is_active == True
    ).scalar() or 0

    # Get unique platforms and versions
    platforms = [
        row[0] for row in
        db.query(ReleaseManifest.platform).distinct().order_by(ReleaseManifest.platform).all()
    ]
    versions = [
        row[0] for row in
        db.query(ReleaseManifest.version).distinct().order_by(ReleaseManifest.version.desc()).all()
    ]

    return ReleaseManifestStatsResponse(
        total_count=total_count,
        active_count=active_count,
        platforms=platforms,
        versions=versions,
    )


@router.get("/{guid}", response_model=ReleaseManifestResponse)
async def get_release_manifest(
    guid: str,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Get a release manifest by GUID.

    **Requires super admin privileges.**
    """
    try:
        uuid = ReleaseManifest.parse_guid(guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release manifest not found"
        )

    manifest = db.query(ReleaseManifest).filter(
        ReleaseManifest.uuid == uuid
    ).first()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release manifest not found"
        )

    return manifest_to_response(manifest)


@router.patch("/{guid}", response_model=ReleaseManifestResponse)
async def update_release_manifest(
    guid: str,
    request: ReleaseManifestUpdateRequest,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Update a release manifest.

    Only `is_active` and `notes` can be updated. Version, platform, and
    checksum are immutable after creation.

    **Requires super admin privileges.**
    """
    try:
        uuid = ReleaseManifest.parse_guid(guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release manifest not found"
        )

    manifest = db.query(ReleaseManifest).filter(
        ReleaseManifest.uuid == uuid
    ).first()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release manifest not found"
        )

    # Update fields if provided
    if request.is_active is not None:
        old_active = manifest.is_active
        manifest.is_active = request.is_active

        if old_active != request.is_active:
            action = "activated" if request.is_active else "deactivated"
            logger.info(
                f"Super admin {action} release manifest",
                extra={
                    "event": f"admin.release_manifest.{action}",
                    "admin_email": ctx.user_email,
                    "admin_guid": ctx.user_guid,
                    "manifest_guid": manifest.guid,
                    "version": manifest.version,
                    "platform": manifest.platform,
                }
            )

    if request.notes is not None:
        manifest.notes = request.notes

    db.commit()
    db.refresh(manifest)

    return manifest_to_response(manifest)


@router.delete("/{guid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release_manifest(
    guid: str,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a release manifest.

    Permanently removes the manifest. Consider deactivating instead if
    you want to preserve the record.

    **Requires super admin privileges.**
    """
    try:
        uuid = ReleaseManifest.parse_guid(guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release manifest not found"
        )

    manifest = db.query(ReleaseManifest).filter(
        ReleaseManifest.uuid == uuid
    ).first()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release manifest not found"
        )

    # Log before deletion
    logger.warning(
        "Super admin deleted release manifest",
        extra={
            "event": "admin.release_manifest.deleted",
            "admin_email": ctx.user_email,
            "admin_guid": ctx.user_guid,
            "manifest_guid": manifest.guid,
            "version": manifest.version,
            "platform": manifest.platform,
            "checksum": manifest.checksum,
        }
    )

    db.delete(manifest)
    db.commit()

    return None
