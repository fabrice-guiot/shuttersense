"""
Integration tests for conflict rules and scoring weights config API endpoints.

Tests end-to-end flows for:
- GET /config/conflict_rules
- PUT /config/conflict_rules
- GET /config/scoring_weights
- PUT /config/scoring_weights

Issue #182 - Calendar Conflict Visualization & Event Picker
"""

import pytest

from backend.src.models import Configuration, ConfigSource


class TestConflictRulesAPI:
    """Integration tests for /config/conflict_rules endpoints."""

    def test_get_defaults(self, test_client):
        """Returns default values when no config exists."""
        response = test_client.get("/api/config/conflict_rules")
        assert response.status_code == 200

        data = response.json()
        assert data["distance_threshold_miles"] == 150
        assert data["consecutive_window_days"] == 1
        assert data["travel_buffer_days"] == 3
        assert data["colocation_radius_miles"] == 70
        assert data["performer_ceiling"] == 5

    def test_update_single_field(self, test_client):
        """PUT with one field updates only that field."""
        response = test_client.put("/api/config/conflict_rules", json={
            "distance_threshold_miles": 100,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["distance_threshold_miles"] == 100
        # Others remain at default
        assert data["consecutive_window_days"] == 1
        assert data["travel_buffer_days"] == 3

    def test_update_multiple_fields(self, test_client):
        """PUT with multiple fields updates all specified."""
        response = test_client.put("/api/config/conflict_rules", json={
            "distance_threshold_miles": 75,
            "travel_buffer_days": 5,
            "performer_ceiling": 10,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["distance_threshold_miles"] == 75
        assert data["travel_buffer_days"] == 5
        assert data["performer_ceiling"] == 10

    def test_get_after_update(self, test_client):
        """GET reflects values set by PUT."""
        test_client.put("/api/config/conflict_rules", json={
            "colocation_radius_miles": 25,
        })

        response = test_client.get("/api/config/conflict_rules")
        assert response.status_code == 200
        assert response.json()["colocation_radius_miles"] == 25

    def test_update_idempotent(self, test_client):
        """Setting the same value twice is idempotent."""
        test_client.put("/api/config/conflict_rules", json={
            "distance_threshold_miles": 60,
        })
        response = test_client.put("/api/config/conflict_rules", json={
            "distance_threshold_miles": 60,
        })
        assert response.status_code == 200
        assert response.json()["distance_threshold_miles"] == 60

    def test_update_preserves_existing_with_db_entry(
        self, test_client, test_db_session, test_team,
    ):
        """Pre-existing DB entry is updated, not duplicated."""
        # Seed one entry via API
        test_client.put("/api/config/conflict_rules", json={
            "distance_threshold_miles": 80,
        })

        # Update the same entry again
        test_client.put("/api/config/conflict_rules", json={
            "distance_threshold_miles": 90,
        })

        # Verify only one DB row
        configs = test_db_session.query(Configuration).filter(
            Configuration.team_id == test_team.id,
            Configuration.category == "conflict_rules",
            Configuration.key == "distance_threshold_miles",
        ).all()
        assert len(configs) == 1
        assert configs[0].value_json["value"] == 90


class TestScoringWeightsAPI:
    """Integration tests for /config/scoring_weights endpoints."""

    def test_get_defaults(self, test_client):
        """Returns default weights when no config exists."""
        response = test_client.get("/api/config/scoring_weights")
        assert response.status_code == 200

        data = response.json()
        assert data["weight_venue_quality"] == 20
        assert data["weight_organizer_reputation"] == 20
        assert data["weight_performer_lineup"] == 20
        assert data["weight_logistics_ease"] == 20
        assert data["weight_readiness"] == 20

    def test_update_single_weight(self, test_client):
        """PUT with one weight updates only that weight."""
        response = test_client.put("/api/config/scoring_weights", json={
            "weight_venue_quality": 40,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["weight_venue_quality"] == 40
        assert data["weight_organizer_reputation"] == 20  # unchanged

    def test_update_multiple_weights(self, test_client):
        """PUT with multiple weights updates all specified."""
        response = test_client.put("/api/config/scoring_weights", json={
            "weight_venue_quality": 30,
            "weight_organizer_reputation": 30,
            "weight_performer_lineup": 10,
            "weight_logistics_ease": 10,
            "weight_readiness": 20,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["weight_venue_quality"] == 30
        assert data["weight_organizer_reputation"] == 30
        assert data["weight_performer_lineup"] == 10
        assert data["weight_logistics_ease"] == 10
        assert data["weight_readiness"] == 20

    def test_get_after_update(self, test_client):
        """GET reflects values set by PUT."""
        test_client.put("/api/config/scoring_weights", json={
            "weight_readiness": 50,
        })

        response = test_client.get("/api/config/scoring_weights")
        assert response.status_code == 200
        assert response.json()["weight_readiness"] == 50

    def test_weight_zero_allowed(self, test_client):
        """A weight of 0 is valid (disables that dimension)."""
        response = test_client.put("/api/config/scoring_weights", json={
            "weight_logistics_ease": 0,
        })
        assert response.status_code == 200
        assert response.json()["weight_logistics_ease"] == 0

    def test_weight_max_allowed(self, test_client):
        """A weight of 100 is valid."""
        response = test_client.put("/api/config/scoring_weights", json={
            "weight_venue_quality": 100,
        })
        assert response.status_code == 200
        assert response.json()["weight_venue_quality"] == 100
