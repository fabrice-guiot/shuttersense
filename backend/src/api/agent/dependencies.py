"""
Agent authentication dependencies for the Agent API.

Provides FastAPI dependencies for authenticating agents via API key,
separate from user authentication (session/JWT tokens).

Agent authentication uses:
- Bearer token in Authorization header
- API key format: agt_key_xxxxx
- SHA-256 hash comparison against stored api_key_hash
"""

from dataclasses import dataclass, field
from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.models.agent import Agent, AgentStatus
from backend.src.utils.logging_config import get_logger


logger = get_logger("agent")


@dataclass
class AgentContext:
    """
    Context for an authenticated agent request.

    Provides agent identification and team scope for API operations.

    Attributes:
        agent_id: Internal agent ID for database queries
        agent_guid: Agent's external GUID (agt_xxx)
        team_id: Team ID for tenant isolation
        team_guid: Team's external GUID (tea_xxx)
        agent_name: Agent's display name
        status: Current agent status
        agent: The full Agent model (for accessing capabilities, etc.)
    """

    agent_id: int
    agent_guid: str
    team_id: int
    team_guid: str
    agent_name: str
    status: AgentStatus
    agent: Optional[Agent] = field(default=None)

    def __post_init__(self):
        """Validate required fields."""
        if not self.agent_id or not self.agent_guid:
            raise ValueError("agent_id and agent_guid are required")
        if not self.team_id or not self.team_guid:
            raise ValueError("team_id and team_guid are required")


async def get_agent_context(
    request: Request,
    db: Session = Depends(get_db)
) -> AgentContext:
    """
    FastAPI dependency to authenticate agents via API key.

    Extracts the API key from the Authorization header (Bearer token),
    validates it against stored agent API keys, and returns the agent context.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        AgentContext with authenticated agent information

    Raises:
        HTTPException 401: If no Authorization header or invalid format
        HTTPException 401: If API key is invalid or not found
        HTTPException 403: If agent is revoked

    Example:
        @router.post("/heartbeat")
        async def send_heartbeat(
            ctx: AgentContext = Depends(get_agent_context)
        ):
            # ctx.agent_id is the authenticated agent
            ...
    """
    # Import here to avoid circular imports
    from backend.src.services.agent_service import AgentService

    # Extract Bearer token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning("Agent auth failed: no Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not auth_header.startswith("Bearer "):
        logger.warning("Agent auth failed: invalid Authorization format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"}
        )

    api_key = auth_header[7:]  # Remove "Bearer " prefix

    # Validate API key format (should start with agent key prefix)
    if not api_key.startswith("agt_key_"):
        logger.warning("Agent auth failed: invalid API key format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Look up agent by API key
    service = AgentService(db)
    agent = service.get_agent_by_api_key(api_key)

    if not agent:
        logger.warning(
            "Agent auth failed: API key not found",
            extra={"api_key_prefix": api_key[:16] if len(api_key) > 16 else api_key}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if agent is revoked
    if agent.status == AgentStatus.REVOKED:
        logger.warning(
            "Agent auth failed: agent is revoked",
            extra={"agent_guid": agent.guid, "revocation_reason": agent.revocation_reason}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent access has been revoked"
        )

    # Build agent context with the full agent model
    return AgentContext(
        agent_id=agent.id,
        agent_guid=agent.guid,
        team_id=agent.team_id,
        team_guid=agent.team.guid if agent.team else "",
        agent_name=agent.name,
        status=agent.status,
        agent=agent,
    )


async def get_optional_agent_context(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[AgentContext]:
    """
    FastAPI dependency for optional agent authentication.

    Returns AgentContext if authenticated, None otherwise.
    Use this for endpoints that work both with and without agent authentication.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        AgentContext if authenticated, None otherwise
    """
    try:
        return await get_agent_context(request, db)
    except HTTPException:
        return None


def require_online_agent(
    ctx: AgentContext = Depends(get_agent_context)
) -> AgentContext:
    """
    Dependency that requires the agent to be in ONLINE status.

    Use this for endpoints that should only be accessible to online agents
    (e.g., job claiming).

    Args:
        ctx: Agent context from get_agent_context

    Returns:
        AgentContext if agent is online

    Raises:
        HTTPException 403: If agent is not online

    Example:
        @router.post("/jobs/claim")
        async def claim_job(
            ctx: AgentContext = Depends(require_online_agent)
        ):
            # Only online agents can claim jobs
            ...
    """
    if ctx.status != AgentStatus.ONLINE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent must be online to perform this action. Current status: {ctx.status.value}"
        )
    return ctx


def require_verified_agent(
    ctx: AgentContext = Depends(require_online_agent)
) -> AgentContext:
    """
    Dependency that requires the agent to be online AND have a verified binary.

    Use this for job operation endpoints where unverified agents must be
    blocked. Unverified agents can still heartbeat and disconnect, but
    cannot claim, execute, or upload job results.

    Enforcement is controlled by SHUSAI_REQUIRE_AGENT_ATTESTATION (default: True).
    Set to False only in development where agents run from source.

    Args:
        ctx: Agent context from require_online_agent

    Returns:
        AgentContext if agent is online and verified

    Raises:
        HTTPException 403: If agent binary is not verified (production only)
    """
    from backend.src.config.settings import get_settings

    settings = get_settings()
    if not settings.require_agent_attestation:
        # Attestation enforcement disabled for this environment.
        # Only set SHUSAI_REQUIRE_AGENT_ATTESTATION=false in development.
        return ctx

    if not ctx.agent or not ctx.agent.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent binary not verified. Ensure you are running an official release."
        )
    return ctx
