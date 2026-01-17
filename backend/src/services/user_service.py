"""
User service for managing authenticated users.

Provides business logic for creating, retrieving, and managing users
with validation and team association.

Design:
- Users are pre-provisioned by admins before OAuth login
- Email is globally unique across ALL teams
- User status tracks lifecycle (pending→active→deactivated)
- OAuth profile data synced on each login
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from backend.src.models import User, UserStatus, UserType, Team
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService


logger = get_logger("services")


class UserService:
    """
    Service for managing users.

    Handles user creation, retrieval, updates, and OAuth profile syncing
    with validation and team membership enforcement.

    Usage:
        >>> service = UserService(db_session)
        >>> user = service.create(
        ...     team_id=1,
        ...     email="user@example.com",
        ...     first_name="John",
        ...     last_name="Doe"
        ... )
        >>> print(user.guid)  # usr_01hgw2bbg...
    """

    def __init__(self, db: Session):
        """
        Initialize user service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        team_id: int,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
        is_active: bool = True,
        status: UserStatus = UserStatus.PENDING,
    ) -> User:
        """
        Create a new user (pre-provision).

        Args:
            team_id: ID of the team this user belongs to
            email: User's email address (must be globally unique)
            first_name: User's first name (optional)
            last_name: User's last name (optional)
            display_name: Display name (optional)
            is_active: Whether user is active (default: True)
            status: Initial user status (default: PENDING)

        Returns:
            Created User instance

        Raises:
            NotFoundError: If team not found
            ConflictError: If email already exists
            ValidationError: If email format is invalid
        """
        # Validate email
        if not email or not email.strip():
            raise ValidationError("Email cannot be empty", field="email")

        email = email.strip().lower()
        if not self._is_valid_email(email):
            raise ValidationError(
                f"Invalid email format: {email}", field="email"
            )

        if len(email) > 255:
            raise ValidationError(
                "Email cannot exceed 255 characters", field="email"
            )

        # Verify team exists
        team = self.db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundError("Team", team_id)

        # Check for existing user with same email (globally unique)
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise ConflictError(f"User with email '{email}' already exists")

        # Validate name lengths
        if first_name and len(first_name) > 100:
            raise ValidationError(
                "First name cannot exceed 100 characters", field="first_name"
            )
        if last_name and len(last_name) > 100:
            raise ValidationError(
                "Last name cannot exceed 100 characters", field="last_name"
            )
        if display_name and len(display_name) > 255:
            raise ValidationError(
                "Display name cannot exceed 255 characters", field="display_name"
            )

        try:
            user = User(
                team_id=team_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                display_name=display_name,
                is_active=is_active,
                status=status,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Created user: {user.email} ({user.guid}) in team {team.name}")
            return user

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create user '{email}': {e}")
            raise ConflictError(f"User with email '{email}' already exists")

    def get_by_guid(self, guid: str) -> User:
        """
        Get a user by GUID.

        Args:
            guid: User GUID (usr_xxx format)

        Returns:
            User instance

        Raises:
            NotFoundError: If user not found
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "usr"):
            raise NotFoundError("User", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "usr")
        except ValueError:
            raise NotFoundError("User", guid)

        user = self.db.query(User).filter(User.uuid == uuid_value).first()
        if not user:
            raise NotFoundError("User", guid)

        return user

    def get_by_id(self, user_id: int) -> User:
        """
        Get a user by internal ID.

        Args:
            user_id: Internal database ID

        Returns:
            User instance

        Raises:
            NotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("User", user_id)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            email: User's email address (case-insensitive)

        Returns:
            User instance or None if not found
        """
        if not email:
            return None
        return (
            self.db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        )

    def get_by_oauth_subject(self, oauth_subject: str) -> Optional[User]:
        """
        Get a user by OAuth subject claim.

        Args:
            oauth_subject: OAuth provider's sub claim

        Returns:
            User instance or None if not found
        """
        if not oauth_subject:
            return None
        return (
            self.db.query(User)
            .filter(User.oauth_subject == oauth_subject)
            .first()
        )

    def list_by_team(
        self,
        team_id: int,
        active_only: bool = False,
        status_filter: Optional[UserStatus] = None,
        include_system_users: bool = False,
    ) -> List[User]:
        """
        List all users in a team.

        Args:
            team_id: Team ID to filter by
            active_only: If True, only return active users
            status_filter: Filter by specific status (optional)
            include_system_users: If False (default), exclude system users

        Returns:
            List of User instances
        """
        query = self.db.query(User).filter(User.team_id == team_id)

        # By default, exclude system users (they are for API tokens)
        if not include_system_users:
            query = query.filter(User.user_type == UserType.HUMAN)

        if active_only:
            query = query.filter(User.is_active == True)

        if status_filter:
            query = query.filter(User.status == status_filter)

        return query.order_by(User.email.asc()).all()

    def update(
        self,
        guid: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        status: Optional[UserStatus] = None,
    ) -> User:
        """
        Update an existing user.

        Args:
            guid: User GUID
            first_name: New first name (optional)
            last_name: New last name (optional)
            display_name: New display name (optional)
            is_active: New active status (optional)
            status: New user status (optional)

        Returns:
            Updated User instance

        Raises:
            NotFoundError: If user not found
            ValidationError: If field values are invalid
        """
        user = self.get_by_guid(guid)

        # Validate and update fields
        if first_name is not None:
            if first_name and len(first_name) > 100:
                raise ValidationError(
                    "First name cannot exceed 100 characters", field="first_name"
                )
            user.first_name = first_name or None

        if last_name is not None:
            if last_name and len(last_name) > 100:
                raise ValidationError(
                    "Last name cannot exceed 100 characters", field="last_name"
                )
            user.last_name = last_name or None

        if display_name is not None:
            if display_name and len(display_name) > 255:
                raise ValidationError(
                    "Display name cannot exceed 255 characters", field="display_name"
                )
            user.display_name = display_name or None

        if is_active is not None:
            user.is_active = is_active

        if status is not None:
            user.status = status

        self.db.commit()
        self.db.refresh(user)
        logger.info(f"Updated user: {user.email} ({user.guid})")
        return user

    def update_oauth_profile(
        self,
        user: User,
        provider: str,
        oauth_subject: str,
        display_name: Optional[str] = None,
        picture_url: Optional[str] = None,
    ) -> User:
        """
        Update user's OAuth profile data after successful login.

        Called by AuthService during OAuth callback to sync profile info.

        Args:
            user: User instance to update
            provider: OAuth provider name (google, microsoft)
            oauth_subject: OAuth sub claim (immutable identifier)
            display_name: Display name from OAuth profile
            picture_url: Profile picture URL from OAuth profile

        Returns:
            Updated User instance
        """
        user.oauth_provider = provider
        user.oauth_subject = oauth_subject
        user.last_login_at = datetime.utcnow()

        # Sync profile data if provided
        if display_name:
            user.display_name = display_name[:255]
        if picture_url:
            user.picture_url = picture_url  # Text column, no length limit

        # Transition from PENDING to ACTIVE on first login
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE
            logger.info(f"User {user.email} activated on first login")

        self.db.commit()
        self.db.refresh(user)
        logger.info(f"Updated OAuth profile for user: {user.email}")
        return user

    def deactivate(self, guid: str) -> User:
        """
        Deactivate a user.

        Deactivating a user prevents them from logging in.

        Args:
            guid: User GUID

        Returns:
            Updated User instance

        Raises:
            NotFoundError: If user not found
        """
        return self.update(guid, is_active=False, status=UserStatus.DEACTIVATED)

    def activate(self, guid: str) -> User:
        """
        Activate a user.

        Args:
            guid: User GUID

        Returns:
            Updated User instance

        Raises:
            NotFoundError: If user not found
        """
        user = self.get_by_guid(guid)
        # Determine new status based on whether user has ever logged in
        new_status = UserStatus.ACTIVE if user.last_login_at else UserStatus.PENDING
        return self.update(guid, is_active=True, status=new_status)

    def count_by_team(self, team_id: int, include_system_users: bool = False) -> int:
        """
        Get user count for a team.

        Args:
            team_id: Team ID
            include_system_users: If False (default), exclude system users

        Returns:
            Number of users in the team
        """
        query = (
            self.db.query(func.count(User.id))
            .filter(User.team_id == team_id)
        )

        if not include_system_users:
            query = query.filter(User.user_type == UserType.HUMAN)

        return query.scalar()

    def invite(self, team_id: int, email: str) -> User:
        """
        Invite a user by email (pre-provisioning).

        Creates a pending user in the specified team. The user will be
        activated on their first OAuth login.

        This is the preferred method for user creation as it enforces
        the pre-provisioning workflow.

        Args:
            team_id: ID of the team to invite user to
            email: User's email address (must be globally unique)

        Returns:
            Created User instance with PENDING status

        Raises:
            NotFoundError: If team not found
            ConflictError: If email already exists (globally)
            ValidationError: If email format is invalid
        """
        return self.create(
            team_id=team_id,
            email=email,
            status=UserStatus.PENDING,
            is_active=True,
        )

    def delete_pending(self, guid: str) -> None:
        """
        Delete a pending user invitation.

        Only users with PENDING status can be deleted. Active and
        deactivated users cannot be deleted (to preserve history).

        Args:
            guid: User GUID to delete

        Raises:
            NotFoundError: If user not found
            ValidationError: If user is not in PENDING status
        """
        user = self.get_by_guid(guid)

        if user.status != UserStatus.PENDING:
            raise ValidationError(
                f"Only pending users can be deleted. User status is: {user.status.value}",
                field="status"
            )

        email = user.email
        self.db.delete(user)
        self.db.commit()
        logger.info(f"Deleted pending user: {email} ({guid})")

    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.

        Basic validation - checks for @ and domain.

        Args:
            email: Email to validate

        Returns:
            True if valid email format
        """
        if not email or "@" not in email:
            return False

        local, domain = email.rsplit("@", 1)
        if not local or not domain:
            return False

        if "." not in domain:
            return False

        return True
