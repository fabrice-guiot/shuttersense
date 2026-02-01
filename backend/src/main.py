"""
FastAPI application entry point for ShutterSense backend.

This module initializes the FastAPI application with:
- Application state (FileListingCache, JobQueue, CredentialEncryptor)
- CORS middleware for frontend development
- Exception handlers for consistent error responses
- Startup event handlers for environment validation
- Logging configuration
- SPA (Single Page Application) serving from frontend/dist/

The application serves both the REST API (under /api/) and the React SPA
from the same server, enabling single-port HTTPS deployment.

Environment Variables:
    SHUSAI_MASTER_KEY: Master encryption key (required)
    SHUSAI_ENV: Environment (production/development, default: development)
    SHUSAI_LOG_LEVEL: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
    SHUSAI_AUTHORIZED_LOCAL_ROOTS: Comma-separated list of authorized root
        paths for local collections (security - required for local collections)
    SHUSAI_SPA_DIST_PATH: Path to SPA dist directory (default: frontend/dist)
    RATE_LIMIT_STORAGE_URI: Rate limit storage backend (default: memory://)
        Use "redis://host:6379" for multi-worker deployments.
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.src.utils.cache import FileListingCache
from backend.src.utils.job_queue import JobQueue
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import init_logging, get_logger
from backend.src.utils.websocket import get_connection_manager
from backend.src.db.database import SessionLocal
from backend.src.services.config_service import ConfigService

# Import version management
from version import __version__


# ============================================================================
# Rate Limiting Configuration (T168)
# ============================================================================
# Configure rate limiter with configurable storage backend.
# Default: in-memory (single-process). Set RATE_LIMIT_STORAGE_URI for
# multi-worker deployments (e.g., "redis://localhost:6379").
from backend.src.config.settings import get_settings as _get_rate_limit_settings

_rate_limit_storage = _get_rate_limit_settings().rate_limit_storage_uri
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_rate_limit_storage,
)


# ============================================================================
# Security Headers Middleware (T170)
# ============================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter (legacy, but still useful)
    - Referrer-Policy: Control referrer information
    - Content-Security-Policy: Restrict resource loading
    - Permissions-Policy: Control browser features

    Note: CSRF protection is handled via SameSite cookies in browsers.
    For API-only backends, CORS with credentials=True provides adequate
    protection since the Origin header is verified.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip WebSocket connections - BaseHTTPMiddleware doesn't handle them properly
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking (allow for docs pages)
        if request.url.path not in ["/api-docs", "/api-redoc", "/openapi.json"]:
            response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # Different CSP for API vs SPA pages
        path = request.url.path
        if path in ["/api-docs", "/api-redoc", "/openapi.json"]:
            # Skip restrictive CSP for documentation pages (Swagger UI needs external resources)
            pass
        elif path.startswith("/api/") or path == "/health":
            # Restrictive CSP for API endpoints
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'"
            )
        else:
            # CSP for SPA pages - allow self-hosted scripts, styles, images, fonts
            # Note: 'self' includes same-origin API calls (/api/*)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self' ws: wss:; "
                "manifest-src 'self'; "
                "worker-src 'self' blob:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )

        # Disable browser features not needed by API
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        return response


# ============================================================================
# Request Size Limit Middleware (T169)
# ============================================================================
# Maximum request body size: 10MB for file uploads
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent resource exhaustion.

    Checks Content-Length header for early rejection, and wraps the
    request body stream to enforce the limit for chunked transfers
    that omit Content-Length.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip WebSocket connections - BaseHTTPMiddleware doesn't handle them properly
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > MAX_REQUEST_SIZE:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "Request Entity Too Large",
                            "message": f"Request body exceeds maximum size of {MAX_REQUEST_SIZE // (1024 * 1024)}MB",
                            "max_size_bytes": MAX_REQUEST_SIZE
                        }
                    )
            except ValueError:
                pass  # Invalid Content-Length, let server handle it
        elif request.method in ("POST", "PUT", "PATCH"):
            # No Content-Length header (chunked transfer) — wrap the body
            # stream to enforce the size limit while reading.
            original_receive = request._receive
            bytes_received = 0

            async def size_limited_receive():
                nonlocal bytes_received
                message = await original_receive()
                if message.get("type") == "http.request":
                    body = message.get("body", b"")
                    bytes_received += len(body)
                    if bytes_received > MAX_REQUEST_SIZE:
                        from starlette.exceptions import HTTPException as StarletteHTTPException
                        raise StarletteHTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Request body exceeds maximum size of {MAX_REQUEST_SIZE // (1024 * 1024)}MB",
                        )
                return message

            request._receive = size_limited_receive

        return await call_next(request)


def validate_master_key() -> None:
    """
    Validate that SHUSAI_MASTER_KEY environment variable is set.

    Raises:
        SystemExit: If master key is not set or invalid

    Note:
        This function is called during application startup to fail fast
        if the encryption key is missing.
    """
    master_key = os.environ.get("SHUSAI_MASTER_KEY")

    if not master_key:
        print(
            "\n" + "=" * 70,
            "\nERROR: SHUSAI_MASTER_KEY environment variable is not set.",
            "\n\nThe master encryption key is required to encrypt/decrypt remote",
            "\nstorage credentials stored in the database.",
            "\n\nTo set up the master key, run:",
            "\n  python3 setup_master_key.py",
            "\n\nThis will guide you through generating and configuring the key.",
            "\n" + "=" * 70 + "\n",
            file=sys.stderr
        )
        sys.exit(1)

    # Validate key format by attempting to create CredentialEncryptor
    try:
        CredentialEncryptor(master_key=master_key)
    except Exception as e:
        print(
            "\n" + "=" * 70,
            "\nERROR: SHUSAI_MASTER_KEY is invalid.",
            f"\n\nEncryption validation failed: {e}",
            "\n\nThe key must be a valid Fernet key (44 characters, base64-encoded).",
            "\n\nTo generate a new key, run:",
            "\n  python3 setup_master_key.py",
            "\n" + "=" * 70 + "\n",
            file=sys.stderr
        )
        sys.exit(1)


async def dead_agent_safety_net() -> None:
    """
    Background task that periodically checks for dead agents across all teams.

    Runs every 120 seconds, marking agents with stale heartbeats as offline
    and triggering pool_offline notifications if a team's pool becomes empty.

    This is a safety net for cases where agents die without sending a disconnect
    (e.g., crash, network partition, kill -9).

    Issue #114 - Phase 8 (T035)
    """
    safety_logger = get_logger("agent")
    safety_logger.info("Dead agent safety net background task started")

    while True:
        await asyncio.sleep(120)

        db = None
        try:
            db = SessionLocal()

            # Get all distinct team_ids from non-revoked agents
            from backend.src.models import Agent, AgentStatus
            team_ids = (
                db.query(Agent.team_id)
                .filter(Agent.status != AgentStatus.REVOKED)
                .distinct()
                .all()
            )

            for (team_id,) in team_ids:
                try:
                    from backend.src.services.agent_service import AgentService

                    agent_service = AgentService(db)
                    result = agent_service.check_offline_agents(team_id)

                    if result.pool_now_empty and result.newly_offline_agents:
                        # Use the first newly-offline agent as representative
                        representative_agent = result.newly_offline_agents[0]
                        try:
                            from backend.src.services.notification_service import NotificationService
                            from backend.src.config.settings import get_settings

                            settings = get_settings()
                            vapid_claims = (
                                {"sub": settings.vapid_subject}
                                if settings.vapid_subject
                                else {}
                            )
                            notification_service = NotificationService(
                                db=db,
                                vapid_private_key=settings.vapid_private_key,
                                vapid_claims=vapid_claims,
                            )
                            sent_count = notification_service.notify_agent_status(
                                agent=representative_agent,
                                team_id=team_id,
                                transition_type="pool_offline",
                            )

                            # Broadcast hint so frontend refreshes unread badge
                            if sent_count > 0:
                                from backend.src.utils.websocket import get_connection_manager

                                manager = get_connection_manager()
                                await manager.broadcast_notification_hint(team_id)
                        except Exception as e:
                            safety_logger.error(
                                f"Failed to send pool_offline notification: {e}",
                                extra={"team_id": team_id},
                            )
                except Exception as e:
                    safety_logger.error(
                        f"Error checking offline agents for team: {e}",
                        extra={"team_id": team_id},
                    )
        except Exception as e:
            safety_logger.error(f"Dead agent safety net iteration error: {e}")
        finally:
            if db:
                db.close()


async def deadline_check_scheduler() -> None:
    """
    Background task that periodically checks for approaching event deadlines.

    Runs every hour, querying all teams with deadline events and sending
    reminder push notifications to users based on their deadline_days_before
    and timezone preferences.

    Deduplication is handled in check_deadlines() — hourly runs are safe
    and handle server restarts and timezone edge cases without complex
    "last run" tracking.

    Issue #114 - Phase 9 (T036)
    """
    deadline_logger = get_logger("notifications")
    deadline_logger.info("Deadline check scheduler background task started")

    while True:
        await asyncio.sleep(3600)  # Hourly

        db = None
        try:
            db = SessionLocal()

            # Find distinct team_ids that have events with deadlines
            from backend.src.models import Event
            team_ids = (
                db.query(Event.team_id)
                .filter(
                    Event.deadline_date.isnot(None),
                    Event.deleted_at.is_(None),
                )
                .distinct()
                .all()
            )

            total_sent = 0
            team_count = len(team_ids)

            for (team_id,) in team_ids:
                try:
                    from backend.src.services.notification_service import NotificationService
                    from backend.src.config.settings import get_settings

                    settings = get_settings()
                    vapid_claims = (
                        {"sub": settings.vapid_subject}
                        if settings.vapid_subject
                        else {}
                    )
                    notification_service = NotificationService(
                        db=db,
                        vapid_private_key=settings.vapid_private_key,
                        vapid_claims=vapid_claims,
                    )
                    sent = notification_service.check_deadlines(team_id=team_id)
                    total_sent += sent

                    # Broadcast hint so frontend refreshes unread badge
                    if sent > 0:
                        from backend.src.utils.websocket import get_connection_manager

                        manager = get_connection_manager()
                        await manager.broadcast_notification_hint(team_id)
                except Exception as e:
                    deadline_logger.error(
                        f"Error checking deadlines for team: {e}",
                        extra={"team_id": team_id},
                    )
            deadline_logger.info(
                f"Deadline check completed: {total_sent} reminders across {team_count} teams"
            )
        except Exception as e:
            deadline_logger.error(f"Deadline check scheduler iteration error: {e}")
        finally:
            if db:
                db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Validate master key, initialize logging, create singletons
    - Shutdown: Clean up resources

    Args:
        app: FastAPI application instance

    Yields:
        Control to the application
    """
    # Startup
    logger = get_logger("api")
    logger.info("Starting ShutterSense backend application")

    # Validate master key
    logger.info("Validating SHUSAI_MASTER_KEY environment variable")
    validate_master_key()
    logger.info("Master key validation successful")

    # Initialize application state
    logger.info("Initializing application state (cache, job queue, encryptor, websocket)")
    app.state.file_cache = FileListingCache()
    app.state.job_queue = JobQueue()
    app.state.credential_encryptor = CredentialEncryptor()
    app.state.websocket_manager = get_connection_manager()
    logger.info("Application state initialized successfully")

    # Log CORS configuration
    logger.info(f"CORS allowed origins: {cors_origins}")

    # Validate Web Push (VAPID) configuration
    from backend.src.config.settings import get_settings
    _settings = get_settings()
    if _settings.vapid_configured:
        try:
            from pywebpush import webpush  # noqa: F401
            logger.info(
                "Web Push (VAPID) configured — push notifications enabled"
            )
        except ImportError:
            logger.warning(
                "VAPID keys configured but pywebpush is not installed. "
                "Push notifications will fail. Install with: pip install pywebpush>=2.0.0"
            )
    else:
        missing = []
        if not _settings.vapid_public_key:
            missing.append("VAPID_PUBLIC_KEY")
        if not _settings.vapid_private_key:
            missing.append("VAPID_PRIVATE_KEY")
        if not _settings.vapid_subject:
            missing.append("VAPID_SUBJECT")
        logger.warning(
            f"Web Push (VAPID) not configured — push notifications disabled. "
            f"Missing: {', '.join(missing)}"
        )

    # NOTE: Default configuration seeding (extensions) is now team-specific
    # and should be done when a team is created, not on application startup.
    # The seed_default_extensions(team_id) method requires a team_id parameter
    # for proper tenant isolation.
    logger.info("Skipping global configuration seeding (tenant-specific data is seeded per-team)")

    # Validate session security configuration (SEC-03)
    _env = os.environ.get("SHUSAI_ENV", "development").lower()
    _session_settings = get_session_settings()
    if _env == "production":
        if not _session_settings.session_https_only:
            logger.warning(
                "SESSION_HTTPS_ONLY is False in production. "
                "Session cookies will be sent over unencrypted HTTP. "
                "Set SESSION_HTTPS_ONLY=true for production deployments."
            )
        if not _session_settings.is_configured:
            logger.warning(
                "SESSION_SECRET_KEY is not set. "
                "Sessions will not work. Set a strong secret key (min 32 characters)."
            )

    # Log GeoIP geofencing configuration status
    if _settings.geoip_configured:
        if _geofence_reader is not None:
            allowed = _settings.geoip_allowed_countries_set
            fail_mode = "fail-open" if _settings.geoip_fail_open else "fail-closed"
            if allowed:
                logger.info(
                    "GeoIP geofencing enabled — allowed countries: %s (%s, db: %s)",
                    ", ".join(sorted(allowed)),
                    fail_mode,
                    _settings.geoip_db_path,
                )
            else:
                logger.warning(
                    "GeoIP database configured but SHUSAI_GEOIP_ALLOWED_COUNTRIES is empty — "
                    "ALL requests from non-private IPs will be BLOCKED (%s)",
                    fail_mode,
                )
        else:
            logger.error(
                "GeoIP database not found at %s — geofencing DISABLED. "
                "Download GeoLite2-Country.mmdb from MaxMind.",
                _settings.geoip_db_path,
            )
    else:
        logger.info("GeoIP geofencing disabled (SHUSAI_GEOIP_DB_PATH not set)")

    # Store GeoIP reader reference for shutdown cleanup
    app.state.geoip_reader = _geofence_reader

    logger.info("ShutterSense backend started successfully")

    # Start dead agent safety net background task (Phase 8, T035)
    safety_net_task = asyncio.create_task(dead_agent_safety_net())

    # Start deadline check scheduler background task (Phase 9, T036)
    deadline_task = asyncio.create_task(deadline_check_scheduler())

    yield

    # Shutdown
    logger.info("Shutting down ShutterSense backend application")

    # Cancel dead agent safety net
    safety_net_task.cancel()
    try:
        await safety_net_task
    except asyncio.CancelledError:
        logger.info("Dead agent safety net background task stopped")
    except Exception as e:
        logger.error(f"Dead agent safety net failed: {e}")

    # Cancel deadline check scheduler
    deadline_task.cancel()
    try:
        await deadline_task
    except asyncio.CancelledError:
        logger.info("Deadline check scheduler background task stopped")
    except Exception as e:
        logger.error(f"Deadline check scheduler failed: {e}")

    # Close GeoIP reader if it was opened
    if hasattr(app.state, 'geoip_reader') and app.state.geoip_reader:
        app.state.geoip_reader.close()
        logger.info("GeoIP database reader closed")


