"""
Team service for managing teams (tenants).

Provides business logic for creating and retrieving teams with validation.
Teams represent tenancy boundaries - all data in the system belongs to exactly
one Team for complete data isolation.

Design:
- Team names must be unique
- Slugs are auto-generated from names
- Teams cannot be hard-deleted (use is_active=false)
- First team creation is handled by seed_first_team.py script
"""

from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from backend.src.models import Team
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService


logger = get_logger("services")


class TeamService:
    """
    Service for managing teams.

    Handles team creation, retrieval, and updates with automatic validation
    and slug generation.

    Usage:
        >>> service = TeamService(db_session)
        >>> team = service.create(name="My Photo Team")
        >>> print(team.guid)  # ten_01hgw2bbg...
    """

    def __init__(self, db: Session):
        """
        Initialize team service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        name: str,
        slug: Optional[str] = None,
        is_active: bool = True,
        settings: Optional[dict] = None,
    ) -> Team:
        """
        Create a new team.

        Args:
            name: Team display name (must be unique)
            slug: URL-safe identifier (auto-generated from name if not provided)
            is_active: Whether team is active (default: True)
            settings: Optional team settings dictionary

        Returns:
            Created Team instance

        Raises:
            ConflictError: If name or slug already exists
            ValidationError: If name is empty or too long
        """
        # Validate name
        if not name or not name.strip():
            raise ValidationError("Team name cannot be empty", field="name")

        name = name.strip()
        if len(name) > 255:
            raise ValidationError(
                "Team name cannot exceed 255 characters", field="name"
            )

        # Generate slug if not provided
        if not slug:
            slug = Team.generate_slug(name)

        if not slug:
            raise ValidationError(
                "Could not generate valid slug from team name", field="name"
            )

        # Check for existing team with same name (case-insensitive)
        existing_name = (
            self.db.query(Team)
            .filter(func.lower(Team.name) == func.lower(name))
            .first()
        )
        if existing_name:
            raise ConflictError(f"Team with name '{name}' already exists")

        # Check for existing team with same slug
        existing_slug = (
            self.db.query(Team)
            .filter(Team.slug == slug)
            .first()
        )
        if existing_slug:
            raise ConflictError(f"Team with slug '{slug}' already exists")

        try:
            import json
            team = Team(
                name=name,
                slug=slug,
                is_active=is_active,
                settings_json=json.dumps(settings) if settings else None,
            )
            self.db.add(team)
            self.db.commit()
            self.db.refresh(team)

            logger.info(f"Created team: {team.name} ({team.guid})")
            return team

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create team '{name}': {e}")
            raise ConflictError(f"Team with name '{name}' or slug '{slug}' already exists")

    def get_by_guid(self, guid: str) -> Team:
        """
        Get a team by GUID.

        Args:
            guid: Team GUID (ten_xxx format)

        Returns:
            Team instance

        Raises:
            NotFoundError: If team not found
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "ten"):
            raise NotFoundError("Team", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "ten")
        except ValueError:
            raise NotFoundError("Team", guid)

        team = self.db.query(Team).filter(Team.uuid == uuid_value).first()
        if not team:
            raise NotFoundError("Team", guid)

        return team

    def get_by_id(self, team_id: int) -> Team:
        """
        Get a team by internal ID.

        Args:
            team_id: Internal database ID

        Returns:
            Team instance

        Raises:
            NotFoundError: If team not found
        """
        team = self.db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundError("Team", team_id)
        return team

    def get_by_slug(self, slug: str) -> Team:
        """
        Get a team by slug.

        Args:
            slug: Team slug (URL-safe identifier)

        Returns:
            Team instance

        Raises:
            NotFoundError: If team not found
        """
        team = self.db.query(Team).filter(Team.slug == slug).first()
        if not team:
            raise NotFoundError("Team", slug)
        return team

    def get_by_name(self, name: str) -> Optional[Team]:
        """
        Get a team by name (case-insensitive).

        Args:
            name: Team name

        Returns:
            Team instance or None if not found
        """
        return (
            self.db.query(Team)
            .filter(func.lower(Team.name) == func.lower(name))
            .first()
        )

    def list(
        self,
        active_only: bool = False,
    ) -> List[Team]:
        """
        List all teams.

        Args:
            active_only: If True, only return active teams

        Returns:
            List of Team instances
        """
        query = self.db.query(Team)

        if active_only:
            query = query.filter(Team.is_active == True)

        return query.order_by(Team.name.asc()).all()

    def update(
        self,
        guid: str,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        settings: Optional[dict] = None,
    ) -> Team:
        """
        Update an existing team.

        Args:
            guid: Team GUID
            name: New name (optional)
            is_active: New active status (optional)
            settings: New settings dictionary (optional)

        Returns:
            Updated Team instance

        Raises:
            NotFoundError: If team not found
            ConflictError: If new name conflicts with existing
            ValidationError: If name is invalid
        """
        team = self.get_by_guid(guid)

        # Validate and update name
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("Team name cannot be empty", field="name")
            if len(name) > 255:
                raise ValidationError(
                    "Team name cannot exceed 255 characters", field="name"
                )

            # Check for name conflict (case-insensitive)
            if name.lower() != team.name.lower():
                existing = (
                    self.db.query(Team)
                    .filter(func.lower(Team.name) == func.lower(name))
                    .filter(Team.id != team.id)
                    .first()
                )
                if existing:
                    raise ConflictError(f"Team with name '{name}' already exists")

            team.name = name
            # Regenerate slug when name changes
            team.slug = Team.generate_slug(name)

        if is_active is not None:
            team.is_active = is_active

        if settings is not None:
            import json
            team.settings_json = json.dumps(settings)

        try:
            self.db.commit()
            self.db.refresh(team)
            logger.info(f"Updated team: {team.name} ({team.guid})")
            return team

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update team {guid}: {e}")
            raise ConflictError(f"Team update failed due to conflict")

    def deactivate(self, guid: str) -> Team:
        """
        Deactivate a team.

        Deactivating a team prevents all members from logging in.

        Args:
            guid: Team GUID

        Returns:
            Updated Team instance

        Raises:
            NotFoundError: If team not found
        """
        return self.update(guid, is_active=False)

    def activate(self, guid: str) -> Team:
        """
        Activate a team.

        Args:
            guid: Team GUID

        Returns:
            Updated Team instance

        Raises:
            NotFoundError: If team not found
        """
        return self.update(guid, is_active=True)

    def count(self) -> int:
        """
        Get total team count.

        Returns:
            Number of teams
        """
        return self.db.query(func.count(Team.id)).scalar()

    def get_first(self) -> Optional[Team]:
        """
        Get the first team (by ID).

        Used by migration scripts to find the default team.

        Returns:
            First Team instance or None if no teams exist
        """
        return self.db.query(Team).order_by(Team.id.asc()).first()
