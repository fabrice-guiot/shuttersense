"""
GUID service for entity identification.

Provides utilities for generating, encoding, decoding, and validating
Global Unique Identifiers used in URLs and API responses.

GUID Format: {prefix}_{base32_uuid}
- prefix: 3-character entity type identifier (col, con, pip, res)
- base32_uuid: 26-character Crockford Base32 encoded UUIDv7
"""

import re
import uuid

import base32_crockford
from uuid_extensions import uuid7

# Prefix mappings for entity types
# Database entities (persisted):
#   col - Collection
#   con - Connector
#   pip - Pipeline
#   res - AnalysisResult
#   evt - Event (calendar event)
#   ser - EventSeries (multi-day event grouping)
#   loc - Location (known locations)
#   org - Organizer (event organizers)
#   prf - Performer (event performers)
#   cat - Category (event categories)
# In-memory entities (transient):
#   job - Tool execution job
#   imp - Config import session
ENTITY_PREFIXES = {
    "col": "Collection",
    "con": "Connector",
    "pip": "Pipeline",
    "res": "AnalysisResult",
    "evt": "Event",
    "ser": "EventSeries",
    "loc": "Location",
    "org": "Organizer",
    "prf": "Performer",
    "cat": "Category",
    "job": "Job",
    "imp": "ImportSession",
}

# Crockford Base32 alphabet (excludes I, L, O, U to avoid confusion)
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Pattern for validating GUIDs
# Format: {3-char prefix}_{26-char Crockford Base32}
GUID_PATTERN = re.compile(
    r"^(col|con|pip|res|evt|ser|loc|org|prf|cat|job|imp)_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$",
    re.IGNORECASE
)


