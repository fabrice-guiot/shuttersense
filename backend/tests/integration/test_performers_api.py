"""
Integration tests for Performers API endpoints.

Tests end-to-end flows for performer management:
- CRUD operations via API
- Filtering by category and search
- Deletion protection (associated with events)
- Statistics endpoint
- Category matching validation

Issue #39 - Calendar Events feature (Phase 11)
"""

import pytest


@pytest.fixture
def sample_category(test_client):
    """Create a sample category for performer tests."""
    response = test_client.post("/api/categories", json={
        "name": "Test Performer Category",
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


class TestPerformersAPI:
    """Integration tests for Performers API endpoints"""

    def test_create_performer_minimal(self, test_client, sample_category):
        """Test creating a performer with minimal required fields"""
        performer_data = {
            "name": "Test Performer",
            "category_guid": sample_category["guid"],
        }

        response = test_client.post("/api/performers", json=performer_data)
        assert response.status_code == 201

        performer = response.json()
        assert performer["name"] == "Test Performer"
        assert performer["category"]["guid"] == sample_category["guid"]
        assert performer["guid"].startswith("prf_")
        assert performer["instagram_handle"] is None
        assert performer["website"] is None
        assert "created_at" in performer
        assert "updated_at" in performer

    def test_create_performer_full(self, test_client, sample_category):
        """Test creating a performer with all fields"""
        performer_data = {
            "name": "Blue Angels",
            "category_guid": sample_category["guid"],
            "website": "https://www.blueangels.navy.mil",
            "instagram_handle": "usaborngirl",
            "additional_info": "U.S. Navy flight demonstration squadron",
        }

        response = test_client.post("/api/performers", json=performer_data)
        assert response.status_code == 201

        performer = response.json()
        assert performer["name"] == "Blue Angels"
        assert performer["website"] == "https://www.blueangels.navy.mil"
        assert performer["instagram_handle"] == "usaborngirl"
        assert performer["instagram_url"] == "https://www.instagram.com/usaborngirl"
        assert performer["additional_info"] == "U.S. Navy flight demonstration squadron"

    def test_create_performer_website_without_protocol(self, test_client, sample_category):
        """Test creating a performer with website without protocol adds https"""
        performer_data = {
            "name": "Simple Site Performer",
            "category_guid": sample_category["guid"],
            "website": "example.com",
        }

        response = test_client.post("/api/performers", json=performer_data)
        assert response.status_code == 201

        performer = response.json()
        assert performer["website"] == "https://example.com"

    def test_create_performer_instagram_strips_at(self, test_client, sample_category):
        """Test creating a performer with @ in Instagram handle strips it"""
        performer_data = {
            "name": "Instagram Test Performer",
            "category_guid": sample_category["guid"],
            "instagram_handle": "@testhandle",
        }

        response = test_client.post("/api/performers", json=performer_data)
        assert response.status_code == 201

        performer = response.json()
        assert performer["instagram_handle"] == "testhandle"

    def test_create_performer_invalid_category(self, test_client):
        """Test creating a performer with non-existent category fails"""
        performer_data = {
            "name": "Invalid Category Performer",
            "category_guid": "cat_00000000000000000000000000",
        }

        response = test_client.post("/api/performers", json=performer_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_performer_inactive_category(self, test_client, sample_category_inactive):
        """Test creating a performer with inactive category fails"""
        performer_data = {
            "name": "Inactive Category Performer",
            "category_guid": sample_category_inactive["guid"],
        }

        response = test_client.post("/api/performers", json=performer_data)
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    def test_get_performer(self, test_client, sample_category):
        """Test getting a performer by GUID"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Get Test Performer",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Get performer
        response = test_client.get(f"/api/performers/{performer_guid}")
        assert response.status_code == 200

        performer = response.json()
        assert performer["guid"] == performer_guid
        assert performer["name"] == "Get Test Performer"

    def test_get_performer_not_found(self, test_client):
        """Test getting non-existent performer returns 404"""
        response = test_client.get("/api/performers/prf_00000000000000000000000000")
        assert response.status_code == 404

    def test_list_performers_empty(self, test_client):
        """Test listing performers when none exist"""
        response = test_client.get("/api/performers")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_performers(self, test_client, sample_category):
        """Test listing performers"""
        # Create performers
        for i in range(3):
            test_client.post("/api/performers", json={
                "name": f"Performer {i}",
                "category_guid": sample_category["guid"],
            })

        response = test_client.get("/api/performers")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    def test_list_performers_by_category(self, test_client, sample_category, second_category):
        """Test filtering performers by category"""
        # Create performers in different categories
        test_client.post("/api/performers", json={
            "name": "Category 1 Performer",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/performers", json={
            "name": "Category 2 Performer",
            "category_guid": second_category["guid"],
        })

        # Filter by first category
        response = test_client.get(f"/api/performers?category_guid={sample_category['guid']}")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Category 1 Performer"

    def test_list_performers_search_by_name(self, test_client, sample_category):
        """Test searching performers by name"""
        test_client.post("/api/performers", json={
            "name": "Blue Angels",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/performers", json={
            "name": "Thunderbirds",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get("/api/performers?search=angels")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Blue Angels"

    def test_list_performers_search_by_instagram(self, test_client, sample_category):
        """Test searching performers by instagram handle"""
        test_client.post("/api/performers", json={
            "name": "Performer with Instagram",
            "category_guid": sample_category["guid"],
            "instagram_handle": "unique_handle_xyz",
        })
        test_client.post("/api/performers", json={
            "name": "Performer without",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get("/api/performers?search=unique_handle")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1

    def test_list_performers_pagination(self, test_client, sample_category):
        """Test pagination"""
        for i in range(5):
            test_client.post("/api/performers", json={
                "name": f"Pagination Performer {i:02d}",
                "category_guid": sample_category["guid"],
            })

        response = test_client.get("/api/performers?limit=2&offset=1")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 5
        assert len(data["items"]) == 2

    def test_update_performer(self, test_client, sample_category):
        """Test updating a performer"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Original Name",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Update performer
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "name": "Updated Name",
            "additional_info": "Updated info",
        })
        assert response.status_code == 200

        performer = response.json()
        assert performer["name"] == "Updated Name"
        assert performer["additional_info"] == "Updated info"

    def test_update_performer_website(self, test_client, sample_category):
        """Test updating performer website"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Website Test Performer",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Update with website
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "website": "https://newsite.com",
        })
        assert response.status_code == 200
        assert response.json()["website"] == "https://newsite.com"

    def test_update_performer_clear_website(self, test_client, sample_category):
        """Test clearing performer website"""
        # Create performer with website
        create_response = test_client.post("/api/performers", json={
            "name": "Clear Website Test",
            "category_guid": sample_category["guid"],
            "website": "https://oldsite.com",
        })
        performer_guid = create_response.json()["guid"]

        # Clear website
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "website": "",
        })
        assert response.status_code == 200
        assert response.json()["website"] is None

    def test_update_performer_instagram(self, test_client, sample_category):
        """Test updating performer instagram handle"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Instagram Update Test",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Update instagram
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "instagram_handle": "newhandle",
        })
        assert response.status_code == 200
        assert response.json()["instagram_handle"] == "newhandle"
        assert response.json()["instagram_url"] == "https://www.instagram.com/newhandle"

    def test_update_performer_clear_instagram(self, test_client, sample_category):
        """Test clearing performer instagram handle"""
        # Create performer with instagram
        create_response = test_client.post("/api/performers", json={
            "name": "Clear Instagram Test",
            "category_guid": sample_category["guid"],
            "instagram_handle": "oldhandle",
        })
        performer_guid = create_response.json()["guid"]

        # Clear instagram
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "instagram_handle": "",
        })
        assert response.status_code == 200
        assert response.json()["instagram_handle"] is None
        assert response.json()["instagram_url"] is None

    def test_update_performer_change_category(self, test_client, sample_category, second_category):
        """Test changing performer category"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Category Change Test",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Update category
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "category_guid": second_category["guid"],
        })
        assert response.status_code == 200
        assert response.json()["category"]["guid"] == second_category["guid"]

    def test_update_performer_inactive_category(self, test_client, sample_category, sample_category_inactive):
        """Test updating to inactive category fails"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Inactive Category Update Test",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Try to update to inactive category
        response = test_client.patch(f"/api/performers/{performer_guid}", json={
            "category_guid": sample_category_inactive["guid"],
        })
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    def test_update_performer_not_found(self, test_client):
        """Test updating non-existent performer returns 404"""
        response = test_client.patch("/api/performers/prf_00000000000000000000000000", json={
            "name": "New Name",
        })
        assert response.status_code == 404

    def test_delete_performer(self, test_client, sample_category):
        """Test deleting a performer"""
        # Create performer
        create_response = test_client.post("/api/performers", json={
            "name": "Delete Test Performer",
            "category_guid": sample_category["guid"],
        })
        performer_guid = create_response.json()["guid"]

        # Delete performer
        response = test_client.delete(f"/api/performers/{performer_guid}")
        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(f"/api/performers/{performer_guid}")
        assert get_response.status_code == 404

    def test_delete_performer_not_found(self, test_client):
        """Test deleting non-existent performer returns 404"""
        response = test_client.delete("/api/performers/prf_00000000000000000000000000")
        assert response.status_code == 404


