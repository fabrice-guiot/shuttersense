"""Seed collection TTL configuration for existing teams

Revision ID: 043_collection_ttl_config
Revises: 042_agent_metrics
Create Date: 2026-01-21

Seeds default collection_ttl configuration for all existing teams.
TTL values are used to determine cache expiration based on collection state.

Part of Collection TTL Team-Level Configuration Refactor.
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '043_collection_ttl_config'
down_revision = '042_agent_metrics'
branch_labels = None
depends_on = None


# Default collection TTL values (in seconds) matching seed_data_service.py
DEFAULT_COLLECTION_TTL = {
    'live': {'value': 3600, 'label': 'Live (1 hour)'},
    'closed': {'value': 86400, 'label': 'Closed (24 hours)'},
    'archived': {'value': 604800, 'label': 'Archived (7 days)'},
}


def upgrade() -> None:
    """
    Seed collection_ttl configurations for all existing teams.

    For each existing team, inserts 3 configuration records:
    - collection_ttl/live: 3600 seconds (1 hour)
    - collection_ttl/closed: 86400 seconds (24 hours)
    - collection_ttl/archived: 604800 seconds (7 days)

    Skips teams that already have collection_ttl configs.
    """
    conn = op.get_bind()

    # Get all existing teams
    result = conn.execute(text("SELECT id FROM teams"))
    teams = result.fetchall()

    if not teams:
        return

    now = datetime.utcnow()

    for (team_id,) in teams:
        for state_key, ttl_data in DEFAULT_COLLECTION_TTL.items():
            # Check if config already exists for this team
            existing = conn.execute(
                text("""
                    SELECT id FROM configurations
                    WHERE team_id = :team_id
                    AND category = 'collection_ttl'
                    AND key = :key
                """),
                {"team_id": team_id, "key": state_key}
            ).fetchone()

            if existing:
                continue

            # Insert the config
            import json
            value_json = json.dumps(ttl_data)

            conn.execute(
                text("""
                    INSERT INTO configurations (team_id, category, key, value_json, description, source, created_at, updated_at)
                    VALUES (:team_id, 'collection_ttl', :key, :value_json, :description, 'database', :now, :now)
                """),
                {
                    "team_id": team_id,
                    "key": state_key,
                    "value_json": value_json,
                    "description": f"Collection cache TTL for {state_key} state",
                    "now": now
                }
            )


def downgrade() -> None:
    """
    Remove collection_ttl configurations from all teams.
    """
    conn = op.get_bind()

    conn.execute(
        text("DELETE FROM configurations WHERE category = 'collection_ttl'")
    )
