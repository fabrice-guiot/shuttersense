"""
Integration tests for configuration import/export flow.

Tests end-to-end flows across multiple config API endpoints,
ensuring proper integration for YAML import with conflict detection
and resolution.

T153: Backend integration test for import flow
"""

import pytest


class TestConfigImportFlow:
    """Integration tests for configuration import lifecycle - T153"""

    def test_complete_import_flow_no_conflicts(self, test_client):
        """
        Test complete import flow without conflicts.

        Flow:
        1. Upload YAML file
        2. Verify import session created with no conflicts
        3. Apply import
        4. Verify configuration is updated
        """
        # Step 1: Upload YAML file
        yaml_content = """
photo_extensions:
  - .dng
  - .cr3
  - .arw
metadata_extensions:
  - .xmp
camera_mappings:
  AB3D:
    name: Canon EOS R5
    serial_number: "12345"
  XY7Z:
    name: Sony A7R IV
    serial_number: "67890"
processing_methods:
  HDR: High Dynamic Range
  BW: Black and White
"""
        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")}
        )
        assert import_response.status_code == 200
        session = import_response.json()
        session_id = session["session_id"]

        # Step 2: Verify session created with no conflicts
        assert session["status"] == "pending"
        assert session["conflicts"] == []
        assert session["total_items"] > 0

        # Step 3: Apply import
        apply_response = test_client.post(
            f"/api/config/import/{session_id}/resolve",
            json={"resolutions": []}
        )
        assert apply_response.status_code == 200
        apply_result = apply_response.json()
        assert apply_result["success"] is True
        assert apply_result["items_imported"] > 0

        # Step 4: Verify configuration is updated
        config_response = test_client.get("/api/config")
        assert config_response.status_code == 200
        config = config_response.json()

        assert "AB3D" in config["cameras"]
        assert config["cameras"]["AB3D"]["name"] == "Canon EOS R5"
        assert "HDR" in config["processing_methods"]
        assert config["processing_methods"]["HDR"] == "High Dynamic Range"

    def test_import_flow_with_conflicts_use_yaml(self, test_client):
        """
        Test import flow with conflicts, resolving to use YAML values.

        Flow:
        1. Create initial camera configuration
        2. Upload YAML with different camera value
        3. Verify conflict is detected
        4. Resolve conflict to use YAML value
        5. Verify YAML value was applied
        """
        # Step 1: Create initial camera configuration
        create_response = test_client.post(
            "/api/config/cameras/AB3D",
            json={
                "value": {"name": "Old Camera Name", "serial_number": "11111"},
                "description": "Initial camera"
            }
        )
        assert create_response.status_code == 201

        # Step 2: Upload YAML with different camera value
        yaml_content = """
camera_mappings:
  AB3D:
    name: New Camera Name
    serial_number: "22222"
"""
        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")}
        )
        assert import_response.status_code == 200
        session = import_response.json()
        session_id = session["session_id"]

        # Step 3: Verify conflict is detected
        assert len(session["conflicts"]) == 1
        conflict = session["conflicts"][0]
        assert conflict["category"] == "cameras"
        assert conflict["key"] == "AB3D"
        assert conflict["database_value"]["name"] == "Old Camera Name"
        assert conflict["yaml_value"]["name"] == "New Camera Name"

        # Step 4: Resolve conflict to use YAML value
        apply_response = test_client.post(
            f"/api/config/import/{session_id}/resolve",
            json={
                "resolutions": [
                    {"category": "cameras", "key": "AB3D", "use_yaml": True}
                ]
            }
        )
        assert apply_response.status_code == 200
        assert apply_response.json()["success"] is True

        # Step 5: Verify YAML value was applied
        config_response = test_client.get("/api/config/cameras/AB3D")
        assert config_response.status_code == 200
        camera = config_response.json()
        assert camera["value"]["name"] == "New Camera Name"
        assert camera["value"]["serial_number"] == "22222"

    def test_import_flow_with_conflicts_keep_database(self, test_client):
        """
        Test import flow with conflicts, resolving to keep database values.

        Flow:
        1. Create initial processing method
        2. Upload YAML with different value
        3. Resolve conflict to keep database value
        4. Verify database value is retained
        """
        # Step 1: Create initial processing method
        create_response = test_client.post(
            "/api/config/processing_methods/HDR",
            json={
                "value": "Original HDR Description",
                "description": "Original method"
            }
        )
        assert create_response.status_code == 201

        # Step 2: Upload YAML with different value
        yaml_content = """
processing_methods:
  HDR: New HDR Description From YAML
"""
        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")}
        )
        assert import_response.status_code == 200
        session = import_response.json()
        session_id = session["session_id"]

        # Verify conflict detected
        assert len(session["conflicts"]) == 1

        # Step 3: Resolve conflict to keep database value
        apply_response = test_client.post(
            f"/api/config/import/{session_id}/resolve",
            json={
                "resolutions": [
                    {"category": "processing_methods", "key": "HDR", "use_yaml": False}
                ]
            }
        )
        assert apply_response.status_code == 200
        result = apply_response.json()
        assert result["items_skipped"] > 0

        # Step 4: Verify database value is retained
        config_response = test_client.get("/api/config/processing_methods/HDR")
        assert config_response.status_code == 200
        method = config_response.json()
        assert method["value"] == "Original HDR Description"

    def test_import_cancel_flow(self, test_client):
        """
        Test canceling an import session.

        Flow:
        1. Start import
        2. Cancel import
        3. Verify session is cancelled
        """
        # Step 1: Start import
        yaml_content = """
camera_mappings:
  TEST1:
    name: Test Camera
"""
        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")}
        )
        assert import_response.status_code == 200
        session_id = import_response.json()["session_id"]

        # Step 2: Cancel import
        cancel_response = test_client.post(f"/api/config/import/{session_id}/cancel")
        assert cancel_response.status_code == 200

        # Step 3: Verify session is cancelled
        get_response = test_client.get(f"/api/config/import/{session_id}")
        assert get_response.status_code == 404

    def test_import_session_retrieval(self, test_client):
        """
        Test retrieving import session status.

        Flow:
        1. Start import
        2. Retrieve session status
        3. Verify session data is complete
        """
        yaml_content = """
photo_extensions:
  - .dng
camera_mappings:
  TEST2:
    name: Test Camera 2
"""
        # Step 1: Start import
        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")}
        )
        assert import_response.status_code == 200
        session_id = import_response.json()["session_id"]

        # Step 2: Retrieve session status
        get_response = test_client.get(f"/api/config/import/{session_id}")
        assert get_response.status_code == 200
        session = get_response.json()

        # Step 3: Verify session data
        assert session["session_id"] == session_id
        assert session["status"] == "pending"
        assert "total_items" in session
        assert "new_items" in session
        assert "conflicts" in session
        assert "file_name" in session

    def test_import_invalid_yaml(self, test_client):
        """
        Test importing invalid YAML content.

        Should return validation error.
        """
        invalid_yaml = "invalid: yaml: content: {"

        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", invalid_yaml, "application/x-yaml")}
        )
        assert import_response.status_code == 400
        assert "yaml" in import_response.json()["detail"].lower()


