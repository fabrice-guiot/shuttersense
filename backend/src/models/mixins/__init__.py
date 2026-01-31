"""
Model mixins for shared functionality across entities.

This module provides reusable SQLAlchemy mixins that can be inherited
by multiple models to add common functionality.
"""

from backend.src.models.mixins.guid import GuidMixin
from backend.src.models.mixins.audit import AuditMixin

__all__ = ["GuidMixin", "AuditMixin"]
