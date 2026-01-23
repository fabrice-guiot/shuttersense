"""
Unit tests for RetentionService.

Issue #92: Storage Optimization for Analysis Results
Tests retention settings retrieval, updates, validation, and defaults.
"""

import pytest

from backend.src.middleware.tenant import TenantContext
from backend.src.models import Configuration, ConfigSource
from backend.src.services.retention_service import (
    RetentionService,
    RETENTION_CATEGORY,
    KEY_JOB_COMPLETED_DAYS,
    KEY_JOB_FAILED_DAYS,
    KEY_RESULT_COMPLETED_DAYS,
    KEY_PRESERVE_PER_COLLECTION,
)
from backend.src.schemas.retention import (
    RetentionSettingsUpdate,
    DEFAULT_JOB_COMPLETED_DAYS,
    DEFAULT_JOB_FAILED_DAYS,
    DEFAULT_RESULT_COMPLETED_DAYS,
    DEFAULT_PRESERVE_PER_COLLECTION,
    VALID_RETENTION_DAYS,
    VALID_PRESERVE_COUNTS,
)
from backend.src.services.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def retention_service(test_db_session):
    """Create a RetentionService instance."""
    return RetentionService(test_db_session)


@pytest.fixture
def sample_retention_setting(test_db_session, test_team):
    """Factory for creating sample retention settings."""
    def _create(key, value, team_id=None):
        config = Configuration(
            category=RETENTION_CATEGORY,
            key=key,
            value_json=value,
            source=ConfigSource.DATABASE,
            team_id=team_id if team_id is not None else test_team.id
        )
        test_db_session.add(config)
        test_db_session.commit()
        test_db_session.refresh(config)
        return config
    return _create


# ============================================================================
# Test: get_settings
# ============================================================================

class TestGetSettings:
    """Tests for RetentionService.get_settings."""

    def test_returns_defaults_when_no_settings_exist(
        self, retention_service, test_tenant_context
    ):
        """Should return default values when no settings are configured."""
        settings = retention_service.get_settings(test_tenant_context)

        assert settings.job_completed_days == DEFAULT_JOB_COMPLETED_DAYS
        assert settings.job_failed_days == DEFAULT_JOB_FAILED_DAYS
        assert settings.result_completed_days == DEFAULT_RESULT_COMPLETED_DAYS
        assert settings.preserve_per_collection == DEFAULT_PRESERVE_PER_COLLECTION

    def test_returns_configured_settings(
        self, retention_service, test_tenant_context, sample_retention_setting
    ):
        """Should return configured values when settings exist."""
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)
        sample_retention_setting(KEY_JOB_FAILED_DAYS, 14)
        sample_retention_setting(KEY_RESULT_COMPLETED_DAYS, 30)
        sample_retention_setting(KEY_PRESERVE_PER_COLLECTION, 3)

        settings = retention_service.get_settings(test_tenant_context)

        assert settings.job_completed_days == 7
        assert settings.job_failed_days == 14
        assert settings.result_completed_days == 30
        assert settings.preserve_per_collection == 3

    def test_returns_mix_of_defaults_and_configured(
        self, retention_service, test_tenant_context, sample_retention_setting
    ):
        """Should return defaults for missing settings and configured values for existing."""
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 14)
        # Other settings not configured

        settings = retention_service.get_settings(test_tenant_context)

        assert settings.job_completed_days == 14  # Configured
        assert settings.job_failed_days == DEFAULT_JOB_FAILED_DAYS  # Default
        assert settings.result_completed_days == DEFAULT_RESULT_COMPLETED_DAYS  # Default
        assert settings.preserve_per_collection == DEFAULT_PRESERVE_PER_COLLECTION  # Default

    def test_tenant_isolation(
        self, retention_service, test_db_session, test_team, test_tenant_context, sample_retention_setting
    ):
        """Should only return settings for the specified team."""
        # Create another team
        from backend.src.models import Team
        other_team = Team(name='Other Team', slug='other-team', is_active=True)
        test_db_session.add(other_team)
        test_db_session.commit()

        # Configure settings for test_team only
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 30, team_id=test_team.id)

        # Test team should have configured value
        settings = retention_service.get_settings(test_tenant_context)
        assert settings.job_completed_days == 30

        # Other team should have default (use get_settings_by_team_id for internal lookup)
        other_settings = retention_service.get_settings_by_team_id(other_team.id)
        assert other_settings.job_completed_days == DEFAULT_JOB_COMPLETED_DAYS


# ============================================================================
# Test: update_settings
# ============================================================================

