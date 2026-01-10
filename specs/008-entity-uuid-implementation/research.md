# Research: Entity UUID Implementation

**Feature Branch**: `008-entity-uuid-implementation`
**Date**: 2026-01-09
**Status**: Complete

## Research Questions

### 1. Python Library for UUIDv7 Generation

**Question**: Which Python library should be used for UUIDv7 generation?

**Decision**: Use `uuid7` package from PyPI

**Rationale**:
- Simple, focused library specifically for UUIDv7
- Provides 200ns time resolution with 48 bits of randomness
- RFC 9562 compliant
- Actively maintained
- Minimal dependencies

**Alternatives Considered**:

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| `uuid7` (PyPI) | Simple, focused, minimal | Basic features only | **Selected** |
| `edwh-uuid7` | PostgreSQL pg_uuidv7 compatible, timestamp extraction | More complex API | Good alternative if PG compatibility needed |
| Python 3.14 stdlib | Native support, no dependencies | Requires Python 3.14+ (project uses 3.10+) | Not available for our version |
| `uuid7-standard` | Standard compliant, pythonic | Smaller community | Consider as fallback |

**Installation**: `pip install uuid7`

**Usage Example**:
```python
from uuid7 import uuid7

# Generate new UUIDv7
new_uuid = uuid7()  # Returns uuid.UUID object
uuid_bytes = new_uuid.bytes  # 16-byte binary for storage
```

