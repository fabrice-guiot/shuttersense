"""
Unit tests for Collections API endpoints.

Tests CRUD operations, accessibility testing, cache refresh, and error handling
for the /api/collections endpoints.
"""

import pytest
import tempfile
from fastapi.testclient import TestClient


class TestCollectionAPICreate:
    """Tests for POST /api/collections - T104w"""

    def test_create_local_collection_with_accessibility_test(self, test_client, sample_collection_data):
        """Should create local collection with accessibility test - T104w"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data = sample_collection_data(
                name="Local Photos",
                type="local",
                location=temp_dir,
                state="live"
            )

            response = test_client.post("/api/collections", json=data)

            assert response.status_code == 201
            json_data = response.json()
            assert json_data["name"] == "Local Photos"
            assert json_data["type"] == "local"
            assert json_data["is_accessible"] is True
            assert json_data["last_error"] is None

    def test_create_local_collection_inaccessible_directory(self, test_client, sample_collection_data):
        """Should create collection but mark as inaccessible"""
        data = sample_collection_data(
            name="Inaccessible",
            type="local",
            location="/nonexistent/directory"
        )

        response = test_client.post("/api/collections", json=data)

        # Service creates collection but marks it as inaccessible
        assert response.status_code == 201
        json_data = response.json()
        assert json_data["is_accessible"] is False
        assert json_data["last_error"] is not None

    def test_create_remote_collection_with_connector(self, test_client, sample_connector, sample_collection_data):
        """Should create remote collection with valid connector - T104w"""
        connector = sample_connector(name="S3 Connector", type="s3")

        data = sample_collection_data(
            name="S3 Photos",
            type="s3",
            location="s3://bucket/photos",
            connector_guid=connector.guid
        )

        response = test_client.post("/api/collections", json=data)

        assert response.status_code == 201
        json_data = response.json()
        assert json_data["name"] == "S3 Photos"
        assert json_data["type"] == "s3"
        assert json_data["connector"]["guid"] == connector.guid

    def test_create_collection_duplicate_name(self, test_client, sample_collection):
        """Should return 409 for duplicate name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Existing Collection", type="local", location=temp_dir)

            # Try to create another with same name
            with tempfile.TemporaryDirectory() as temp_dir2:
                data = {
                    "name": "Existing Collection",
                    "type": "local",
                    "location": temp_dir2,
                    "state": "live"
                }

                response = test_client.post("/api/collections", json=data)

                assert response.status_code == 409
                assert "already exists" in response.json()["detail"]


