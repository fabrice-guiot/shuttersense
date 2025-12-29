"""
Credential encryption and decryption utilities.

This module provides the CredentialEncryptor class for securely encrypting
and decrypting remote storage credentials using Fernet symmetric encryption.

Based on research.md Task 2 decision: Use Fernet with environment-based
master key storage for credential encryption.
"""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptor:
    """
    Encrypts and decrypts credentials using Fernet symmetric encryption.

    The master encryption key is loaded from the PHOTO_ADMIN_MASTER_KEY
    environment variable. This key must be generated using setup_master_key.py
    before using this class.

    Usage:
        # Initialize with master key from environment
        encryptor = CredentialEncryptor()

        # Encrypt credentials
        encrypted = encryptor.encrypt('{"access_key": "...", "secret_key": "..."}')

        # Decrypt credentials
        decrypted = encryptor.decrypt(encrypted)

    Tasks implemented:
        - T015: CredentialEncryptor class with environment-based master key
        - T016: encrypt() method using Fernet
        - T017: decrypt() method using Fernet
    """

    ENV_VAR_NAME = "PHOTO_ADMIN_MASTER_KEY"

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the credential encryptor.

        Args:
            master_key: Optional master key. If not provided, loads from
                       PHOTO_ADMIN_MASTER_KEY environment variable.

        Raises:
            ValueError: If master key is not provided and not found in environment
            ValueError: If master key is invalid Fernet key format

        Task: T015 - CredentialEncryptor class initialization
        """
        # Get master key from parameter or environment
        if master_key is None:
            master_key = os.environ.get(self.ENV_VAR_NAME)

        if not master_key:
            raise ValueError(
                f"{self.ENV_VAR_NAME} environment variable not set. "
                f"Run setup_master_key.py to generate and configure the master key."
            )

        try:
            # Initialize Fernet cipher with the master key
            self.cipher = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
        except Exception as e:
            raise ValueError(
                f"Invalid master key format. The key must be a valid Fernet key. "
                f"Run setup_master_key.py to generate a new key. Error: {str(e)}"
            )

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt credentials for database storage.

        This method encrypts credential JSON strings (e.g., S3 access keys,
        GCS service account JSON, SMB passwords) before storing in the database.

        Args:
            plaintext: The plaintext credential string to encrypt

        Returns:
            str: Base64-encoded encrypted credential string

        Raises:
            ValueError: If plaintext is empty
            Exception: If encryption fails

        Example:
            >>> encryptor = CredentialEncryptor()
            >>> credentials = '{"access_key": "AKIA...", "secret_key": "..."}'
            >>> encrypted = encryptor.encrypt(credentials)
            >>> print(encrypted)
            'gAAAAABf...'

        Task: T016 - encrypt() method using Fernet
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty plaintext")

        try:
            # Encrypt the plaintext using Fernet
            # Fernet automatically handles:
            # - AES-128 encryption in CBC mode
            # - HMAC for authentication
            # - Timestamp for key rotation support
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))

            # Return as string (base64-encoded)
            return encrypted_bytes.decode('utf-8')

        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt credentials from database.

        This method decrypts credential strings retrieved from the database
        back to their original plaintext JSON format.

        Args:
            ciphertext: The base64-encoded encrypted credential string

        Returns:
            str: Decrypted plaintext credential string

        Raises:
            ValueError: If ciphertext is empty
            InvalidToken: If decryption fails (wrong key, corrupted data, or tampered)
            Exception: If decryption fails for other reasons

        Example:
            >>> encryptor = CredentialEncryptor()
            >>> encrypted = 'gAAAAABf...'
            >>> credentials = encryptor.decrypt(encrypted)
            >>> print(credentials)
            '{"access_key": "AKIA...", "secret_key": "..."}'

        Security Notes:
            - InvalidToken exception indicates:
                1. Wrong master key (key was rotated or changed)
                2. Corrupted ciphertext (database corruption)
                3. Tampered ciphertext (security breach)
            - NEVER log decrypted credentials

        Task: T017 - decrypt() method using Fernet
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty ciphertext")

        try:
            # Decrypt the ciphertext using Fernet
            # Fernet automatically:
            # - Verifies HMAC (authentication)
            # - Checks timestamp (within TTL if set)
            # - Decrypts with AES-128
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode('utf-8'))

            # Return as string (UTF-8 decoded)
            return decrypted_bytes.decode('utf-8')

        except InvalidToken as e:
            # This exception means:
            # - Wrong master key (most common)
            # - Corrupted or tampered ciphertext
            # - Expired token (if TTL was set, which we don't use)
            raise InvalidToken(
                "Decryption failed: Invalid master key or corrupted/tampered ciphertext. "
                "Verify that PHOTO_ADMIN_MASTER_KEY matches the key used for encryption. "
                "If the key was rotated, use setup_master_key.py --rotate to re-encrypt."
            )
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")

    def encrypt_dict(self, credentials: dict) -> str:
        """
        Convenience method to encrypt a dictionary of credentials.

        Args:
            credentials: Dictionary containing credential key-value pairs

        Returns:
            str: Base64-encoded encrypted credential string

        Example:
            >>> encryptor = CredentialEncryptor()
            >>> creds = {"access_key": "AKIA...", "secret_key": "..."}
            >>> encrypted = encryptor.encrypt_dict(creds)
        """
        import json
        json_str = json.dumps(credentials)
        return self.encrypt(json_str)

    def decrypt_dict(self, ciphertext: str) -> dict:
        """
        Convenience method to decrypt credentials into a dictionary.

        Args:
            ciphertext: Base64-encoded encrypted credential string

        Returns:
            dict: Decrypted credentials as dictionary

        Example:
            >>> encryptor = CredentialEncryptor()
            >>> encrypted = 'gAAAAABf...'
            >>> creds = encryptor.decrypt_dict(encrypted)
            >>> print(creds['access_key'])
            'AKIA...'
        """
        import json
        plaintext = self.decrypt(ciphertext)
        return json.loads(plaintext)


# Singleton instance for dependency injection in FastAPI
# This will be initialized when the application starts
_encryptor_instance: Optional[CredentialEncryptor] = None


def get_credential_encryptor() -> CredentialEncryptor:
    """
    Get or create the singleton CredentialEncryptor instance.

    This function is used as a FastAPI dependency for routes that need
    to encrypt/decrypt credentials.

    Returns:
        CredentialEncryptor: Singleton instance

    Raises:
        ValueError: If master key is not configured

    Usage in FastAPI:
        from fastapi import Depends
        from backend.src.utils.crypto import get_credential_encryptor

        @app.post("/connectors")
        async def create_connector(
            encryptor: CredentialEncryptor = Depends(get_credential_encryptor)
        ):
            encrypted = encryptor.encrypt(credentials)
            # ...
    """
    global _encryptor_instance

    if _encryptor_instance is None:
        _encryptor_instance = CredentialEncryptor()

    return _encryptor_instance


def init_credential_encryptor(master_key: Optional[str] = None):
    """
    Initialize the credential encryptor singleton.

    This should be called during application startup to validate that
    the master key is configured correctly.

    Args:
        master_key: Optional master key override (for testing)

    Raises:
        ValueError: If master key is not configured or invalid
    """
    global _encryptor_instance
    _encryptor_instance = CredentialEncryptor(master_key)