# Initialize logging before creating app
init_logging()

# ============================================================================
# OpenAPI Tag Metadata
# ============================================================================
# Define tag groups and descriptions for API documentation.
# Order here determines display order in Swagger UI and ReDoc.
# Groups align with frontend menu structure for consistency.
openapi_tags = [
    # === Core Application ===
    {
        "name": "Collections",
        "description": "Photo collection management - create, configure, and organize collections.",
    },
    {
        "name": "Pipelines",
        "description": "Processing pipeline workflows - define and manage validation rules.",
    },
    {
        "name": "Events",
        "description": "Calendar event management for photo shoots and sessions.",
    },

    # === Processing & Results ===
    {
        "name": "Tools",
        "description": "Job execution - run analysis tools against collections.",
    },
    {
        "name": "Results",
        "description": "Analysis results storage and retrieval.",
    },
    {
        "name": "Trends",
        "description": "Historical analysis data and trend aggregation.",
    },
    {
        "name": "Analytics",
        "description": "Storage metrics, usage analytics, and trend analysis.",
    },

    # === Directory ===
    {
        "name": "Locations",
        "description": "Event location and venue management.",
    },
    {
        "name": "Organizers",
        "description": "Event organizer management.",
    },
    {
        "name": "Performers",
        "description": "Event performer and participant management.",
    },

    # === Settings ===
    {
        "name": "Configuration",
        "description": "Application configuration and tool settings.",
    },
    {
        "name": "Categories",
        "description": "Event category taxonomy management.",
    },
    {
        "name": "Connectors",
        "description": "Remote storage connectors - S3, GCS, SMB configuration. "
                      "Includes **inventory endpoints** under `/api/connectors/{guid}/inventory/*` "
                      "for S3 Inventory and GCS Storage Insights integration.",
    },
    {
        "name": "Users",
        "description": "User profile and account management.",
    },

    # === Infrastructure (internal APIs - not accessible via API tokens) ===
    {
        "name": "Agents",
        "description": "Distributed agent operations - registration, heartbeat, job execution. "
                      "Includes inventory import phases: folder extraction (Phase A), "
                      "FileInfo population (Phase B), and delta detection (Phase C). "
                      "**Internal API**: Not accessible via API tokens.",
    },
    {
        "name": "Authentication",
        "description": "OAuth 2.0 authentication - Google and Microsoft login. "
                      "**Internal API**: Not accessible via API tokens.",
    },
    {
        "name": "Tokens",
        "description": "API token management for programmatic access. "
                      "**Internal API**: Not accessible via API tokens.",
    },

    # === Administration (internal APIs - not accessible via API tokens) ===
    {
        "name": "Admin - Teams",
        "description": "Super admin: Multi-tenant team management. "
                      "**Internal API**: Not accessible via API tokens.",
    },
    {
        "name": "Admin - Release Manifests",
        "description": "Super admin: Agent binary release attestation. "
                      "**Internal API**: Not accessible via API tokens.",
    },

    # === System ===
    {
        "name": "Health",
        "description": "Health check and liveness probe.",
    },
    {
        "name": "System",
        "description": "System information and version endpoint.",
    },
]