class TestConfigExportFlow:
    """Integration tests for configuration export - T153"""

    def test_export_after_import(self, test_client):
        """
        Test exporting configuration after importing.

        Flow:
        1. Import configuration
        2. Export configuration
        3. Verify exported YAML contains imported data
        """
        # Step 1: Import configuration
        yaml_content = """
photo_extensions:
  - .dng
  - .cr3
camera_mappings:
  EXP1:
    name: Export Test Camera
    serial_number: "99999"
processing_methods:
  TEST: Test Method
"""
        import_response = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")}
        )
        assert import_response.status_code == 200
        session_id = import_response.json()["session_id"]

        # Apply import
        apply_response = test_client.post(
            f"/api/config/import/{session_id}/resolve",
            json={"resolutions": []}
        )
        assert apply_response.status_code == 200

        # Step 2: Export configuration
        export_response = test_client.get("/api/config/export")
        assert export_response.status_code == 200

        # Step 3: Verify exported YAML
        import yaml
        exported = yaml.safe_load(export_response.content)

        assert "camera_mappings" in exported
        assert "EXP1" in exported["camera_mappings"]
        assert exported["camera_mappings"]["EXP1"]["name"] == "Export Test Camera"
        assert "processing_methods" in exported
        assert exported["processing_methods"]["TEST"] == "Test Method"


