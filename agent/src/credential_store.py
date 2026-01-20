"""
Agent credential store for managing connector credentials locally.

Provides secure storage for connector credentials using Fernet encryption.
The master key is auto-generated on first use and stored locally.

Design:
- Credentials are encrypted using Fernet symmetric encryption
- Each connector's credentials are stored separately
- Master key is generated automatically when first credential is stored
- Credentials can be tested before storage to ensure validity
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from cryptography.fernet import Fernet


class CredentialStore:
    """
    Secure local storage for connector credentials.

    Stores credentials encrypted with a master key that is auto-generated
    on first use. Each connector's credentials are stored in a separate file.

    Directory structure:
        ~/.shuttersense-agent/
            master.key          # Fernet encryption key (auto-generated)
            credentials/
                con_xxx.json    # Encrypted credentials for connector con_xxx
                con_yyy.json    # Encrypted credentials for connector con_yyy

    Usage:
        >>> store = CredentialStore()
        >>> store.store_credentials("con_xxx", {"server": "...", "username": "..."})
        >>> creds = store.get_credentials("con_xxx")
        >>> guids = store.list_connector_guids()
    """

    DEFAULT_BASE_DIR = Path.home() / ".shuttersense-agent"
    MASTER_KEY_FILE = "master.key"
    CREDENTIALS_DIR = "credentials"

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize credential store.

        Args:
            base_dir: Base directory for credential storage (defaults to ~/.shuttersense-agent)
        """
        self.base_dir = base_dir or self.DEFAULT_BASE_DIR
        self.credentials_dir = self.base_dir / self.CREDENTIALS_DIR
        self._fernet: Optional[Fernet] = None

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        # Ensure proper permissions on base directory (owner only)
        os.chmod(self.base_dir, 0o700)
        os.chmod(self.credentials_dir, 0o700)

    @property
    def master_key_path(self) -> Path:
        """Path to master key file."""
        return self.base_dir / self.MASTER_KEY_FILE

    def has_master_key(self) -> bool:
        """Check if master key exists."""
        return self.master_key_path.exists()

    def _generate_master_key(self) -> bytes:
        """
        Generate a new master key.

        Returns:
            New Fernet key as bytes
        """
        return Fernet.generate_key()

    def _load_or_create_master_key(self) -> bytes:
        """
        Load existing master key or create a new one.

        Returns:
            Master key as bytes
        """
        self._ensure_directories()

        if self.master_key_path.exists():
            # Load existing key
            with open(self.master_key_path, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = self._generate_master_key()

            # Save key with restricted permissions
            with open(self.master_key_path, "wb") as f:
                f.write(key)
            os.chmod(self.master_key_path, 0o600)

            return key

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet cipher."""
        if self._fernet is None:
            key = self._load_or_create_master_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _credential_file_path(self, connector_guid: str) -> Path:
        """Get path to credential file for a connector."""
        # Sanitize GUID for filesystem safety
        safe_guid = connector_guid.replace("/", "_").replace("\\", "_")
        return self.credentials_dir / f"{safe_guid}.json"

    def store_credentials(
        self,
        connector_guid: str,
        credentials: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store credentials for a connector.

        Args:
            connector_guid: Connector GUID (con_xxx)
            credentials: Credentials dictionary
            metadata: Optional metadata to store alongside credentials

        Raises:
            ValueError: If connector_guid is invalid
        """
        if not connector_guid or not connector_guid.startswith("con_"):
            raise ValueError(f"Invalid connector GUID: {connector_guid}")

        self._ensure_directories()
        fernet = self._get_fernet()

        # Prepare data to store
        data = {
            "connector_guid": connector_guid,
            "credentials": credentials,
            "metadata": metadata or {},
            "stored_at": datetime.utcnow().isoformat(),
        }

        # Encrypt and store
        json_data = json.dumps(data)
        encrypted = fernet.encrypt(json_data.encode("utf-8"))

        file_path = self._credential_file_path(connector_guid)
        with open(file_path, "wb") as f:
            f.write(encrypted)
        os.chmod(file_path, 0o600)

    def _load_credential_data(self, connector_guid: str) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt the full credential data for a connector.

        Args:
            connector_guid: Connector GUID (con_xxx)

        Returns:
            Full data dictionary or None if not found/corrupted
        """
        file_path = self._credential_file_path(connector_guid)

        if not file_path.exists():
            return None

        fernet = self._get_fernet()

        with open(file_path, "rb") as f:
            encrypted = f.read()

        try:
            decrypted = fernet.decrypt(encrypted)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            # Invalid or corrupted credential file
            return None

    def get_credentials(self, connector_guid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve credentials for a connector.

        Args:
            connector_guid: Connector GUID (con_xxx)

        Returns:
            Credentials dictionary or None if not found
        """
        data = self._load_credential_data(connector_guid)
        return data.get("credentials") if data else None

    def get_metadata(self, connector_guid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a connector's stored credentials.

        Args:
            connector_guid: Connector GUID (con_xxx)

        Returns:
            Metadata dictionary or None if not found
        """
        data = self._load_credential_data(connector_guid)
        return data.get("metadata") if data else None

    def has_credentials(self, connector_guid: str) -> bool:
        """
        Check if credentials exist for a connector.

        Args:
            connector_guid: Connector GUID (con_xxx)

        Returns:
            True if credentials exist
        """
        file_path = self._credential_file_path(connector_guid)
        return file_path.exists()

    def delete_credentials(self, connector_guid: str) -> bool:
        """
        Delete credentials for a connector.

        Args:
            connector_guid: Connector GUID (con_xxx)

        Returns:
            True if credentials were deleted, False if they didn't exist
        """
        file_path = self._credential_file_path(connector_guid)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_connector_guids(self) -> List[str]:
        """
        List all connector GUIDs with stored credentials.

        Returns:
            List of connector GUIDs
        """
        if not self.credentials_dir.exists():
            return []

        guids = []
        for file_path in self.credentials_dir.glob("*.json"):
            # Extract GUID from filename (remove .json extension)
            guid = file_path.stem
            if guid.startswith("con_"):
                guids.append(guid)

        return sorted(guids)

    def get_all_credentials(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all stored credentials.

        Returns:
            Dictionary mapping connector GUID to credentials
        """
        result = {}
        for guid in self.list_connector_guids():
            creds = self.get_credentials(guid)
            if creds:
                result[guid] = creds
        return result

    def initialize_master_key(self) -> bool:
        """
        Explicitly initialize the master key.

        Can be called to set up the credential store before storing any credentials.
        If the master key already exists, this is a no-op.

        Returns:
            True if key was created, False if it already existed
        """
        if self.has_master_key():
            return False

        self._load_or_create_master_key()
        return True
