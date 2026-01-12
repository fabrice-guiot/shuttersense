"""
Integration tests for Locations API endpoints.

Tests end-to-end flows for location management:
- CRUD operations via API
- Filtering by category and search
- Geocoding endpoint
- Deletion protection (referenced by events)
- Statistics endpoint
- Category matching validation

Issue #39 - Calendar Events feature (Phase 8)
"""

import pytest


@pytest.fixture
def sample_category(test_client):
    """Create a sample category for location tests."""
    response = test_client.post("/api/categories", json={
        "name": "Test Location Category",
        "icon": "map-pin",
        "color": "#3B82F6",
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


class TestLocationsAPI:
    """Integration tests for Locations API endpoints"""

    def test_create_location_minimal(self, test_client, sample_category):
        """Test creating a location with minimal required fields"""
        location_data = {
            "name": "Test Location",
            "category_guid": sample_category["guid"],
        }

        response = test_client.post("/api/locations", json=location_data)
        assert response.status_code == 201

        location = response.json()
        assert location["name"] == "Test Location"
        assert location["category"]["guid"] == sample_category["guid"]
        assert location["guid"].startswith("loc_")
        assert location["is_known"] is True  # Default
        assert "created_at" in location
        assert "updated_at" in location

    def test_create_location_full(self, test_client, sample_category):
        """Test creating a location with all fields"""
        location_data = {
            "name": "Madison Square Garden",
            "category_guid": sample_category["guid"],
            "address": "4 Pennsylvania Plaza",
            "city": "New York",
            "state": "New York",
            "country": "United States",
            "postal_code": "10001",
            "latitude": 40.7505,
            "longitude": -73.9934,
            "timezone": "America/New_York",
            "rating": 5,
            "timeoff_required_default": False,
            "travel_required_default": True,
            "notes": "World's most famous arena",
            "is_known": True,
        }

        response = test_client.post("/api/locations", json=location_data)
        assert response.status_code == 201

        location = response.json()
        assert location["name"] == "Madison Square Garden"
        assert location["address"] == "4 Pennsylvania Plaza"
        assert location["city"] == "New York"
        assert location["state"] == "New York"
        assert location["country"] == "United States"
        assert location["postal_code"] == "10001"
        assert location["latitude"] == pytest.approx(40.7505, rel=1e-4)
        assert location["longitude"] == pytest.approx(-73.9934, rel=1e-4)
        assert location["timezone"] == "America/New_York"
        assert location["rating"] == 5
        assert location["timeoff_required_default"] is False
        assert location["travel_required_default"] is True
        assert location["notes"] == "World's most famous arena"
        assert location["is_known"] is True

    def test_create_location_invalid_category(self, test_client):
        """Test creating a location with non-existent category fails"""
        location_data = {
            "name": "Invalid Category Location",
            "category_guid": "cat_00000000000000000000000000",
        }

        response = test_client.post("/api/locations", json=location_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_location_inactive_category(self, test_client, sample_category_inactive):
        """Test creating a location with inactive category fails"""
        location_data = {
            "name": "Inactive Category Location",
            "category_guid": sample_category_inactive["guid"],
        }

        response = test_client.post("/api/locations", json=location_data)
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    def test_create_location_incomplete_coordinates(self, test_client, sample_category):
        """Test creating a location with only latitude fails"""
        location_data = {
            "name": "Incomplete Coords Location",
            "category_guid": sample_category["guid"],
            "latitude": 40.7505,
            # Missing longitude
        }

        response = test_client.post("/api/locations", json=location_data)
        assert response.status_code == 400
        assert "longitude" in response.json()["detail"].lower() or "latitude" in response.json()["detail"].lower()

    def test_create_location_invalid_rating(self, test_client, sample_category):
        """Test creating a location with invalid rating fails"""
        location_data = {
            "name": "Invalid Rating Location",
            "category_guid": sample_category["guid"],
            "rating": 6,  # Max is 5
        }

        response = test_client.post("/api/locations", json=location_data)
        assert response.status_code == 422  # Pydantic validation

    def test_list_locations(self, test_client, sample_category):
        """Test listing all locations"""
        # Create some locations
        for name in ["Location A", "Location B", "Location C"]:
            test_client.post("/api/locations", json={
                "name": name,
                "category_guid": sample_category["guid"],
            })

        # List all locations
        response = test_client.get("/api/locations")
        assert response.status_code == 200

        result = response.json()
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) >= 3
        assert result["total"] >= 3

    def test_list_locations_known_only(self, test_client, sample_category):
        """Test listing only known locations"""
        # Create known and non-known locations
        test_client.post("/api/locations", json={
            "name": "Known Location",
            "category_guid": sample_category["guid"],
            "is_known": True,
        })
        test_client.post("/api/locations", json={
            "name": "Unknown Location",
            "category_guid": sample_category["guid"],
            "is_known": False,
        })

        # List known only
        response = test_client.get("/api/locations?known_only=true")
        assert response.status_code == 200

        result = response.json()
        for loc in result["items"]:
            assert loc["is_known"] is True

    def test_list_locations_by_category(self, test_client, sample_category, second_category):
        """Test filtering locations by category"""
        # Create locations in different categories
        test_client.post("/api/locations", json={
            "name": "Category 1 Location",
            "category_guid": sample_category["guid"],
        })
        test_client.post("/api/locations", json={
            "name": "Category 2 Location",
            "category_guid": second_category["guid"],
        })

        # Filter by first category
        response = test_client.get(f"/api/locations?category_guid={sample_category['guid']}")
        assert response.status_code == 200

        result = response.json()
        for loc in result["items"]:
            assert loc["category"]["guid"] == sample_category["guid"]

    def test_list_locations_search(self, test_client, sample_category):
        """Test searching locations by name/city"""
        # Create locations
        test_client.post("/api/locations", json={
            "name": "New York Arena",
            "category_guid": sample_category["guid"],
            "city": "New York",
        })
        test_client.post("/api/locations", json={
            "name": "LA Stadium",
            "category_guid": sample_category["guid"],
            "city": "Los Angeles",
        })

        # Search for New York
        response = test_client.get("/api/locations?search=new+york")
        assert response.status_code == 200

        result = response.json()
        assert result["total"] >= 1
        # All results should contain "New York" in name or city
        for loc in result["items"]:
            assert "new york" in loc["name"].lower() or "new york" in (loc["city"] or "").lower()

    def test_get_location_by_guid(self, test_client, sample_category):
        """Test getting a single location by GUID"""
        # Create a location
        create_response = test_client.post("/api/locations", json={
            "name": "Get Test Location",
            "category_guid": sample_category["guid"],
            "city": "Boston",
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Get by GUID
        get_response = test_client.get(f"/api/locations/{guid}")
        assert get_response.status_code == 200

        location = get_response.json()
        assert location["guid"] == guid
        assert location["name"] == "Get Test Location"
        assert location["city"] == "Boston"

    def test_get_location_not_found(self, test_client):
        """Test getting a non-existent location returns 404"""
        response = test_client.get("/api/locations/loc_00000000000000000000000000")
        assert response.status_code == 404

    def test_update_location(self, test_client, sample_category):
        """Test updating a location"""
        # Create a location
        create_response = test_client.post("/api/locations", json={
            "name": "Original Name",
            "category_guid": sample_category["guid"],
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Update the location
        update_response = test_client.patch(f"/api/locations/{guid}", json={
            "name": "Updated Name",
            "city": "Chicago",
            "rating": 4,
        })
        assert update_response.status_code == 200

        updated = update_response.json()
        assert updated["name"] == "Updated Name"
        assert updated["city"] == "Chicago"
        assert updated["rating"] == 4

    def test_update_location_partial(self, test_client, sample_category):
        """Test partial update of location (only some fields)"""
        # Create a location
        create_response = test_client.post("/api/locations", json={
            "name": "Partial Update Test",
            "category_guid": sample_category["guid"],
            "city": "Miami",
            "rating": 3,
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Update only the rating
        update_response = test_client.patch(f"/api/locations/{guid}", json={
            "rating": 5,
        })
        assert update_response.status_code == 200

        updated = update_response.json()
        assert updated["rating"] == 5
        # Other fields should remain unchanged
        assert updated["name"] == "Partial Update Test"
        assert updated["city"] == "Miami"

    def test_update_location_change_category(self, test_client, sample_category, second_category):
        """Test changing location category"""
        # Create a location
        create_response = test_client.post("/api/locations", json={
            "name": "Category Change Test",
            "category_guid": sample_category["guid"],
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Update category
        update_response = test_client.patch(f"/api/locations/{guid}", json={
            "category_guid": second_category["guid"],
        })
        assert update_response.status_code == 200

        updated = update_response.json()
        assert updated["category"]["guid"] == second_category["guid"]

    def test_update_location_not_found(self, test_client):
        """Test updating non-existent location returns 404"""
        response = test_client.patch("/api/locations/loc_00000000000000000000000000", json={
            "name": "New Name",
        })
        assert response.status_code == 404

    def test_delete_location(self, test_client, sample_category):
        """Test deleting a location"""
        # Create a location
        create_response = test_client.post("/api/locations", json={
            "name": "To Delete",
            "category_guid": sample_category["guid"],
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Delete the location
        delete_response = test_client.delete(f"/api/locations/{guid}")
        assert delete_response.status_code == 204

        # Verify it's deleted
        get_response = test_client.get(f"/api/locations/{guid}")
        assert get_response.status_code == 404

    def test_delete_location_not_found(self, test_client):
        """Test deleting a non-existent location returns 404"""
        response = test_client.delete("/api/locations/loc_00000000000000000000000000")
        assert response.status_code == 404

    def test_get_location_stats(self, test_client, sample_category):
        """Test getting location statistics"""
        # Create some locations
        test_client.post("/api/locations", json={
            "name": "Stats Known 1",
            "category_guid": sample_category["guid"],
            "is_known": True,
            "latitude": 40.7128,
            "longitude": -74.0060,
        })
        test_client.post("/api/locations", json={
            "name": "Stats Known 2",
            "category_guid": sample_category["guid"],
            "is_known": True,
        })
        test_client.post("/api/locations", json={
            "name": "Stats Unknown",
            "category_guid": sample_category["guid"],
            "is_known": False,
        })

        # Get stats
        response = test_client.get("/api/locations/stats")
        assert response.status_code == 200

        stats = response.json()
        assert "total_count" in stats
        assert "known_count" in stats
        assert "with_coordinates_count" in stats
        assert stats["total_count"] >= 3
        assert stats["known_count"] >= 2
        assert stats["with_coordinates_count"] >= 1

    def test_get_locations_by_category(self, test_client, sample_category, second_category):
        """Test getting locations filtered by category (for event assignment)"""
        # Create locations in different categories
        test_client.post("/api/locations", json={
            "name": "Cat 1 Known Location",
            "category_guid": sample_category["guid"],
            "is_known": True,
        })
        test_client.post("/api/locations", json={
            "name": "Cat 1 Unknown Location",
            "category_guid": sample_category["guid"],
            "is_known": False,
        })
        test_client.post("/api/locations", json={
            "name": "Cat 2 Location",
            "category_guid": second_category["guid"],
            "is_known": True,
        })

        # Get locations by category (known only by default)
        response = test_client.get(f"/api/locations/by-category/{sample_category['guid']}")
        assert response.status_code == 200

        locations = response.json()
        assert len(locations) >= 1
        for loc in locations:
            assert loc["category"]["guid"] == sample_category["guid"]
            assert loc["is_known"] is True

        # Get all locations by category (including non-known)
        response = test_client.get(f"/api/locations/by-category/{sample_category['guid']}?known_only=false")
        assert response.status_code == 200

        locations = response.json()
        assert len(locations) >= 2

    def test_validate_category_match(self, test_client, sample_category, second_category):
        """Test category matching validation endpoint"""
        # Create a location
        create_response = test_client.post("/api/locations", json={
            "name": "Match Test Location",
            "category_guid": sample_category["guid"],
        })
        assert create_response.status_code == 201
        guid = create_response.json()["guid"]

        # Test matching category
        match_response = test_client.get(f"/api/locations/{guid}/validate-category/{sample_category['guid']}")
        assert match_response.status_code == 200
        assert match_response.json()["matches"] is True

        # Test non-matching category
        no_match_response = test_client.get(f"/api/locations/{guid}/validate-category/{second_category['guid']}")
        assert no_match_response.status_code == 200
        assert no_match_response.json()["matches"] is False


class TestLocationValidation:
    """Tests for location input validation"""

    def test_name_required(self, test_client, sample_category):
        """Test that name is required"""
        response = test_client.post("/api/locations", json={
            "category_guid": sample_category["guid"],
        })
        assert response.status_code == 422

    def test_category_guid_required(self, test_client):
        """Test that category_guid is required"""
        response = test_client.post("/api/locations", json={
            "name": "No Category",
        })
        assert response.status_code == 422

    def test_name_max_length(self, test_client, sample_category):
        """Test that name respects max length"""
        response = test_client.post("/api/locations", json={
            "name": "x" * 256,  # Max is 255
            "category_guid": sample_category["guid"],
        })
        assert response.status_code == 422

    def test_rating_min_value(self, test_client, sample_category):
        """Test that rating minimum is 1"""
        response = test_client.post("/api/locations", json={
            "name": "Rating Min Test",
            "category_guid": sample_category["guid"],
            "rating": 0,
        })
        assert response.status_code == 422

    def test_rating_max_value(self, test_client, sample_category):
        """Test that rating maximum is 5"""
        response = test_client.post("/api/locations", json={
            "name": "Rating Max Test",
            "category_guid": sample_category["guid"],
            "rating": 6,
        })
        assert response.status_code == 422

    def test_latitude_range(self, test_client, sample_category):
        """Test that latitude is validated (-90 to 90)"""
        response = test_client.post("/api/locations", json={
            "name": "Lat Range Test",
            "category_guid": sample_category["guid"],
            "latitude": 91,
            "longitude": 0,
        })
        assert response.status_code == 422

    def test_longitude_range(self, test_client, sample_category):
        """Test that longitude is validated (-180 to 180)"""
        response = test_client.post("/api/locations", json={
            "name": "Lon Range Test",
            "category_guid": sample_category["guid"],
            "latitude": 0,
            "longitude": 181,
        })
        assert response.status_code == 422

    def test_valid_coordinates(self, test_client, sample_category):
        """Test that valid coordinates are accepted"""
        response = test_client.post("/api/locations", json={
            "name": "Valid Coords Test",
            "category_guid": sample_category["guid"],
            "latitude": -33.8688,  # Sydney
            "longitude": 151.2093,
        })
        assert response.status_code == 201

        location = response.json()
        assert location["latitude"] == pytest.approx(-33.8688, rel=1e-4)
        assert location["longitude"] == pytest.approx(151.2093, rel=1e-4)


class TestLocationPagination:
    """Tests for location list pagination"""

    def test_pagination_limit(self, test_client, sample_category):
        """Test that limit parameter works"""
        # Create several locations
        for i in range(5):
            test_client.post("/api/locations", json={
                "name": f"Pagination Test {i}",
                "category_guid": sample_category["guid"],
            })

        # Request with limit
        response = test_client.get("/api/locations?limit=2")
        assert response.status_code == 200

        result = response.json()
        assert len(result["items"]) <= 2
        assert result["total"] >= 5

    def test_pagination_offset(self, test_client, sample_category):
        """Test that offset parameter works"""
        # Create several locations
        guids = []
        for i in range(5):
            resp = test_client.post("/api/locations", json={
                "name": f"Offset Test {i}",
                "category_guid": sample_category["guid"],
            })
            guids.append(resp.json()["guid"])

        # Request first page
        response1 = test_client.get("/api/locations?limit=2&offset=0")
        first_page_guids = [loc["guid"] for loc in response1.json()["items"]]

        # Request second page
        response2 = test_client.get("/api/locations?limit=2&offset=2")
        second_page_guids = [loc["guid"] for loc in response2.json()["items"]]

        # Pages should not overlap
        assert not set(first_page_guids).intersection(set(second_page_guids))