# Create FastAPI application
# Note: docs_url and redoc_url are set to None to use custom endpoints with favicon
app = FastAPI(
    title="ShutterSense.ai API",
    description="Backend API for ShutterSense.ai - Capture. Process. Analyze. "
                "Supports remote photo collection management, pipeline configuration, "
                "and analysis tool execution with persistent result storage.",
    version=__version__,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=openapi_tags,
)

# ============================================================================
# Configure Rate Limiter (T168)
# ============================================================================
# Attach limiter to app state for access in routes
app.state.limiter = limiter

# Add rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Module-level reference for GeoIP reader (opened conditionally below, closed in lifespan)
_geofence_reader = None
_geofence_settings = _get_rate_limit_settings()  # Reuse cached AppSettings

# ============================================================================
# Security Middlewares (T169, T170)
# ============================================================================
# Note: Starlette middleware order is LIFO — last added runs first (outermost).
# Registration order below (innermost → outermost):
#   1. RequestSizeLimitMiddleware (innermost)
#   2. SecurityHeadersMiddleware
#   3. CORS
#   4. SessionMiddleware
#   5. GeoFenceMiddleware (outermost, if enabled) — added after Session below
app.add_middleware(RequestSizeLimitMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


# Configure CORS middleware for frontend development
# Read allowed origins from CORS_ORIGINS env var (comma-separated) or use defaults
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    cors_origins = [
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",  # React dev server (alternative)
        "http://localhost:8000",  # Backend serving SPA
        "http://127.0.0.1:8000",  # Backend serving SPA (alternative)
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Disposition"],  # Expose for report download filenames
)

# ============================================================================
# Session Middleware (Issue #73 - Authentication)
# ============================================================================
# SessionMiddleware provides signed cookie-based sessions for OAuth auth flow.
# The session stores user_id after successful OAuth login.
# Configuration is loaded from environment variables via SessionSettings.
from backend.src.config.session import get_session_settings

_session_settings = get_session_settings()
if _session_settings.is_configured:
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_settings.session_secret_key,
        session_cookie=_session_settings.session_cookie_name,
        max_age=_session_settings.session_max_age,
        same_site=_session_settings.session_same_site,
        https_only=_session_settings.session_https_only,
        path=_session_settings.session_path,
    )
