"""
SQLAlchemy models for photo-admin application.

This module provides the declarative base class and imports all models
to ensure they are registered with SQLAlchemy's metadata.
"""

import enum
from sqlalchemy.orm import declarative_base

# Create the declarative base class
# All models will inherit from this Base class
Base = declarative_base()


# ============================================================================
# Shared Enums
# ============================================================================


class ResultStatus(enum.Enum):
    """Status of an analysis result after tool execution."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ToolType(enum.Enum):
    """Available analysis tools."""
    PHOTOSTATS = "photostats"
    PHOTO_PAIRING = "photo_pairing"
    PIPELINE_VALIDATION = "pipeline_validation"


# Import all models here so they are registered with Base.metadata
# This is required for Alembic autogenerate to detect models

# Connector and Collection models (User Story 1)
from backend.src.models.connector import Connector, ConnectorType
from backend.src.models.collection import Collection, CollectionType, CollectionState

# Pipeline models (must be imported before AnalysisResult due to FK reference)
from backend.src.models.pipeline import Pipeline
from backend.src.models.pipeline_history import PipelineHistory

# Analysis Result model
from backend.src.models.analysis_result import AnalysisResult

# Configuration model
from backend.src.models.configuration import Configuration, ConfigSource

# Calendar Events models (Issue #39)
# Import order matters due to FK relationships
from backend.src.models.category import Category
from backend.src.models.location import Location
from backend.src.models.organizer import Organizer
from backend.src.models.performer import Performer
from backend.src.models.event_series import EventSeries
from backend.src.models.event import (
    Event,
    EventStatus,
    AttendanceStatus,
    TicketStatus,
    TimeoffStatus,
    TravelStatus,
)
from backend.src.models.event_performer import EventPerformer, PerformerStatus

# User Management models (Issue #73)
from backend.src.models.team import Team
from backend.src.models.user import User, UserStatus, UserType
from backend.src.models.api_token import ApiToken

# Export Base and all models
__all__ = [
    "Base",
    # Enums
    "ResultStatus",
    "ToolType",
    "ConfigSource",
    # Connector
    "Connector",
    "ConnectorType",
    # Collection
    "Collection",
    "CollectionType",
    "CollectionState",
    # Pipeline
    "Pipeline",
    "PipelineHistory",
    # Analysis
    "AnalysisResult",
    # Configuration
    "Configuration",
    # Calendar Events (Issue #39)
    "Category",
    "Location",
    "Organizer",
    "Performer",
    "EventSeries",
    "Event",
    "EventStatus",
    "AttendanceStatus",
    "TicketStatus",
    "TimeoffStatus",
    "TravelStatus",
    "EventPerformer",
    "PerformerStatus",
    # User Management (Issue #73)
    "Team",
    "User",
    "UserStatus",
    "UserType",
    "ApiToken",
]