class TestUpdateSettings:
    """Tests for RetentionService.update_settings."""

    def test_updates_single_setting(
        self, retention_service, test_tenant_context
    ):
        """Should update a single setting and return all settings."""
        update = RetentionSettingsUpdate(job_completed_days=7)
        settings = retention_service.update_settings(test_tenant_context, update)

        assert settings.job_completed_days == 7
        assert settings.job_failed_days == DEFAULT_JOB_FAILED_DAYS
        assert settings.result_completed_days == DEFAULT_RESULT_COMPLETED_DAYS
        assert settings.preserve_per_collection == DEFAULT_PRESERVE_PER_COLLECTION

    def test_updates_multiple_settings(
        self, retention_service, test_tenant_context
    ):
        """Should update multiple settings at once."""
        update = RetentionSettingsUpdate(
            job_completed_days=14,
            job_failed_days=30,
            preserve_per_collection=5
        )
        settings = retention_service.update_settings(test_tenant_context, update)

        assert settings.job_completed_days == 14
        assert settings.job_failed_days == 30
        assert settings.result_completed_days == DEFAULT_RESULT_COMPLETED_DAYS
        assert settings.preserve_per_collection == 5

    def test_empty_update_returns_current_settings(
        self, retention_service, test_tenant_context, sample_retention_setting
    ):
        """Should return current settings when no fields are provided."""
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)

        update = RetentionSettingsUpdate()  # No fields set
        settings = retention_service.update_settings(test_tenant_context, update)

        assert settings.job_completed_days == 7

    def test_overwrites_existing_setting(
        self, retention_service, test_tenant_context, sample_retention_setting
    ):
        """Should overwrite existing setting value."""
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)

        update = RetentionSettingsUpdate(job_completed_days=30)
        settings = retention_service.update_settings(test_tenant_context, update)

        assert settings.job_completed_days == 30

    def test_validates_retention_days_values(self):
        """Should reject invalid retention days values at schema level."""
        # Valid values are: 0, 1, 2, 5, 7, 14, 30, 90, 180, 365
        # 3 is not valid - Pydantic validates this at schema level
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError) as exc_info:
            RetentionSettingsUpdate(job_completed_days=3)  # type: ignore

        assert "job_completed_days" in str(exc_info.value)

    def test_validates_preserve_count_values(self):
        """Should reject invalid preserve count values at schema level."""
        # Valid values are: 1, 2, 3, 5, 10
        # 4 is not valid - Pydantic validates this at schema level
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError) as exc_info:
            RetentionSettingsUpdate(preserve_per_collection=4)  # type: ignore

        assert "preserve_per_collection" in str(exc_info.value)

    def test_accepts_all_valid_retention_days(
        self, retention_service, test_tenant_context
    ):
        """Should accept all valid retention days values."""
        for value in VALID_RETENTION_DAYS:
            update = RetentionSettingsUpdate(job_completed_days=value)
            settings = retention_service.update_settings(test_tenant_context, update)
            assert settings.job_completed_days == value

    def test_accepts_all_valid_preserve_counts(
        self, retention_service, test_tenant_context
    ):
        """Should accept all valid preserve count values."""
        for value in VALID_PRESERVE_COUNTS:
            update = RetentionSettingsUpdate(preserve_per_collection=value)
            settings = retention_service.update_settings(test_tenant_context, update)
            assert settings.preserve_per_collection == value


# ============================================================================
# Test: seed_defaults
# ============================================================================

class TestSeedDefaults:
    """Tests for RetentionService.seed_defaults."""

    def test_seeds_all_defaults(
        self, retention_service, test_team, test_db_session
    ):
        """Should create all default retention settings."""
        retention_service.seed_defaults(test_team.id)

        # Verify all settings were created
        configs = (
            test_db_session.query(Configuration)
            .filter(
                Configuration.team_id == test_team.id,
                Configuration.category == RETENTION_CATEGORY
            )
            .all()
        )

        assert len(configs) == 4  # All 4 settings

        config_map = {c.key: c.value_json for c in configs}
        assert config_map[KEY_JOB_COMPLETED_DAYS] == DEFAULT_JOB_COMPLETED_DAYS
        assert config_map[KEY_JOB_FAILED_DAYS] == DEFAULT_JOB_FAILED_DAYS
        assert config_map[KEY_RESULT_COMPLETED_DAYS] == DEFAULT_RESULT_COMPLETED_DAYS
        assert config_map[KEY_PRESERVE_PER_COLLECTION] == DEFAULT_PRESERVE_PER_COLLECTION

    def test_does_not_overwrite_existing_settings(
        self, retention_service, test_team, sample_retention_setting, test_db_session
    ):
        """Should not overwrite existing settings when seeding."""
        # Create a custom setting before seeding
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 30)

        retention_service.seed_defaults(test_team.id)

        # Verify custom setting was preserved
        config = (
            test_db_session.query(Configuration)
            .filter(
                Configuration.team_id == test_team.id,
                Configuration.category == RETENTION_CATEGORY,
                Configuration.key == KEY_JOB_COMPLETED_DAYS
            )
            .first()
        )

        assert config.value_json == 30  # Custom value preserved

    def test_seeds_missing_settings_only(
        self, retention_service, test_team, sample_retention_setting, test_db_session
    ):
        """Should only seed missing settings, not existing ones."""
        # Create some settings before seeding
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 30)
        sample_retention_setting(KEY_PRESERVE_PER_COLLECTION, 5)

        retention_service.seed_defaults(test_team.id)

        configs = (
            test_db_session.query(Configuration)
            .filter(
                Configuration.team_id == test_team.id,
                Configuration.category == RETENTION_CATEGORY
            )
            .all()
        )

        config_map = {c.key: c.value_json for c in configs}

        # Custom values preserved
        assert config_map[KEY_JOB_COMPLETED_DAYS] == 30
        assert config_map[KEY_PRESERVE_PER_COLLECTION] == 5
        # Defaults seeded for missing
        assert config_map[KEY_JOB_FAILED_DAYS] == DEFAULT_JOB_FAILED_DAYS
        assert config_map[KEY_RESULT_COMPLETED_DAYS] == DEFAULT_RESULT_COMPLETED_DAYS

    def test_idempotent_seeding(
        self, retention_service, test_team, test_db_session
    ):
        """Should be safe to call seed_defaults multiple times."""
        retention_service.seed_defaults(test_team.id)
        retention_service.seed_defaults(test_team.id)  # Second call

        # Should still have exactly 4 settings
        configs = (
            test_db_session.query(Configuration)
            .filter(
                Configuration.team_id == test_team.id,
                Configuration.category == RETENTION_CATEGORY
            )
            .all()
        )

        assert len(configs) == 4
