"""
GUID mixin for SQLAlchemy models.

Provides UUID-based Global Unique Identifiers for user-facing entities.
Uses UUIDv7 (time-ordered) with Crockford's Base32 encoding for URL-safe,
human-readable identifiers.

GUID Format: {prefix}_{base32_uuid}
Examples:
    - col_01HGW2BBG0000000000000000 (Collection)
    - con_01HGW2BBG0000000000000001 (Connector)
    - pip_01HGW2BBG0000000000000002 (Pipeline)
    - res_01HGW2BBG0000000000000003 (AnalysisResult)
"""

import uuid as uuid_module
from typing import ClassVar

import base32_crockford
from sqlalchemy import Column, TypeDecorator, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid_extensions import uuid7


class UUIDType(TypeDecorator):
    """
    Platform-independent UUID type.

    Uses PostgreSQL's native UUID type when available,
    otherwise stores as 16-byte LargeBinary for SQLite.

    Always presents as a Python UUID object.
    """

    impl = LargeBinary
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(LargeBinary(16))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value if isinstance(value, uuid_module.UUID) else uuid_module.UUID(bytes=value)
        else:
            # SQLite - store as bytes
            if isinstance(value, uuid_module.UUID):
                return value.bytes
            elif isinstance(value, bytes):
                return value
            else:
                return uuid_module.UUID(str(value)).bytes

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_module.UUID):
            return value
        elif isinstance(value, bytes):
            return uuid_module.UUID(bytes=value)
        else:
            return uuid_module.UUID(str(value))


class GuidMixin:
    """
    Mixin providing GUID (Global Unique Identifier) support for entities.

    Adds:
    - uuid: Binary UUID column (UUIDv7, time-ordered)
    - guid: Property returning prefixed Base32 string
    - parse_guid: Class method to decode GUID strings

    Usage:
        class MyEntity(Base, GuidMixin):
            GUID_PREFIX = "mye"
            # ... other columns

        entity = MyEntity()
        print(entity.guid)  # mye_01HGW2BBG...

    Entity Prefixes:
        - col: Collection
        - con: Connector
        - pip: Pipeline
        - res: AnalysisResult
    """

    # Abstract: Subclasses must define their 3-character prefix
    GUID_PREFIX: ClassVar[str]

    # UUID column definition using platform-agnostic UUIDType
    # PostgreSQL: Uses native UUID type
    # SQLite: Uses LargeBinary(16) for test compatibility
    uuid = Column(
        UUIDType(),
        nullable=False,
        unique=True,
        index=True,
        default=uuid7,  # Callable default generates new UUID on insert
    )

    @property
    def guid(self) -> str:
        """
        Get the full GUID with prefix.

        Returns:
            GUID in format {prefix}_{base32_uuid}
            Example: col_01HGW2BBG0000000000000000

        Note:
            The UUID is encoded using Crockford's Base32 encoding which:
            - Is case-insensitive
            - Excludes confusing characters (I, L, O, U)
            - Is URL-safe without encoding
        """
        if self.uuid is None:
            return None

        # Handle both UUID objects and bytes (SQLite compatibility)
        if isinstance(self.uuid, bytes):
            uuid_bytes = self.uuid
        else:
            uuid_bytes = self.uuid.bytes

        encoded = base32_crockford.encode(int.from_bytes(uuid_bytes, "big"))
        # Pad to 26 characters (full UUIDv7 encoding)
        encoded = encoded.zfill(26)
        return f"{self.GUID_PREFIX}_{encoded.lower()}"

    @classmethod
    def parse_guid(cls, guid: str) -> uuid_module.UUID:
        """
        Parse a GUID string to a UUID object.

        Args:
            guid: GUID string (e.g., "col_01HGW2BBG...")

        Returns:
            UUID object

        Raises:
            ValueError: If the GUID format is invalid or prefix doesn't match
        """
        if not guid:
            raise ValueError("GUID cannot be empty")

        expected_prefix = f"{cls.GUID_PREFIX}_"
        if not guid.lower().startswith(expected_prefix.lower()):
            raise ValueError(
                f"Invalid prefix for {cls.__name__}. "
                f"Expected '{cls.GUID_PREFIX}', got '{guid.split('_')[0]}'"
            )

        # Extract the encoded part after the prefix
        encoded_part = guid[len(expected_prefix):]

        if len(encoded_part) != 26:
            raise ValueError(
                f"Invalid GUID length. Expected 26 characters after prefix, "
                f"got {len(encoded_part)}"
            )

        try:
            # Decode from Crockford Base32 (case-insensitive)
            uuid_int = base32_crockford.decode(encoded_part.upper())
            uuid_bytes = uuid_int.to_bytes(16, "big")
            return uuid_module.UUID(bytes=uuid_bytes)
        except (ValueError, OverflowError) as e:
            raise ValueError(f"Invalid GUID encoding: {e}")

    @classmethod
    def get_uuid_from_guid(cls, guid: str) -> uuid_module.UUID:
        """
        Alias for parse_guid for backward compatibility.

        Args:
            guid: GUID string

        Returns:
            UUID object
        """
        return cls.parse_guid(guid)
