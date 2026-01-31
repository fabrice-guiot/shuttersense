"""
Unit tests for audit trail API response integration.

Issue #120: Audit Trail Visibility Enhancement (NFR-400.3)
Tests that build_audit_info helper works correctly and that entity
response schemas include the audit field with proper user summaries.
"""

import pytest
from datetime import datetime

from backend.src.schemas.audit import (
    AuditInfo,
    AuditUserSummary,
    build_audit_info,
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockUser:
    """Simulates a User model instance for testing."""

    def __init__(self, guid="usr_01test", display_name="Test User", email="test@example.com"):
        self.guid = guid
        self.display_name = display_name
        self.email = email


class MockModel:
    """Simulates a model instance with audit columns."""

    def __init__(
        self,
        created_at=None,
        updated_at=None,
        created_by_user=None,
        updated_by_user=None,
    ):
        self.created_at = created_at or datetime(2026, 1, 15, 10, 0, 0)
        self.updated_at = updated_at or datetime(2026, 1, 20, 9, 30, 0)
        self.created_by_user = created_by_user
        self.updated_by_user = updated_by_user


class MockGroupBModel:
    """Simulates a Group B model with 'created_by' relationship name."""

    def __init__(
        self,
        created_at=None,
        updated_at=None,
        created_by=None,
        updated_by_user=None,
    ):
        self.created_at = created_at or datetime(2026, 1, 15, 10, 0, 0)
        self.updated_at = updated_at or datetime(2026, 1, 20, 9, 30, 0)
        self.created_by = created_by
        self.updated_by_user = updated_by_user


# ---------------------------------------------------------------------------
# Tests: build_audit_info helper
# ---------------------------------------------------------------------------

class TestBuildAuditInfo:
    """Tests for the build_audit_info helper function."""

    def test_full_data_both_users(self):
        """build_audit_info returns correct dict with both users present."""
        creator = MockUser(
            guid="usr_01creator", display_name="Creator", email="creator@example.com"
        )
        updater = MockUser(
            guid="usr_02updater", display_name="Updater", email="updater@example.com"
        )
        model = MockModel(created_by_user=creator, updated_by_user=updater)

        result = build_audit_info(model)

        assert result is not None
        assert result["created_at"] == model.created_at
        assert result["updated_at"] == model.updated_at
        assert result["created_by"]["guid"] == "usr_01creator"
        assert result["created_by"]["display_name"] == "Creator"
        assert result["created_by"]["email"] == "creator@example.com"
        assert result["updated_by"]["guid"] == "usr_02updater"

    def test_null_users_historical_record(self):
        """build_audit_info returns null users for historical records."""
        model = MockModel(created_by_user=None, updated_by_user=None)

        result = build_audit_info(model)

        assert result is not None
        assert result["created_by"] is None
        assert result["updated_by"] is None
        assert result["created_at"] == model.created_at
        assert result["updated_at"] == model.updated_at

    def test_mixed_null_created_present_updated_null(self):
        """build_audit_info handles created_by present but updated_by null."""
        creator = MockUser()
        model = MockModel(created_by_user=creator, updated_by_user=None)

        result = build_audit_info(model)

        assert result["created_by"] is not None
        assert result["updated_by"] is None

    def test_returns_none_when_no_created_at(self):
        """build_audit_info returns None for non-auditable objects."""
        class NoTimestamps:
            pass

        result = build_audit_info(NoTimestamps())
        assert result is None

    def test_updated_at_falls_back_to_created_at(self):
        """build_audit_info uses created_at when updated_at is missing."""
        class NoUpdatedAt:
            created_at = datetime(2026, 1, 10, 8, 0, 0)
            created_by_user = None
            updated_by_user = None

        result = build_audit_info(NoUpdatedAt())

        assert result["updated_at"] == datetime(2026, 1, 10, 8, 0, 0)

    def test_group_b_created_by_attr(self):
        """build_audit_info uses custom created_by_attr for Group B models."""
        creator = MockUser(guid="usr_admin", email="admin@example.com")
        model = MockGroupBModel(created_by=creator)

        result = build_audit_info(model, created_by_attr="created_by")

        assert result["created_by"]["guid"] == "usr_admin"
        assert result["created_by"]["email"] == "admin@example.com"

    def test_validates_into_audit_info_schema(self):
        """build_audit_info dict validates into AuditInfo Pydantic model."""
        creator = MockUser()
        model = MockModel(created_by_user=creator)

        result = build_audit_info(model)
        info = AuditInfo.model_validate(result)

        assert isinstance(info, AuditInfo)
        assert isinstance(info.created_by, AuditUserSummary)
        assert info.created_by.guid == creator.guid
        assert info.created_by.email == creator.email
        assert info.updated_by is None


# ---------------------------------------------------------------------------
# Tests: AuditUserSummary
# ---------------------------------------------------------------------------

class TestAuditUserSummary:
    """Tests for AuditUserSummary schema."""

    def test_from_user_model(self):
        """AuditUserSummary validates from a User-like object."""
        user = MockUser(
            guid="usr_01abc", display_name="John Doe", email="john@example.com"
        )
        summary = AuditUserSummary.model_validate(user, from_attributes=True)

        assert summary.guid == "usr_01abc"
        assert summary.display_name == "John Doe"
        assert summary.email == "john@example.com"

    def test_null_display_name(self):
        """AuditUserSummary allows null display_name (system users)."""
        user = MockUser(guid="usr_system", display_name=None, email="system@local")
        summary = AuditUserSummary.model_validate(user, from_attributes=True)

        assert summary.display_name is None
        assert summary.email == "system@local"

    def test_contains_guid_not_id(self):
        """AuditUserSummary exposes guid, not internal numeric id."""
        summary = AuditUserSummary(
            guid="usr_01xyz", display_name="Test", email="t@test.com"
        )
        assert hasattr(summary, "guid")
        assert not hasattr(summary, "id")


# ---------------------------------------------------------------------------
# Tests: Schema integration (CategoryResponse as representative)
# ---------------------------------------------------------------------------

class TestSchemaAuditFieldIntegration:
    """Tests that entity response schemas accept the audit field."""

    def test_category_response_with_audit(self):
        """CategoryResponse includes audit field when populated."""
        from backend.src.schemas.category import CategoryResponse

        data = {
            "guid": "cat_01test",
            "name": "Test",
            "icon": "star",
            "color": "#FF0000",
            "is_active": True,
            "display_order": 0,
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 20, 9, 0, 0),
            "audit": {
                "created_at": datetime(2026, 1, 15, 10, 0, 0),
                "created_by": {
                    "guid": "usr_01abc",
                    "display_name": "Creator",
                    "email": "creator@test.com",
                },
                "updated_at": datetime(2026, 1, 20, 9, 0, 0),
                "updated_by": None,
            },
        }
        resp = CategoryResponse.model_validate(data)

        assert resp.audit is not None
        assert resp.audit.created_by.guid == "usr_01abc"
        assert resp.audit.updated_by is None

    def test_category_response_without_audit(self):
        """CategoryResponse works without audit field (backward compat)."""
        from backend.src.schemas.category import CategoryResponse

        data = {
            "guid": "cat_01test",
            "name": "Test",
            "icon": None,
            "color": None,
            "is_active": True,
            "display_order": 0,
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 20, 9, 0, 0),
        }
        resp = CategoryResponse.model_validate(data)

        assert resp.audit is None

    def test_pipeline_response_with_audit(self):
        """PipelineResponse includes audit field when populated."""
        from backend.src.schemas.pipelines import PipelineResponse

        data = {
            "guid": "pip_01test",
            "name": "Test Pipeline",
            "nodes": [],
            "edges": [],
            "is_active": True,
            "is_default": False,
            "is_valid": True,
            "version": 1,
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 20, 9, 0, 0),
            "audit": {
                "created_at": datetime(2026, 1, 15, 10, 0, 0),
                "created_by": None,
                "updated_at": datetime(2026, 1, 20, 9, 0, 0),
                "updated_by": None,
            },
        }
        resp = PipelineResponse.model_validate(data)

        assert resp.audit is not None
        assert resp.audit.created_by is None
        assert resp.audit.updated_by is None


