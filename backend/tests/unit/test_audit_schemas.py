"""
Unit tests for AuditUserSummary and AuditInfo Pydantic schemas.

Issue #120: Audit Trail Visibility Enhancement (NFR-400.3)
Tests schema serialization with full data, null users, mixed null,
and from_attributes ORM conversion.

NOTE: build_audit_info helper tests belong in test_audit_responses.py (Phase 3 T064a).
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.src.schemas.audit import AuditUserSummary, AuditInfo


class TestAuditUserSummary:
    """Tests for AuditUserSummary schema serialization."""

    def test_full_user_summary(self):
        """AuditUserSummary should serialize with all fields."""
        summary = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000001",
            display_name="John Doe",
            email="john@example.com",
        )
        assert summary.guid == "usr_01hgw2bbg0000000000000001"
        assert summary.display_name == "John Doe"
        assert summary.email == "john@example.com"

    def test_null_display_name(self):
        """AuditUserSummary should accept null display_name (system users)."""
        summary = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000002",
            display_name=None,
            email="system@system.local",
        )
        assert summary.display_name is None
        assert summary.email == "system@system.local"

    def test_json_serialization(self):
        """AuditUserSummary should serialize to JSON correctly."""
        summary = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000001",
            display_name="John Doe",
            email="john@example.com",
        )
        data = summary.model_dump()
        assert data == {
            "guid": "usr_01hgw2bbg0000000000000001",
            "display_name": "John Doe",
            "email": "john@example.com",
        }

    def test_json_null_display_name(self):
        """AuditUserSummary with null display_name should serialize null."""
        summary = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000002",
            display_name=None,
            email="agent@system.local",
        )
        data = summary.model_dump()
        assert data["display_name"] is None

    def test_guid_required(self):
        """AuditUserSummary should require guid."""
        with pytest.raises(ValidationError):
            AuditUserSummary(display_name="Test", email="test@example.com")

    def test_email_optional(self):
        """AuditUserSummary should default email to None when omitted."""
        summary = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000001",
            display_name="Test",
        )
        assert summary.email is None

    def test_from_orm_user(self, test_user):
        """AuditUserSummary should be constructable from User model attributes."""
        summary = AuditUserSummary(
            guid=test_user.guid,
            display_name=test_user.display_name,
            email=test_user.email,
        )
        assert summary.guid == test_user.guid
        assert summary.display_name == test_user.display_name
        assert summary.email == test_user.email


class TestAuditInfo:
    """Tests for AuditInfo schema serialization."""

    def test_full_audit_info(self):
        """AuditInfo should serialize with both users present."""
        created_by = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000001",
            display_name="Creator",
            email="creator@example.com",
        )
        updated_by = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000002",
            display_name="Modifier",
            email="modifier@example.com",
        )
        audit = AuditInfo(
            created_at=datetime(2026, 1, 15, 15, 45, 0),
            created_by=created_by,
            updated_at=datetime(2026, 1, 20, 9, 12, 0),
            updated_by=updated_by,
        )
        assert audit.created_by.guid == "usr_01hgw2bbg0000000000000001"
        assert audit.updated_by.guid == "usr_01hgw2bbg0000000000000002"
        assert audit.created_at == datetime(2026, 1, 15, 15, 45, 0)
        assert audit.updated_at == datetime(2026, 1, 20, 9, 12, 0)

    def test_null_users_historical_record(self):
        """AuditInfo should accept null for both users (historical records)."""
        audit = AuditInfo(
            created_at=datetime(2025, 12, 1, 10, 0, 0),
            created_by=None,
            updated_at=datetime(2025, 12, 15, 14, 30, 0),
            updated_by=None,
        )
        assert audit.created_by is None
        assert audit.updated_by is None
        assert audit.created_at == datetime(2025, 12, 1, 10, 0, 0)

    def test_mixed_null_created_by_only(self):
        """AuditInfo should handle created_by present but updated_by null."""
        created_by = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000001",
            display_name="Creator",
            email="creator@example.com",
        )
        audit = AuditInfo(
            created_at=datetime(2026, 1, 15, 15, 45, 0),
            created_by=created_by,
            updated_at=datetime(2026, 1, 15, 15, 45, 0),
            updated_by=None,
        )
        assert audit.created_by is not None
        assert audit.updated_by is None

    def test_mixed_null_updated_by_only(self):
        """AuditInfo should handle updated_by present but created_by null."""
        updated_by = AuditUserSummary(
            guid="usr_01hgw2bbg0000000000000002",
            display_name="Modifier",
            email="modifier@example.com",
        )
        audit = AuditInfo(
            created_at=datetime(2026, 1, 15, 15, 45, 0),
            created_by=None,
            updated_at=datetime(2026, 1, 20, 9, 12, 0),
            updated_by=updated_by,
        )
        assert audit.created_by is None
        assert audit.updated_by is not None

    def test_json_serialization_full(self):
        """AuditInfo should serialize to JSON with nested user summaries."""
        audit = AuditInfo(
            created_at=datetime(2026, 1, 15, 15, 45, 0),
            created_by=AuditUserSummary(
                guid="usr_01hgw2bbg0000000000000001",
                display_name="John",
                email="john@example.com",
            ),
            updated_at=datetime(2026, 1, 20, 9, 12, 0),
            updated_by=AuditUserSummary(
                guid="usr_01hgw2bbg0000000000000002",
                display_name="Jane",
                email="jane@example.com",
            ),
        )
        data = audit.model_dump()
        assert data["created_by"]["guid"] == "usr_01hgw2bbg0000000000000001"
        assert data["updated_by"]["email"] == "jane@example.com"

    def test_json_serialization_null_users(self):
        """AuditInfo should serialize null users as null in JSON."""
        audit = AuditInfo(
            created_at=datetime(2025, 12, 1, 10, 0, 0),
            created_by=None,
            updated_at=datetime(2025, 12, 15, 14, 30, 0),
            updated_by=None,
        )
        data = audit.model_dump()
        assert data["created_by"] is None
        assert data["updated_by"] is None

    def test_timestamps_required(self):
        """AuditInfo should require both timestamps."""
        with pytest.raises(Exception):
            AuditInfo(created_by=None, updated_by=None)
