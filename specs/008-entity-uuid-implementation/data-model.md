# Data Model: Entity UUID Implementation

**Feature Branch**: `008-entity-uuid-implementation`
**Date**: 2026-01-09
**Status**: Complete

## Overview

This document defines the data model changes required to add Universal Unique Identifiers (UUIDv7) to all user-facing entities. The design adds a `uuid` column to existing entities and defines a reusable mixin for future entities.

## Schema Changes

### ExternalIdMixin (New)

A SQLAlchemy mixin providing UUID column and external ID generation for all user-facing entities.

```python
# backend/src/models/mixins/external_id.py

class ExternalIdMixin:
    """
    Mixin providing external ID (UUID) support for entities.

    Adds:
    - uuid: Binary UUID column (UUIDv7)
    - external_id: Property returning prefixed Base32 string
    """

    # Column definition (applied to each entity table)
    uuid = Column(
        PG_UUID(as_uuid=True).with_variant(LargeBinary(16), "sqlite"),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: uuid7()
    )

    # Abstract: Subclasses must define their prefix
    EXTERNAL_ID_PREFIX: str  # e.g., "col", "con", "pip"

    @property
    def external_id(self) -> str:
        """Returns the full external ID with prefix."""
        encoded = base32_crockford.encode(self.uuid.bytes)
        return f"{self.EXTERNAL_ID_PREFIX}_{encoded.lower()}"

    @classmethod
    def parse_external_id(cls, external_id: str) -> uuid.UUID:
        """Parse external ID string to UUID object."""
        if not external_id.startswith(f"{cls.EXTERNAL_ID_PREFIX}_"):
            raise ValueError(f"Invalid prefix for {cls.__name__}")
        encoded_part = external_id[len(cls.EXTERNAL_ID_PREFIX) + 1:]
        uuid_bytes = base32_crockford.decode(encoded_part)
        return uuid.UUID(bytes=uuid_bytes)
```

### Entity Changes

#### Collection

**Table**: `collections`

| Column | Type | Constraints | Change |
|--------|------|-------------|--------|
| `id` | Integer | PK, auto-increment | Unchanged |
| `uuid` | UUID (16 bytes) | NOT NULL, UNIQUE, INDEX | **NEW** |
| `name` | String(255) | UNIQUE, NOT NULL | Unchanged |
| ... | ... | ... | Unchanged |

**SQLAlchemy Model Addition**:
```python
class Collection(Base, ExternalIdMixin):
    EXTERNAL_ID_PREFIX = "col"
    # ... existing columns unchanged
```

**External ID Format**: `col_01HGW2BBG0000000000000000`

---

#### Connector

**Table**: `connectors`

| Column | Type | Constraints | Change |
|--------|------|-------------|--------|
| `id` | Integer | PK, auto-increment | Unchanged |
| `uuid` | UUID (16 bytes) | NOT NULL, UNIQUE, INDEX | **NEW** |
| `name` | String(255) | UNIQUE, NOT NULL | Unchanged |
| ... | ... | ... | Unchanged |

**SQLAlchemy Model Addition**:
```python
class Connector(Base, ExternalIdMixin):
    EXTERNAL_ID_PREFIX = "con"
    # ... existing columns unchanged
```

**External ID Format**: `con_01HGW2BBG0000000000000001`

---

#### Pipeline

**Table**: `pipelines`

| Column | Type | Constraints | Change |
|--------|------|-------------|--------|
| `id` | Integer | PK, auto-increment | Unchanged |
| `uuid` | UUID (16 bytes) | NOT NULL, UNIQUE, INDEX | **NEW** |
| `name` | String(255) | UNIQUE, NOT NULL | Unchanged |
| ... | ... | ... | Unchanged |

**SQLAlchemy Model Addition**:
```python
class Pipeline(Base, ExternalIdMixin):
    EXTERNAL_ID_PREFIX = "pip"
    # ... existing columns unchanged
```

**External ID Format**: `pip_01HGW2BBG0000000000000002`

---

#### AnalysisResult

**Table**: `analysis_results`