**Sources**:
- [uuid7 on PyPI](https://pypi.org/project/uuid7/)
- [edwh-uuid7 on PyPI](https://pypi.org/project/edwh-uuid7/)
- [Python uuid7 in stdlib discussion](https://discuss.python.org/t/add-uuid7-in-uuid-module-in-standard-library/44390)

---

### 2. Crockford Base32 Encoding Library

**Question**: Which library should be used for Crockford's Base32 encoding?

**Decision**: Use `base32-crockford` package from PyPI

**Rationale**:
- Most established and widely used
- Full implementation of Douglas Crockford's specification
- Handles check symbols (optional)
- Case-insensitive decoding
- Removes hyphens automatically during decode
- BSD licensed

**Alternatives Considered**:

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| `base32-crockford` | Full spec, well-tested, BSD | Python 2/3 compatible (not modern typing) | **Selected** |
| `krock32` | Checksumming support, modern | Smaller community | Good alternative |
| `base32-lib` | Docs available | Fewer features | Not selected |
| Custom implementation | No dependency | Maintenance burden, error-prone | Not recommended |

**Installation**: `pip install base32-crockford`

**Usage Example**:
```python
import base32_crockford

# Encode bytes to Crockford Base32
encoded = base32_crockford.encode(uuid_bytes)  # Returns uppercase string

# Decode back to bytes (case-insensitive)
decoded = base32_crockford.decode(encoded)
```

**Sources**:
- [base32-crockford on PyPI](https://pypi.org/project/base32-crockford/)
- [GitHub: jbittel/base32-crockford](https://github.com/jbittel/base32-crockford)

---

### 3. Database Storage Strategy

**Question**: How should UUIDs be stored in PostgreSQL?

**Decision**: Store as 16-byte binary using PostgreSQL's native UUID type

**Rationale**:
- Native UUID type is 16 bytes (compact)
- Efficient indexing compared to string storage
- SQLAlchemy's `UUID` type maps directly
- SQLite compatibility via `LargeBinary` with variant

**Implementation**:
```python
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import LargeBinary
import uuid

# PostgreSQL UUID with SQLite fallback
uuid_column = Column(
    PG_UUID(as_uuid=True).with_variant(LargeBinary(16), "sqlite"),
    nullable=False,
    unique=True,
    index=True
)
```

**Index Strategy**:
- Create unique index on UUID column for fast lookups by external ID
- Keep primary key as integer for internal joins (foreign keys reference int ID)

---

### 4. External ID Format Specification

**Question**: What is the exact format for external IDs?

**Decision**: `{prefix}_{crockford_base32_uuid}`

**Format Details**:
- **Prefix**: 3-4 lowercase characters identifying entity type + underscore
- **UUID Part**: Crockford's Base32 encoded UUIDv7 (26 characters)
- **Total Length**: 30-31 characters (e.g., `col_01HGW2BBG0000000000000000`)

**Entity Prefixes** (from domain model):

| Entity | Prefix | Example |
|--------|--------|---------|
| Collection | `col_` | `col_01HGW2BBG0000000000000000` |
| Connector | `con_` | `con_01HGW2BBG0000000000000001` |
| Pipeline | `pip_` | `pip_01HGW2BBG0000000000000002` |
| AnalysisResult | `res_` | `res_01HGW2BBG0000000000000003` |

**Validation Rules**:
- External ID must start with valid prefix
- Remaining characters must be valid Crockford Base32
- Case-insensitive for input (normalize to lowercase for storage)
- Reject IDs with wrong prefix for endpoint (e.g., `con_xxx` at `/collections/`)

---

### 5. API Path Parameter Handling

**Question**: How should API endpoints handle both numeric IDs (backward compat) and external IDs?

**Decision**: Use string path parameter with smart detection

**Implementation Pattern**:
```python
from fastapi import Path, HTTPException

def parse_entity_identifier(
    entity_id: str = Path(...),
    expected_prefix: str = "col"
) -> tuple[int | None, str | None]:
    """
    Parse entity identifier, returning (internal_id, external_id).
    One will be None, the other populated.
    """
    # Check if numeric (backward compatibility)
    if entity_id.isdigit():
        return (int(entity_id), None)

    # Validate external ID format
    if not entity_id.startswith(f"{expected_prefix}_"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid identifier format. Expected {expected_prefix}_* or numeric ID"
        )

    return (None, entity_id)
```

**Backward Compatibility**:
- Numeric IDs continue to work (transition period)
- External IDs preferred for new integrations
- Consider deprecation warning header for numeric ID usage

---

### 6. Frontend TypeScript Utilities

**Question**: What TypeScript utilities are needed for external ID handling?

**Decision**: Create `externalId.ts` utility module

**Required Functions**:
```typescript
// Validate external ID format
function isValidExternalId(id: string, entityType: EntityType): boolean

// Extract entity type from external ID
function getEntityTypeFromId(externalId: string): EntityType | null

// Parse external ID to components
interface ExternalIdParts {
  prefix: string
  uuid: string
  entityType: EntityType
}
function parseExternalId(id: string): ExternalIdParts | null
```

**Entity Type Enum**:
```typescript
enum EntityType {
  Collection = 'collection',
  Connector = 'connector',
  Pipeline = 'pipeline',
  AnalysisResult = 'result'
}

const ENTITY_PREFIXES: Record<EntityType, string> = {
  [EntityType.Collection]: 'col',
  [EntityType.Connector]: 'con',
  [EntityType.Pipeline]: 'pip',
  [EntityType.AnalysisResult]: 'res'
}
```

---

### 7. Migration Strategy

**Question**: How should existing entities be migrated to have UUIDs?

**Decision**: Alembic migration with batch UUID generation

**Migration Steps**:
1. Add nullable UUID column to each entity table
2. Batch generate UUIDs for all existing rows
3. Make UUID column non-nullable
4. Create unique index on UUID column

**Migration Script Pattern**:
```python
def upgrade():
    # Step 1: Add nullable column
    op.add_column('collections', sa.Column('uuid', PG_UUID(), nullable=True))

    # Step 2: Populate existing rows
    conn = op.get_bind()
    collections = conn.execute(sa.text("SELECT id FROM collections")).fetchall()
    for (id,) in collections:
        conn.execute(
            sa.text("UPDATE collections SET uuid = :uuid WHERE id = :id"),
            {"uuid": uuid7().bytes, "id": id}
        )

    # Step 3: Make non-nullable
    op.alter_column('collections', 'uuid', nullable=False)

    # Step 4: Create unique index
    op.create_index('ix_collections_uuid', 'collections', ['uuid'], unique=True)
```

**Rollback Safety**: Migration includes downgrade to drop column if needed.

---

## Summary

| Decision Area | Choice | Dependencies Added |
|--------------|--------|-------------------|
| UUIDv7 Generation | `uuid7` package | `pip install uuid7` |
| Base32 Encoding | `base32-crockford` package | `pip install base32-crockford` |
| Database Storage | PostgreSQL UUID type (16-byte binary) | None (SQLAlchemy built-in) |
| External ID Format | `{prefix}_{base32_uuid}` (30-31 chars) | None |
| API Handling | Smart detection (numeric or external) | None |
| Migration | Alembic batch migration | None (Alembic exists) |

All research questions have been resolved. Ready for Phase 1: Design & Contracts.
