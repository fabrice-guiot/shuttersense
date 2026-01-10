"""
Model mixins for shared functionality across entities.

This module provides reusable SQLAlchemy mixins that can be inherited
by multiple models to add common functionality.
"""

from backend.src.models.mixins.guid import GuidMixin

__all__ = ["GuidMixin"]