| Column | Type | Constraints | Change |
|--------|------|-------------|--------|
| `id` | Integer | PK, auto-increment | Unchanged |
| `uuid` | UUID (16 bytes) | NOT NULL, UNIQUE, INDEX | **NEW** |
| `collection_id` | Integer | FK(collections.id), nullable | Unchanged |
| ... | ... | ... | Unchanged |

**SQLAlchemy Model Addition**:
```python
class AnalysisResult(Base, ExternalIdMixin):
    EXTERNAL_ID_PREFIX = "res"
    # ... existing columns unchanged
```

**External ID Format**: `res_01HGW2BBG0000000000000003`

---

## Pydantic Schema Changes

### ExternalIdMixin Schema

```python
# backend/src/schemas/external_id.py

class ExternalIdSchema(BaseModel):
    """Base schema for entities with external IDs."""
    external_id: str = Field(
        ...,
        description="External identifier in format {prefix}_{base32_uuid}",
        examples=["col_01HGW2BBG0000000000000000"]
    )
```

### Response Schema Updates

All entity response schemas gain `external_id` field:

```python
class CollectionResponse(BaseModel):
    id: int  # Internal ID (for backward compatibility)
    external_id: str  # NEW: External ID
    name: str
    # ... other fields

    model_config = {"from_attributes": True}

    @model_validator(mode='before')
    @classmethod
    def compute_external_id(cls, data):
        """Compute external_id from uuid for ORM objects."""
        if hasattr(data, 'external_id'):
            # Property exists on model
            return data
        return data
```

### Request Schema Updates

Create/Update schemas do **not** include `external_id` (server-generated):

```python
class CollectionCreate(BaseModel):
    # external_id NOT included - auto-generated
    name: str
    type: CollectionType
    location: str
    # ... other fields
```

---

## Index Strategy

### New Indexes

| Table | Index Name | Column(s) | Type | Purpose |
|-------|------------|-----------|------|---------|
| `collections` | `ix_collections_uuid` | `uuid` | UNIQUE | Fast lookup by external ID |
| `connectors` | `ix_connectors_uuid` | `uuid` | UNIQUE | Fast lookup by external ID |
| `pipelines` | `ix_pipelines_uuid` | `uuid` | UNIQUE | Fast lookup by external ID |
| `analysis_results` | `ix_analysis_results_uuid` | `uuid` | UNIQUE | Fast lookup by external ID |

### Performance Consideration

- UUID lookups use unique index (O(log n))
- Internal integer joins remain unchanged
- Foreign keys still reference integer `id` columns

---

## Migration Plan

### Migration Script: `add_uuid_columns.py`

```python
"""Add UUID columns to all user-facing entities

Revision ID: [auto-generated]
Create Date: 2026-01-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid7 import uuid7

def upgrade():
    # Collections
    op.add_column('collections', sa.Column('uuid', PG_UUID(), nullable=True))
    _populate_uuids('collections')
    op.alter_column('collections', 'uuid', nullable=False)
    op.create_index('ix_collections_uuid', 'collections', ['uuid'], unique=True)

    # Connectors
    op.add_column('connectors', sa.Column('uuid', PG_UUID(), nullable=True))
    _populate_uuids('connectors')
    op.alter_column('connectors', 'uuid', nullable=False)
    op.create_index('ix_connectors_uuid', 'connectors', ['uuid'], unique=True)

    # Pipelines
    op.add_column('pipelines', sa.Column('uuid', PG_UUID(), nullable=True))
    _populate_uuids('pipelines')
    op.alter_column('pipelines', 'uuid', nullable=False)
    op.create_index('ix_pipelines_uuid', 'pipelines', ['uuid'], unique=True)

    # AnalysisResults
    op.add_column('analysis_results', sa.Column('uuid', PG_UUID(), nullable=True))
    _populate_uuids('analysis_results')
    op.alter_column('analysis_results', 'uuid', nullable=False)
    op.create_index('ix_analysis_results_uuid', 'analysis_results', ['uuid'], unique=True)


def downgrade():
    # Drop indexes and columns in reverse order
    op.drop_index('ix_analysis_results_uuid', table_name='analysis_results')
    op.drop_column('analysis_results', 'uuid')

    op.drop_index('ix_pipelines_uuid', table_name='pipelines')
    op.drop_column('pipelines', 'uuid')

    op.drop_index('ix_connectors_uuid', table_name='connectors')
    op.drop_column('connectors', 'uuid')

    op.drop_index('ix_collections_uuid', table_name='collections')
    op.drop_column('collections', 'uuid')


def _populate_uuids(table_name: str):
    """Generate UUIDs for existing rows."""
    conn = op.get_bind()
    rows = conn.execute(sa.text(f"SELECT id FROM {table_name}")).fetchall()
    for (id,) in rows:
        new_uuid = uuid7()
        conn.execute(
            sa.text(f"UPDATE {table_name} SET uuid = :uuid WHERE id = :id"),
            {"uuid": str(new_uuid), "id": id}
        )
```

