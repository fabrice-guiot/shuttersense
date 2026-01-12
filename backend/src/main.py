"""
FastAPI application entry point for photo-admin backend.

This module initializes the FastAPI application with:
- Application state (FileListingCache, JobQueue, CredentialEncryptor)
- CORS middleware for frontend development
- Exception handlers for consistent error responses
- Startup event handlers for environment validation
- Logging configuration

Environment Variables:
    PHOTO_ADMIN_MASTER_KEY: Master encryption key (required)
    PHOTO_ADMIN_ENV: Environment (production/development, default: development)
    PHOTO_ADMIN_LOG_LEVEL: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
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
        # Skip restrictive CSP for documentation pages (Swagger UI needs external resources)
        if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
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

    # Seed default configuration (extension keys must always exist)
    # Skip during testing to avoid database session conflicts
    if os.environ.get('PYTEST_CURRENT_TEST') is None:
        logger.info("Seeding default configuration values")
        db = SessionLocal()
        try:
            config_service = ConfigService(db)
            config_service.seed_default_extensions()
            logger.info("Default configuration seeded successfully")
        finally:
            db.close()
    else:
        logger.info("Skipping configuration seeding in test environment")

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


# Root endpoint


@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint with API information.

    Returns:
        API metadata and documentation links
    """
    return {
        "message": "Photo Admin API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }
