"""
Unit tests for CategoryService.

Tests CRUD operations, reordering, and cascade protection for categories.
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch

from backend.src.models import Category
from backend.src.services.category_service import CategoryService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def category_service(test_db_session):
    """Create a CategoryService instance for testing."""
    return CategoryService(test_db_session)


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


# ============================================================================
# CRUD Tests (T020a)
# ============================================================================


class TestCategoryServiceCreate:
    """Tests for category creation."""

    def test_create_category(self, category_service):
        """Test creating a new category."""
        result = category_service.create(
            name="Airshow",
            icon="plane",
            color="#3B82F6",
        )

        assert result.id is not None
        assert result.uuid is not None
        assert result.name == "Airshow"
        assert result.icon == "plane"
        assert result.color == "#3B82F6"
        assert result.is_active is True
        assert result.display_order == 0

    def test_create_category_auto_display_order(self, category_service, sample_category):
        """Test display_order is auto-incremented."""
        sample_category(name="First", display_order=0)
        sample_category(name="Second", display_order=1)

        result = category_service.create(name="Third", icon="star")

        assert result.display_order == 2

    def test_create_category_duplicate_name(self, category_service, sample_category):
        """Test error when creating duplicate category name."""
        sample_category(name="Airshow")

        with pytest.raises(ConflictError) as exc_info:
            category_service.create(name="Airshow", icon="plane")

        assert "already exists" in str(exc_info.value).lower()

    def test_create_category_duplicate_name_case_insensitive(
        self, category_service, sample_category
    ):
        """Test duplicate detection is case-insensitive."""
        sample_category(name="Airshow")

        with pytest.raises(ConflictError):
            category_service.create(name="AIRSHOW", icon="plane")

        with pytest.raises(ConflictError):
            category_service.create(name="airshow", icon="plane")

    def test_create_category_invalid_color(self, category_service):
        """Test error on invalid color format."""
        with pytest.raises(ValidationError) as exc_info:
            category_service.create(name="Test", color="red")

        assert "color" in str(exc_info.value).lower()

    def test_create_category_valid_short_color(self, category_service):
        """Test short hex color format (#RGB) is accepted."""
        result = category_service.create(name="Test", color="#F00")
        assert result.color == "#F00"

    def test_create_category_minimal(self, category_service):
        """Test creating category with minimal fields."""
        result = category_service.create(name="Minimal")

        assert result.name == "Minimal"
        assert result.icon is None
        assert result.color is None
        assert result.is_active is True


class TestCategoryServiceGet:
    """Tests for category retrieval."""

    def test_get_by_guid(self, category_service, sample_category):
        """Test getting category by GUID."""
        category = sample_category(name="Test")

        result = category_service.get_by_guid(category.guid)

        assert result.id == category.id
        assert result.name == "Test"

    def test_get_by_guid_not_found(self, category_service):
        """Test error when GUID not found."""
        with pytest.raises(NotFoundError):
            category_service.get_by_guid("cat_00000000000000000000000000")

    def test_get_by_guid_invalid_format(self, category_service):
        """Test error on invalid GUID format."""
        with pytest.raises(NotFoundError):
            category_service.get_by_guid("invalid_guid")

    def test_get_by_guid_wrong_prefix(self, category_service):
        """Test error on wrong GUID prefix."""
        with pytest.raises(NotFoundError):
            category_service.get_by_guid("evt_00000000000000000000000000")

    def test_get_by_id(self, category_service, sample_category):
        """Test getting category by internal ID."""
        category = sample_category(name="Test")

        result = category_service.get_by_id(category.id)

        assert result.guid == category.guid
        assert result.name == "Test"

    def test_get_by_id_not_found(self, category_service):
        """Test error when ID not found."""
        with pytest.raises(NotFoundError):
            category_service.get_by_id(99999)


class TestCategoryServiceList:
    """Tests for listing categories."""

    def test_list_all(self, category_service, sample_category):
        """Test listing all categories."""
        sample_category(name="Airshow", display_order=0)
        sample_category(name="Wildlife", display_order=1)
        sample_category(name="Wedding", display_order=2)

        result = category_service.list()

        assert len(result) == 3
        assert result[0].name == "Airshow"
        assert result[1].name == "Wildlife"
        assert result[2].name == "Wedding"

    def test_list_active_only(self, category_service, sample_category):
        """Test listing only active categories."""
        sample_category(name="Active", is_active=True)
        sample_category(name="Inactive", is_active=False)

        result = category_service.list(active_only=True)

        assert len(result) == 1
        assert result[0].name == "Active"

    def test_list_order_by_display(self, category_service, sample_category):
        """Test categories are ordered by display_order."""
        sample_category(name="Third", display_order=2)
        sample_category(name="First", display_order=0)
        sample_category(name="Second", display_order=1)

        result = category_service.list(order_by_display=True)

        assert result[0].name == "First"
        assert result[1].name == "Second"
        assert result[2].name == "Third"

    def test_list_order_by_name(self, category_service, sample_category):
        """Test categories can be ordered by name."""
        sample_category(name="Zebra", display_order=0)
        sample_category(name="Alpha", display_order=1)
        sample_category(name="Middle", display_order=2)

        result = category_service.list(order_by_display=False)

        assert result[0].name == "Alpha"
        assert result[1].name == "Middle"
        assert result[2].name == "Zebra"

    def test_list_empty(self, category_service):
        """Test listing when no categories exist."""
        result = category_service.list()
        assert result == []


class TestCategoryServiceUpdate:
    """Tests for category updates."""

    def test_update_name(self, category_service, sample_category):
        """Test updating category name."""
        category = sample_category(name="Original")

        result = category_service.update(category.guid, name="Updated")

        assert result.name == "Updated"

    def test_update_icon(self, category_service, sample_category):
        """Test updating category icon."""
        category = sample_category(name="Test", icon="plane")

        result = category_service.update(category.guid, icon="bird")

        assert result.icon == "bird"

    def test_update_color(self, category_service, sample_category):
        """Test updating category color."""
        category = sample_category(name="Test", color="#FF0000")

        result = category_service.update(category.guid, color="#00FF00")

        assert result.color == "#00FF00"

    def test_update_is_active(self, category_service, sample_category):
        """Test deactivating category."""
        category = sample_category(name="Test", is_active=True)

        result = category_service.update(category.guid, is_active=False)

        assert result.is_active is False

    def test_update_duplicate_name(self, category_service, sample_category):
        """Test error when updating to existing name."""
        sample_category(name="Existing")
        category = sample_category(name="ToUpdate")

        with pytest.raises(ConflictError):
            category_service.update(category.guid, name="Existing")

    def test_update_same_name_case_change(self, category_service, sample_category):
        """Test updating name with only case change is allowed."""
        category = sample_category(name="airshow")

        result = category_service.update(category.guid, name="Airshow")

        assert result.name == "Airshow"

    def test_update_invalid_color(self, category_service, sample_category):
        """Test error on invalid color format during update."""
        category = sample_category(name="Test")

        with pytest.raises(ValidationError):
            category_service.update(category.guid, color="not-a-color")

    def test_update_not_found(self, category_service):
        """Test error when updating non-existent category."""
        with pytest.raises(NotFoundError):
            category_service.update(
                "cat_00000000000000000000000000", name="New Name"
            )


class TestCategoryServiceDelete:
    """Tests for category deletion."""

    def test_delete_category(self, category_service, sample_category):
        """Test deleting a category."""
        category = sample_category(name="ToDelete")
        guid = category.guid

        category_service.delete(guid)

        with pytest.raises(NotFoundError):
            category_service.get_by_guid(guid)

    def test_delete_not_found(self, category_service):
        """Test error when deleting non-existent category."""
        with pytest.raises(NotFoundError):
            category_service.delete("cat_00000000000000000000000000")

    def test_delete_with_events_fails(self, category_service, sample_category, test_db_session):
        """Test deleting category with events fails."""
        from backend.src.models import Event

        category = sample_category(name="HasEvents")

        # Create an event using this category
        event = Event(
            category_id=category.id,
            title="Test Event",
            event_date=date(2026, 1, 15),
        )
        test_db_session.add(event)
        test_db_session.commit()

        with pytest.raises(ConflictError) as exc_info:
            category_service.delete(category.guid)

        assert "event" in str(exc_info.value).lower()

    def test_delete_with_locations_fails(self, category_service, sample_category, test_db_session):
        """Test deleting category with locations fails."""
        from backend.src.models import Location

        category = sample_category(name="HasLocations")

        location = Location(
            category_id=category.id,
            name="Test Location",
        )
        test_db_session.add(location)
        test_db_session.commit()

        with pytest.raises(ConflictError) as exc_info:
            category_service.delete(category.guid)

        assert "location" in str(exc_info.value).lower()


class TestCategoryServiceReorder:
    """Tests for category reordering."""

    def test_reorder_categories(self, category_service, sample_category):
        """Test reordering categories."""
        cat1 = sample_category(name="First", display_order=0)
        cat2 = sample_category(name="Second", display_order=1)
        cat3 = sample_category(name="Third", display_order=2)

        # Reorder: Third, First, Second
        result = category_service.reorder([cat3.guid, cat1.guid, cat2.guid])

        assert result[0].name == "Third"
        assert result[0].display_order == 0
        assert result[1].name == "First"
        assert result[1].display_order == 1
        assert result[2].name == "Second"
        assert result[2].display_order == 2

    def test_reorder_partial(self, category_service, sample_category):
        """Test reordering subset of categories."""
        cat1 = sample_category(name="First", display_order=0)
        cat2 = sample_category(name="Second", display_order=1)
        sample_category(name="Third", display_order=2)  # Not included

        result = category_service.reorder([cat2.guid, cat1.guid])

        assert len(result) == 2
        assert result[0].display_order == 0
        assert result[1].display_order == 1

    def test_reorder_invalid_guid(self, category_service, sample_category):
        """Test error when reordering with invalid GUID."""
        cat1 = sample_category(name="Valid")

        with pytest.raises(NotFoundError):
            category_service.reorder([cat1.guid, "cat_00000000000000000000000000"])


class TestCategoryServiceStats:
    """Tests for category statistics."""

    def test_get_stats(self, category_service, sample_category):
        """Test getting category statistics."""
        sample_category(name="Active1", is_active=True)
        sample_category(name="Active2", is_active=True)
        sample_category(name="Inactive", is_active=False)

        stats = category_service.get_stats()

        assert stats["total_count"] == 3
        assert stats["active_count"] == 2
        assert stats["inactive_count"] == 1

    def test_get_stats_empty(self, category_service):
        """Test statistics when no categories exist."""
        stats = category_service.get_stats()

        assert stats["total_count"] == 0
        assert stats["active_count"] == 0
        assert stats["inactive_count"] == 0


class TestColorValidation:
    """Tests for color validation."""

    def test_valid_hex_6(self, category_service):
        """Test valid 6-digit hex color."""
        assert category_service._is_valid_color("#FF5733") is True
        assert category_service._is_valid_color("#000000") is True
        assert category_service._is_valid_color("#ffffff") is True
        assert category_service._is_valid_color("#AABBCC") is True

    def test_valid_hex_3(self, category_service):
        """Test valid 3-digit hex color."""
        assert category_service._is_valid_color("#F00") is True
        assert category_service._is_valid_color("#abc") is True

    def test_invalid_missing_hash(self, category_service):
        """Test color without # is invalid."""
        assert category_service._is_valid_color("FF5733") is False

    def test_invalid_wrong_length(self, category_service):
        """Test color with wrong length is invalid."""
        assert category_service._is_valid_color("#FF57") is False
        assert category_service._is_valid_color("#FF57339") is False

    def test_invalid_non_hex(self, category_service):
        """Test non-hex characters are invalid."""
        assert category_service._is_valid_color("#GGGGGG") is False
        assert category_service._is_valid_color("#red") is False

    def test_empty_color_valid(self, category_service):
        """Test empty/None color is valid (allowed)."""
        assert category_service._is_valid_color("") is True
        assert category_service._is_valid_color(None) is True