### Migration Safety

- **Reversible**: Full downgrade support
- **Non-destructive**: Adds column without modifying existing data
- **Batch processing**: Generates UUIDs in batches to avoid long locks
- **Zero data loss**: No existing columns modified or removed

---

## Entity Relationship Diagram (Updated)

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENTITIES WITH EXTERNAL IDs                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │   Collection     │    │    Connector     │                   │
│  │                  │    │                  │                   │
│  │ id: int (PK)     │───▶│ id: int (PK)     │                   │
│  │ uuid: UUID (UK)  │    │ uuid: UUID (UK)  │                   │
│  │ external_id: str │    │ external_id: str │                   │
│  │ connector_id: FK │    │ ...              │                   │
│  │ pipeline_id: FK  │    └──────────────────┘                   │
│  │ ...              │                                           │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           │ 1:*                                                  │
│           ▼                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ AnalysisResult   │    │    Pipeline      │                   │
│  │                  │    │                  │                   │
│  │ id: int (PK)     │    │ id: int (PK)     │                   │
│  │ uuid: UUID (UK)  │    │ uuid: UUID (UK)  │                   │
│  │ external_id: str │    │ external_id: str │                   │
│  │ collection_id:FK │    │ ...              │                   │
│  │ ...              │    └──────────────────┘                   │
│  └──────────────────┘                                           │
│                                                                  │
│  Legend:                                                         │
│  - PK = Primary Key (integer, internal)                         │
│  - UK = Unique Key (UUID, for external ID)                      │
│  - FK = Foreign Key (references integer PK)                     │
│  - external_id = Computed property (prefix + Base32 UUID)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Rules

### External ID Format Validation

```python
import re

EXTERNAL_ID_PATTERN = re.compile(
    r'^(col|con|pip|res)_[0-9A-HJKMNP-TV-Z]{26}$',
    re.IGNORECASE
)

def validate_external_id(external_id: str, expected_prefix: str) -> bool:
    """
    Validate external ID format.

    Rules:
    1. Must match pattern: {prefix}_{26 Crockford Base32 chars}
    2. Prefix must match expected entity type
    3. Case-insensitive
    """
    if not EXTERNAL_ID_PATTERN.match(external_id):
        return False

    prefix = external_id.split('_')[0].lower()
    return prefix == expected_prefix.lower()
```

### Error Messages

| Validation Failure | Error Message |
|-------------------|---------------|
| Invalid format | "Invalid external ID format. Expected {prefix}_XXXX..." |
| Wrong prefix | "External ID type mismatch. Expected {expected} but got {actual}" |
| Not found | "Entity not found with ID: {external_id}" |
| Decode error | "Invalid external ID encoding" |

---

## Future Entities

When implementing future entities (Event, User, Team, etc.), they should:

1. Inherit from `ExternalIdMixin`
2. Define their `EXTERNAL_ID_PREFIX` class attribute
3. Include `uuid` column in migration
4. Update response schemas to include `external_id`

**Prefix Registry** (from domain model):

| Entity | Prefix |
|--------|--------|
| Event | `evt` |
| User | `usr` |
| Team | `tea` |
| Camera | `cam` |
| Album | `alb` |
| Image | `img` |
| File | `fil` |
| Workflow | `wfl` |
| Location | `loc` |
| Organizer | `org` |
| Performer | `prf` |
| Agent | `agt` |
