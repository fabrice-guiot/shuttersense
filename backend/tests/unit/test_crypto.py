"""
Unit tests for credential encryption and decryption utilities.

Tests the CredentialEncryptor class for:
- Initialization with master key from environment or parameter
- Encrypt/decrypt roundtrip validation
- Error handling for invalid keys and empty data
- Dictionary convenience methods
- UTF-8 character support

Task: T104a - Unit tests for crypto module
"""

import os
import pytest
from cryptography.fernet import Fernet, InvalidToken

from backend.src.utils.crypto import (
    CredentialEncryptor,
    get_credential_encryptor,
    init_credential_encryptor
)


class TestCredentialEncryptorInitialization:
    """Tests for CredentialEncryptor initialization."""

    def test_init_with_explicit_key(self):
        """Test initialization with explicit master key parameter."""
        master_key = Fernet.generate_key().decode('utf-8')
        encryptor = CredentialEncryptor(master_key=master_key)

        assert encryptor.cipher is not None
        # Verify it works by encrypting/decrypting
        encrypted = encryptor.encrypt("test")
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == "test"

    def test_init_from_environment(self):
        """Test initialization with master key from environment variable."""
        # The test environment already has PHOTO_ADMIN_MASTER_KEY set
        encryptor = CredentialEncryptor()

        assert encryptor.cipher is not None
        # Verify it works
        encrypted = encryptor.encrypt("test")
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == "test"

    def test_init_missing_master_key(self, monkeypatch):
        """Test initialization fails when master key is not available."""
        # Remove the environment variable
        monkeypatch.delenv('PHOTO_ADMIN_MASTER_KEY', raising=False)

        with pytest.raises(ValueError) as exc_info:
            CredentialEncryptor()

        assert "PHOTO_ADMIN_MASTER_KEY environment variable not set" in str(exc_info.value)
        assert "setup_master_key.py" in str(exc_info.value)

    def test_init_invalid_master_key_format(self):
        """Test initialization fails with invalid Fernet key format."""
        invalid_key = "not-a-valid-fernet-key"

        with pytest.raises(ValueError) as exc_info:
            CredentialEncryptor(master_key=invalid_key)

        assert "Invalid master key format" in str(exc_info.value)
        assert "valid Fernet key" in str(exc_info.value)


class TestEncryption:
    """Tests for credential encryption."""

    def test_encrypt_valid_plaintext(self, test_encryptor):
        """Test encrypting valid plaintext credentials."""
        plaintext = '{"access_key": "AKIAIOSFODNN7EXAMPLE", "secret_key": "wJalrXUtnFEMI"}'

        encrypted = test_encryptor.encrypt(plaintext)

        # Should return a non-empty string
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

        # Encrypted text should be different from plaintext
        assert encrypted != plaintext

        # Should be base64-encoded Fernet token (starts with 'gAAAAA')
        assert encrypted.startswith('gAAAAA')

    def test_encrypt_empty_plaintext(self, test_encryptor):
        """Test encrypting empty plaintext raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            test_encryptor.encrypt("")

        assert "Cannot encrypt empty plaintext" in str(exc_info.value)

    def test_encrypt_utf8_characters(self, test_encryptor):
        """Test encrypting plaintext with UTF-8 special characters."""
        plaintext = '{"password": "pàsswörd123™", "user": "José"}'

        encrypted = test_encryptor.encrypt(plaintext)

        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_encrypt_consistent_format(self, test_encryptor):
        """Test that encryption produces consistent base64 format."""
        plaintext = "test credentials"

        # Encrypt multiple times
        encrypted1 = test_encryptor.encrypt(plaintext)
        encrypted2 = test_encryptor.encrypt(plaintext)

        # Each encryption should produce unique ciphertext (due to IV)
        assert encrypted1 != encrypted2

        # But both should be valid base64 Fernet tokens
        assert encrypted1.startswith('gAAAAA')
        assert encrypted2.startswith('gAAAAA')


class TestDecryption:
    """Tests for credential decryption."""

    def test_decrypt_valid_ciphertext(self, test_encryptor):
        """Test decrypting valid ciphertext."""
        plaintext = '{"access_key": "AKIAIOSFODNN7EXAMPLE"}'
        encrypted = test_encryptor.encrypt(plaintext)

        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_decrypt_empty_ciphertext(self, test_encryptor):
        """Test decrypting empty ciphertext raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            test_encryptor.decrypt("")

        assert "Cannot decrypt empty ciphertext" in str(exc_info.value)

    def test_decrypt_invalid_ciphertext(self, test_encryptor):
        """Test decrypting invalid/corrupted ciphertext raises InvalidToken."""
        invalid_ciphertext = "not-a-valid-encrypted-string"

        with pytest.raises(InvalidToken) as exc_info:
            test_encryptor.decrypt(invalid_ciphertext)

        assert "Invalid master key or corrupted/tampered ciphertext" in str(exc_info.value)
        assert "PHOTO_ADMIN_MASTER_KEY" in str(exc_info.value)

    def test_decrypt_with_wrong_key(self, test_encryptor):
        """Test decrypting with a different master key raises InvalidToken."""
        plaintext = '{"access_key": "AKIAIOSFODNN7EXAMPLE"}'
        encrypted = test_encryptor.encrypt(plaintext)

        # Create a different encryptor with a different key
        different_key = Fernet.generate_key().decode('utf-8')
        different_encryptor = CredentialEncryptor(master_key=different_key)

        with pytest.raises(InvalidToken) as exc_info:
            different_encryptor.decrypt(encrypted)

        assert "Invalid master key or corrupted/tampered ciphertext" in str(exc_info.value)

    def test_decrypt_utf8_characters(self, test_encryptor):
        """Test decrypting ciphertext with UTF-8 special characters."""
        plaintext = '{"password": "pàsswörd123™", "user": "José"}'
        encrypted = test_encryptor.encrypt(plaintext)

        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == plaintext