class TestPerformersAPIStats:
    """Tests for performer statistics endpoint"""

    def test_stats_empty(self, test_client):
        """Test stats when no performers exist"""
        response = test_client.get("/api/performers/stats")
        assert response.status_code == 200

        stats = response.json()
        assert stats["total_count"] == 0
        assert stats["with_instagram_count"] == 0
        assert stats["with_website_count"] == 0

    def test_stats_with_performers(self, test_client, sample_category):
        """Test stats with performers"""
        # Create performers with various fields
        test_client.post("/api/performers", json={
            "name": "With Both",
            "category_guid": sample_category["guid"],
            "website": "https://example.com",
            "instagram_handle": "handle1",
        })
        test_client.post("/api/performers", json={
            "name": "With Website Only",
            "category_guid": sample_category["guid"],
            "website": "https://example2.com",
        })
        test_client.post("/api/performers", json={
            "name": "With Instagram Only",
            "category_guid": sample_category["guid"],
            "instagram_handle": "handle2",
        })
        test_client.post("/api/performers", json={
            "name": "Without Either",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get("/api/performers/stats")
        assert response.status_code == 200

        stats = response.json()
        assert stats["total_count"] == 4
        assert stats["with_instagram_count"] == 2
        assert stats["with_website_count"] == 2


class TestPerformersAPICategoryMatching:
    """Tests for category matching and by-category endpoints"""

    def test_get_by_category(self, test_client, sample_category, second_category):
        """Test getting performers by category"""
        # Create performers in different categories
        test_client.post("/api/performers", json={
            "name": "Cat 1 Performer A",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/performers", json={
            "name": "Cat 1 Performer B",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/performers", json={
            "name": "Cat 2 Performer",
            "category_guid": second_category["guid"],
        })

        response = test_client.get(f"/api/performers/by-category/{sample_category['guid']}")
        assert response.status_code == 200

        performers = response.json()
        assert len(performers) == 2
        assert all(p["category"]["guid"] == sample_category["guid"] for p in performers)

    def test_get_by_category_with_search(self, test_client, sample_category):
        """Test getting performers by category with search"""
        test_client.post("/api/performers", json={
            "name": "Blue Angels",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/performers", json={
            "name": "Thunderbirds",
            "category_guid": sample_category["guid"],
        })

        response = test_client.get(
            f"/api/performers/by-category/{sample_category['guid']}?search=blue"
        )
        assert response.status_code == 200

        performers = response.json()
        assert len(performers) == 1
        assert performers[0]["name"] == "Blue Angels"

    def test_get_by_category_empty(self, test_client, sample_category):
        """Test getting performers for category with none"""
        response = test_client.get(f"/api/performers/by-category/{sample_category['guid']}")
        assert response.status_code == 200

        performers = response.json()
        assert len(performers) == 0

    def test_get_by_category_not_found(self, test_client):
        """Test getting performers for non-existent category"""
        response = test_client.get("/api/performers/by-category/cat_00000000000000000000000000")
        assert response.status_code == 404

    def test_validate_category_match_true(self, test_client, sample_category):
        """Test category match returns true when categories match"""
        # Create performer
        prf_response = test_client.post("/api/performers", json={
            "name": "Category Match Test",
            "category_guid": sample_category["guid"],
        })
        performer_guid = prf_response.json()["guid"]

        response = test_client.get(
            f"/api/performers/{performer_guid}/validate-category/{sample_category['guid']}"
        )
        assert response.status_code == 200
        assert response.json()["matches"] is True

    def test_validate_category_match_false(self, test_client, sample_category, second_category):
        """Test category match returns false when categories don't match"""
        # Create performer in first category
        prf_response = test_client.post("/api/performers", json={
            "name": "Category Mismatch Test",
            "category_guid": sample_category["guid"],
        })
        performer_guid = prf_response.json()["guid"]

        # Check against second category
        response = test_client.get(
            f"/api/performers/{performer_guid}/validate-category/{second_category['guid']}"
        )
        assert response.status_code == 200
        assert response.json()["matches"] is False

    def test_validate_category_match_performer_not_found(self, test_client, sample_category):
        """Test category match with non-existent performer returns 404"""
        response = test_client.get(
            f"/api/performers/prf_00000000000000000000000000/validate-category/{sample_category['guid']}"
        )
        assert response.status_code == 404