else:
    # Session not configured - auth features will be unavailable
    # This is acceptable for development without OAuth setup
    import warnings
    warnings.warn(
        "SESSION_SECRET_KEY not configured. Session-based authentication disabled. "
        "Set SESSION_SECRET_KEY in .env to enable OAuth login.",
        UserWarning
    )

# ============================================================================
# GeoIP Geofencing Middleware (optional, outermost)
# ============================================================================
# Added last so it runs first (outermost in Starlette's LIFO middleware stack).
# When configured via SHUSAI_GEOIP_DB_PATH and SHUSAI_GEOIP_ALLOWED_COUNTRIES,
# blocks requests from countries not in the allowlist before any other processing.
if _geofence_settings.geoip_configured:
    import os as _geofence_os
    if _geofence_os.path.isfile(_geofence_settings.geoip_db_path):
        import geoip2.database as _geoip2_db
        from backend.src.middleware.geofence import GeoFenceMiddleware

        _geofence_reader = _geoip2_db.Reader(_geofence_settings.geoip_db_path)
        app.add_middleware(
            GeoFenceMiddleware,
            reader=_geofence_reader,
            allowed_countries=_geofence_settings.geoip_allowed_countries_set,
            fail_open=_geofence_settings.geoip_fail_open,
        )


# ============================================================================
# Custom OpenAPI Schema with Bearer Token Authentication
# ============================================================================
def custom_openapi():
    """
    Generate custom OpenAPI schema with Bearer token authentication.

    This adds the HTTPBearer security scheme to the OpenAPI spec, enabling
    the "Authorize" button in Swagger UI (/api-docs) and ReDoc (/api-redoc).

    Users can enter their API token to test authenticated endpoints.

    Note: /health and /api/version endpoints do not require authentication
    and are marked accordingly in their route definitions.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=openapi_tags,
    )

    # Add security scheme for Bearer token authentication
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "API Token authentication. Generate a token from Settings > API Tokens "
                "in the web UI. Enter the token value (without 'Bearer ' prefix)."
            )
        }
    }

    # Apply security globally to all endpoints except public ones
    # Public endpoints: /health, /api/version, /api/auth/*, /api/agent/v1/register
    public_paths = {"/health", "/api/version", "/api/agent/v1/register"}
    public_prefixes = ["/api/auth/"]

    for path, path_item in openapi_schema.get("paths", {}).items():
        # Skip public paths
        if path in public_paths:
            continue
        if any(path.startswith(prefix) for prefix in public_prefixes):
            continue
        # Skip non-API paths (SPA routes)
        if not path.startswith("/api") and path != "/health":
            continue

        # Apply security to all methods on this path
        for method in path_item.values():
            if isinstance(method, dict):
                method["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Custom Documentation Endpoints with Favicon
# ============================================================================
@app.get("/api-docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Serve Swagger UI with custom favicon."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_favicon_url="/favicon.svg"
    )


@app.get("/api-redoc", include_in_schema=False)
async def custom_redoc_html():
    """Serve ReDoc with custom favicon."""
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_favicon_url="/favicon.svg"
    )


# Exception handlers


@app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: HTTP request
        exc: Pydantic ValidationError

    Returns:
        JSON response with validation error details
    """
    logger = get_logger("api")
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": exc.errors(),
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle SQLAlchemy database errors.

    Args:
        request: HTTP request
        exc: SQLAlchemy exception

    Returns:
        JSON response with database error message
    """
    logger = get_logger("db")
    logger.error(
        "Database error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
        },
        exc_info=True,  # Include full traceback for debugging
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database Error",
            "message": "An error occurred while accessing the database. "
                      "Please try again later.",
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle all other unhandled exceptions.

    Args:
        request: HTTP request
        exc: Unhandled exception

    Returns:
        JSON response with generic error message
    """
    logger = get_logger("api")
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error": str(exc),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
        }
    )