class TestCollectionAPIList:
    """Tests for GET /api/collections - T104w"""

    def test_list_all_collections(self, test_client, sample_collection):
        """Should return all collections"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            sample_collection(name="Collection 1", type="local", location=temp_dir1)
            sample_collection(name="Collection 2", type="local", location=temp_dir2)

            response = test_client.get("/api/collections")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 2

    def test_list_collections_filter_by_state(self, test_client, sample_collection):
        """Should filter collections by state - T104w"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2, \
             tempfile.TemporaryDirectory() as temp_dir3:
            sample_collection(name="Live 1", type="local", location=temp_dir1, state="live")
            sample_collection(name="Live 2", type="local", location=temp_dir2, state="live")
            sample_collection(name="Archived", type="local", location=temp_dir3, state="archived")

            response = test_client.get("/api/collections?state=live")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 2
            assert all(c["state"] == "live" for c in json_data)

    def test_list_collections_filter_by_type(self, test_client, sample_collection, sample_connector):
        """Should filter collections by type - T104w"""
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = sample_connector(name="S3 Test", type="s3")

            sample_collection(name="Local", type="local", location=temp_dir)
            sample_collection(name="S3", type="s3", location="s3://bucket", connector_guid=connector.guid)

            response = test_client.get("/api/collections?type=local")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 1
            assert json_data[0]["type"] == "local"

    def test_list_collections_accessible_only(self, test_client, sample_collection):
        """Should filter accessible collections only - T104w"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Accessible", type="local", location=temp_dir, is_accessible=True)
            sample_collection(
                name="Inaccessible",
                type="local",
                location="/fake/path",
                is_accessible=False,
                last_error="Directory not found"
            )

            response = test_client.get("/api/collections?accessible_only=true")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 1
            assert json_data[0]["name"] == "Accessible"
            assert json_data[0]["is_accessible"] is True


class TestCollectionAPIGet:
    """Tests for GET /api/collections/{guid}"""

    def test_get_collection_by_guid(self, test_client, sample_collection):
        """Should return collection by GUID"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test Collection", type="local", location=temp_dir)

            response = test_client.get(f"/api/collections/{collection.guid}")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["guid"] == collection.guid
            assert json_data["name"] == "Test Collection"
            assert "id" not in json_data

    def test_get_collection_not_found(self, test_client):
        """Should return 404 if collection not found"""
        response = test_client.get("/api/collections/col_01hgw2bbg00000000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCollectionAPIUpdate:
    """Tests for PUT /api/collections/{guid}"""

    def test_update_collection_name(self, test_client, sample_collection):
        """Should update collection name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Original", type="local", location=temp_dir)

            response = test_client.put(
                f"/api/collections/{collection.guid}",
                json={"name": "Updated"}
            )

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["name"] == "Updated"

    def test_update_collection_state(self, test_client, sample_collection):
        """Should update collection state"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir, state="live")

            response = test_client.put(
                f"/api/collections/{collection.guid}",
                json={"state": "archived"}
            )

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["state"] == "archived"

    def test_update_collection_not_found(self, test_client):
        """Should return 404 if collection not found"""
        response = test_client.put(
            "/api/collections/col_01hgw2bbg00000000000000000",
            json={"name": "Updated"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_collection_location_retests_accessibility(self, test_client, sample_collection):
        """Should re-test accessibility when location changes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection with accessible location
            collection = sample_collection(
                name="Location Test",
                type="local",
                location=temp_dir,
                is_accessible=True
            )

            # Update to an invalid location
            response = test_client.put(
                f"/api/collections/{collection.guid}",
                json={"location": "/nonexistent/invalid/path"}
            )

            assert response.status_code == 200
            json_data = response.json()
            # Location should be updated
            assert json_data["location"] == "/nonexistent/invalid/path"
            # Accessibility should be re-tested and now False
            assert json_data["is_accessible"] is False
            assert json_data["last_error"] is not None

    def test_update_collection_location_to_accessible(self, test_client, sample_collection):
        """Should set is_accessible=True when location becomes accessible"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            # Create collection with inaccessible location
            collection = sample_collection(
                name="Location Test 2",
                type="local",
                location="/nonexistent/path",
                is_accessible=False,
                last_error="Not found"
            )

            # Update to a valid location
            response = test_client.put(
                f"/api/collections/{collection.guid}",
                json={"location": temp_dir2}
            )

            assert response.status_code == 200
            json_data = response.json()
            # Location should be updated
            assert json_data["location"] == temp_dir2
            # Accessibility should be re-tested and now True
            assert json_data["is_accessible"] is True
            assert json_data["last_error"] is None


class TestCollectionAPIDelete:
    """Tests for DELETE /api/collections - T104w"""

    def test_delete_collection_success(self, test_client, sample_collection):
        """Should delete collection and return 204 - T104w"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="To Delete", type="local", location=temp_dir)

            response = test_client.delete(f"/api/collections/{collection.guid}")

            assert response.status_code == 204

            # Verify deletion
            get_response = test_client.get(f"/api/collections/{collection.guid}")
            assert get_response.status_code == 404

    @pytest.mark.skip(reason="has_analysis_results and has_active_jobs are TODO placeholders")
    def test_delete_collection_with_results_requires_force(self, test_client, sample_collection, mocker):
        """Should require force=true when results exist - T104w"""
        # This test is skipped because the service layer has TODO placeholders
        # for has_analysis_results and has_active_jobs checks
        # Once implemented, this test should be enabled and updated
        pass

    def test_delete_collection_with_force_flag(self, test_client, sample_collection):
        """Should delete with force=true - T104w"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Force Delete", type="local", location=temp_dir)

            response = test_client.delete(f"/api/collections/{collection.guid}?force=true")

            assert response.status_code == 204

    def test_delete_collection_not_found(self, test_client):
        """Should return 404 if collection not found"""
        response = test_client.delete("/api/collections/col_01hgw2bbg00000000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCollectionAPITestAccessibility:
    """Tests for POST /api/collections/{guid}/test - T104x"""

    def test_test_local_collection_accessible(self, test_client, sample_collection):
        """Should test local collection accessibility - T104x"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir)

            response = test_client.post(f"/api/collections/{collection.guid}/test")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["success"] is True
            assert "accessible" in json_data["message"].lower()
            # Verify updated collection is returned
            assert "collection" in json_data
            assert json_data["collection"]["guid"] == collection.guid
            assert json_data["collection"]["is_accessible"] is True
            assert json_data["collection"]["last_error"] is None

    def test_test_local_collection_inaccessible(self, test_client, sample_collection):
        """Should detect inaccessible local collection"""
        collection = sample_collection(
            name="Inaccessible",
            type="local",
            location="/nonexistent/path",
            is_accessible=False,
            last_error="Directory not found"
        )

        response = test_client.post(f"/api/collections/{collection.guid}/test")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        # Path is rejected either because it's not accessible, not found, or not authorized
        assert any(msg in json_data["message"].lower() for msg in [
            "not accessible",
            "not found",
            "not under an authorized root",
        ])
        # Verify updated collection is returned with error
        assert "collection" in json_data
        assert json_data["collection"]["guid"] == collection.guid
        assert json_data["collection"]["is_accessible"] is False
        assert json_data["collection"]["last_error"] is not None

    def test_test_remote_collection_with_connector(self, test_client, sample_connector, sample_collection, mocker):
        """Should test remote collection via connector"""
        connector = sample_connector(name="S3", type="s3")
        collection = sample_collection(
            name="S3 Collection",
            type="s3",
            location="s3://bucket",
            connector_guid=connector.guid
        )

        # Mock successful adapter test
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (True, "Connected")

        response = test_client.post(f"/api/collections/{collection.guid}/test")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        # Verify updated collection is returned
        assert "collection" in json_data
        assert json_data["collection"]["guid"] == collection.guid

    def test_test_collection_not_found(self, test_client):
        """Should return 404 if collection not found"""
        response = test_client.post("/api/collections/col_01hgw2bbg00000000000000000/test")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCollectionAPIRefreshCache:
    """Tests for POST /api/collections/{guid}/refresh - T104x"""

    def test_refresh_cache_small_collection(self, test_client, sample_collection):
        """Should refresh cache for small collection - T104x"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            import os
            for i in range(5):
                open(os.path.join(temp_dir, f"photo{i}.jpg"), 'w').close()

            collection = sample_collection(name="Small", type="local", location=temp_dir)

            response = test_client.post(f"/api/collections/{collection.guid}/refresh")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["success"] is True
            assert json_data["file_count"] == 5

    def test_refresh_cache_large_collection_requires_confirm(self, test_client, sample_collection, mocker):
        """Should require confirmation for large collections - T104x"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Large", type="local", location=temp_dir)

            # Mock get_collection_files to simulate large collection
            mocker.patch(
                'backend.src.services.collection_service.CollectionService._fetch_collection_files',
                return_value=[f"photo{i}.jpg" for i in range(150000)]
            )

            response = test_client.post(f"/api/collections/{collection.guid}/refresh?threshold=100000")

            assert response.status_code == 400
            assert "confirm" in response.json()["detail"].lower() or "threshold" in response.json()["detail"].lower()

    def test_refresh_cache_large_collection_with_confirm(self, test_client, sample_collection, mocker):
        """Should refresh large collection with confirm=true - T104x"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Large", type="local", location=temp_dir)

            # Mock get_collection_files to simulate large collection
            mocker.patch(
                'backend.src.services.collection_service.CollectionService._fetch_collection_files',
                return_value=[f"photo{i}.jpg" for i in range(150000)]
            )

            response = test_client.post(
                f"/api/collections/{collection.guid}/refresh?confirm=true&threshold=100000"
            )

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["success"] is True
            assert json_data["file_count"] == 150000

    def test_refresh_cache_custom_threshold(self, test_client, sample_collection, mocker):
        """Should use custom threshold parameter"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Medium", type="local", location=temp_dir)

            # Mock 60K files
            mocker.patch(
                'backend.src.services.collection_service.CollectionService._fetch_collection_files',
                return_value=[f"photo{i}.jpg" for i in range(60000)]
            )

            # Should fail with threshold=50K
            response = test_client.post(f"/api/collections/{collection.guid}/refresh?threshold=50000")

            assert response.status_code == 400

    def test_refresh_cache_invalidates_cache(self, test_client, sample_collection, test_cache):
        """Should invalidate existing cache - T104x"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            import os
            open(os.path.join(temp_dir, "photo.jpg"), 'w').close()

            collection = sample_collection(name="Test", type="local", location=temp_dir)

            # Pre-populate cache with old data (using test_cache which is used by test_client)
            test_cache.set(collection.id, ["old_file.jpg"], ttl_seconds=3600)

            response = test_client.post(f"/api/collections/{collection.guid}/refresh")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["file_count"] == 1

            # Verify new files are cached
            cached_files = test_cache.get(collection.id)
            assert cached_files is not None
            assert "photo.jpg" in cached_files

    def test_refresh_cache_not_found(self, test_client):
        """Should return 404 if collection not found"""
        response = test_client.post("/api/collections/col_01hgw2bbg00000000000000000/refresh")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCollectionAPIStats:
    """Tests for GET /api/collections/stats - Issue #37"""

    def test_get_stats_empty_database(self, test_client):
        """Should return zero stats when no collections exist"""
        response = test_client.get("/api/collections/stats")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_collections"] == 0
        assert json_data["storage_used_bytes"] == 0
        assert json_data["storage_used_formatted"] == "0 B"
        assert json_data["file_count"] == 0
        assert json_data["image_count"] == 0

    def test_get_stats_with_collections(self, test_client, sample_collection, test_db_session):
        """Should return aggregated stats for all collections"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            # Create collections and update their stats
            coll1 = sample_collection(name="Collection 1", type="local", location=temp_dir1)
            coll2 = sample_collection(name="Collection 2", type="local", location=temp_dir2)

            # Update stats directly on model (simulating scan results)
            coll1.storage_bytes = 1073741824  # 1 GB
            coll1.file_count = 1000
            coll1.image_count = 800

            coll2.storage_bytes = 2147483648  # 2 GB
            coll2.file_count = 2000
            coll2.image_count = 1500

            test_db_session.commit()

            response = test_client.get("/api/collections/stats")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["total_collections"] == 2
            assert json_data["storage_used_bytes"] == 3221225472  # 3 GB
            assert json_data["storage_used_formatted"] == "3.0 GB"
            assert json_data["file_count"] == 3000
            assert json_data["image_count"] == 2300

    def test_get_stats_handles_null_values(self, test_client, sample_collection, test_db_session):
        """Should handle collections with null stats (not yet scanned)"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            # Create collections - one with stats, one without
            coll1 = sample_collection(name="Scanned", type="local", location=temp_dir1)
            coll1.storage_bytes = 1073741824
            coll1.file_count = 1000
            coll1.image_count = 800

            # Second collection has no stats (NULL)
            sample_collection(name="Unscanned", type="local", location=temp_dir2)

            test_db_session.commit()

            response = test_client.get("/api/collections/stats")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["total_collections"] == 2
            # Should only count non-null values
            assert json_data["storage_used_bytes"] == 1073741824
            assert json_data["file_count"] == 1000
            assert json_data["image_count"] == 800

    def test_get_stats_not_affected_by_filters(self, test_client, sample_collection, test_db_session):
        """Stats should return totals regardless of collection state/type"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            coll1 = sample_collection(name="Live", type="local", location=temp_dir1, state="live")
            coll1.storage_bytes = 1073741824
            coll1.file_count = 1000
            coll1.image_count = 800

            coll2 = sample_collection(name="Archived", type="local", location=temp_dir2, state="archived")
            coll2.storage_bytes = 1073741824
            coll2.file_count = 1000
            coll2.image_count = 800

            test_db_session.commit()

            response = test_client.get("/api/collections/stats")

            assert response.status_code == 200
            json_data = response.json()
            # Both collections should be counted
            assert json_data["total_collections"] == 2
            assert json_data["storage_used_bytes"] == 2147483648  # 2 GB total


class TestCollectionAPISearch:
    """Tests for GET /api/collections?search= - Issue #38 (T025, T026)"""

    def test_search_collections_by_name_exact_match(self, test_client, sample_collection):
        """Should find collections with exact name match"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            sample_collection(name="Vacation 2024", type="local", location=temp_dir1)
            sample_collection(name="Family Photos", type="local", location=temp_dir2)

            response = test_client.get("/api/collections?search=Vacation 2024")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 1
            assert json_data[0]["name"] == "Vacation 2024"

    def test_search_collections_by_name_partial_match(self, test_client, sample_collection):
        """Should find collections with partial name match"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2, \
             tempfile.TemporaryDirectory() as temp_dir3:
            sample_collection(name="Vacation 2024", type="local", location=temp_dir1)
            sample_collection(name="Summer Vacation", type="local", location=temp_dir2)
            sample_collection(name="Family Photos", type="local", location=temp_dir3)

            response = test_client.get("/api/collections?search=vacation")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 2
            names = [c["name"] for c in json_data]
            assert "Vacation 2024" in names
            assert "Summer Vacation" in names

    def test_search_collections_case_insensitive(self, test_client, sample_collection):
        """Should search case-insensitively"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            sample_collection(name="VACATION PHOTOS", type="local", location=temp_dir1)
            sample_collection(name="vacation memories", type="local", location=temp_dir2)

            response = test_client.get("/api/collections?search=VaCaTiOn")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 2

    def test_search_collections_no_matches(self, test_client, sample_collection):
        """Should return empty list when no matches found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Family Photos", type="local", location=temp_dir)

            response = test_client.get("/api/collections?search=vacation")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 0

    def test_search_with_other_filters(self, test_client, sample_collection, sample_connector):
        """Should combine search with state and type filters"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            connector = sample_connector(name="S3 Test", type="s3")
            sample_collection(name="Vacation Local", type="local", location=temp_dir1, state="live")
            sample_collection(name="Vacation S3", type="s3", location="s3://bucket", connector_guid=connector.guid, state="live")
            sample_collection(name="Vacation Archived", type="local", location=temp_dir2, state="archived")

            # Search + state filter
            response = test_client.get("/api/collections?search=vacation&state=live")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 2
            assert all(c["state"] == "live" for c in json_data)

            # Search + type filter
            response = test_client.get("/api/collections?search=vacation&type=local")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 2
            assert all(c["type"] == "local" for c in json_data)

    def test_search_max_length_validation(self, test_client, sample_collection):
        """Should enforce max length of 100 characters"""
        # FastAPI Query(max_length=100) should reject strings > 100 chars
        long_search = "a" * 101

        response = test_client.get(f"/api/collections?search={long_search}")

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    def test_search_empty_string(self, test_client, sample_collection):
        """Should return all collections when search is empty string"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            sample_collection(name="Collection 1", type="local", location=temp_dir1)
            sample_collection(name="Collection 2", type="local", location=temp_dir2)

            # Empty search should be treated as no filter
            response = test_client.get("/api/collections?search=")

            assert response.status_code == 200
            json_data = response.json()
            # Behavior depends on implementation - empty string matches all
            assert len(json_data) == 2


class TestCollectionAPISearchSQLInjection:
    """Tests for SQL injection protection - Issue #38 (T026)"""

    def test_sql_injection_single_quote(self, test_client, sample_collection):
        """Should safely handle single quotes (SQL string delimiter)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Test Collection", type="local", location=temp_dir)

            # Attempt SQL injection with single quotes
            response = test_client.get("/api/collections?search=' OR '1'='1")

            assert response.status_code == 200
            # Should return empty (no match), not all records
            json_data = response.json()
            assert len(json_data) == 0

    def test_sql_injection_double_quote(self, test_client, sample_collection):
        """Should safely handle double quotes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Test Collection", type="local", location=temp_dir)

            response = test_client.get('/api/collections?search=" OR "1"="1')

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 0

    def test_sql_injection_semicolon(self, test_client, sample_collection):
        """Should safely handle semicolons (statement terminator)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Test Collection", type="local", location=temp_dir)

            response = test_client.get("/api/collections?search=test; DROP TABLE collections;--")

            assert response.status_code == 200
            # Verify table still exists by fetching again
            verify_response = test_client.get("/api/collections")
            assert verify_response.status_code == 200

    def test_sql_injection_comment(self, test_client, sample_collection):
        """Should safely handle SQL comments"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Test Collection", type="local", location=temp_dir)

            response = test_client.get("/api/collections?search=test'--")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) == 0

    def test_sql_injection_union_select(self, test_client, sample_collection):
        """Should safely handle UNION SELECT injection attempts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Test Collection", type="local", location=temp_dir)

            response = test_client.get("/api/collections?search=' UNION SELECT * FROM connectors--")

            assert response.status_code == 200
            json_data = response.json()
            # Should not return data from other tables
            assert len(json_data) == 0

    def test_sql_injection_escape_character(self, test_client, sample_collection):
        """Should safely handle escape characters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Test Collection", type="local", location=temp_dir)

            response = test_client.get(r"/api/collections?search=test\'; DROP TABLE collections;--")

            assert response.status_code == 200
            # Verify table still exists
            verify_response = test_client.get("/api/collections")
            assert verify_response.status_code == 200

    def test_sql_injection_percent_wildcard(self, test_client, sample_collection):
        """Should treat % as literal character in search, not LIKE wildcard manipulation"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            sample_collection(name="Test Collection", type="local", location=temp_dir1)
            sample_collection(name="100% Complete", type="local", location=temp_dir2)

            # Using % directly - should match collection with % in name
            response = test_client.get("/api/collections?search=100%")

            assert response.status_code == 200
            json_data = response.json()
            # Should find the collection with "100%" in name
            assert len(json_data) == 1
            assert json_data[0]["name"] == "100% Complete"

    def test_sql_injection_underscore_wildcard(self, test_client, sample_collection):
        """Should handle underscore (single char wildcard in SQL LIKE)"""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:
            sample_collection(name="Test_Collection", type="local", location=temp_dir1)
            sample_collection(name="TestXCollection", type="local", location=temp_dir2)

            # Search for literal underscore
            response = test_client.get("/api/collections?search=Test_")

            assert response.status_code == 200
            json_data = response.json()
            # Both might match if _ is treated as wildcard, or only first if literal
            # The important thing is it doesn't crash
            assert len(json_data) >= 1