class TestConfigMultipleImports:
    """Integration tests for multiple sequential imports - T153"""

    def test_multiple_sequential_imports(self, test_client):
        """
        Test multiple imports updating different parts of configuration.

        Flow:
        1. Import cameras
        2. Import processing methods
        3. Verify both are in final configuration
        """
        # Step 1: Import cameras
        cameras_yaml = """
camera_mappings:
  CAM1:
    name: Camera One
    serial_number: "1111"
  CAM2:
    name: Camera Two
    serial_number: "2222"
"""
        import1_response = test_client.post(
            "/api/config/import",
            files={"file": ("cameras.yaml", cameras_yaml, "application/x-yaml")}
        )
        assert import1_response.status_code == 200
        session1_id = import1_response.json()["session_id"]

        apply1_response = test_client.post(
            f"/api/config/import/{session1_id}/resolve",
            json={"resolutions": []}
        )
        assert apply1_response.status_code == 200

        # Step 2: Import processing methods
        methods_yaml = """
processing_methods:
  MTH1: Method One
  MTH2: Method Two
"""
        import2_response = test_client.post(
            "/api/config/import",
            files={"file": ("methods.yaml", methods_yaml, "application/x-yaml")}
        )
        assert import2_response.status_code == 200
        session2_id = import2_response.json()["session_id"]

        apply2_response = test_client.post(
            f"/api/config/import/{session2_id}/resolve",
            json={"resolutions": []}
        )
        assert apply2_response.status_code == 200

        # Step 3: Verify final configuration
        config_response = test_client.get("/api/config")
        assert config_response.status_code == 200
        config = config_response.json()

        # Both cameras should be present
        assert "CAM1" in config["cameras"]
        assert "CAM2" in config["cameras"]

        # Both methods should be present
        assert "MTH1" in config["processing_methods"]
        assert "MTH2" in config["processing_methods"]

    def test_import_updates_existing_from_prior_import(self, test_client):
        """
        Test that a second import can update values from prior import.

        Flow:
        1. Import camera with name A
        2. Import same camera with name B
        3. Resolve to use new YAML value
        4. Verify name is B
        """
        # Step 1: First import
        yaml1 = """
camera_mappings:
  UPD1:
    name: Original Name
    serial_number: "1234"
"""
        import1 = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml1, "application/x-yaml")}
        )
        assert import1.status_code == 200
        test_client.post(
            f"/api/config/import/{import1.json()['session_id']}/resolve",
            json={"resolutions": []}
        )

        # Step 2: Second import with different value
        yaml2 = """
camera_mappings:
  UPD1:
    name: Updated Name
    serial_number: "5678"
"""
        import2 = test_client.post(
            "/api/config/import",
            files={"file": ("config.yaml", yaml2, "application/x-yaml")}
        )
        assert import2.status_code == 200
        session2 = import2.json()

        # Should have a conflict
        assert len(session2["conflicts"]) == 1

        # Step 3: Resolve to use YAML value
        apply2 = test_client.post(
            f"/api/config/import/{session2['session_id']}/resolve",
            json={"resolutions": [{"category": "cameras", "key": "UPD1", "use_yaml": True}]}
        )
        assert apply2.status_code == 200

        # Step 4: Verify updated value
        config = test_client.get("/api/config/cameras/UPD1")
        assert config.status_code == 200
        assert config.json()["value"]["name"] == "Updated Name"
        assert config.json()["value"]["serial_number"] == "5678"
