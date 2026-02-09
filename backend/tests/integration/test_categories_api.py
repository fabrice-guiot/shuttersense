"""
Integration tests for Categories API endpoints.

Tests end-to-end flows for category management:
- CRUD operations via API
- Reordering categories
- Deletion protection (referenced by events)
- Statistics endpoint

Issue #39 - Calendar Events feature (Phase 3)
"""

import pytest


class TestCategoriesAPI:
    """Integration tests for Categories API endpoints"""

    def test_create_category(self, test_client):
        """Test creating a new category via API"""
        category_data = {
            "name": "Airshow",
            "icon": "plane",
            "color": "#3B82F6",
            "is_active": True,
        }

        response = test_client.post("/api/categories", json=category_data)
        assert response.status_code == 201

        category = response.json()
        assert category["name"] == "Airshow"
        assert category["icon"] == "plane"
        assert category["color"] == "#3B82F6"
        assert category["is_active"] is True
        assert category["guid"].startswith("cat_")
        assert "created_at" in category
        assert "updated_at" in category

    def test_create_category_duplicate_name(self, test_client):
        """Test that duplicate category names are rejected"""
        category_data = {
            "name": "Duplicate Test",
            "icon": "test",
        }

        # First creation should succeed
        response1 = test_client.post("/api/categories", json=category_data)
        assert response1.status_code == 201

        # Second creation with same name should fail
        response2 = test_client.post("/api/categories", json=category_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"].lower()

    def test_create_category_invalid_color(self, test_client):
        """Test that invalid color format is rejected"""
        category_data = {
            "name": "Invalid Color",
            "color": "not-a-color",
        }

        response = test_client.post("/api/categories", json=category_data)
        assert response.status_code == 422  # Pydantic validation error

    def test_list_categories(self, test_client):
        """Test listing all categories"""
        # Create some categories
        for name in ["Category A", "Category B", "Category C"]:
            test_client.post("/api/categories", json={"name": name})

        # List all categories
        response = test_client.get("/api/categories")
        assert response.status_code == 200

        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) >= 3

    def test_list_categories_active_only(self, test_client):
        """Test listing only active categories"""
        # Create active and inactive categories
        test_client.post("/api/categories", json={
            "name": "Active Category",
            "is_active": True,
        })
        test_client.post("/api/categories", json={
            "name": "Inactive Category",
            "is_active": False,
        })

        # List active only
        response = test_client.get("/api/categories?is_active=true")
        assert response.status_code == 200

        categories = response.json()
        for cat in categories:
            assert cat["is_active"] is True

    def test_get_category_by_guid(self, test_client):
        """Test getting a single category by GUID"""
        # Create a category
        create_response = test_client.post("/api/categories", json={
            "name": "Get Test Category",
            "icon": "star",
            "color": "#FF0000",
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Get by GUID
        get_response = test_client.get(f"/api/categories/{guid}")
        assert get_response.status_code == 200

        category = get_response.json()
        assert category["guid"] == guid
        assert category["name"] == "Get Test Category"
        assert category["icon"] == "star"
        assert category["color"] == "#FF0000"

    def test_get_category_not_found(self, test_client):
        """Test getting a non-existent category returns 404"""
        response = test_client.get("/api/categories/cat_00000000000000000000000000")
        assert response.status_code == 404

    def test_update_category(self, test_client):
        """Test updating a category"""
        # Create a category
        create_response = test_client.post("/api/categories", json={
            "name": "Original Name",
            "icon": "circle",
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Update the category
        update_response = test_client.patch(f"/api/categories/{guid}", json={
            "name": "Updated Name",
            "icon": "square",
            "color": "#00FF00",
        })
        assert update_response.status_code == 200

        updated = update_response.json()
        assert updated["name"] == "Updated Name"
        assert updated["icon"] == "square"
        assert updated["color"] == "#00FF00"

    def test_update_category_partial(self, test_client):
        """Test partial update of category (only some fields)"""
        # Create a category
        create_response = test_client.post("/api/categories", json={
            "name": "Partial Update Test",
            "icon": "original-icon",
            "color": "#000000",
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Update only the name
        update_response = test_client.patch(f"/api/categories/{guid}", json={
            "name": "New Name Only",
        })
        assert update_response.status_code == 200

        updated = update_response.json()
        assert updated["name"] == "New Name Only"
        # Icon and color should remain unchanged
        assert updated["icon"] == "original-icon"
        assert updated["color"] == "#000000"

    def test_update_category_name_conflict(self, test_client):
        """Test that updating to an existing name fails"""
        # Create two categories
        test_client.post("/api/categories", json={"name": "Existing Name"})
        create_response = test_client.post("/api/categories", json={"name": "To Update"})
        guid = create_response.json()["guid"]

        # Try to update to the existing name
        update_response = test_client.patch(f"/api/categories/{guid}", json={
            "name": "Existing Name",
        })
        assert update_response.status_code == 409

    def test_delete_category(self, test_client):
        """Test deleting a category"""
        # Create a category
        create_response = test_client.post("/api/categories", json={
            "name": "To Delete",
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Delete the category
        delete_response = test_client.delete(f"/api/categories/{guid}")
        assert delete_response.status_code == 204

        # Verify it's deleted
        get_response = test_client.get(f"/api/categories/{guid}")
        assert get_response.status_code == 404

    def test_delete_category_not_found(self, test_client):
        """Test deleting a non-existent category returns 404"""
        response = test_client.delete("/api/categories/cat_00000000000000000000000000")
        assert response.status_code == 404

    def test_reorder_categories(self, test_client):
        """Test reordering categories"""
        # Create categories with different display orders
        guids = []
        for i, name in enumerate(["First", "Second", "Third"]):
            response = test_client.post("/api/categories", json={
                "name": f"Reorder {name}",
            })
            assert response.status_code == 201
            guids.append(response.json()["guid"])

        # Reorder: reverse the order
        reorder_response = test_client.post("/api/categories/reorder", json={
            "ordered_guids": list(reversed(guids)),
        })
        assert reorder_response.status_code == 200

        # Verify new order
        reordered = reorder_response.json()
        assert len(reordered) == 3
        assert reordered[0]["guid"] == guids[2]  # Third is now first
        assert reordered[1]["guid"] == guids[1]  # Second stays second
        assert reordered[2]["guid"] == guids[0]  # First is now third

        # Verify display_order values
        assert reordered[0]["display_order"] == 0
        assert reordered[1]["display_order"] == 1
        assert reordered[2]["display_order"] == 2

    def test_reorder_categories_invalid_guid(self, test_client):
        """Test reordering with invalid GUID fails"""
        response = test_client.post("/api/categories/reorder", json={
            "ordered_guids": ["cat_00000000000000000000000000"],
        })
        assert response.status_code == 404

    def test_get_category_stats(self, test_client):
        """Test getting category statistics"""
        # Create some active and inactive categories
        test_client.post("/api/categories", json={
            "name": "Stats Active 1",
            "is_active": True,
        })
        test_client.post("/api/categories", json={
            "name": "Stats Active 2",
            "is_active": True,
        })
        test_client.post("/api/categories", json={
            "name": "Stats Inactive",
            "is_active": False,
        })

        # Get stats
        response = test_client.get("/api/categories/stats")
        assert response.status_code == 200

        stats = response.json()
        assert "total_count" in stats
        assert "active_count" in stats
        assert "inactive_count" in stats
        assert stats["total_count"] >= 3
        assert stats["active_count"] >= 2
        assert stats["inactive_count"] >= 1

    def test_category_display_order_auto_assigned(self, test_client):
        """Test that display_order is auto-assigned for new categories"""
        # Create categories without specifying display_order
        responses = []
        for name in ["Auto Order A", "Auto Order B", "Auto Order C"]:
            response = test_client.post("/api/categories", json={"name": name})
            assert response.status_code == 201
            responses.append(response.json())

        # Each should have a sequential display_order
        orders = [r["display_order"] for r in responses]
        # They should be monotonically increasing
        assert orders == sorted(orders)

    def test_category_deactivate_via_update(self, test_client):
        """Test deactivating a category via update"""
        # Create an active category
        create_response = test_client.post("/api/categories", json={
            "name": "To Deactivate",
            "is_active": True,
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Deactivate
        update_response = test_client.patch(f"/api/categories/{guid}", json={
            "is_active": False,
        })
        assert update_response.status_code == 200
        assert update_response.json()["is_active"] is False

        # Verify in list
        list_response = test_client.get("/api/categories?is_active=true")
        guids_in_active = [c["guid"] for c in list_response.json()]
        assert guid not in guids_in_active


class TestCategorySeedDefaults:
    """Integration tests for POST /api/categories/seed-defaults endpoint"""

    def test_seed_defaults_creates_categories(self, test_client):
        """Test seeding creates default categories on empty team."""
        response = test_client.post("/api/categories/seed-defaults")
        assert response.status_code == 200

        data = response.json()
        assert "categories_created" in data
        assert "categories" in data
        assert data["categories_created"] > 0
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) == data["categories_created"]

        # Verify each category has expected fields
        for cat in data["categories"]:
            assert "guid" in cat
            assert cat["guid"].startswith("cat_")
            assert "name" in cat

    def test_seed_defaults_idempotent(self, test_client):
        """Test seeding twice creates nothing on second call."""
        # First seed
        response1 = test_client.post("/api/categories/seed-defaults")
        assert response1.status_code == 200
        first_count = response1.json()["categories_created"]
        assert first_count > 0

        # Second seed - should create 0
        response2 = test_client.post("/api/categories/seed-defaults")
        assert response2.status_code == 200
        assert response2.json()["categories_created"] == 0
        # Categories list should be the same size
        assert len(response2.json()["categories"]) == len(response1.json()["categories"])

    def test_seed_defaults_skips_existing(self, test_client):
        """Test seeding skips categories that already exist."""
        # Create one category that matches a default name
        test_client.post("/api/categories", json={"name": "Airshow", "icon": "plane"})

        # Seed should skip the existing "Airshow"
        response = test_client.post("/api/categories/seed-defaults")
        assert response.status_code == 200

        data = response.json()
        # Should have created all defaults minus the one that already existed
        from backend.src.services.seed_data_service import DEFAULT_CATEGORIES
        assert data["categories_created"] == len(DEFAULT_CATEGORIES) - 1

    def test_seed_defaults_returns_full_list(self, test_client):
        """Test seed response includes all categories (seeded + pre-existing)."""
        # Create a custom category
        test_client.post("/api/categories", json={"name": "Custom Category"})

        # Seed defaults
        response = test_client.post("/api/categories/seed-defaults")
        assert response.status_code == 200

        data = response.json()
        names = [c["name"] for c in data["categories"]]
        # Custom category should be in the list too
        assert "Custom Category" in names


class TestCategoryValidation:
    """Tests for category input validation"""

    def test_name_required(self, test_client):
        """Test that name is required"""
        response = test_client.post("/api/categories", json={
            "icon": "star",
        })
        assert response.status_code == 422

    def test_name_max_length(self, test_client):
        """Test that name respects max length"""
        response = test_client.post("/api/categories", json={
            "name": "x" * 101,  # Max is 100
        })
        assert response.status_code == 422

    def test_color_format_valid_short(self, test_client):
        """Test that short hex color format is valid"""
        response = test_client.post("/api/categories", json={
            "name": "Short Color Test",
            "color": "#FFF",
        })
        assert response.status_code == 201

    def test_color_format_valid_long(self, test_client):
        """Test that long hex color format is valid"""
        response = test_client.post("/api/categories", json={
            "name": "Long Color Test",
            "color": "#FFFFFF",
        })
        assert response.status_code == 201

    def test_icon_max_length(self, test_client):
        """Test that icon respects max length"""
        response = test_client.post("/api/categories", json={
            "name": "Icon Length Test",
            "icon": "x" * 51,  # Max is 50
        })
        assert response.status_code == 422
