"""
Unit tests for the agent credential store.

Tests the CredentialStore class which manages encrypted storage
for connector credentials.

Issue #90 - Distributed Agent Architecture (Phase 8)
"""

import sys

import pytest
from pathlib import Path

from src.credential_store import CredentialStore


class TestCredentialStore:
    """Tests for CredentialStore class."""

    def test_init_default_base_dir(self):
        """Test default base directory is user home."""
        store = CredentialStore()
        assert store.base_dir == Path.home() / ".shuttersense-agent"

    def test_init_custom_base_dir(self, tmp_path):
        """Test custom base directory."""
        store = CredentialStore(base_dir=tmp_path / "custom")
        assert store.base_dir == tmp_path / "custom"

    def test_master_key_path(self, tmp_path):
        """Test master key path property."""
        store = CredentialStore(base_dir=tmp_path)
        assert store.master_key_path == tmp_path / "master.key"

    def test_has_master_key_false_when_not_exists(self, tmp_path):
        """Test has_master_key returns False when key doesn't exist."""
        store = CredentialStore(base_dir=tmp_path)
        assert not store.has_master_key()

    def test_has_master_key_true_when_exists(self, tmp_path):
        """Test has_master_key returns True when key exists."""
        store = CredentialStore(base_dir=tmp_path)
        # Create the directory and master key file
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "master.key").write_bytes(b"test_key")
        assert store.has_master_key()

    def test_initialize_master_key_creates_key(self, tmp_path):
        """Test initialize_master_key creates a new key."""
        store = CredentialStore(base_dir=tmp_path)
        result = store.initialize_master_key()

        assert result is True
        assert store.has_master_key()
        assert store.master_key_path.exists()
        # Key should be a valid Fernet key (44 bytes base64 encoded)
        key_data = store.master_key_path.read_bytes()
        assert len(key_data) == 44

    def test_initialize_master_key_noop_when_exists(self, tmp_path):
        """Test initialize_master_key is no-op when key exists."""
        store = CredentialStore(base_dir=tmp_path)

        # First initialization
        store.initialize_master_key()
        original_key = store.master_key_path.read_bytes()

        # Second initialization should be no-op
        result = store.initialize_master_key()
        assert result is False
        assert store.master_key_path.read_bytes() == original_key

    def test_store_credentials_valid_guid(self, tmp_path):
        """Test storing credentials for valid connector GUID."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"server": "example.com", "username": "user"},
            metadata={"connector_name": "Test Connector"}
        )

        # Credential file should exist
        cred_file = tmp_path / "credentials" / "con_01abc123xyz.json"
        assert cred_file.exists()

    def test_store_credentials_invalid_guid(self, tmp_path):
        """Test storing credentials rejects invalid GUID."""
        store = CredentialStore(base_dir=tmp_path)

        with pytest.raises(ValueError, match="Invalid connector GUID"):
            store.store_credentials(
                connector_guid="invalid_guid",
                credentials={"server": "example.com"}
            )

    def test_store_credentials_empty_guid(self, tmp_path):
        """Test storing credentials rejects empty GUID."""
        store = CredentialStore(base_dir=tmp_path)

        with pytest.raises(ValueError, match="Invalid connector GUID"):
            store.store_credentials(
                connector_guid="",
                credentials={"server": "example.com"}
            )

    def test_get_credentials_returns_stored(self, tmp_path):
        """Test retrieving stored credentials."""
        store = CredentialStore(base_dir=tmp_path)

        original_creds = {"server": "example.com", "username": "user", "password": "secret"}
        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials=original_creds
        )

        retrieved = store.get_credentials("con_01abc123xyz")
        assert retrieved == original_creds

    def test_get_credentials_not_found(self, tmp_path):
        """Test retrieving non-existent credentials returns None."""
        store = CredentialStore(base_dir=tmp_path)

        result = store.get_credentials("con_nonexistent")
        assert result is None

    def test_has_credentials_true_when_stored(self, tmp_path):
        """Test has_credentials returns True when credentials exist."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"server": "example.com"}
        )

        assert store.has_credentials("con_01abc123xyz") is True

    def test_has_credentials_false_when_not_stored(self, tmp_path):
        """Test has_credentials returns False when credentials don't exist."""
        store = CredentialStore(base_dir=tmp_path)

        assert store.has_credentials("con_nonexistent") is False

    def test_delete_credentials_removes_file(self, tmp_path):
        """Test deleting credentials removes the file."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"server": "example.com"}
        )
        assert store.has_credentials("con_01abc123xyz") is True

        result = store.delete_credentials("con_01abc123xyz")

        assert result is True
        assert store.has_credentials("con_01abc123xyz") is False

    def test_delete_credentials_not_found(self, tmp_path):
        """Test deleting non-existent credentials returns False."""
        store = CredentialStore(base_dir=tmp_path)

        result = store.delete_credentials("con_nonexistent")
        assert result is False

    def test_list_connector_guids_empty(self, tmp_path):
        """Test listing GUIDs when no credentials stored."""
        store = CredentialStore(base_dir=tmp_path)

        result = store.list_connector_guids()
        assert result == []

    def test_list_connector_guids_returns_all(self, tmp_path):
        """Test listing all stored connector GUIDs."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials("con_aaa", credentials={"a": 1})
        store.store_credentials("con_bbb", credentials={"b": 2})
        store.store_credentials("con_ccc", credentials={"c": 3})

        result = store.list_connector_guids()

        assert len(result) == 3
        assert "con_aaa" in result
        assert "con_bbb" in result
        assert "con_ccc" in result

    def test_list_connector_guids_sorted(self, tmp_path):
        """Test listed GUIDs are sorted."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials("con_zzz", credentials={"z": 1})
        store.store_credentials("con_aaa", credentials={"a": 2})
        store.store_credentials("con_mmm", credentials={"m": 3})

        result = store.list_connector_guids()

        assert result == ["con_aaa", "con_mmm", "con_zzz"]

    def test_get_all_credentials(self, tmp_path):
        """Test getting all credentials."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials("con_aaa", credentials={"server": "a.com"})
        store.store_credentials("con_bbb", credentials={"server": "b.com"})

        result = store.get_all_credentials()

        assert len(result) == 2
        assert result["con_aaa"] == {"server": "a.com"}
        assert result["con_bbb"] == {"server": "b.com"}

    def test_credentials_are_encrypted(self, tmp_path):
        """Test that stored credentials are actually encrypted."""
        store = CredentialStore(base_dir=tmp_path)

        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"password": "super_secret_password"}
        )

        # Read raw file contents
        cred_file = tmp_path / "credentials" / "con_01abc123xyz.json"
        raw_content = cred_file.read_bytes()

        # Raw content should not contain the plaintext password
        assert b"super_secret_password" not in raw_content

    def test_credentials_persist_across_instances(self, tmp_path):
        """Test credentials persist when creating new store instance."""
        # First instance stores credentials
        store1 = CredentialStore(base_dir=tmp_path)
        store1.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"server": "example.com", "key": "value"}
        )

        # Second instance should be able to retrieve them
        store2 = CredentialStore(base_dir=tmp_path)
        creds = store2.get_credentials("con_01abc123xyz")

        assert creds == {"server": "example.com", "key": "value"}

    def test_update_existing_credentials(self, tmp_path):
        """Test updating existing credentials replaces them."""
        store = CredentialStore(base_dir=tmp_path)

        # Store initial credentials
        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"username": "old_user", "password": "old_pass"}
        )

        # Update with new credentials
        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"username": "new_user", "password": "new_pass"}
        )

        # Should get updated credentials
        creds = store.get_credentials("con_01abc123xyz")
        assert creds == {"username": "new_user", "password": "new_pass"}

    def test_sanitizes_guid_with_slashes(self, tmp_path):
        """Test that GUIDs with slashes are sanitized."""
        store = CredentialStore(base_dir=tmp_path)

        # This shouldn't happen in practice, but test the safety measure
        store.store_credentials(
            connector_guid="con_test/path",
            credentials={"key": "value"}
        )

        # File should be created with sanitized name
        cred_file = tmp_path / "credentials" / "con_test_path.json"
        assert cred_file.exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix file permissions not applicable on Windows")
    def test_directory_permissions(self, tmp_path):
        """Test that directories are created with restricted permissions."""
        store = CredentialStore(base_dir=tmp_path / "secure")
        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"key": "value"}
        )

        import stat
        base_mode = stat.S_IMODE((tmp_path / "secure").stat().st_mode)
        creds_mode = stat.S_IMODE((tmp_path / "secure" / "credentials").stat().st_mode)

        # Should be owner-only (0o700)
        assert base_mode == 0o700
        assert creds_mode == 0o700

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix file permissions not applicable on Windows")
    def test_file_permissions(self, tmp_path):
        """Test that credential files are created with restricted permissions."""
        store = CredentialStore(base_dir=tmp_path)
        store.store_credentials(
            connector_guid="con_01abc123xyz",
            credentials={"key": "value"}
        )

        import stat
        cred_file = tmp_path / "credentials" / "con_01abc123xyz.json"
        file_mode = stat.S_IMODE(cred_file.stat().st_mode)

        # Should be owner read/write only (0o600)
        assert file_mode == 0o600
