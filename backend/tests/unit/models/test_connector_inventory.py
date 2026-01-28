"""
Unit tests for Connector model inventory extensions.

Tests inventory configuration fields and properties.

Issue #107: Cloud Storage Bucket Inventory Import
"""

import pytest

from backend.src.models.connector import Connector, ConnectorType, CredentialLocation


class TestConnectorInventoryFields:
    """Tests for inventory-related fields on Connector model."""

    def test_inventory_config_default_none(self):
        """Test that inventory_config defaults to None."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.inventory_config is None

    def test_inventory_config_can_be_set(self):
        """Test that inventory_config can be set to a dict."""
        config = {
            "provider": "s3",
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photo-bucket",
            "config_name": "daily-inventory",
            "format": "CSV"
        }
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_config=config
        )
        assert connector.inventory_config == config
        assert connector.inventory_config["provider"] == "s3"

    def test_inventory_validation_status_default_none(self):
        """Test that inventory_validation_status defaults to None."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.inventory_validation_status is None

    def test_inventory_validation_status_can_be_set(self):
        """Test that inventory_validation_status can be set."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_validation_status="validated"
        )
        assert connector.inventory_validation_status == "validated"

    def test_inventory_validation_error_default_none(self):
        """Test that inventory_validation_error defaults to None."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.inventory_validation_error is None

    def test_inventory_validation_error_can_be_set(self):
        """Test that inventory_validation_error can be set."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_validation_error="Cannot access inventory bucket"
        )
        assert connector.inventory_validation_error == "Cannot access inventory bucket"

    def test_inventory_schedule_default_manual(self):
        """Test that inventory_schedule defaults to manual."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER
        )
        # Default is "manual" (set via Column default)
        assert connector.inventory_schedule in [None, "manual"]

    def test_inventory_schedule_can_be_set(self):
        """Test that inventory_schedule can be set."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_schedule="weekly"
        )
        assert connector.inventory_schedule == "weekly"

    def test_inventory_last_import_at_default_none(self):
        """Test that inventory_last_import_at defaults to None."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.inventory_last_import_at is None


class TestConnectorHasInventoryConfig:
    """Tests for has_inventory_config property."""

    def test_has_inventory_config_true(self):
        """Test has_inventory_config returns True when config is set."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_config={"provider": "s3", "destination_bucket": "test"}
        )
        assert connector.has_inventory_config is True

    def test_has_inventory_config_false(self):
        """Test has_inventory_config returns False when config is None."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_config=None
        )
        assert connector.has_inventory_config is False


class TestConnectorIsInventoryValidated:
    """Tests for is_inventory_validated property."""

    def test_is_inventory_validated_true(self):
        """Test is_inventory_validated returns True when status is validated."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_validation_status="validated"
        )
        assert connector.is_inventory_validated is True

    def test_is_inventory_validated_false_pending(self):
        """Test is_inventory_validated returns False when status is pending."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_validation_status="pending"
        )
        assert connector.is_inventory_validated is False

    def test_is_inventory_validated_false_failed(self):
        """Test is_inventory_validated returns False when status is failed."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_validation_status="failed"
        )
        assert connector.is_inventory_validated is False

    def test_is_inventory_validated_false_none(self):
        """Test is_inventory_validated returns False when status is None."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            inventory_validation_status=None
        )
        assert connector.is_inventory_validated is False


class TestConnectorSupportsInventory:
    """Tests for supports_inventory property."""

    def test_supports_inventory_s3(self):
        """Test supports_inventory returns True for S3 connectors."""
        connector = Connector(
            name="Test S3",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.supports_inventory is True

    def test_supports_inventory_gcs(self):
        """Test supports_inventory returns True for GCS connectors."""
        connector = Connector(
            name="Test GCS",
            type=ConnectorType.GCS,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.supports_inventory is True

    def test_supports_inventory_smb(self):
        """Test supports_inventory returns False for SMB connectors."""
        connector = Connector(
            name="Test SMB",
            type=ConnectorType.SMB,
            credential_location=CredentialLocation.SERVER
        )
        assert connector.supports_inventory is False
