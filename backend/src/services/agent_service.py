"""
Agent service for agent lifecycle management.

Handles the business logic for:
- Agent registration via one-time tokens
- Heartbeat processing and status updates
- SYSTEM user creation for audit trail
- Agent revocation and cleanup
- Offline detection and job release

Security:
- API keys are hashed (never stored in plaintext)
- Registration tokens are single-use
- Agents are scoped to teams
"""

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.src.models import (
    Agent, AgentStatus,
    AgentRegistrationToken,
    User, UserStatus, UserType,
    Team,
    Job, JobStatus,
)
from backend.src.models.agent_registration_token import DEFAULT_TOKEN_EXPIRATION_HOURS
from backend.src.services.exceptions import NotFoundError, ValidationError, ConflictError
from backend.src.utils.logging_config import get_logger


logger = get_logger("agent")


# Configuration constants
HEARTBEAT_TIMEOUT_SECONDS = 90  # Agent is offline after 90 seconds without heartbeat
API_KEY_PREFIX = "agt_key_"
API_KEY_LENGTH = 48  # Total length including prefix


@dataclass
class RegistrationResult:
    """
    Result of agent registration.

    Attributes:
        agent: The registered agent
        api_key: The plaintext API key (only returned once)
    """
    agent: Agent
    api_key: str


@dataclass
class TokenGenerationResult:
    """
    Result of token generation.

    Attributes:
        token: The registration token entity
        plaintext_token: The plaintext token (only returned once)
    """
    token: AgentRegistrationToken
    plaintext_token: str


