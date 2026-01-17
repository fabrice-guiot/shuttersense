"""
FastAPI application entry point for photo-admin backend.

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
    PHOTO_ADMIN_MASTER_KEY: Master encryption key (required)
    PHOTO_ADMIN_ENV: Environment (production/development, default: development)
    PHOTO_ADMIN_LOG_LEVEL: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
    PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS: Comma-separated list of authorized root
        paths for local collections (security - required for local collections)
    PHOTO_ADMIN_SPA_DIST_PATH: Path to SPA dist directory (default: frontend/dist)
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
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
# Configure rate limiter with sensible defaults for single-user deployment
# These protect against runaway scripts and misconfigured clients
limiter = Limiter(key_func=get_remote_address)


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
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking (allow for docs pages)
        if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
            response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # Different CSP for API vs SPA pages
        path = request.url.path
        if path in ["/docs", "/redoc", "/openapi.json"]:
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

    This middleware checks the Content-Length header and rejects
    requests that exceed the configured maximum.
    """

    async def dispatch(self, request: Request, call_next):
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

        return await call_next(request)


def validate_master_key() -> None:
    """
    Validate that PHOTO_ADMIN_MASTER_KEY environment variable is set.

    Raises:
        SystemExit: If master key is not set or invalid

    Note:
        This function is called during application startup to fail fast
        if the encryption key is missing.
    """
    master_key = os.environ.get("PHOTO_ADMIN_MASTER_KEY")

    if not master_key:
        print(
            "\n" + "=" * 70,
            "\nERROR: PHOTO_ADMIN_MASTER_KEY environment variable is not set.",
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
            "\nERROR: PHOTO_ADMIN_MASTER_KEY is invalid.",
            f"\n\nEncryption validation failed: {e}",
            "\n\nThe key must be a valid Fernet key (44 characters, base64-encoded).",
            "\n\nTo generate a new key, run:",
            "\n  python3 setup_master_key.py",
            "\n" + "=" * 70 + "\n",
            file=sys.stderr
        )
        sys.exit(1)


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
    logger.info("Starting photo-admin backend application")

    # Validate master key
    logger.info("Validating PHOTO_ADMIN_MASTER_KEY environment variable")
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

    # NOTE: Default configuration seeding (extensions) is now team-specific
    # and should be done when a team is created, not on application startup.
    # The seed_default_extensions(team_id) method requires a team_id parameter
    # for proper tenant isolation.
    logger.info("Skipping global configuration seeding (tenant-specific data is seeded per-team)")

    logger.info("Photo-admin backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down photo-admin backend application")


# Initialize logging before creating app
init_logging()

# Create FastAPI application
app = FastAPI(
    title="Photo Admin API",
    description="Backend API for photo-admin web application. "
                "Supports remote photo collection management, pipeline configuration, "
                "and analysis tool execution with persistent result storage.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ============================================================================
# Configure Rate Limiter (T168)
# ============================================================================
# Attach limiter to app state for access in routes
app.state.limiter = limiter

# Add rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================================
# Security Middlewares (T169, T170)
# ============================================================================
# Note: Middleware order matters - first added is outermost
# Add request size limit middleware
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
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
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
# Custom OpenAPI Schema with Bearer Token Authentication
# ============================================================================
def custom_openapi():
    """
    Generate custom OpenAPI schema with Bearer token authentication.

    This adds the HTTPBearer security scheme to the OpenAPI spec, enabling
    the "Authorize" button in Swagger UI (/docs) and ReDoc (/redoc).

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
    # Public endpoints: /health, /api/version, /api/auth/*
    public_paths = {"/health", "/api/version"}
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
        }
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
        "service": "photo-admin-backend",
        "version": __version__,
    }


@app.get("/api/version", tags=["System"])
async def get_version() -> Dict[str, str]:
    """
    Get the current version of the photo-admin application.

    This endpoint returns the version number synchronized with GitHub release tags.
    The version is automatically determined from Git tags during development and
    production builds.

    Returns:
        Dictionary with version information
    """
    return {
        "version": __version__,
    }


# API routers
from backend.src.api import collections, connectors, tools, results, pipelines, trends, config, categories, events, locations, organizers, performers
from backend.src.api import auth as auth_router
from backend.src.api import users as users_router
from backend.src.api import tokens as tokens_router
from backend.src.api.admin import teams_router as admin_teams_router

app.include_router(collections.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(organizers.router, prefix="/api")
app.include_router(performers.router, prefix="/api")

# Authentication router
app.include_router(auth_router.router, prefix="/api")

# User management router
app.include_router(users_router.router, prefix="/api")

# Token management routes (Phase 10)
app.include_router(tokens_router.router)

# Admin routes (super admin only)
app.include_router(admin_teams_router, prefix="/api/admin")


# ============================================================================
# SPA Static Files Configuration
# ============================================================================
# Security: Use centralized security settings for SPA path configuration
# The SPA dist path can be configured via PHOTO_ADMIN_SPA_DIST_PATH env var
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