class TestEncryptDecryptRoundtrip:
    """Tests for encrypt/decrypt roundtrip validation."""

    def test_roundtrip_simple_credentials(self, test_encryptor):
        """Test encrypt/decrypt roundtrip with simple credentials."""
        original = '{"username": "admin", "password": "secret123"}'

        encrypted = test_encryptor.encrypt(original)
        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == original

    def test_roundtrip_s3_credentials(self, test_encryptor):
        """Test encrypt/decrypt roundtrip with S3 credentials."""
        original = '{"aws_access_key_id": "AKIAIOSFODNN7EXAMPLE", "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "region": "us-east-1"}'

        encrypted = test_encryptor.encrypt(original)
        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == original

    def test_roundtrip_gcs_service_account(self, test_encryptor):
        """Test encrypt/decrypt roundtrip with GCS service account JSON."""
        original = '{"type": "service_account", "project_id": "my-project", "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQ...\\n-----END PRIVATE KEY-----\\n"}'

        encrypted = test_encryptor.encrypt(original)
        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == original

    def test_roundtrip_smb_credentials(self, test_encryptor):
        """Test encrypt/decrypt roundtrip with SMB credentials."""
        original = '{"username": "domain\\\\user", "password": "P@ssw0rd!", "domain": "WORKGROUP"}'

        encrypted = test_encryptor.encrypt(original)
        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == original

    def test_roundtrip_long_credentials(self, test_encryptor):
        """Test encrypt/decrypt roundtrip with very long credentials."""
        # Simulate a large GCS service account JSON
        original = '{"key": "' + 'x' * 10000 + '"}'

        encrypted = test_encryptor.encrypt(original)
        decrypted = test_encryptor.decrypt(encrypted)

        assert decrypted == original


