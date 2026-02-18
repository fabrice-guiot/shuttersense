"""
Manifest cleanup service for automatic lifecycle management of release manifests.

Issue #240: When a new release manifest is created, old per-platform manifests
are automatically deactivated and deleted. For each platform in the new manifest,
we keep the N most recent manifests and remove the rest (including CASCADE to
release_artifacts).

Design:
- Triggered after successful manifest creation via admin API
- Per-platform cleanup: each platform is cleaned up independently
- Multi-platform manifests count for every platform they list
- Retention count is a named constant for easy adjustment
- Deactivation + deletion logged per manifest
"""

from typing import List

from sqlalchemy.orm import Session

from backend.src.models.release_manifest import ReleaseManifest
from backend.src.utils.logging_config import get_logger

logger = get_logger("services")

# Number of manifests to retain per platform (current + N-1 previous).
# Setting this to 3 means we keep the latest 3 and remove the rest.
MANIFEST_RETENTION_COUNT = 3


def cleanup_old_manifests_for_platform(
    db: Session,
    platform: str,
) -> int:
    """Clean up old manifests for a single platform.

    Finds all manifests that list the given platform, orders them by
    created_at DESC, keeps the first MANIFEST_RETENTION_COUNT,
    and deactivates + deletes the rest (CASCADE removes artifacts).
    Both active and inactive manifests count toward the retention window.

    Args:
        db: Database session (caller is responsible for committing).
        platform: Platform string to clean up (e.g., "darwin-arm64").

    Returns:
        Number of manifests removed.
    """
    platform_lower = platform.lower()

    # Fetch all manifests ordered by created_at DESC so the newest come first.
    # We use created_at (not version) because lexicographic string sort is
    # incorrect for semver (e.g., "9.0.0" > "10.0.0").
    # Platform matching is done in Python since platforms_json is
    # JSONB on PostgreSQL and TEXT on SQLite.
    all_manifests: List[ReleaseManifest] = (
        db.query(ReleaseManifest)
        .order_by(ReleaseManifest.created_at.desc())
        .all()
    )

    # Filter to manifests supporting this platform
    matching = [m for m in all_manifests if m.supports_platform(platform_lower)]

    if len(matching) <= MANIFEST_RETENTION_COUNT:
        return 0

    # The ones to remove are everything after the retention window
    to_remove = matching[MANIFEST_RETENTION_COUNT:]
    removed_count = 0

    for manifest in to_remove:
        logger.info(
            "Manifest cleanup: deactivating and deleting manifest",
            extra={
                "event": "manifest_cleanup.delete",
                "manifest_guid": manifest.guid,
                "version": manifest.version,
                "platforms": manifest.platforms,
                "platform_trigger": platform_lower,
            },
        )
        # Deactivate first (in case delete fails, at least it's inactive)
        manifest.is_active = False
        db.delete(manifest)
        removed_count += 1

    return removed_count


def cleanup_old_manifests(db: Session, platforms: List[str]) -> int:
    """Clean up old manifests for all given platforms.

    Called after a new manifest is created. Iterates over each platform
    in the new manifest and removes excess old manifests.

    Args:
        db: Database session. The function flushes deletions but does
            NOT commit — the caller should commit as part of the
            broader transaction.
        platforms: List of platform strings from the newly created manifest.

    Returns:
        Total number of manifests removed across all platforms.
    """
    total_removed = 0

    for platform in platforms:
        removed = cleanup_old_manifests_for_platform(db, platform)
        total_removed += removed

    if total_removed > 0:
        logger.info(
            "Manifest cleanup summary",
            extra={
                "event": "manifest_cleanup.summary",
                "platforms": platforms,
                "total_removed": total_removed,
            },
        )

    return total_removed
