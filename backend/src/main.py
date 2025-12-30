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
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.src.utils.cache import FileListingCache
from backend.src.utils.job_queue import JobQueue
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import init_logging, get_logger


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
    logger.info("Initializing application state (cache, job queue, encryptor)")
    app.state.file_cache = FileListingCache()
    app.state.job_queue = JobQueue()
    app.state.credential_encryptor = CredentialEncryptor()
    logger.info("Application state initialized successfully")

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
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Configure CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",  # React dev server (alternative)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
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
        "version": "1.0.0",
    }


# API routers
from backend.src.api import collections, connectors

app.include_router(collections.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")


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
