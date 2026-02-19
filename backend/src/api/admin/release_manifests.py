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

from backend.src.schemas.audit import AuditInfo
from pydantic import BaseModel, Field

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_super_admin, TenantContext
from backend.src.models.release_manifest import ReleaseManifest
from backend.src.models.release_artifact import ReleaseArtifact
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.services.download_service import resolve_binary_path
from backend.src.config.settings import get_settings
from backend.src.services.manifest_cleanup_service import cleanup_old_manifests
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(prefix="/release-manifests", tags=["Admin - Release Manifests"])


# ============================================================================
# Schemas
# ============================================================================


class ArtifactCreateRequest(BaseModel):
    """Request schema for creating a release artifact alongside a manifest."""

    platform: str = Field(
        ...,
        description="Platform identifier (e.g., 'darwin-arm64')"
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Binary filename (no path separators)"
    )
    checksum: str = Field(
        ...,
        pattern=r'^(sha256:)?[0-9a-fA-F]{64}$',
        description="sha256:-prefixed hex checksum (or plain 64 hex chars)"
    )
    file_size: Optional[int] = Field(
        None,
        ge=0,
        description="File size in bytes"
    )


class ReleaseManifestCreateRequest(BaseModel):
    """Request schema for creating a release manifest."""

    version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Semantic version (e.g., '1.0.0', '1.2.3-beta')"
    )
    platforms: List[str] = Field(
        ...,
        min_length=1,
        description="Platform identifiers (e.g., ['darwin-arm64', 'darwin-amd64'])"
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
    artifacts: Optional[List[ArtifactCreateRequest]] = Field(
        None,
        description="Optional per-platform binary artifacts. If omitted, no artifacts are created."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": "1.0.0",
                "platforms": ["darwin-arm64", "darwin-amd64"],
                "checksum": "a" * 64,
                "notes": "macOS universal binary (Apple Silicon + Intel)",
                "is_active": True,
                "artifacts": [
                    {
                        "platform": "darwin-arm64",
                        "filename": "shuttersense-agent-darwin-arm64",
                        "checksum": "sha256:" + "b" * 64,
                        "file_size": 15728640,
                    }
                ],
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


class ArtifactResponse(BaseModel):
    """Response schema for a release artifact."""

    platform: str = Field(..., description="Platform identifier")
    filename: str = Field(..., description="Binary filename")
    checksum: str = Field(..., description="sha256:-prefixed hex checksum")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    created_at: str = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class ReleaseManifestResponse(BaseModel):
    """Response schema for a release manifest."""

    guid: str = Field(..., description="Release manifest GUID (rel_xxx)")
    version: str = Field(..., description="Semantic version")
    platforms: List[str] = Field(..., description="Platform identifiers")
    checksum: str = Field(..., description="SHA-256 checksum")
    is_active: bool = Field(..., description="Whether manifest is active")
    notes: Optional[str] = Field(None, description="Optional notes")
    artifacts: List[ArtifactResponse] = Field(default_factory=list, description="Per-platform binary artifacts")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    audit: Optional[AuditInfo] = Field(None, description="Audit trail")

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


def artifact_to_response(artifact: ReleaseArtifact) -> ArtifactResponse:
    """Convert ReleaseArtifact model to response schema.

    Args:
        artifact: ReleaseArtifact ORM instance with platform, filename,
            checksum, file_size, and created_at fields populated.

    Returns:
        ArtifactResponse with created_at serialized to ISO 8601 string.

    Raises:
        AttributeError: If artifact is missing expected fields.
    """
    return ArtifactResponse(
        platform=artifact.platform,
        filename=artifact.filename,
        checksum=artifact.checksum,
        file_size=artifact.file_size,
        created_at=artifact.created_at.isoformat(),
    )


def manifest_to_response(manifest: ReleaseManifest) -> ReleaseManifestResponse:
    """Convert ReleaseManifest model to response schema."""
    return ReleaseManifestResponse(
        guid=manifest.guid,
        version=manifest.version,
        platforms=manifest.platforms,
        checksum=manifest.checksum,
        is_active=manifest.is_active,
        notes=manifest.notes,
        artifacts=[artifact_to_response(a) for a in manifest.artifacts] if manifest.artifacts else [],
        created_at=manifest.created_at.isoformat(),
        updated_at=manifest.updated_at.isoformat(),
        audit=manifest.audit,
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
    - **platforms**: Target platforms (can include multiple for universal binaries)
    - **checksum**: SHA-256 hash of the binary (64 hex chars)
    - **notes**: Optional notes about this release
    - **is_active**: Whether to allow registration with this checksum
    - **artifacts**: Optional per-platform binary metadata (filename, checksum, file_size)
    """
    try:
        # Validate platforms list is not empty
        if not request.platforms:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one platform is required"
            )

        # Check for duplicate (version, checksum)
        existing = db.query(ReleaseManifest).filter(
            ReleaseManifest.version == request.version.strip(),
            ReleaseManifest.checksum == request.checksum.lower(),
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Manifest already exists for version {request.version} with this checksum"
            )

        manifest = ReleaseManifest(
            version=request.version,
            checksum=request.checksum,
            notes=request.notes,
            is_active=request.is_active,
            created_by_user_id=ctx.user_id,
            updated_by_user_id=ctx.user_id,
        )
        # Set platforms using the property setter (normalizes to lowercase)
        manifest.platforms = request.platforms

        db.add(manifest)
        db.flush()  # Flush to get manifest.id for FK references

        # Create per-platform artifacts if provided (Issue #136)
        if request.artifacts:
            # Validate: no duplicate platforms in artifacts
            artifact_platforms = [a.platform.lower().strip() for a in request.artifacts]
            duplicate_platforms = [
                p for p in artifact_platforms if artifact_platforms.count(p) > 1
            ]
            if duplicate_platforms:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Duplicate artifact platforms: {', '.join(set(duplicate_platforms))}",
                )

            # Validate: every artifact platform must be in manifest platforms
            manifest_platforms = {p.lower().strip() for p in request.platforms}
            invalid_platforms = [
                p for p in artifact_platforms if p not in manifest_platforms
            ]
            if invalid_platforms:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Artifact platforms not in manifest platforms: {', '.join(invalid_platforms)}",
                )

            for art_req in request.artifacts:
                artifact = ReleaseArtifact(
                    manifest_id=manifest.id,
                    platform=art_req.platform,
                    filename=art_req.filename,
                    checksum=art_req.checksum,
                    file_size=art_req.file_size,
                )
                db.add(artifact)

            # Validate binary files exist in dist dir when configured (Issue #136)
            settings = get_settings()
            if settings.agent_dist_configured and request.is_active:
                missing_files = []
                for art_req in request.artifacts:
                    file_path, error = resolve_binary_path(
                        dist_dir=settings.agent_dist_dir,
                        version=request.version,
                        filename=art_req.filename,
                    )
                    if error:
                        missing_files.append(f"{art_req.platform}: {art_req.filename} ({error})")

                if missing_files:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Binary files not found in {settings.agent_dist_dir}/{request.version}/. "
                            f"Missing: {'; '.join(missing_files)}. "
                            f"Either deploy the files first, or set is_active=false to create an inactive manifest."
                        ),
                    )

        # Auto-cleanup old manifests for each platform (Issue #240)
        # Run cleanup before commit so both creation and cleanup are atomic.
        cleanup_old_manifests(db, manifest.platforms)

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
                "platforms": manifest.platforms,
                "is_active": manifest.is_active,
            }
        )

        return manifest_to_response(manifest)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ReleaseManifestListResponse)
async def list_release_manifests(
    active_only: bool = Query(False, description="Only return active manifests"),
    platform: Optional[str] = Query(None, description="Filter by platform (manifests containing this platform)"),
    version: Optional[str] = Query(None, description="Filter by version"),
    latest_only: bool = Query(False, description="Only return the most recent manifest per version string"),
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    List all release manifests.

    **Requires super admin privileges.**

    Query parameters:
    - **active_only**: If true, only return active manifests
    - **platform**: Filter by platform (returns manifests that support this platform)
    - **version**: Filter by version string
    - **latest_only**: If true, only return the most recent manifest per version
    """
    query = db.query(ReleaseManifest)

    if active_only:
        query = query.filter(ReleaseManifest.is_active == True)

    if version:
        query = query.filter(ReleaseManifest.version == version)

    # Sort by created_at DESC (not version) because lexicographic string sort
    # is incorrect for semver (e.g., "9.0.0" > "10.0.0").
    manifests = query.order_by(
        ReleaseManifest.created_at.desc(),
    ).all()

    # Filter by platform in Python since JSON array filtering is dialect-specific
    if platform:
        platform_lower = platform.lower()
        manifests = [m for m in manifests if m.supports_platform(platform_lower)]

    # Deduplicate: keep only the most recent manifest per version string.
    # Since results are already sorted by created_at DESC, the first occurrence
    # of each version is the newest.
    if latest_only:
        seen_versions: dict[str, bool] = {}
        deduplicated = []
        for m in manifests:
            if m.version not in seen_versions:
                seen_versions[m.version] = True
                deduplicated.append(m)
        manifests = deduplicated

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

    # Get unique versions
    versions = [
        row[0] for row in
        db.query(ReleaseManifest.version).distinct().order_by(ReleaseManifest.version.desc()).all()
    ]

    # Get unique platforms by iterating through all manifests
    # (JSON array aggregation is dialect-specific, so we do it in Python)
    all_manifests = db.query(ReleaseManifest).all()
    platforms_set: set[str] = set()
    for manifest in all_manifests:
        platforms_set.update(manifest.platforms)
    platforms = sorted(platforms_set)

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
        # Validate binary files exist when activating a manifest with artifacts
        settings = get_settings()
        if request.is_active and settings.agent_dist_configured and manifest.artifacts:
            missing_files = []
            for artifact in manifest.artifacts:
                file_path, error = resolve_binary_path(
                    dist_dir=settings.agent_dist_dir,
                    version=manifest.version,
                    filename=artifact.filename,
                )
                if error:
                    missing_files.append(f"{artifact.platform}: {artifact.filename} ({error})")

            if missing_files:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Cannot activate: binary files not found in {settings.agent_dist_dir}/{manifest.version}/. "
                        f"Missing: {'; '.join(missing_files)}. "
                        f"Deploy the files before activating the manifest."
                    ),
                )

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
                    "platforms": manifest.platforms,
                }
            )

    if request.notes is not None:
        manifest.notes = request.notes

    manifest.updated_by_user_id = ctx.user_id

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
            "platforms": manifest.platforms,
            "checksum": manifest.checksum,
        }
    )

    db.delete(manifest)
    db.commit()

    return None