class TestDictionaryConvenienceMethods:
    """Tests for encrypt_dict and decrypt_dict convenience methods."""

    def test_encrypt_dict_valid_credentials(self, test_encryptor):
        """Test encrypting a dictionary of credentials."""
        credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'region': 'us-east-1'
        }

        encrypted = test_encryptor.encrypt_dict(credentials)

        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        assert encrypted.startswith('gAAAAA')

    def test_decrypt_dict_valid_ciphertext(self, test_encryptor):
        """Test decrypting ciphertext into a dictionary."""
        credentials = {
            'username': 'admin',
            'password': 'secret123'
        }
        encrypted = test_encryptor.encrypt_dict(credentials)

        decrypted = test_encryptor.decrypt_dict(encrypted)

        assert isinstance(decrypted, dict)
        assert decrypted == credentials

    def test_dict_roundtrip_complex_credentials(self, test_encryptor):
        """Test encrypt_dict/decrypt_dict roundtrip with nested structures."""
        credentials = {
            'type': 's3',
            'config': {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'aws_secret_access_key': 'wJalrXUtnFEMI',
                'region': 'us-east-1'
            },
            'metadata': {
                'created_at': '2025-01-01T00:00:00Z',
                'owner': 'test-user'
            }
        }

        encrypted = test_encryptor.encrypt_dict(credentials)
        decrypted = test_encryptor.decrypt_dict(encrypted)

        assert decrypted == credentials

    def test_dict_roundtrip_with_special_types(self, test_encryptor):
        """Test encrypt_dict/decrypt_dict with various data types."""
        credentials = {
            'string': 'value',
            'number': 123,
            'float': 45.67,
            'boolean': True,
            'null': None,
            'array': [1, 2, 3],
            'nested': {'key': 'value'}
        }

        encrypted = test_encryptor.encrypt_dict(credentials)
        decrypted = test_encryptor.decrypt_dict(encrypted)

        assert decrypted == credentials


class TestSingletonPattern:
    """Tests for singleton credential encryptor instance."""

    def test_get_credential_encryptor_returns_instance(self):
        """Test get_credential_encryptor returns a CredentialEncryptor."""
        encryptor = get_credential_encryptor()

        assert isinstance(encryptor, CredentialEncryptor)
        assert encryptor.cipher is not None

    def test_get_credential_encryptor_returns_same_instance(self):
        """Test get_credential_encryptor returns the same singleton instance."""
        encryptor1 = get_credential_encryptor()
        encryptor2 = get_credential_encryptor()

        assert encryptor1 is encryptor2

    def test_init_credential_encryptor_with_custom_key(self):
        """Test init_credential_encryptor sets up singleton with custom key."""
        custom_key = Fernet.generate_key().decode('utf-8')

        init_credential_encryptor(master_key=custom_key)
        encryptor = get_credential_encryptor()

        assert isinstance(encryptor, CredentialEncryptor)

        # Verify it works with the custom key
        encrypted = encryptor.encrypt("test")
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == "test"

    def test_init_credential_encryptor_from_environment(self):
        """Test init_credential_encryptor uses environment variable."""
        # Reset singleton
        import backend.src.utils.crypto as crypto_module
        crypto_module._encryptor_instance = None

        init_credential_encryptor()
        encryptor = get_credential_encryptor()

        assert isinstance(encryptor, CredentialEncryptor)


class TestErrorMessages:
    """Tests for error message clarity and helpfulness."""

    def test_missing_env_var_error_message(self, monkeypatch):
        """Test error message for missing environment variable is helpful."""
        monkeypatch.delenv('PHOTO_ADMIN_MASTER_KEY', raising=False)

        with pytest.raises(ValueError) as exc_info:
            CredentialEncryptor()

        error_msg = str(exc_info.value)
        assert "PHOTO_ADMIN_MASTER_KEY" in error_msg
        assert "environment variable not set" in error_msg
        assert "setup_master_key.py" in error_msg

    def test_invalid_key_error_message(self):
        """Test error message for invalid master key is helpful."""
        with pytest.raises(ValueError) as exc_info:
            CredentialEncryptor(master_key="invalid-key")

        error_msg = str(exc_info.value)
        assert "Invalid master key format" in error_msg
        assert "valid Fernet key" in error_msg
        assert "setup_master_key.py" in error_msg

    def test_decrypt_invalid_token_error_message(self, test_encryptor):
        """Test error message for decryption failure is helpful."""
        with pytest.raises(InvalidToken) as exc_info:
            test_encryptor.decrypt("invalid-ciphertext")

        error_msg = str(exc_info.value)
        assert "Invalid master key or corrupted/tampered ciphertext" in error_msg
        assert "PHOTO_ADMIN_MASTER_KEY" in error_msg
        assert "setup_master_key.py --rotate" in error_msg
