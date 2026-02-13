"""
Tests for conflict rules and scoring weights seeding.

Verifies idempotency, correct entry counts, and that
seed methods do NOT commit (caller responsibility).
"""

import pytest
from unittest.mock import MagicMock, call

from backend.src.services.seed_data_service import (
    SeedDataService,
    DEFAULT_CONFLICT_RULES,
    DEFAULT_SCORING_WEIGHTS,
)
from backend.src.models import Configuration, ConfigSource


class TestSeedConflictRules:
    """Tests for seed_conflict_rules()."""

    def test_creates_all_entries(self, test_db_session, test_team):
        """Should create 5 conflict rule entries for a new team."""
        service = SeedDataService(test_db_session)
        count = service.seed_conflict_rules(test_team.id)
        test_db_session.flush()

        assert count == 5

        # Verify entries in session (not committed yet)
        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "conflict_rules",
        ).all()
        assert len(configs) == 5

    def test_idempotent(self, test_db_session, test_team):
        """Running twice should not create duplicates."""
        service = SeedDataService(test_db_session)
        first_count = service.seed_conflict_rules(test_team.id)
        test_db_session.flush()  # Make first batch visible to queries

        second_count = service.seed_conflict_rules(test_team.id)

        assert first_count == 5
        assert second_count == 0

        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "conflict_rules",
        ).all()
        assert len(configs) == 5

    def test_does_not_overwrite_existing(self, test_db_session, test_team):
        """Existing entries should not be modified."""
        # Create a custom value
        custom = Configuration(
            team_id=test_team.id,
            category="conflict_rules",
            key="distance_threshold_miles",
            value_json={"value": 100, "label": "Custom Distance"},
            source=ConfigSource.DATABASE,
        )
        test_db_session.add(custom)
        test_db_session.flush()

        service = SeedDataService(test_db_session)
        count = service.seed_conflict_rules(test_team.id)

        # Should create 4 (skipping the existing one)
        assert count == 4

        # Verify custom value is preserved
        existing = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "conflict_rules",
            Configuration.key == "distance_threshold_miles",
        ).first()
        assert existing.value_json["value"] == 100

    def test_correct_keys(self, test_db_session, test_team):
        """Should create entries for all expected keys."""
        service = SeedDataService(test_db_session)
        service.seed_conflict_rules(test_team.id)
        test_db_session.flush()

        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "conflict_rules",
        ).all()

        keys = {c.key for c in configs}
        expected_keys = set(DEFAULT_CONFLICT_RULES.keys())
        assert keys == expected_keys


class TestSeedScoringWeights:
    """Tests for seed_scoring_weights()."""

    def test_creates_all_entries(self, test_db_session, test_team):
        """Should create 5 scoring weight entries for a new team."""
        service = SeedDataService(test_db_session)
        count = service.seed_scoring_weights(test_team.id)
        test_db_session.flush()

        assert count == 5

        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "scoring_weights",
        ).all()
        assert len(configs) == 5

    def test_idempotent(self, test_db_session, test_team):
        """Running twice should not create duplicates."""
        service = SeedDataService(test_db_session)
        first_count = service.seed_scoring_weights(test_team.id)
        test_db_session.flush()

        second_count = service.seed_scoring_weights(test_team.id)

        assert first_count == 5
        assert second_count == 0

    def test_correct_default_values(self, test_db_session, test_team):
        """All weights should default to 20."""
        service = SeedDataService(test_db_session)
        service.seed_scoring_weights(test_team.id)
        test_db_session.flush()

        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "scoring_weights",
        ).all()

        for config in configs:
            assert config.value_json["value"] == 20

    def test_correct_keys(self, test_db_session, test_team):
        """Should create entries for all expected keys."""
        service = SeedDataService(test_db_session)
        service.seed_scoring_weights(test_team.id)
        test_db_session.flush()

        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "scoring_weights",
        ).all()

        keys = {c.key for c in configs}
        expected_keys = set(DEFAULT_SCORING_WEIGHTS.keys())
        assert keys == expected_keys


class TestSeedTeamDefaultsIntegration:
    """Tests for seed_team_defaults() including conflict config."""

    def test_includes_conflict_and_scoring(self, test_db_session, test_team):
        """seed_team_defaults() should seed conflict rules and scoring weights."""
        service = SeedDataService(test_db_session)
        result = service.seed_team_defaults(test_team.id)

        # Result should now be a 5-tuple
        assert len(result) == 5
        _cats, _statuses, _ttl, conflict_rules, scoring_weights = result
        assert conflict_rules == 5
        assert scoring_weights == 5
