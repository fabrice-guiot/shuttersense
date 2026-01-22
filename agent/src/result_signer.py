"""
HMAC result signing for job attestation.

Signs job results using HMAC-SHA256 with the job's signing secret
to prove the results came from the agent that claimed the job.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T094, T100
"""

import hashlib
import hmac
import json
from base64 import b64decode


class ResultSigner:
    """
    HMAC-SHA256 signer for job results.

    Signs job results with the signing secret provided during job claim.
    The server verifies the signature before accepting results.

    Attributes:
        signing_secret: Base64-encoded signing secret
    """

    def __init__(self, signing_secret_b64: str):
        """
        Initialize the result signer.

        Args:
            signing_secret_b64: Base64-encoded signing secret from job claim
        """
        self._secret_bytes = b64decode(signing_secret_b64)

    def sign(self, data: dict) -> str:
        """
        Sign data using HMAC-SHA256.

        Args:
            data: Dictionary to sign

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        # Canonical JSON: sorted keys, no whitespace
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))

        # Compute HMAC
        signature = hmac.new(
            self._secret_bytes,
            canonical.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify(self, data: dict, signature: str) -> bool:
        """
        Verify a signature against data.

        Args:
            data: Dictionary that was signed
            signature: Hex-encoded signature to verify

        Returns:
            True if signature is valid
        """
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)
