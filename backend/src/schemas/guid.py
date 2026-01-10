"""
Pydantic schemas for GUID validation and response formatting.

These schemas provide validation for GUID strings and serve as
base classes for entity response schemas.
"""

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# Crockford Base32 pattern (excludes I, L, O, U)
GUID_PATTERN = re.compile(
    r"^(col|con|pip|res)_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$",
    re.IGNORECASE
)


class GuidField(BaseModel):
    """
    Schema mixin providing guid field validation.

    The guid field is validated to ensure:
    1. Correct format: {prefix}_{26-char base32}
    2. Valid prefix (col, con, pip, res)
    3. Valid Crockford Base32 characters

    Example:
        class MyEntityResponse(GuidField):
            name: str
    """

    guid: Annotated[
        str,
        Field(
            description="Global unique identifier in format {prefix}_{base32_uuid}",
            examples=["col_01HGW2BBG0000000000000000"],
            min_length=30,  # 3 (prefix) + 1 (_) + 26 (base32)
            max_length=30,
        )
    ]

    @field_validator("guid", mode="before")
    @classmethod
    def validate_guid_format(cls, v: str) -> str:
        """Validate GUID format."""
        if v is None:
            return v

        if not isinstance(v, str):
            raise ValueError("GUID must be a string")

        if not GUID_PATTERN.match(v):
            raise ValueError(
                f"Invalid GUID format: {v}. "
                f"Expected format: {{prefix}}_{{26-char base32}}"
            )

        return v.lower()  # Normalize to lowercase


class GuidResponse(BaseModel):
    """
    Base response schema including guid.

    All entity response schemas should either inherit from this
    or include the guid field.

    Example:
        class CollectionResponse(GuidResponse):
            id: int
            name: str
            # ... other fields
    """

    guid: str = Field(
        ...,
        description="Global unique identifier in format {prefix}_{base32_uuid}",
        examples=["col_01HGW2BBG0000000000000000"]
    )

    model_config = {"from_attributes": True}


class GuidRequest(BaseModel):
    """
    Request schema for endpoints accepting GUIDs.

    Use this for path/query parameters that require a GUID.

    Example:
        @router.get("/{guid}")
        async def get_by_guid(
            guid: GuidRequest = Depends()
        ):
            ...
    """

    guid: Annotated[
        str,
        Field(
            description="Global unique identifier",
            examples=["col_01HGW2BBG0000000000000000"],
            pattern=r"^(col|con|pip|res)_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$"
        )
    ]


# Type aliases for clarity in annotations
Guid = Annotated[
    str,
    Field(
        description="Global unique identifier in format {prefix}_{base32_uuid}",
        min_length=30,
        max_length=30
    )
]

# Specific entity GUID types with prefix validation
CollectionGuid = Annotated[
    str,
    Field(
        description="Collection GUID",
        pattern=r"^col_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$"
    )
]

ConnectorGuid = Annotated[
    str,
    Field(
        description="Connector GUID",
        pattern=r"^con_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$"
    )
]

PipelineGuid = Annotated[
    str,
    Field(
        description="Pipeline GUID",
        pattern=r"^pip_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$"
    )
]

AnalysisResultGuid = Annotated[
    str,
    Field(
        description="Analysis result GUID",
        pattern=r"^res_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$"
    )
]