# Health check endpoint


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Health status and application information
    """
    return {
        "status": "healthy",
        "service": "shuttersense-backend",
        "version": __version__,
    }


@app.get("/api/version", tags=["System"])
async def get_version() -> Dict[str, str]:
    """
    Get the current version of the ShutterSense.ai application.

    This endpoint returns the version number synchronized with GitHub release tags.
    The version is automatically determined from Git tags during development and
    production builds.

    Returns:
        Dictionary with version information
    """
    return {
        "version": __version__,
    }


# ============================================================================
# API Routers
# ============================================================================
# Router registration order matches openapi_tags for consistent documentation.
# Groups align with frontend menu structure.

from backend.src.api import (
    collections, connectors, tools, results, pipelines, trends,
    config, categories, events, locations, organizers, performers, analytics,
    notifications
)
from backend.src.api import auth as auth_router
from backend.src.api import users as users_router
from backend.src.api import tokens as tokens_router
from backend.src.api.admin import teams_router as admin_teams_router
from backend.src.api.admin import release_manifests_router as admin_release_manifests_router
from backend.src.api.agent import router as agent_router

# === Core Application ===
app.include_router(collections.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(events.router, prefix="/api")

# === Processing & Results ===
app.include_router(tools.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# === Directory ===
app.include_router(locations.router, prefix="/api")
app.include_router(organizers.router, prefix="/api")
app.include_router(performers.router, prefix="/api")

# === Settings ===
app.include_router(config.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(users_router.router, prefix="/api")

# === Notifications (Issue #114) ===
app.include_router(notifications.router, prefix="/api")

# === Infrastructure (internal APIs - not accessible via API tokens) ===
app.include_router(agent_router)
app.include_router(auth_router.router, prefix="/api")
app.include_router(tokens_router.router)

# === Administration (internal APIs - not accessible via API tokens) ===
app.include_router(admin_teams_router, prefix="/api/admin")
app.include_router(admin_release_manifests_router, prefix="/api/admin")


# ============================================================================
# SPA Static Files Configuration
# ============================================================================
# Security: Use centralized security settings for SPA path configuration
# The SPA dist path can be configured via SHUSAI_SPA_DIST_PATH env var
# All static file paths are validated to prevent path traversal attacks
from backend.src.utils.security_settings import (
    get_spa_dist_path,
    is_safe_static_file_path
)

_spa_dist_path = get_spa_dist_path()
_spa_index_path = _spa_dist_path / "index.html"


async def serve_spa(request: Request) -> FileResponse:
    """
    Serve the SPA index.html for client-side routing.

    This handles all non-API routes by returning the SPA's index.html,
    allowing React Router to handle the routing on the client side.

    Args:
        request: The incoming HTTP request

    Returns:
        FileResponse with index.html content
    """
    if not _spa_index_path.exists():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "SPA Not Built",
                "message": "The frontend application has not been built. "
                          "Run 'npm run build' in the frontend directory.",
                "hint": f"Expected path: {_spa_index_path}"
            }
        )
    return FileResponse(_spa_index_path, media_type="text/html")


# Mount static assets if the dist directory exists
# This serves JS, CSS, images, and other assets from frontend/dist/assets/
if _spa_dist_path.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_spa_dist_path / "assets")),
        name="spa-assets"
    )


# Root endpoint - serve SPA
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root(request: Request):
    """Serve the SPA index.html at root."""
    return await serve_spa(request)


# Catch-all route for SPA client-side routing
# This must be registered AFTER all other routes
@app.get("/{full_path:path}", response_class=FileResponse, include_in_schema=False)
async def spa_catch_all(request: Request, full_path: str):
    """
    Catch-all route for SPA client-side routing.

    Handles all routes not matched by API endpoints, serving the SPA's
    index.html so that React Router can handle the routing.

    Note: This route is excluded from OpenAPI schema as it's not an API endpoint.
    """
    # Don't serve SPA for API routes that weren't found (return 404 from API handlers)
    if full_path.startswith("api/"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not Found",
                "message": f"API endpoint '/{full_path}' not found"
            }
        )

    # Check if the requested path is a static file that exists in dist root
    # This handles files like favicon.ico, robots.txt, etc.
    # Security: Use is_safe_static_file_path to validate the path is within
    # the SPA dist directory and doesn't contain path traversal sequences
    if full_path and "." in full_path.split("/")[-1]:
        # Only serve files from the root of dist (not subdirectories)
        # to limit exposure - assets are served via /assets mount
        filename = full_path.split("/")[-1] if "/" in full_path else full_path
        is_safe, safe_path = is_safe_static_file_path(filename, _spa_dist_path)
        if is_safe and safe_path:
            return FileResponse(safe_path)

    return await serve_spa(request)
