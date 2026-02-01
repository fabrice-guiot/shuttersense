"""
Unit tests for AuditMixin.

Issue #120: Audit Trail Visibility Enhancement (NFR-400.1)
Tests AuditMixin columns, FK constraints, SET NULL on user delete,
nullable behavior, relationship loading, and created_by immutability.
"""

import pytest

from backend.src.models import Collection, CollectionType, CollectionState
from backend.src.models.user import User, UserStatus


class TestAuditMixinColumns:
    """Tests that AuditMixin adds expected columns to Group A models."""

    def test_collection_has_created_by_user_id(self, test_db_session, test_team):
        """Collection model should have created_by_user_id column."""
        collection = Collection(
            name="Audit Test Collection",
            type=CollectionType.LOCAL,
            location="/tmp/test",
            state=CollectionState.LIVE,
            team_id=test_team.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()

        assert hasattr(collection, "created_by_user_id")
        assert collection.created_by_user_id is None

    def test_collection_has_updated_by_user_id(self, test_db_session, test_team):
        """Collection model should have updated_by_user_id column."""
        collection = Collection(
            name="Audit Test Collection",
            type=CollectionType.LOCAL,
            location="/tmp/test",
            state=CollectionState.LIVE,
            team_id=test_team.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()

        assert hasattr(collection, "updated_by_user_id")
        assert collection.updated_by_user_id is None


class TestAuditMixinNullable:
    """Tests that audit columns are nullable for historical data compatibility."""

    def test_created_by_nullable(self, test_db_session, test_team):
        """created_by_user_id should accept null (historical records)."""
        collection = Collection(
            name="Historical Collection",
            type=CollectionType.LOCAL,
            location="/tmp/historical",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            created_by_user_id=None,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.created_by_user_id is None

    def test_updated_by_nullable(self, test_db_session, test_team):
        """updated_by_user_id should accept null (historical records)."""
        collection = Collection(
            name="Historical Collection",
            type=CollectionType.LOCAL,
            location="/tmp/historical",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            updated_by_user_id=None,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.updated_by_user_id is None


class TestAuditMixinForeignKey:
    """Tests that audit columns correctly reference the users table."""

    def test_created_by_references_user(self, test_db_session, test_team, test_user):
        """created_by_user_id should accept a valid user ID."""
        collection = Collection(
            name="User Ref Collection",
            type=CollectionType.LOCAL,
            location="/tmp/ref",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.created_by_user_id == test_user.id
        assert collection.updated_by_user_id == test_user.id

    def test_set_null_on_user_delete(self, test_db_session, test_team):
        """Deleting a user should SET NULL on audit columns (not block deletion)."""
        # Create a dedicated user for this test
        user = User(
            team_id=test_team.id,
            email="deletable@example.com",
            display_name="Deletable User",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(user)
        test_db_session.commit()
        user_id = user.id

        # Create collection attributed to this user
        collection = Collection(
            name="Attributed Collection",
            type=CollectionType.LOCAL,
            location="/tmp/attributed",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        collection_id = collection.id

        # Delete the user
        test_db_session.delete(user)
        test_db_session.commit()

        # Refresh collection — audit columns should be null
        test_db_session.expire(collection)
        refreshed = test_db_session.get(Collection, collection_id)
        assert refreshed.created_by_user_id is None
        assert refreshed.updated_by_user_id is None


class TestAuditMixinRelationships:
    """Tests that audit relationships resolve to User instances."""

    def test_created_by_user_relationship(self, test_db_session, test_team, test_user):
        """created_by_user should resolve to the User who created the record."""
        collection = Collection(
            name="Relationship Test",
            type=CollectionType.LOCAL,
            location="/tmp/rel",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.created_by_user is not None
        assert collection.created_by_user.id == test_user.id
        assert collection.created_by_user.email == test_user.email

    def test_updated_by_user_relationship(self, test_db_session, test_team, test_user):
        """updated_by_user should resolve to the User who last modified the record."""
        collection = Collection(
            name="Update Rel Test",
            type=CollectionType.LOCAL,
            location="/tmp/upd",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.updated_by_user is not None
        assert collection.updated_by_user.id == test_user.id

    def test_null_relationship_for_historical_record(self, test_db_session, test_team):
        """Audit relationships should be None for records without attribution."""
        collection = Collection(
            name="No Attribution",
            type=CollectionType.LOCAL,
            location="/tmp/none",
            state=CollectionState.LIVE,
            team_id=test_team.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.created_by_user is None
        assert collection.updated_by_user is None

    def test_different_created_and_updated_users(
        self, test_db_session, test_team, test_user
    ):
        """created_by and updated_by can reference different users."""
        other_user = User(
            team_id=test_team.id,
            email="other@example.com",
            display_name="Other User",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        collection = Collection(
            name="Two Users",
            type=CollectionType.LOCAL,
            location="/tmp/two",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            updated_by_user_id=other_user.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.created_by_user.id == test_user.id
        assert collection.updated_by_user.id == other_user.id
        assert collection.created_by_user.id != collection.updated_by_user.id


class TestAuditMixinMutability:
    """Tests for audit column mutability behavior."""

    def test_updated_by_is_mutable(self, test_db_session, test_team, test_user):
        """updated_by_user_id should be freely changeable."""
        other_user = User(
            team_id=test_team.id,
            email="updater@example.com",
            display_name="Updater",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        collection = Collection(
            name="Mutable Update Test",
            type=CollectionType.LOCAL,
            location="/tmp/mutable",
            state=CollectionState.LIVE,
            team_id=test_team.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()

        # Should not raise
        collection.updated_by_user_id = other_user.id
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.updated_by_user_id == other_user.id


class TestAuditMixinSelfReferencing:
    """Tests that AuditMixin works on User model (self-referencing FK)."""

    def test_user_created_by_returns_single_user(
        self, test_db_session, test_team, test_user
    ):
        """User.created_by_user should return a single User, not a list."""
        new_user = User(
            team_id=test_team.id,
            email="created-by-test@example.com",
            display_name="Created By Test",
            status=UserStatus.ACTIVE,
            created_by_user_id=test_user.id,
        )
        test_db_session.add(new_user)
        test_db_session.commit()
        test_db_session.refresh(new_user)

        creator = new_user.created_by_user
        assert creator is not None
        assert not isinstance(creator, list)
        assert creator.id == test_user.id
        assert creator.email == test_user.email

    def test_user_updated_by_returns_single_user(
        self, test_db_session, test_team, test_user
    ):
        """User.updated_by_user should return a single User, not a list."""
        new_user = User(
            team_id=test_team.id,
            email="updated-by-test@example.com",
            display_name="Updated By Test",
            status=UserStatus.ACTIVE,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(new_user)
        test_db_session.commit()
        test_db_session.refresh(new_user)

        updater = new_user.updated_by_user
        assert updater is not None
        assert not isinstance(updater, list)
        assert updater.id == test_user.id

    def test_user_audit_property_works(
        self, test_db_session, test_team, test_user
    ):
        """User.audit should return a valid dict (not crash on self-reference)."""
        new_user = User(
            team_id=test_team.id,
            email="audit-prop-test@example.com",
            display_name="Audit Prop Test",
            status=UserStatus.ACTIVE,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(new_user)
        test_db_session.commit()
        test_db_session.refresh(new_user)

        audit = new_user.audit
        assert audit is not None
        assert "created_at" in audit
        assert "created_by" in audit
        assert "updated_at" in audit
        assert "updated_by" in audit
        assert audit["created_by"]["guid"] == test_user.guid
        assert audit["updated_by"]["guid"] == test_user.guid

    def test_user_audit_null_attribution(self, test_db_session, test_team):
        """User.audit should handle null attribution (historical records)."""
        new_user = User(
            team_id=test_team.id,
            email="no-attrib-test@example.com",
            display_name="No Attrib",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(new_user)
        test_db_session.commit()
        test_db_session.refresh(new_user)

        audit = new_user.audit
        assert audit is not None
        assert audit["created_by"] is None
        assert audit["updated_by"] is None
