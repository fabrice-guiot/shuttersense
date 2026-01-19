"""
Unit tests for ResultSigner.

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T094
"""

import pytest
import secrets
from base64 import b64encode

from src.result_signer import ResultSigner


class TestResultSigner:
    """Tests for result signing functionality."""

    def test_sign_produces_hex_signature(self):
        """Signing produces a hex-encoded HMAC-SHA256 signature."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data = {"total_files": 100, "issues_found": 5}
        signature = signer.sign(data)

        # SHA-256 produces 32 bytes = 64 hex characters
        assert len(signature) == 64
        assert all(c in '0123456789abcdef' for c in signature)

    def test_sign_is_deterministic(self):
        """Same data and secret produces same signature."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data = {"total_files": 100, "issues_found": 5}

        sig1 = signer.sign(data)
        sig2 = signer.sign(data)

        assert sig1 == sig2

    def test_sign_different_data_different_signature(self):
        """Different data produces different signatures."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data1 = {"total_files": 100}
        data2 = {"total_files": 101}

        sig1 = signer.sign(data1)
        sig2 = signer.sign(data2)

        assert sig1 != sig2

    def test_sign_different_secret_different_signature(self):
        """Different secrets produce different signatures."""
        secret1 = b64encode(secrets.token_bytes(32)).decode('utf-8')
        secret2 = b64encode(secrets.token_bytes(32)).decode('utf-8')

        signer1 = ResultSigner(secret1)
        signer2 = ResultSigner(secret2)

        data = {"total_files": 100}

        sig1 = signer1.sign(data)
        sig2 = signer2.sign(data)

        assert sig1 != sig2

    def test_sign_key_ordering_independent(self):
        """Signature is independent of key ordering in input."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        # These should produce the same signature because keys are sorted
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}

        sig1 = signer.sign(data1)
        sig2 = signer.sign(data2)

        assert sig1 == sig2

    def test_verify_valid_signature(self):
        """Verification succeeds for valid signature."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data = {"total_files": 100}
        signature = signer.sign(data)

        assert signer.verify(data, signature) is True

    def test_verify_invalid_signature(self):
        """Verification fails for invalid signature."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data = {"total_files": 100}
        invalid_signature = "0" * 64

        assert signer.verify(data, invalid_signature) is False

    def test_verify_tampered_data(self):
        """Verification fails for tampered data."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        original_data = {"total_files": 100}
        signature = signer.sign(original_data)

        tampered_data = {"total_files": 101}

        assert signer.verify(tampered_data, signature) is False

    def test_sign_nested_data(self):
        """Signing works with nested data structures."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data = {
            "results": {
                "total_files": 100,
                "categories": ["photo", "video"],
                "nested": {"a": 1, "b": 2}
            },
            "metadata": {"version": "1.0"}
        }

        signature = signer.sign(data)
        assert signer.verify(data, signature) is True

    def test_sign_empty_dict(self):
        """Signing works with empty dictionary."""
        secret = b64encode(secrets.token_bytes(32)).decode('utf-8')
        signer = ResultSigner(secret)

        data = {}
        signature = signer.sign(data)

        assert len(signature) == 64
        assert signer.verify(data, signature) is True
