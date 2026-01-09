"""
Structured logging configuration for photo-admin backend.

Provides JSON-formatted logging with file rotation for production environments
and human-readable console logging for development.

Loggers:
- api: HTTP requests, responses, middleware
- services: Business logic operations (collection, pipeline, config services)
- tools: CLI tool execution (PhotoStats, Photo Pairing, Pipeline Validation)
- db: Database operations, migrations, query performance
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON for structured logging.

    Each log record includes:
    - timestamp: ISO 8601 format
    - level: Log level (INFO, ERROR, etc.)
    - logger: Logger name (api, services, tools, db)
    - message: Log message
    - module: Python module name
    - function: Function name where log was created
    - line: Line number
    - Additional fields: exception info, extra fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present (from logger.info("msg", extra={...}))
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for console output in development.

    Format: [TIMESTAMP] LEVEL - LOGGER - MESSAGE
    Example: [2025-12-29 10:30:45] INFO - api - GET /api/collections 200 OK
    """

    def __init__(self):
        super().__init__(
            fmt="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def _get_log_level() -> int:
    """
    Get log level from environment variable.

    Returns:
        Log level constant (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Environment Variables:
        PHOTO_ADMIN_LOG_LEVEL: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                               Defaults to INFO
    """
    level_str = os.environ.get("PHOTO_ADMIN_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def _get_log_dir() -> Path:
    """
    Get log directory path from environment variable or use default.

    Returns:
        Path to log directory

    Environment Variables:
        PHOTO_ADMIN_LOG_DIR: Custom log directory path
                             Defaults to ./logs (relative to CWD)
    """
    log_dir_str = os.environ.get("PHOTO_ADMIN_LOG_DIR", "logs")
    log_dir = Path(log_dir_str)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _is_production() -> bool:
    """
    Check if running in production environment.

    Returns:
        True if production, False if development

    Environment Variables:
        PHOTO_ADMIN_ENV: Environment name (production, development, test)
                         Defaults to development
    """
    env = os.environ.get("PHOTO_ADMIN_ENV", "development").lower()
    return env == "production"


def configure_logging() -> Dict[str, logging.Logger]:
    """
    Configure structured logging for the photo-admin backend.

    Behavior:
    - Production (PHOTO_ADMIN_ENV=production):
      * JSON-formatted logs to files with rotation
      * Separate files per logger: api.log, services.log, tools.log, db.log
      * File rotation: 10MB max size, 5 backup files

    - Development (default):
      * Human-readable console output
      * No file logging

    Returns:
        Dictionary mapping logger names to configured Logger instances:
        - "api": Logger for API endpoints and middleware
        - "services": Logger for business logic services
        - "tools": Logger for CLI tool execution
        - "db": Logger for database operations

    Example:
        >>> loggers = configure_logging()
        >>> loggers["api"].info("GET /api/collections", extra={"status_code": 200})
        >>> loggers["services"].error("Collection not found", extra={"collection_id": 123})
    """
    # Get configuration
    log_level = _get_log_level()
    is_prod = _is_production()
    log_dir = _get_log_dir() if is_prod else None

    # Logger names
    logger_names = ["api", "services", "tools", "db", "websocket"]
    loggers = {}

    for logger_name in logger_names:
        logger = logging.getLogger(f"photo_admin.{logger_name}")
        logger.setLevel(log_level)
        logger.propagate = False  # Don't propagate to root logger

        # Remove existing handlers
        logger.handlers.clear()

        if is_prod:
            # Production: JSON logs to rotating file
            log_file = log_dir / f"{logger_name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        else:
            # Development: Human-readable console output
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(ConsoleFormatter())
            logger.addHandler(console_handler)

        loggers[logger_name] = logger

    return loggers


# Singleton logger instances
_loggers: Optional[Dict[str, logging.Logger]] = None


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger by name.

    Args:
        name: Logger name (api, services, tools, db, websocket)

    Returns:
        Configured Logger instance

    Raises:
        ValueError: If logger name is not recognized

    Example:
        >>> logger = get_logger("api")
        >>> logger.info("Request received", extra={"method": "GET", "path": "/collections"})
    """
    global _loggers

    if _loggers is None:
        _loggers = configure_logging()

    if name not in _loggers:
        raise ValueError(
            f"Unknown logger name: {name}. "
            f"Valid names: {', '.join(_loggers.keys())}"
        )

    return _loggers[name]


def init_logging() -> Dict[str, logging.Logger]:
    """
    Initialize logging configuration (called on application startup).

    Returns:
        Dictionary of configured loggers

    Example:
        >>> # In FastAPI main.py startup event
        >>> @app.on_event("startup")
        >>> async def startup():
        >>>     init_logging()
    """
    global _loggers
    _loggers = configure_logging()
    return _loggers
