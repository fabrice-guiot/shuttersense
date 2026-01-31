"""
Audit mixin for SQLAlchemy models.

Provides user attribution columns and relationships to track who created
and last modified each record. Uses select loading (lazy="select") to
avoid cascading JOIN chains through User's own eager relationships.

Design:
- created_by_user_id: Set once on creation, never modified afterward.
- updated_by_user_id: Set on creation and updated on every mutation.
- Both nullable for historical records (pre-existing data without attribution).
- FK ON DELETE SET NULL: User deletion clears attribution rather than blocking.

Immutability of created_by_user_id is enforced at two levels:
1. Service layer: update methods never modify created_by_user_id.
2. PostgreSQL trigger: BEFORE UPDATE trigger rejects created_by_user_id changes
   (created in migration 058_add_audit_user_columns).

Issue #120: Audit Trail Visibility Enhancement
"""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, declared_attr


class AuditMixin:
    """
    Mixin providing user attribution columns for audit trail visibility.

    Adds:
    - created_by_user_id: FK to users.id (who created the record)
    - updated_by_user_id: FK to users.id (who last modified the record)
    - created_by_user: User relationship for created_by (lazy select)
    - updated_by_user: User relationship for updated_by (lazy select)

    Usage:
        class MyEntity(Base, GuidMixin, AuditMixin):
            __tablename__ = "my_entities"
            # ... other columns

    Note:
        Group B entities (Agent, ApiToken, AgentRegistrationToken) already
        have created_by_user_id and should NOT use this mixin. They add
        updated_by_user_id manually instead.
    """

    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    updated_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    @declared_attr
    def created_by_user(cls):
        return relationship(
            "User",
            foreign_keys=[cls.created_by_user_id],
            lazy="select",
        )

    @declared_attr
    def updated_by_user(cls):
        return relationship(
            "User",
            foreign_keys=[cls.updated_by_user_id],
            lazy="select",
        )

    @property
    def audit(self):
        """Computed audit info dict for API serialization via from_attributes."""
        from backend.src.schemas.audit import build_audit_info
        return build_audit_info(self)