# ---------------------------------------------------------------------------
# Tests: ORM integration via AuditMixin.audit property
# ---------------------------------------------------------------------------

class TestAuditMixinProperty:
    """Tests that AuditMixin audit property produces valid audit dicts."""

    def test_audit_mixin_property_with_db(
        self, test_db_session, test_team, test_user
    ):
        """AuditMixin.audit property returns valid dict from real model."""
        from backend.src.services.category_service import CategoryService

        service = CategoryService(test_db_session)
        category = service.create(
            name="Audit Property Test",
            team_id=test_team.id,
            user_id=test_user.id,
        )

        audit = category.audit

        assert audit is not None
        assert audit["created_at"] == category.created_at
        assert audit["created_by"]["guid"] == test_user.guid
        assert audit["created_by"]["email"] == test_user.email

        # Validate into AuditInfo
        info = AuditInfo.model_validate(audit)
        assert info.created_by.guid == test_user.guid

    def test_audit_mixin_property_null_users(self, test_db_session, test_team):
        """AuditMixin.audit property handles null users (no user_id)."""
        from backend.src.services.category_service import CategoryService

        service = CategoryService(test_db_session)
        category = service.create(
            name="No User Category",
            team_id=test_team.id,
        )

        audit = category.audit

        assert audit is not None
        assert audit["created_by"] is None
        assert audit["updated_by"] is None
