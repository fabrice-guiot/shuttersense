"""
Integration tests for Organizers API endpoints.

Tests end-to-end flows for organizer management:
- CRUD operations via API
- Filtering by category and search
- Deletion protection (referenced by events)
- Statistics endpoint
- Category matching validation

Issue #39 - Calendar Events feature (Phase 9)
"""

import pytest


@pytest.fixture
def sample_category(test_client):
    """Create a sample category for organizer tests."""
    response = test_client.post("/api/categories", json={
        "name": "Test Organizer Category",
        "icon": "users",
        "color": "#8B5CF6",
        "is_active": True,
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sample_category_inactive(test_client):
    """Create an inactive category for testing validation."""
    response = test_client.post("/api/categories", json={
        "name": "Inactive Category",
        "icon": "x",
        "is_active": False,
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def second_category(test_client):
    """Create a second category for testing category filtering."""
    response = test_client.post("/api/categories", json={
        "name": "Second Test Category",
        "icon": "star",
        "color": "#FF5733",
        "is_active": True,
    })
    assert response.status_code == 201
    return response.json()


class TestOrganizersAPI:
    """Integration tests for Organizers API endpoints"""

    def test_create_organizer_minimal(self, test_client, sample_category):
        """Test creating an organizer with minimal required fields"""
        organizer_data = {
            "name": "Test Organizer",
            "category_guid": sample_category["guid"],
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 201

        organizer = response.json()
        assert organizer["name"] == "Test Organizer"
        assert organizer["category"]["guid"] == sample_category["guid"]
        assert organizer["guid"].startswith("org_")
        assert organizer["ticket_required_default"] is False  # Default
        assert "created_at" in organizer
        assert "updated_at" in organizer

    def test_create_organizer_full(self, test_client, sample_category):
        """Test creating an organizer with all fields"""
        organizer_data = {
            "name": "Live Nation",
            "category_guid": sample_category["guid"],
            "website": "https://livenation.com",
            "rating": 4,
            "ticket_required_default": True,
            "notes": "Major concert promoter",
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 201

        organizer = response.json()
        assert organizer["name"] == "Live Nation"
        assert organizer["website"] == "https://livenation.com"
        assert organizer["rating"] == 4
        assert organizer["ticket_required_default"] is True
        assert organizer["notes"] == "Major concert promoter"

    def test_create_organizer_website_without_protocol(self, test_client, sample_category):
        """Test creating an organizer with website without protocol adds https"""
        organizer_data = {
            "name": "Simple Site Org",
            "category_guid": sample_category["guid"],
            "website": "example.com",
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 201

        organizer = response.json()
        assert organizer["website"] == "https://example.com"

    def test_create_organizer_invalid_category(self, test_client):
        """Test creating an organizer with non-existent category fails"""
        organizer_data = {
            "name": "Invalid Category Organizer",
            "category_guid": "cat_00000000000000000000000000",
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_organizer_inactive_category(self, test_client, sample_category_inactive):
        """Test creating an organizer with inactive category fails"""
        organizer_data = {
            "name": "Inactive Category Organizer",
            "category_guid": sample_category_inactive["guid"],
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    def test_create_organizer_invalid_rating_low(self, test_client, sample_category):
        """Test creating an organizer with rating < 1 fails"""
        organizer_data = {
            "name": "Low Rating Organizer",
            "category_guid": sample_category["guid"],
            "rating": 0,
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 422  # Pydantic validation

    def test_create_organizer_invalid_rating_high(self, test_client, sample_category):
        """Test creating an organizer with rating > 5 fails"""
        organizer_data = {
            "name": "High Rating Organizer",
            "category_guid": sample_category["guid"],
            "rating": 6,
        }

        response = test_client.post("/api/organizers", json=organizer_data)
        assert response.status_code == 422  # Pydantic validation

    def test_get_organizer(self, test_client, sample_category):
        """Test getting an organizer by GUID"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Get Test Organizer",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]

        # Get organizer
        response = test_client.get(f"/api/organizers/{organizer_guid}")
        assert response.status_code == 200

        organizer = response.json()
        assert organizer["guid"] == organizer_guid
        assert organizer["name"] == "Get Test Organizer"

    def test_get_organizer_not_found(self, test_client):
        """Test getting non-existent organizer returns 404"""
        response = test_client.get("/api/organizers/org_00000000000000000000000000")
        assert response.status_code == 404

    def test_list_organizers_empty(self, test_client):
        """Test listing organizers when none exist"""
        response = test_client.get("/api/organizers")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_organizers(self, test_client, sample_category):
        """Test listing organizers"""
        # Create organizers
        for i in range(3):
            test_client.post("/api/organizers", json={
                "name": f"Organizer {i}",
                "category_guid": sample_category["guid"],
            })

        response = test_client.get("/api/organizers")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    def test_list_organizers_by_category(self, test_client, sample_category, second_category):
        """Test filtering organizers by category"""
        # Create organizers in different categories
        test_client.post("/api/organizers", json={
            "name": "Category 1 Organizer",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/organizers", json={
            "name": "Category 2 Organizer",
            "category_guid": second_category["guid"],
        })

        # Filter by first category
        response = test_client.get(f"/api/organizers?category_guid={sample_category['guid']}")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Category 1 Organizer"

    def test_list_organizers_search_by_name(self, test_client, sample_category):
        """Test searching organizers by name"""
        test_client.post("/api/organizers", json={
            "name": "Live Nation",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/organizers", json={
            "name": "AEG Presents",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get("/api/organizers?search=nation")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Live Nation"

    def test_list_organizers_search_by_website(self, test_client, sample_category):
        """Test searching organizers by website"""
        test_client.post("/api/organizers", json={
            "name": "Org with Website",
            "category_guid": sample_category["guid"],
            "website": "https://example-search.com",
        })
        test_client.post("/api/organizers", json={
            "name": "Org without",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get("/api/organizers?search=example-search")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1

    def test_list_organizers_pagination(self, test_client, sample_category):
        """Test pagination"""
        for i in range(5):
            test_client.post("/api/organizers", json={
                "name": f"Pagination Org {i:02d}",
                "category_guid": sample_category["guid"],
            })

        response = test_client.get("/api/organizers?limit=2&offset=1")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 5
        assert len(data["items"]) == 2

    def test_update_organizer(self, test_client, sample_category):
        """Test updating an organizer"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Original Name",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]

        # Update organizer
        response = test_client.patch(f"/api/organizers/{organizer_guid}", json={
            "name": "Updated Name",
            "rating": 5,
            "notes": "Updated notes",
        })
        assert response.status_code == 200

        organizer = response.json()
        assert organizer["name"] == "Updated Name"
        assert organizer["rating"] == 5
        assert organizer["notes"] == "Updated notes"

    def test_update_organizer_website(self, test_client, sample_category):
        """Test updating organizer website"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Website Test Org",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]

        # Update with website
        response = test_client.patch(f"/api/organizers/{organizer_guid}", json={
            "website": "https://newsite.com",
        })
        assert response.status_code == 200
        assert response.json()["website"] == "https://newsite.com"

    def test_update_organizer_clear_website(self, test_client, sample_category):
        """Test clearing organizer website"""
        # Create organizer with website
        create_response = test_client.post("/api/organizers", json={
            "name": "Clear Website Test",
            "category_guid": sample_category["guid"],
            "website": "https://oldsite.com",
        })
        organizer_guid = create_response.json()["guid"]

        # Clear website
        response = test_client.patch(f"/api/organizers/{organizer_guid}", json={
            "website": "",
        })
        assert response.status_code == 200
        assert response.json()["website"] is None

    def test_update_organizer_ticket_default(self, test_client, sample_category):
        """Test updating ticket_required_default"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Ticket Test Org",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]
        assert create_response.json()["ticket_required_default"] is False

        # Update ticket default
        response = test_client.patch(f"/api/organizers/{organizer_guid}", json={
            "ticket_required_default": True,
        })
        assert response.status_code == 200
        assert response.json()["ticket_required_default"] is True

    def test_update_organizer_change_category(self, test_client, sample_category, second_category):
        """Test changing organizer category"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Category Change Test",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]

        # Update category
        response = test_client.patch(f"/api/organizers/{organizer_guid}", json={
            "category_guid": second_category["guid"],
        })
        assert response.status_code == 200
        assert response.json()["category"]["guid"] == second_category["guid"]

    def test_update_organizer_inactive_category(self, test_client, sample_category, sample_category_inactive):
        """Test updating to inactive category fails"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Inactive Category Update Test",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]

        # Try to update to inactive category
        response = test_client.patch(f"/api/organizers/{organizer_guid}", json={
            "category_guid": sample_category_inactive["guid"],
        })
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    def test_update_organizer_not_found(self, test_client):
        """Test updating non-existent organizer returns 404"""
        response = test_client.patch("/api/organizers/org_00000000000000000000000000", json={
            "name": "New Name",
        })
        assert response.status_code == 404

    def test_delete_organizer(self, test_client, sample_category):
        """Test deleting an organizer"""
        # Create organizer
        create_response = test_client.post("/api/organizers", json={
            "name": "Delete Test Org",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = create_response.json()["guid"]

        # Delete organizer
        response = test_client.delete(f"/api/organizers/{organizer_guid}")
        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(f"/api/organizers/{organizer_guid}")
        assert get_response.status_code == 404

    def test_delete_organizer_not_found(self, test_client):
        """Test deleting non-existent organizer returns 404"""
        response = test_client.delete("/api/organizers/org_00000000000000000000000000")
        assert response.status_code == 404

    def test_delete_organizer_with_events(self, test_client, sample_category):
        """Test deleting organizer with events fails"""
        from datetime import date

        # Create location for event
        loc_response = test_client.post("/api/locations", json={
            "name": "Test Location for Event",
            "category_guid": sample_category["guid"],
        })
        location_guid = loc_response.json()["guid"]

        # Create organizer
        org_response = test_client.post("/api/organizers", json={
            "name": "Organizer with Events",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = org_response.json()["guid"]

        # Create event using this organizer
        test_client.post("/api/events", json={
            "title": "Event using organizer",
            "event_date": date.today().isoformat(),
            "category_guid": sample_category["guid"],
            "location_guid": location_guid,
            "organizer_guid": organizer_guid,
            "attendance": "planned",
        })

        # Try to delete organizer
        response = test_client.delete(f"/api/organizers/{organizer_guid}")
        assert response.status_code == 409
        assert "event" in response.json()["detail"].lower()


class TestOrganizersAPIStats:
    """Tests for organizer statistics endpoint"""

    def test_stats_empty(self, test_client):
        """Test stats when no organizers exist"""
        response = test_client.get("/api/organizers/stats")
        assert response.status_code == 200

        stats = response.json()
        assert stats["total_count"] == 0
        assert stats["with_rating_count"] == 0
        assert stats["avg_rating"] is None

    def test_stats_with_organizers(self, test_client, sample_category):
        """Test stats with organizers"""
        # Create organizers with ratings
        test_client.post("/api/organizers", json={
            "name": "Rating 4 Org",
            "category_guid": sample_category["guid"],
            "rating": 4,
        })
        test_client.post("/api/organizers", json={
            "name": "Rating 5 Org",
            "category_guid": sample_category["guid"],
            "rating": 5,
        })
        test_client.post("/api/organizers", json={
            "name": "No Rating Org",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get("/api/organizers/stats")
        assert response.status_code == 200

        stats = response.json()
        assert stats["total_count"] == 3
        assert stats["with_rating_count"] == 2
        assert stats["avg_rating"] == 4.5


class TestOrganizersAPICategoryMatching:
    """Tests for category matching and by-category endpoints"""

    def test_get_by_category(self, test_client, sample_category, second_category):
        """Test getting organizers by category"""
        # Create organizers in different categories
        test_client.post("/api/organizers", json={
            "name": "Cat 1 Org A",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/organizers", json={
            "name": "Cat 1 Org B",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/organizers", json={
            "name": "Cat 2 Org",
            "category_guid": second_category["guid"],
        })

        response = test_client.get(f"/api/organizers/by-category/{sample_category['guid']}")
        assert response.status_code == 200

        organizers = response.json()
        assert len(organizers) == 2
        assert all(org["category"]["guid"] == sample_category["guid"] for org in organizers)

    def test_get_by_category_empty(self, test_client, sample_category):
        """Test getting organizers for category with none"""
        response = test_client.get(f"/api/organizers/by-category/{sample_category['guid']}")
        assert response.status_code == 200

        organizers = response.json()
        assert len(organizers) == 0

    def test_get_by_category_not_found(self, test_client):
        """Test getting organizers for non-existent category"""
        response = test_client.get("/api/organizers/by-category/cat_00000000000000000000000000")
        assert response.status_code == 404

    def test_validate_category_match_true(self, test_client, sample_category):
        """Test category match returns true when categories match"""
        # Create organizer
        org_response = test_client.post("/api/organizers", json={
            "name": "Category Match Test",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = org_response.json()["guid"]

        response = test_client.get(
            f"/api/organizers/{organizer_guid}/validate-category/{sample_category['guid']}"
        )
        assert response.status_code == 200
        assert response.json()["matches"] is True

    def test_validate_category_match_false(self, test_client, sample_category, second_category):
        """Test category match returns false when categories don't match"""
        # Create organizer in first category
        org_response = test_client.post("/api/organizers", json={
            "name": "Category Mismatch Test",
            "category_guid": sample_category["guid"],
        })
        organizer_guid = org_response.json()["guid"]

        # Check against second category
        response = test_client.get(
            f"/api/organizers/{organizer_guid}/validate-category/{second_category['guid']}"
        )
        assert response.status_code == 200
        assert response.json()["matches"] is False

    def test_validate_category_match_organizer_not_found(self, test_client, sample_category):
        """Test category match with non-existent organizer returns 404"""
        response = test_client.get(
            f"/api/organizers/org_00000000000000000000000000/validate-category/{sample_category['guid']}"
        )
        assert response.status_code == 404