class AgentService:
    """
    Service for managing agent lifecycle.

    Handles agent registration, heartbeat processing, status management,
    and SYSTEM user creation for audit trail purposes.

    Usage:
        >>> service = AgentService(db_session)
        >>> result = service.register_agent(
        ...     token="art_xxxxx...",
        ...     name="My Dev Machine",
        ...     hostname="macbook-pro",
        ...     os_info="macOS 14.2"
        ... )
        >>> print(f"API Key: {result.api_key}")
    """

    def __init__(self, db: Session):
        """
        Initialize the agent service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # =========================================================================
    # Registration Token Management
    # =========================================================================

    def create_registration_token(
        self,
        team_id: int,
        created_by_user_id: int,
        name: Optional[str] = None,
        expiration_hours: int = DEFAULT_TOKEN_EXPIRATION_HOURS
    ) -> TokenGenerationResult:
        """
        Create a new agent registration token.

        Args:
            team_id: Team this token will register agents for
            created_by_user_id: User creating the token
            name: Optional description for the token
            expiration_hours: Hours until token expires (default 24)

        Returns:
            TokenGenerationResult with token entity and plaintext token
        """
        # Generate random token
        random_part = secrets.token_urlsafe(32)
        plaintext_token = f"art_{random_part}"

        # Hash the token for storage
        token_hash = hashlib.sha256(plaintext_token.encode()).hexdigest()

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)

        # Create token entity
        token = AgentRegistrationToken(
            team_id=team_id,
            created_by_user_id=created_by_user_id,
            token_hash=token_hash,
            name=name,
            expires_at=expires_at
        )

        self.db.add(token)
        self.db.commit()

        logger.info(
            "Registration token created",
            extra={
                "token_guid": token.guid,
                "team_id": team_id,
                "created_by": created_by_user_id,
                "expires_at": expires_at.isoformat()
            }
        )

        return TokenGenerationResult(token=token, plaintext_token=plaintext_token)

    def validate_registration_token(self, plaintext_token: str) -> AgentRegistrationToken:
        """
        Validate a registration token.

        Args:
            plaintext_token: The plaintext token to validate

        Returns:
            The valid token entity

        Raises:
            ValidationError: If token is invalid, expired, or already used
        """
        # Hash the token
        token_hash = hashlib.sha256(plaintext_token.encode()).hexdigest()

        # Find the token
        token = self.db.query(AgentRegistrationToken).filter(
            AgentRegistrationToken.token_hash == token_hash
        ).first()

        if not token:
            raise ValidationError("Invalid registration token")

        if token.is_used:
            raise ValidationError("Registration token has already been used")

        if token.is_expired:
            raise ValidationError("Registration token has expired")

        return token

    # =========================================================================
    # Agent Registration
    # =========================================================================

    def register_agent(
        self,
        plaintext_token: str,
        name: str,
        hostname: Optional[str] = None,
        os_info: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        version: Optional[str] = None,
        binary_checksum: Optional[str] = None
    ) -> RegistrationResult:
        """
        Register a new agent using a registration token.

        Creates the agent, a dedicated SYSTEM user for audit trail,
        and generates an API key for authentication.

        Args:
            plaintext_token: Registration token
            name: User-friendly agent name
            hostname: Machine hostname (auto-detected by agent)
            os_info: Operating system information
            capabilities: Initial capabilities list
            version: Agent software version
            binary_checksum: SHA-256 of agent binary

        Returns:
            RegistrationResult with agent and plaintext API key

        Raises:
            ValidationError: If token is invalid or name is empty
        """
        # Validate token
        token = self.validate_registration_token(plaintext_token)

        # Validate name
        if not name or not name.strip():
            raise ValidationError("Agent name is required", field="name")

        name = name.strip()
        if len(name) > 255:
            raise ValidationError("Agent name too long (max 255 characters)", field="name")

        # Generate API key
        api_key, api_key_hash, api_key_prefix = self._generate_api_key()

        # Create SYSTEM user for audit trail
        system_user = self._create_system_user(
            team_id=token.team_id,
            agent_name=name
        )

        # Create agent
        # Serialize capabilities to JSON string for SQLite compatibility
        capabilities_list = capabilities or []
        capabilities_serialized = json.dumps(capabilities_list) if capabilities_list else "[]"

        agent = Agent(
            team_id=token.team_id,
            system_user_id=system_user.id,
            created_by_user_id=token.created_by_user_id,
            name=name,
            hostname=hostname,
            os_info=os_info,
            status=AgentStatus.OFFLINE,  # Start as offline until first heartbeat
            last_heartbeat=None,  # No heartbeat received yet
            capabilities_json=capabilities_serialized,
            connectors_json="[]",  # Empty list serialized for SQLite compatibility
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            version=version,
            binary_checksum=binary_checksum
        )

        self.db.add(agent)
        self.db.flush()  # Flush to get agent.id for token update

        # Mark token as used
        token.mark_as_used(agent.id)
        self.db.commit()  # Commit the entire registration transaction

        logger.info(
            "Agent registered",
            extra={
                "agent_guid": agent.guid,
                "agent_name": name,
                "team_id": token.team_id,
                "token_guid": token.guid
            }
        )

        return RegistrationResult(agent=agent, api_key=api_key)

    def _generate_api_key(self) -> Tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (plaintext_key, key_hash, key_prefix)
        """
        # Generate random part
        random_part = secrets.token_urlsafe(32)
        api_key = f"{API_KEY_PREFIX}{random_part}"

        # Hash for storage
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Prefix for identification (first 8 chars after prefix)
        api_key_prefix = api_key[:len(API_KEY_PREFIX) + 8]

        return api_key, api_key_hash, api_key_prefix

    def _create_system_user(self, team_id: int, agent_name: str) -> User:
        """
        Create a SYSTEM user for agent audit trail.

        Args:
            team_id: Team the agent belongs to
            agent_name: Agent name (used in system user full name)

        Returns:
            The created SYSTEM user
        """
        # Generate a unique email for the system user
        unique_id = secrets.token_hex(8)
        system_email = f"agent-{unique_id}@system.shuttersense.local"

        system_user = User(
            team_id=team_id,
            user_type=UserType.SYSTEM,
            email=system_email,
            first_name="Agent",
            last_name=agent_name,
            display_name=f"Agent: {agent_name}",
            is_active=True,
            status=UserStatus.ACTIVE
        )

        self.db.add(system_user)
        self.db.flush()

        logger.debug(
            "System user created for agent",
            extra={
                "user_guid": system_user.guid,
                "agent_name": agent_name,
                "team_id": team_id
            }
        )

        return system_user

    # =========================================================================
    # Heartbeat and Status Management
    # =========================================================================

    def process_heartbeat(
        self,
        agent: Agent,
        status: Optional[AgentStatus] = None,
        error_message: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        version: Optional[str] = None
    ) -> Agent:
        """
        Process an agent heartbeat.

        Updates last_heartbeat timestamp and optionally updates
        status, capabilities, and version.

        Args:
            agent: The agent sending the heartbeat
            status: Optional new status (defaults to ONLINE)
            error_message: Error message if status is ERROR
            capabilities: Updated capabilities list
            version: Updated agent version

        Returns:
            The updated agent

        Raises:
            ValidationError: If agent is revoked
        """
        if agent.is_revoked:
            raise ValidationError("Agent has been revoked")

        # Update heartbeat timestamp
        agent.last_heartbeat = datetime.utcnow()

        # Update status (default to ONLINE)
        if status:
            agent.status = status
            if status == AgentStatus.ERROR:
                agent.error_message = error_message
            elif agent.status == AgentStatus.ONLINE:
                agent.error_message = None
        else:
            # No status provided, set to ONLINE
            agent.status = AgentStatus.ONLINE
            agent.error_message = None

        # Update optional fields if provided
        if capabilities is not None:
            # Serialize capabilities to JSON string for SQLite compatibility
            agent.capabilities_json = json.dumps(capabilities) if capabilities else "[]"

        if version is not None:
            agent.version = version

        self.db.commit()

        logger.debug(
            "heartbeat_processed",
            extra={
                "agent_guid": agent.guid,
                "status": agent.status.value
            }
        )

        return agent

    def disconnect_agent(self, agent: Agent) -> Agent:
        """
        Mark an agent as disconnected (graceful shutdown).

        Called by the agent when it's shutting down gracefully. This immediately
        marks the agent as OFFLINE and releases any assigned jobs.

        Args:
            agent: Agent that is disconnecting

        Returns:
            Updated agent
        """
        if agent.status == AgentStatus.REVOKED:
            # Revoked agents stay revoked
            return agent

        agent.status = AgentStatus.OFFLINE
        self._release_agent_jobs(agent)
        self.db.commit()

        logger.info(
            "Agent disconnected gracefully",
            extra={"agent_guid": agent.guid}
        )

        return agent

    def check_offline_agents(self, team_id: int) -> List[Agent]:
        """
        Check for agents that have gone offline and release their jobs.

        Agents are considered offline after HEARTBEAT_TIMEOUT_SECONDS
        without a heartbeat.

        Args:
            team_id: Team to check agents for

        Returns:
            List of agents that were marked offline
        """
        cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)

        # Find agents that should be offline
        offline_agents = self.db.query(Agent).filter(
            Agent.team_id == team_id,
            Agent.status == AgentStatus.ONLINE,
            Agent.last_heartbeat < cutoff
        ).all()

        for agent in offline_agents:
            agent.status = AgentStatus.OFFLINE
            self._release_agent_jobs(agent)

            logger.info(
                "Agent marked offline",
                extra={
                    "agent_guid": agent.guid,
                    "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
                }
            )

        self.db.commit()
        return offline_agents

    def _release_agent_jobs(self, agent: Agent) -> int:
        """
        Release jobs assigned to an agent.

        Jobs in ASSIGNED or RUNNING state are released back to PENDING
        and retry_count is incremented.

        Args:
            agent: Agent whose jobs should be released

        Returns:
            Number of jobs released
        """
        jobs = self.db.query(Job).filter(
            Job.agent_id == agent.id,
            Job.status.in_([JobStatus.ASSIGNED, JobStatus.RUNNING])
        ).all()

        released_count = 0
        for job in jobs:
            # Check if we should retry or fail
            if job.retry_count < job.max_retries:
                job.prepare_retry()
                logger.info(
                    "Job released for retry",
                    extra={
                        "job_guid": job.guid,
                        "agent_guid": agent.guid,
                        "retry_count": job.retry_count
                    }
                )
            else:
                job.fail(f"Agent went offline after {job.max_retries} retries")
                logger.warning(
                    "Job failed after max retries",
                    extra={
                        "job_guid": job.guid,
                        "agent_guid": agent.guid,
                        "max_retries": job.max_retries
                    }
                )
            released_count += 1

        return released_count

    # =========================================================================
    # Agent Management
    # =========================================================================

    def get_agent_by_guid(self, guid: str, team_id: int) -> Agent:
        """
        Get an agent by GUID.

        Args:
            guid: Agent GUID (agt_xxx)
            team_id: Team ID for scoping

        Returns:
            The agent

        Raises:
            NotFoundError: If agent not found in team
        """
        try:
            uuid = Agent.parse_guid(guid)
        except ValueError as e:
            raise NotFoundError("Agent", guid)

        agent = self.db.query(Agent).filter(
            Agent.uuid == uuid,
            Agent.team_id == team_id
        ).first()

        if not agent:
            raise NotFoundError("Agent", guid)

        return agent

    def get_agent_by_api_key(self, api_key: str) -> Optional[Agent]:
        """
        Get an agent by API key.

        Args:
            api_key: Plaintext API key

        Returns:
            The agent, or None if not found
        """
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return self.db.query(Agent).filter(
            Agent.api_key_hash == api_key_hash
        ).first()

    def list_agents(
        self,
        team_id: int,
        status: Optional[AgentStatus] = None,
        include_revoked: bool = False
    ) -> List[Agent]:
        """
        List agents for a team.

        Automatically checks for stale heartbeats and marks agents offline
        before returning the list.

        Args:
            team_id: Team ID
            status: Optional status filter
            include_revoked: Whether to include revoked agents

        Returns:
            List of agents
        """
        # Update status of agents with stale heartbeats before listing
        self.check_offline_agents(team_id)

        query = self.db.query(Agent).filter(Agent.team_id == team_id)

        if status:
            query = query.filter(Agent.status == status)

        if not include_revoked:
            query = query.filter(Agent.status != AgentStatus.REVOKED)

        return query.order_by(Agent.name).all()

    def rename_agent(self, agent: Agent, new_name: str) -> Agent:
        """
        Rename an agent.

        Also updates the associated SYSTEM user's display name.

        Args:
            agent: Agent to rename
            new_name: New name

        Returns:
            Updated agent

        Raises:
            ValidationError: If name is invalid
        """
        if not new_name or not new_name.strip():
            raise ValidationError("Agent name is required", field="name")

        new_name = new_name.strip()
        if len(new_name) > 255:
            raise ValidationError("Agent name too long (max 255 characters)", field="name")

        old_name = agent.name
        agent.name = new_name

        # Update SYSTEM user display name
        if agent.system_user:
            agent.system_user.last_name = new_name
            agent.system_user.display_name = f"Agent: {new_name}"

        self.db.commit()

        logger.info(
            "Agent renamed",
            extra={
                "agent_guid": agent.guid,
                "old_name": old_name,
                "new_name": new_name
            }
        )

        return agent

    def revoke_agent(self, agent: Agent, reason: str) -> Agent:
        """
        Revoke an agent.

        Revoked agents cannot authenticate or execute jobs.
        Their jobs are released.

        Args:
            agent: Agent to revoke
            reason: Reason for revocation

        Returns:
            Updated agent
        """
        if agent.is_revoked:
            raise ValidationError("Agent is already revoked")

        agent.status = AgentStatus.REVOKED
        agent.revocation_reason = reason
        agent.revoked_at = datetime.utcnow()

        # Release any assigned jobs
        self._release_agent_jobs(agent)

        self.db.commit()

        logger.warning(
            "Agent revoked",
            extra={
                "agent_guid": agent.guid,
                "reason": reason
            }
        )

        return agent

    def delete_agent(self, agent: Agent) -> None:
        """
        Delete an agent.

        Cannot delete agents with bound collections.

        Args:
            agent: Agent to delete

        Raises:
            ConflictError: If agent has bound collections
        """
        # Check for bound collections
        bound_count = agent.bound_collections.count()
        if bound_count > 0:
            raise ConflictError(
                f"Cannot delete agent with {bound_count} bound collections. "
                "Unbind collections first or reassign them to another agent."
            )

        # Release any jobs
        self._release_agent_jobs(agent)

        # Delete the agent (SYSTEM user is preserved for audit trail)
        self.db.delete(agent)
        self.db.commit()

        logger.info(
            "Agent deleted",
            extra={
                "agent_guid": agent.guid,
                "agent_name": agent.name
            }
        )

    # =========================================================================
    # Pool Status
    # =========================================================================

    def get_pool_status(self, team_id: int) -> dict:
        """
        Get agent pool status for the header badge.

        Automatically checks for stale heartbeats and marks agents offline
        before calculating the status.

        Args:
            team_id: Team ID

        Returns:
            Dict with online_count, idle_count, running_jobs_count, status
        """
        from sqlalchemy import func

        # Update status of agents with stale heartbeats before counting
        self.check_offline_agents(team_id)

        # Count online agents
        online_count = self.db.query(func.count(Agent.id)).filter(
            Agent.team_id == team_id,
            Agent.status == AgentStatus.ONLINE
        ).scalar() or 0

        # Count active jobs (ASSIGNED = claimed by agent, RUNNING = executing)
        # Both count as "in progress" for the badge
        running_jobs_count = self.db.query(func.count(Job.id)).filter(
            Job.team_id == team_id,
            Job.status.in_([JobStatus.ASSIGNED, JobStatus.RUNNING])
        ).scalar() or 0

        # Count idle agents (online agents not currently working on a job)
        busy_agent_ids = self.db.query(Job.agent_id).filter(
            Job.team_id == team_id,
            Job.status.in_([JobStatus.ASSIGNED, JobStatus.RUNNING]),
            Job.agent_id.isnot(None)
        ).subquery()

        idle_count = self.db.query(func.count(Agent.id)).filter(
            Agent.team_id == team_id,
            Agent.status == AgentStatus.ONLINE,
            ~Agent.id.in_(busy_agent_ids)
        ).scalar() or 0

        # Count offline agents (not online, not revoked)
        offline_count = self.db.query(func.count(Agent.id)).filter(
            Agent.team_id == team_id,
            Agent.status == AgentStatus.OFFLINE
        ).scalar() or 0

        # Determine overall status
        if online_count == 0:
            status = "offline"
        elif running_jobs_count > 0:
            status = "running"
        else:
            status = "idle"

        return {
            "online_count": online_count,
            "offline_count": offline_count,
            "idle_count": idle_count,
            "running_jobs_count": running_jobs_count,
            "status": status
        }
