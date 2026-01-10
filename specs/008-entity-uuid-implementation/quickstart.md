# Quickstart: Entity UUID Implementation

**Feature Branch**: `008-entity-uuid-implementation`
**Date**: 2026-01-09

## Overview

This guide provides a quick reference for implementing external IDs (UUIDs) for entities in Photo-Admin.

## Setup

### 1. Install Dependencies

```bash
# Backend dependencies
cd backend
pip install uuid7 base32-crockford
```

### 2. Run Migration

```bash
# Generate migration (if not already created)
cd backend
alembic revision --autogenerate -m "Add UUID columns to entities"

# Apply migration
alembic upgrade head
```

## Backend Implementation

### Using the ExternalIdMixin

```python
# In your model file
from backend.src.models.mixins.external_id import ExternalIdMixin

class MyEntity(Base, ExternalIdMixin):
    __tablename__ = "my_entities"

    EXTERNAL_ID_PREFIX = "mye"  # 3-char prefix for this entity

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # ... other columns

    # UUID column is inherited from ExternalIdMixin
    # external_id property is inherited from ExternalIdMixin
```

### Querying by External ID

```python
from backend.src.services.external_id import ExternalIdService

# In your service class
def get_by_external_id(self, external_id: str) -> MyEntity | None:
    """Get entity by external ID."""
    try:
        uuid_value = ExternalIdService.parse_external_id(
            external_id,
            expected_prefix="mye"
        )
        return self.db.query(MyEntity).filter(
            MyEntity.uuid == uuid_value
        ).first()
    except ValueError:
        return None
```

### API Endpoint Pattern

```python
from fastapi import APIRouter, Path, HTTPException

router = APIRouter()

@router.get("/{entity_id}")
async def get_entity(
    entity_id: str = Path(..., description="Entity ID (external or numeric)"),
    service: MyEntityService = Depends(get_service)
):
    """Get entity by ID (supports both external and numeric IDs)."""
    # Try external ID first
    if entity_id.startswith("mye_"):
        entity = service.get_by_external_id(entity_id)
        if not entity:
            raise HTTPException(404, f"Entity not found: {entity_id}")
        return entity

    # Fall back to numeric ID (backward compatibility)
    if entity_id.isdigit():
        entity = service.get_by_id(int(entity_id))
        if not entity:
            raise HTTPException(404, f"Entity not found: {entity_id}")
        # Add deprecation warning header
        return entity

    raise HTTPException(400, "Invalid identifier format")
```

### Schema with External ID

```python
from pydantic import BaseModel, Field

class MyEntityResponse(BaseModel):
    id: int
    external_id: str = Field(..., description="External ID (mye_...)")
    name: str

    model_config = {"from_attributes": True}
```

## Frontend Implementation

### TypeScript Utilities

```typescript
// src/utils/externalId.ts

type EntityPrefix = 'col' | 'con' | 'pip' | 'res';

export function isValidExternalId(id: string, prefix: EntityPrefix): boolean {
  const pattern = new RegExp(`^${prefix}_[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$`);
  return pattern.test(id);
}

export function getEntityType(externalId: string): EntityPrefix | null {
  const prefixes: EntityPrefix[] = ['col', 'con', 'pip', 'res'];
  for (const prefix of prefixes) {
    if (externalId.startsWith(`${prefix}_`)) {
      return prefix;
    }
  }
  return null;
}
```

### Using External IDs in Components

```tsx
// Display external ID with copy button
import { ExternalIdBadge } from '@/components/ExternalIdBadge';

function CollectionDetail({ collection }) {
  return (
    <div>
      <h1>{collection.name}</h1>
      <ExternalIdBadge externalId={collection.external_id} />
    </div>
  );
}
```

### URL Routing with External IDs

```tsx
// App.tsx routes
<Route path="/collections/:id" element={<CollectionPage />} />

// CollectionPage.tsx
import { useParams } from 'react-router-dom';
import { useCollection } from '@/hooks/useCollections';

function CollectionPage() {
  const { id } = useParams<{ id: string }>();

  // Hook handles both external IDs (col_...) and numeric IDs
  const { collection, loading, error } = useCollection(id);

  // ...
}
```

## Entity Prefix Reference

| Entity | Prefix | Example External ID |
|--------|--------|---------------------|
| Collection | `col` | `col_01HGW2BBG0000000000000000` |
| Connector | `con` | `con_01HGW2BBG0000000000000001` |
| Pipeline | `pip` | `pip_01HGW2BBG0000000000000002` |
| AnalysisResult | `res` | `res_01HGW2BBG0000000000000003` |

## Testing

### Backend Test Example

```python
def test_external_id_generation(sample_collection):
    """Test that external ID is generated correctly."""
    collection = sample_collection(name="Test")

    assert collection.external_id is not None
    assert collection.external_id.startswith("col_")
    assert len(collection.external_id) == 30  # "col_" + 26 chars


def test_get_by_external_id(test_client, sample_collection):
    """Test fetching entity by external ID."""
    collection = sample_collection(name="Test")
    external_id = collection.external_id

    response = test_client.get(f"/api/collections/{external_id}")

    assert response.status_code == 200
    assert response.json()["external_id"] == external_id
```

### Frontend Test Example

```typescript
import { isValidExternalId, getEntityType } from './externalId';

describe('externalId utilities', () => {
  test('validates correct external ID', () => {
    expect(isValidExternalId('col_01HGW2BBG0000000000000000', 'col')).toBe(true);
  });

  test('rejects wrong prefix', () => {
    expect(isValidExternalId('con_01HGW2BBG0000000000000000', 'col')).toBe(false);
  });

  test('extracts entity type', () => {
    expect(getEntityType('col_01HGW2BBG0000000000000000')).toBe('col');
  });
});
```

## Common Patterns

### Error Handling

```python
# Service layer
class EntityNotFoundError(Exception):
    pass

class InvalidExternalIdError(Exception):
    pass

# API layer
@router.get("/{entity_id}")
async def get_entity(entity_id: str):
    try:
        return service.get_by_identifier(entity_id)
    except InvalidExternalIdError:
        raise HTTPException(400, "Invalid external ID format")
    except EntityNotFoundError:
        raise HTTPException(404, f"Entity not found: {entity_id}")
```

### Backward Compatibility

```python
# Add deprecation warning for numeric IDs
from fastapi import Response

@router.get("/{entity_id}")
async def get_entity(entity_id: str, response: Response):
    if entity_id.isdigit():
        response.headers["X-Deprecation-Warning"] = (
            "Numeric IDs are deprecated. Use external_id instead."
        )
    # ... handle request
```

## Troubleshooting

### UUID Not Generated

**Symptom**: Entity created without UUID

**Solution**: Ensure model inherits from `ExternalIdMixin` and migration has run:
```python
class MyEntity(Base, ExternalIdMixin):  # Must include mixin
    EXTERNAL_ID_PREFIX = "mye"  # Must define prefix
```

### Invalid External ID Error

**Symptom**: 400 error when using external ID

**Check**:
1. Prefix matches entity type
2. Base32 portion is 26 characters
3. Only uses Crockford Base32 alphabet

### Migration Failed

**Symptom**: Alembic migration error

**Solution**: Check for existing NULL UUIDs and populate manually:
```sql
-- Find rows missing UUIDs
SELECT id FROM collections WHERE uuid IS NULL;
```
