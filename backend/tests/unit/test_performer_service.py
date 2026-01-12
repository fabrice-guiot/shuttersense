"""
Unit tests for PerformerService.

Tests CRUD operations, category matching, and validation for performers.

Issue #39 - Calendar Events feature (Phase 11)
"""

from datetime import date

import pytest

from backend.src.models import Performer, Category, EventPerformer, Event
from backend.src.services.performer_service import PerformerService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def performer_service(test_db_session):
    """Create a PerformerService instance for testing."""
    return PerformerService(test_db_session)


@pytest.fixture
def sample_category(test_db_session):
    """Factory for creating sample Category models."""

    def _create(
        name="Airshow",
        icon="plane",
        color="#3B82F6",
        is_active=True,
        display_order=0,
    ):
        category = Category(
            name=name,
            icon=icon,
            color=color,
            is_active=is_active,
            display_order=display_order,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    return _create


@pytest.fixture
def sample_performer(test_db_session, sample_category):
    """Factory for creating sample Performer models."""

    def _create(
        name="Test Performer",
        category=None,
        website=None,
        instagram_handle=None,
        additional_info=None,
    ):
        if category is None:
            category = sample_category()

        performer = Performer(
            name=name,
            category_id=category.id,
            website=website,
            instagram_handle=instagram_handle,
            additional_info=additional_info,
        )
        test_db_session.add(performer)
        test_db_session.commit()
        test_db_session.refresh(performer)
        return performer

    return _create


# ============================================================================
# CRUD Tests (T103a)
# ============================================================================


class TestPerformerServiceCreate:
    """Tests for performer creation."""

    def test_create_performer_minimal(self, performer_service, sample_category):
        """Test creating a performer with minimal fields."""
        category = sample_category(name="Airshow")

        result = performer_service.create(
            name="Blue Angels",
            category_guid=category.guid,
        )

        assert result.id is not None
        assert result.guid is not None
        assert result.guid.startswith("prf_")
        assert result.name == "Blue Angels"
        assert result.category_id == category.id

    def test_create_performer_full(self, performer_service, sample_category):
        """Test creating a performer with all fields."""
        category = sample_category(name="Airshow")

        result = performer_service.create(
            name="Blue Angels",
            category_guid=category.guid,
            website="https://www.blueangels.navy.mil",
            instagram_handle="usaborngirl",
            additional_info="U.S. Navy flight demonstration squadron",
        )

        assert result.name == "Blue Angels"
        assert result.website == "https://www.blueangels.navy.mil"
        assert result.instagram_handle == "usaborngirl"
        assert result.additional_info == "U.S. Navy flight demonstration squadron"

    def test_create_performer_invalid_category(self, performer_service):
        """Test error when creating with non-existent category."""
        with pytest.raises(NotFoundError):
            performer_service.create(
                name="Test Performer",
                category_guid="cat_00000000000000000000000000",
            )

    def test_create_performer_inactive_category(self, performer_service, sample_category):
        """Test error when creating with inactive category."""
        category = sample_category(name="Inactive", is_active=False)

        with pytest.raises(ValidationError) as exc_info:
            performer_service.create(
                name="Test Performer",
                category_guid=category.guid,
            )

        assert "inactive" in str(exc_info.value).lower()


class TestPerformerServiceRead:
    """Tests for performer retrieval."""

    def test_get_by_guid(self, performer_service, sample_performer, sample_category):
        """Test retrieving a performer by GUID."""
        category = sample_category()
        performer = sample_performer(name="Blue Angels", category=category)

        result = performer_service.get_by_guid(performer.guid)

        assert result.id == performer.id
        assert result.name == "Blue Angels"

    def test_get_by_guid_not_found(self, performer_service):
        """Test error when performer not found."""
        with pytest.raises(NotFoundError):
            performer_service.get_by_guid("prf_00000000000000000000000000")

    def test_get_by_guid_invalid_format(self, performer_service):
        """Test error when GUID format is invalid."""
        with pytest.raises(NotFoundError):
            performer_service.get_by_guid("invalid_guid")

    def test_get_by_guid_wrong_prefix(self, performer_service):
        """Test error when GUID has wrong prefix."""
        with pytest.raises(NotFoundError):
            performer_service.get_by_guid("org_00000000000000000000000000")

    def test_get_by_id(self, performer_service, sample_performer, sample_category):
        """Test retrieving a performer by internal ID."""
        category = sample_category()
        performer = sample_performer(name="Test", category=category)

        result = performer_service.get_by_id(performer.id)

        assert result.guid == performer.guid

    def test_get_by_id_not_found(self, performer_service):
        """Test error when performer ID not found."""
        with pytest.raises(NotFoundError):
            performer_service.get_by_id(999999)


class TestPerformerServiceList:
    """Tests for performer listing."""

    def test_list_all(self, performer_service, sample_performer, sample_category):
        """Test listing all performers."""
        category = sample_category()
        sample_performer(name="Performer A", category=category)
        sample_performer(name="Performer B", category=category)
        sample_performer(name="Performer C", category=category)

        result, total = performer_service.list()

        assert total == 3
        assert len(result) == 3
        # Should be ordered by name ascending
        assert result[0].name == "Performer A"
        assert result[1].name == "Performer B"
        assert result[2].name == "Performer C"

    def test_list_by_category(self, performer_service, sample_performer, sample_category):
        """Test listing performers filtered by category."""
        cat1 = sample_category(name="Category 1")
        cat2 = sample_category(name="Category 2")
        sample_performer(name="Performer A", category=cat1)
        sample_performer(name="Performer B", category=cat2)
        sample_performer(name="Performer C", category=cat1)

        result, total = performer_service.list(category_guid=cat1.guid)

        assert total == 2
        assert len(result) == 2
        assert all(p.category_id == cat1.id for p in result)

    def test_list_with_search(self, performer_service, sample_performer, sample_category):
        """Test listing performers with search filter."""
        category = sample_category()
        sample_performer(name="Blue Angels", category=category)
        sample_performer(name="Thunderbirds", category=category)
        sample_performer(name="Red Arrows", category=category)

        result, total = performer_service.list(search="Blue")

        assert total == 1
        assert result[0].name == "Blue Angels"

    def test_list_search_instagram(self, performer_service, sample_performer, sample_category):
        """Test searching performers by Instagram handle."""
        category = sample_category()
        sample_performer(name="Performer 1", instagram_handle="blueangels", category=category)
        sample_performer(name="Performer 2", instagram_handle="other", category=category)

        result, total = performer_service.list(search="blueangels")

        assert total == 1
        assert result[0].instagram_handle == "blueangels"

    def test_list_pagination(self, performer_service, sample_performer, sample_category):
        """Test performer list pagination."""
        category = sample_category()
        for i in range(5):
            sample_performer(name=f"Performer {i:02d}", category=category)

        # First page
        result, total = performer_service.list(limit=2, offset=0)
        assert total == 5
        assert len(result) == 2
        assert result[0].name == "Performer 00"

        # Second page
        result, total = performer_service.list(limit=2, offset=2)
        assert total == 5
        assert len(result) == 2
        assert result[0].name == "Performer 02"

    def test_list_empty(self, performer_service):
        """Test listing when no performers exist."""
        result, total = performer_service.list()

        assert total == 0
        assert len(result) == 0


class TestPerformerServiceUpdate:
    """Tests for performer updates."""

    def test_update_name(self, performer_service, sample_performer, sample_category):
        """Test updating performer name."""
        category = sample_category()
        performer = sample_performer(name="Old Name", category=category)

        result = performer_service.update(
            guid=performer.guid,
            name="New Name",
        )

        assert result.name == "New Name"

    def test_update_website(self, performer_service, sample_performer, sample_category):
        """Test updating performer website."""
        category = sample_category()
        performer = sample_performer(name="Test", category=category)

        result = performer_service.update(
            guid=performer.guid,
            website="https://newsite.com",
        )

        assert result.website == "https://newsite.com"

    def test_update_clear_website(self, performer_service, sample_performer, sample_category):
        """Test clearing performer website."""
        category = sample_category()
        performer = sample_performer(
            name="Test",
            website="https://oldsite.com",
            category=category,
        )

        result = performer_service.update(
            guid=performer.guid,
            website="",  # Empty string clears
        )

        assert result.website is None

    def test_update_instagram(self, performer_service, sample_performer, sample_category):
        """Test updating performer Instagram handle."""
        category = sample_category()
        performer = sample_performer(name="Test", category=category)

        result = performer_service.update(
            guid=performer.guid,
            instagram_handle="newhandle",
        )

        assert result.instagram_handle == "newhandle"

    def test_update_clear_instagram(self, performer_service, sample_performer, sample_category):
        """Test clearing performer Instagram handle."""
        category = sample_category()
        performer = sample_performer(
            name="Test",
            instagram_handle="oldhandle",
            category=category,
        )

        result = performer_service.update(
            guid=performer.guid,
            instagram_handle="",  # Empty string clears
        )

        assert result.instagram_handle is None

    def test_update_category(self, performer_service, sample_performer, sample_category):
        """Test updating performer category."""
        cat1 = sample_category(name="Category 1")
        cat2 = sample_category(name="Category 2")
        performer = sample_performer(name="Test", category=cat1)

        result = performer_service.update(
            guid=performer.guid,
            category_guid=cat2.guid,
        )

        assert result.category_id == cat2.id

    def test_update_to_inactive_category(self, performer_service, sample_performer, sample_category):
        """Test error when updating to inactive category."""
        cat1 = sample_category(name="Active")
        cat2 = sample_category(name="Inactive", is_active=False)
        performer = sample_performer(name="Test", category=cat1)

        with pytest.raises(ValidationError) as exc_info:
            performer_service.update(
                guid=performer.guid,
                category_guid=cat2.guid,
            )

        assert "inactive" in str(exc_info.value).lower()

    def test_update_not_found(self, performer_service):
        """Test error when updating non-existent performer."""
        with pytest.raises(NotFoundError):
            performer_service.update(
                guid="prf_00000000000000000000000000",
                name="New Name",
            )

    def test_update_multiple_fields(self, performer_service, sample_performer, sample_category):
        """Test updating multiple fields at once."""
        category = sample_category()
        performer = sample_performer(name="Original", category=category)

        result = performer_service.update(
            guid=performer.guid,
            name="Updated",
            website="https://site.com",
            instagram_handle="handle",
            additional_info="New info",
        )

        assert result.name == "Updated"
        assert result.website == "https://site.com"
        assert result.instagram_handle == "handle"
        assert result.additional_info == "New info"

    def test_update_preserves_unset_fields(self, performer_service, sample_performer, sample_category):
        """Test that unset fields are preserved during update."""
        category = sample_category()
        performer = sample_performer(
            name="Original",
            website="https://original.com",
            instagram_handle="original",
            category=category,
        )

        result = performer_service.update(
            guid=performer.guid,
            name="Updated",
            # website and instagram_handle not provided
        )

        assert result.name == "Updated"
        assert result.website == "https://original.com"  # Preserved
        assert result.instagram_handle == "original"  # Preserved


class TestPerformerServiceDelete:
    """Tests for performer deletion."""

    def test_delete_performer(self, performer_service, sample_performer, sample_category):
        """Test deleting a performer."""
        category = sample_category()
        performer = sample_performer(name="To Delete", category=category)
        guid = performer.guid

        performer_service.delete(guid)

        with pytest.raises(NotFoundError):
            performer_service.get_by_guid(guid)

    def test_delete_not_found(self, performer_service):
        """Test error when deleting non-existent performer."""
        with pytest.raises(NotFoundError):
            performer_service.delete("prf_00000000000000000000000000")

    def test_delete_with_event_associations(
        self, performer_service, sample_performer, sample_category, test_db_session
    ):
        """Test error when deleting performer with event associations."""
        category = sample_category()
        performer = sample_performer(name="In Use", category=category)

        # Create an event and associate the performer
        event = Event(
            title="Test Event",
            event_date=date(2026, 7, 1),
            status="future",
            attendance="planned",
            category_id=category.id,
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)

        event_performer = EventPerformer(
            event_id=event.id,
            performer_id=performer.id,
            status="confirmed",
        )
        test_db_session.add(event_performer)
        test_db_session.commit()

        with pytest.raises(ConflictError) as exc_info:
            performer_service.delete(performer.guid)

        assert "associated with" in str(exc_info.value).lower()


class TestPerformerServiceStats:
    """Tests for performer statistics."""

    def test_get_stats_empty(self, performer_service):
        """Test stats when no performers exist."""
        stats = performer_service.get_stats()

        assert stats["total_count"] == 0
        assert stats["with_instagram_count"] == 0
        assert stats["with_website_count"] == 0

    def test_get_stats_with_data(self, performer_service, sample_performer, sample_category):
        """Test stats with existing performers."""
        category = sample_category()
        sample_performer(name="P1", instagram_handle="handle1", website="https://site1.com", category=category)
        sample_performer(name="P2", instagram_handle="handle2", category=category)  # No website
        sample_performer(name="P3", website="https://site3.com", category=category)  # No instagram
        sample_performer(name="P4", category=category)  # No instagram or website

        stats = performer_service.get_stats()

        assert stats["total_count"] == 4
        assert stats["with_instagram_count"] == 2
        assert stats["with_website_count"] == 2


class TestPerformerServiceCategoryMatch:
    """Tests for category matching validation."""

    def test_validate_category_match_true(self, performer_service, sample_performer, sample_category):
        """Test category match validation returns True."""
        category = sample_category()
        performer = sample_performer(name="Test", category=category)

        result = performer_service.validate_category_match(
            performer_guid=performer.guid,
            event_category_guid=category.guid,
        )

        assert result is True

    def test_validate_category_match_false(self, performer_service, sample_performer, sample_category):
        """Test category match validation returns False."""
        cat1 = sample_category(name="Category 1")
        cat2 = sample_category(name="Category 2")
        performer = sample_performer(name="Test", category=cat1)

        result = performer_service.validate_category_match(
            performer_guid=performer.guid,
            event_category_guid=cat2.guid,
        )

        assert result is False

    def test_validate_category_match_not_found(self, performer_service, sample_category):
        """Test error when performer not found for category match."""
        category = sample_category()

        with pytest.raises(NotFoundError):
            performer_service.validate_category_match(
                performer_guid="prf_00000000000000000000000000",
                event_category_guid=category.guid,
            )


class TestPerformerServiceGetByCategory:
    """Tests for get_by_category method."""

    def test_get_by_category(self, performer_service, sample_performer, sample_category):
        """Test getting performers by category."""
        cat1 = sample_category(name="Category 1")
        cat2 = sample_category(name="Category 2")
        sample_performer(name="A", category=cat1)
        sample_performer(name="B", category=cat1)
        sample_performer(name="C", category=cat2)

        result = performer_service.get_by_category(cat1.guid)

        assert len(result) == 2
        assert all(p.category_id == cat1.id for p in result)

    def test_get_by_category_with_search(self, performer_service, sample_performer, sample_category):
        """Test getting performers by category with search."""
        category = sample_category()
        sample_performer(name="Blue Angels", category=category)
        sample_performer(name="Thunderbirds", category=category)

        result = performer_service.get_by_category(category.guid, search="Blue")

        assert len(result) == 1
        assert result[0].name == "Blue Angels"

    def test_get_by_category_invalid(self, performer_service):
        """Test error when category not found."""
        with pytest.raises(NotFoundError):
            performer_service.get_by_category("cat_00000000000000000000000000")


class TestPerformerServiceBuildResponse:
    """Tests for build_performer_response method."""

    def test_build_performer_response(self, performer_service, sample_performer, sample_category):
        """Test building performer response dictionary."""
        category = sample_category()
        performer = sample_performer(
            name="Blue Angels",
            website="https://blueangels.navy.mil",
            instagram_handle="usaborngirl",
            additional_info="Navy demo team",
            category=category,
        )

        result = performer_service.build_performer_response(performer)

        assert result["guid"] == performer.guid
        assert result["name"] == "Blue Angels"
        assert result["website"] == "https://blueangels.navy.mil"
        assert result["instagram_handle"] == "usaborngirl"
        assert result["instagram_url"] == "https://www.instagram.com/usaborngirl"
        assert result["additional_info"] == "Navy demo team"
        assert result["category"]["guid"] == category.guid
        assert result["category"]["name"] == category.name
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_build_performer_response_no_instagram(self, performer_service, sample_performer, sample_category):
        """Test building response when no Instagram handle."""
        category = sample_category()
        performer = sample_performer(name="Test", category=category)

        result = performer_service.build_performer_response(performer)

        assert result["instagram_handle"] is None
        assert result["instagram_url"] is None
