#!/usr/bin/env python3
"""
Seed the first team and admin user for initial deployment.

This script creates the first team and admin user, enabling OAuth login
for the initial administrator. It is idempotent - running it multiple
times will not create duplicate entries.

Usage:
    python -m backend.src.scripts.seed_first_team --team-name "My Team" --admin-email "admin@example.com"

Options:
    --team-name     Name for the first team (required)
    --admin-email   Email address for the admin user (required)
    --help          Show this help message

Examples:
    # Create team and admin with specified details
    python -m backend.src.scripts.seed_first_team \\
        --team-name "Acme Photography" \\
        --admin-email "admin@acme.com"

    # Short form
    python -m backend.src.scripts.seed_first_team -t "My Team" -e "me@example.com"

The script will output the GUIDs of created resources for configuration reference.
"""

import argparse
import signal
import sys
from typing import Optional

# Flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle CTRL+C gracefully."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\nOperation interrupted by user.")
    sys.exit(130)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Seed the first team and admin user for ShutterSense.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --team-name "Acme Photography" --admin-email "admin@acme.com"
  %(prog)s -t "My Team" -e "me@example.com"

Notes:
  - This script is idempotent; running it multiple times is safe
  - The admin user will be created in PENDING status until first OAuth login
  - GUIDs are printed for reference in configuration files
        """
    )

    parser.add_argument(
        "-t", "--team-name",
        required=True,
        help="Name for the first team"
    )
    parser.add_argument(
        "-e", "--admin-email",
        required=True,
        help="Email address for the admin user"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes"
    )

    return parser.parse_args()


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email or "@" not in email:
        return False
    local, domain = email.rsplit("@", 1)
    return bool(local and domain and "." in domain)


def _has_audit_columns(db) -> bool:
    """Check if the teams table has audit columns (added in migration 058)."""
    from sqlalchemy import text
    try:
        result = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'teams' AND column_name = 'created_by_user_id'"
        ))
        return result.fetchone() is not None
    except Exception:
        return False


def _create_team_raw_sql(db, team_name: str) -> tuple[int, str, str, bool]:
    """
    Create or find a team using raw SQL (for pre-audit-column migrations).

    Returns:
        Tuple of (team_id, team_guid, team_slug, was_created)
    """
    from sqlalchemy import text
    from backend.src.services.guid import GuidService

    # Check if team already exists
    result = db.execute(
        text("SELECT id, uuid, slug FROM teams WHERE lower(name) = lower(:name) LIMIT 1"),
        {"name": team_name}
    )
    row = result.fetchone()

    if row:
        # Return existing team with GUID format
        team_guid = GuidService.encode_uuid(row[1], "ten")
        return row[0], team_guid, row[2], False

    # Create new team - generate raw UUID (not prefixed GUID)
    team_uuid = GuidService.generate_uuid()
    slug = team_name.lower().replace(" ", "-").replace("'", "")[:50]

    # Check for slug collision
    slug_result = db.execute(
        text("SELECT COUNT(*) FROM teams WHERE slug = :slug"),
        {"slug": slug}
    )
    if slug_result.scalar() > 0:
        # Add random suffix
        import secrets
        slug = f"{slug[:42]}-{secrets.token_hex(3)}"

    db.execute(
        text(
            "INSERT INTO teams (name, slug, uuid, is_active, created_at, updated_at) "
            "VALUES (:name, :slug, :uuid, true, now(), now())"
        ),
        {"name": team_name, "slug": slug, "uuid": str(team_uuid)}
    )
    db.commit()

    # Fetch the created team
    result = db.execute(
        text("SELECT id FROM teams WHERE uuid = :uuid"),
        {"uuid": str(team_uuid)}
    )
    row = result.fetchone()
    team_guid = GuidService.encode_uuid(team_uuid, "ten")
    return row[0], team_guid, slug, True


def _create_user_raw_sql(db, team_id: int, email: str) -> tuple[str, str, int, bool]:
    """
    Create or find a user using raw SQL (for pre-audit-column migrations).

    Returns:
        Tuple of (user_guid, status, user_team_id, was_created)
    """
    from sqlalchemy import text
    from backend.src.services.guid import GuidService

    # Check if user already exists
    result = db.execute(
        text("SELECT uuid, status, team_id FROM users WHERE lower(email) = lower(:email) LIMIT 1"),
        {"email": email}
    )
    row = result.fetchone()

    if row:
        # Return existing user with GUID format
        user_guid = GuidService.encode_uuid(row[0], "usr")
        return user_guid, row[1], row[2], False

    # Create new user - generate raw UUID (not prefixed GUID)
    user_uuid = GuidService.generate_uuid()

    db.execute(
        text(
            "INSERT INTO users (email, uuid, team_id, status, created_at, updated_at) "
            "VALUES (:email, :uuid, :team_id, 'PENDING', now(), now())"
        ),
        {"email": email, "uuid": str(user_uuid), "team_id": team_id}
    )
    db.commit()

    user_guid = GuidService.encode_uuid(user_uuid, "usr")
    return user_guid, "PENDING", team_id, True


def _get_user_team_name_raw_sql(db, team_id: int) -> str:
    """Get team name by ID using raw SQL."""
    from sqlalchemy import text
    result = db.execute(
        text("SELECT name FROM teams WHERE id = :team_id"),
        {"team_id": team_id}
    )
    row = result.fetchone()
    return row[0] if row else "N/A"


def seed_first_team(
    team_name: str,
    admin_email: str,
    dry_run: bool = False
) -> tuple[Optional[str], Optional[str]]:
    """
    Create the first team and admin user.

    Args:
        team_name: Name for the team
        admin_email: Email for the admin user
        dry_run: If True, only show what would be created

    Returns:
        Tuple of (team_guid, user_guid) or (None, None) on error
    """
    # Import here to avoid loading database during argument parsing
    from backend.src.db.database import SessionLocal
    from backend.src.services.team_service import TeamService
    from backend.src.services.user_service import UserService
    from backend.src.services.seed_data_service import SeedDataService
    from backend.src.services.exceptions import ConflictError, ValidationError, NotFoundError

    if dry_run:
        print("\n[DRY RUN] Would create:")
        print(f"  Team: {team_name}")
        print(f"  Admin: {admin_email}")
        print(f"  Default categories: 7")
        print(f"  Default event statuses: 4")
        print("\nNo changes made.")
        return None, None

    db = SessionLocal()
    try:
        # Check if we can use ORM (audit columns exist) or need raw SQL
        use_orm = _has_audit_columns(db)

        if use_orm:
            team_service = TeamService(db)
        user_service = UserService(db)
        seed_service = SeedDataService(db)

        team_guid = None
        user_guid = None
        team_created = False
        user_created = False

        # Check for shutdown between operations
        if _shutdown_requested:
            return None, None

        # Create or find team
        if use_orm:
            # Normal ORM path (audit columns exist)
            existing_team = team_service.get_by_name(team_name)
            if existing_team:
                print(f"\n[EXISTS] Team '{team_name}' already exists")
                print(f"  GUID: {existing_team.guid}")
                team_guid = existing_team.guid
                team_id = existing_team.id
            else:
                try:
                    team = team_service.create(name=team_name)
                    print(f"\n[CREATED] Team: {team.name}")
                    print(f"  GUID: {team.guid}")
                    print(f"  Slug: {team.slug}")
                    team_guid = team.guid
                    team_id = team.id
                    team_created = True
                except (ConflictError, ValidationError) as e:
                    print(f"\n[ERROR] Failed to create team: {e}")
                    return None, None
        else:
            # Raw SQL path (pre-audit migration, e.g., migration 030)
            print("\n[INFO] Using raw SQL (audit columns not yet migrated)")
            team_id, team_guid, team_slug, team_created = _create_team_raw_sql(db, team_name)
            if team_created:
                print(f"\n[CREATED] Team: {team_name}")
                print(f"  GUID: {team_guid}")
                print(f"  Slug: {team_slug}")
            else:
                print(f"\n[EXISTS] Team '{team_name}' already exists")
                print(f"  GUID: {team_guid}")

        if _shutdown_requested:
            return team_guid, None

        # Migrate any orphaned data from pre-tenancy migrations
        # Cast team_id to int to satisfy type checker (may be Column[int] from ORM)
        team_id_int = int(team_id)
        orphaned_summary = seed_service.get_orphaned_data_summary()
        if orphaned_summary['orphaned_categories'] > 0 or orphaned_summary['orphaned_configurations'] > 0:
            cats_migrated, configs_migrated = seed_service.migrate_orphaned_data(team_id_int)
            if cats_migrated > 0 or configs_migrated > 0:
                print(f"\n[MIGRATED] Orphaned data assigned to team")
                print(f"  Categories: {cats_migrated}")
                print(f"  Configurations: {configs_migrated}")

        if _shutdown_requested:
            return team_guid, None

        # Seed default data for the team (categories, event statuses, TTL configs)
        categories_created, statuses_created, ttl_configs_created = seed_service.seed_team_defaults(team_id_int)
        total_configs = statuses_created + ttl_configs_created
        if categories_created > 0 or total_configs > 0:
            print(f"\n[SEEDED] Default data for team")
            print(f"  Categories: {categories_created}")
            print(f"  Event statuses: {statuses_created}")
            print(f"  TTL configs: {ttl_configs_created}")
        else:
            # Check if already seeded
            summary = seed_service.get_seed_summary(team_id_int)
            if summary['categories'] > 0 or summary['event_statuses'] > 0:
                print(f"\n[EXISTS] Default data already seeded")
                print(f"  Categories: {summary['categories']}")
                print(f"  Event statuses: {summary['event_statuses']}")

        if _shutdown_requested:
            return team_guid, None

        # Create or find user
        if use_orm:
            # Normal ORM path (audit columns exist)
            existing_user = user_service.get_by_email(admin_email)
            if existing_user:
                print(f"\n[EXISTS] User '{admin_email}' already exists")
                print(f"  GUID: {existing_user.guid}")
                print(f"  Team: {existing_user.team.name if existing_user.team else 'N/A'}")
                user_guid = existing_user.guid

                # Warn if user is in a different team
                if existing_user.team_id != team_id:
                    print(f"\n[WARNING] User is in a different team!")
                    print(f"  Expected team: {team_name}")
                    print(f"  Actual team: {existing_user.team.name if existing_user.team else 'N/A'}")
            else:
                try:
                    user = user_service.create(
                        team_id=int(team_id),
                        email=admin_email,
                    )
                    print(f"\n[CREATED] User: {user.email}")
                    print(f"  GUID: {user.guid}")
                    print(f"  Status: {user.status.value}")
                    user_guid = user.guid
                    user_created = True
                except (ConflictError, ValidationError) as e:
                    print(f"\n[ERROR] Failed to create user: {e}")
                    return team_guid, None
        else:
            # Raw SQL path (pre-audit migration)
            user_guid, user_status, user_team_id, user_created = _create_user_raw_sql(
                db, int(team_id), admin_email
            )
            if user_created:
                print(f"\n[CREATED] User: {admin_email}")
                print(f"  GUID: {user_guid}")
                print(f"  Status: {user_status}")
            else:
                print(f"\n[EXISTS] User '{admin_email}' already exists")
                print(f"  GUID: {user_guid}")

                # Warn if user is in a different team
                if user_team_id != team_id:
                    user_team_name = _get_user_team_name_raw_sql(db, user_team_id)
                    print(f"\n[WARNING] User is in a different team!")
                    print(f"  Expected team: {team_name}")
                    print(f"  Actual team: {user_team_name}")

        # Summary
        print("\n" + "=" * 50)
        if team_created or user_created:
            print("SEED COMPLETE")
        else:
            print("ALREADY SEEDED")

        print(f"\nTeam GUID:  {team_guid}")
        print(f"Admin GUID: {user_guid}")

        if user_created:
            print(f"\nNext steps:")
            print(f"  1. Configure OAuth providers in .env")
            print(f"  2. Start the server")
            print(f"  3. Login with {admin_email} via OAuth")

        return team_guid, user_guid

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        db.rollback()
        return None, None
    finally:
        db.close()


def main():
    """Main entry point."""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_args()

    # Validate inputs
    if not args.team_name.strip():
        print("Error: Team name cannot be empty")
        sys.exit(1)

    if not validate_email(args.admin_email):
        print(f"Error: Invalid email format: {args.admin_email}")
        sys.exit(1)

    print("=" * 50)
    print("ShutterSense: First Team Seed Script")
    print("=" * 50)

    team_guid, user_guid = seed_first_team(
        team_name=args.team_name.strip(),
        admin_email=args.admin_email.strip().lower(),
        dry_run=args.dry_run,
    )

    if args.dry_run:
        sys.exit(0)

    if team_guid and user_guid:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