class GuidService:
    """
    Service for GUID operations.

    Provides static methods for:
    - Generating new UUIDv7 values
    - Encoding UUIDs to GUID strings
    - Decoding GUID strings to UUIDs
    - Validating GUID format
    - Parsing identifiers (distinguishing GUID vs numeric IDs)
    """

    @staticmethod
    def generate_uuid() -> uuid.UUID:
        """
        Generate a new UUIDv7 value.

        UUIDv7 is time-ordered for better database indexing performance.

        Returns:
            New UUID object
        """
        return uuid7()

    @staticmethod
    def encode_uuid(uuid_value: uuid.UUID, prefix: str) -> str:
        """
        Encode a UUID to a GUID string.

        Args:
            uuid_value: UUID to encode
            prefix: Entity type prefix (col, con, pip, res)

        Returns:
            GUID string (e.g., "col_01HGW2BBG...")

        Raises:
            ValueError: If prefix is invalid
        """
        if prefix not in ENTITY_PREFIXES:
            raise ValueError(
                f"Invalid prefix '{prefix}'. "
                f"Valid prefixes: {', '.join(ENTITY_PREFIXES.keys())}"
            )

        # Convert UUID to integer and encode as Crockford Base32
        if isinstance(uuid_value, bytes):
            uuid_int = int.from_bytes(uuid_value, "big")
        else:
            uuid_int = int.from_bytes(uuid_value.bytes, "big")

        encoded = base32_crockford.encode(uuid_int)
        # Pad to 26 characters
        encoded = encoded.zfill(26)
        return f"{prefix}_{encoded.lower()}"

    @staticmethod
    def generate_guid(prefix: str) -> str:
        """
        Generate a new GUID with the specified prefix.

        Convenience method that combines generate_uuid() and encode_uuid().

        Args:
            prefix: Entity type prefix (col, con, pip, res, job, imp)

        Returns:
            New GUID string (e.g., "job_01hgw2bbg...")

        Raises:
            ValueError: If prefix is invalid

        Example:
            >>> job_id = GuidService.generate_guid("job")
            >>> session_id = GuidService.generate_guid("imp")
        """
        return GuidService.encode_uuid(GuidService.generate_uuid(), prefix)

    @staticmethod
    def decode_guid(guid: str) -> tuple[str, uuid.UUID]:
        """
        Decode a GUID string to its components.

        Args:
            guid: GUID string (e.g., "col_01HGW2BBG...")

        Returns:
            Tuple of (prefix, UUID)

        Raises:
            ValueError: If the GUID format is invalid
        """
        if not guid:
            raise ValueError("GUID cannot be empty")

        if not GUID_PATTERN.match(guid):
            raise ValueError(
                f"Invalid GUID format: {guid}. "
                f"Expected format: {{prefix}}_{{26-char base32}}"
            )

        prefix = guid[:3].lower()
        encoded_part = guid[4:]  # Skip "xxx_"

        try:
            uuid_int = base32_crockford.decode(encoded_part.upper())
            uuid_bytes = uuid_int.to_bytes(16, "big")
            return prefix, uuid.UUID(bytes=uuid_bytes)
        except (ValueError, OverflowError) as e:
            raise ValueError(f"Invalid GUID encoding: {e}")

    @staticmethod
    def validate_guid(guid: str, expected_prefix: str = None) -> bool:
        """
        Validate a GUID format.

        Args:
            guid: GUID string to validate
            expected_prefix: Optional expected prefix for type checking

        Returns:
            True if valid, False otherwise
        """
        if not guid:
            return False

        if not GUID_PATTERN.match(guid):
            return False

        if expected_prefix:
            prefix = guid[:3].lower()
            return prefix == expected_prefix.lower()

        return True

    @staticmethod
    def get_entity_type(guid: str) -> str | None:
        """
        Get the entity type name from a GUID.

        Args:
            guid: GUID string

        Returns:
            Entity type name (Collection, Connector, etc.) or None if invalid
        """
        if not guid or len(guid) < 3:
            return None

        prefix = guid[:3].lower()
        return ENTITY_PREFIXES.get(prefix)

    @staticmethod
    def is_numeric_id(identifier: str) -> bool:
        """
        Check if an identifier is a numeric ID.

        Args:
            identifier: ID string to check

        Returns:
            True if the identifier is numeric (integer)
        """
        if not identifier:
            return False
        return identifier.isdigit()

    @staticmethod
    def is_guid(identifier: str) -> bool:
        """
        Check if an identifier is a GUID.

        Args:
            identifier: ID string to check

        Returns:
            True if the identifier matches GUID format
        """
        return GuidService.validate_guid(identifier)

    @staticmethod
    def parse_identifier(identifier: str, expected_prefix: str = None) -> uuid.UUID:
        """
        Parse a GUID identifier and return the UUID.

        Only accepts GUID format identifiers (numeric IDs are no longer supported).

        Args:
            identifier: GUID string (e.g., "col_01HGW2BBG...")
            expected_prefix: Expected prefix for validation (col, con, pip, res)

        Returns:
            UUID object extracted from the GUID

        Raises:
            ValueError: If the identifier format is invalid or prefix doesn't match
        """
        if not identifier:
            raise ValueError("Identifier cannot be empty")

        # Check if GUID
        if GUID_PATTERN.match(identifier):
            if expected_prefix:
                prefix = identifier[:3].lower()
                if prefix != expected_prefix.lower():
                    raise ValueError(
                        f"GUID prefix mismatch. "
                        f"Expected '{expected_prefix}', got '{prefix}'"
                    )

            _prefix, uuid_value = GuidService.decode_guid(identifier)
            return uuid_value

        # Provide helpful error for numeric IDs
        if identifier.isdigit():
            raise ValueError(
                f"Numeric IDs are no longer supported. "
                f"Please use GUID format ({{prefix}}_{{base32}})"
            )

        raise ValueError(
            f"Invalid identifier format: {identifier}. "
            f"Expected GUID format ({{prefix}}_{{base32}})"
        )

    @staticmethod
    def parse_guid(guid: str, expected_prefix: str) -> uuid.UUID:
        """
        Parse a GUID string to UUID, validating the prefix.

        Convenience method for service layer lookups.
        Alias for parse_identifier with required prefix.

        Args:
            guid: GUID string
            expected_prefix: Expected entity prefix

        Returns:
            UUID object

        Raises:
            ValueError: If format invalid or prefix doesn't match
        """
        return GuidService.parse_identifier(guid, expected_prefix)


# Backward compatibility alias
ExternalIdService = GuidService
