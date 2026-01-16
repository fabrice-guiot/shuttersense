# Data Model: Teams/Tenants and User Management with Authentication

**Feature**: 019-user-tenancy
**Date**: 2026-01-15
**Status**: Draft

## Overview

This document defines the database entities for multi-tenancy and user management. All entities follow the established GuidMixin pattern and integrate with existing models.

---

## New Entities

### Team

**GUID Prefix**: `ten`

Represents a tenancy boundary. All data in the system belongs to exactly one Team. Teams provide complete data isolation between different organizations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null, indexed | UUIDv7 for GUID generation (via GuidMixin) |
| `name` | String(255) | unique, not null | Team display name |
| `slug` | String(100) | unique, not null | URL-safe identifier (auto-generated from name) |
| `is_active` | Boolean | not null, default=true | Team active status |
| `settings_json` | Text | nullable | Team-level settings as JSON (timezone, branding, etc.) |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**Relationships**:
- One-to-many with User (team has many users)
- One-to-many with all tenant-scoped entities (Collection, Event, etc.)

**Indexes**:
- `uuid` (unique, for GUID lookups)
- `name` (unique)
- `slug` (unique)
- `is_active` (for filtering)

**State Transitions**:
```
active ──(admin deactivates)──> inactive
inactive ──(admin reactivates)──> active
```

**Notes**:
- `slug` is auto-generated: lowercase name, spaces→hyphens, special chars removed
- Deactivated team blocks ALL member logins
- Teams cannot be hard-deleted (only soft-delete via `is_active=false`)

---

### User

**GUID Prefix**: `usr`

Represents a person who can access the system. Users are pre-provisioned by team administrators before they can log in via OAuth.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null, indexed | UUIDv7 for GUID generation (via GuidMixin) |
| `team_id` | Integer | FK(teams.id), not null, indexed | Team membership |
| `email` | String(255) | unique, not null, indexed | Login email (globally unique across ALL teams) |
| `first_name` | String(100) | nullable | User's first name (from invite or OAuth) |
| `last_name` | String(100) | nullable | User's last name (from invite or OAuth) |
| `display_name` | String(255) | nullable | Display name (OAuth sync or manual) |
| `picture_url` | String(1024) | nullable | Profile picture URL (from OAuth) |
| `is_active` | Boolean | not null, default=true | Account active status |
| `status` | Enum | not null, default='pending' | Account status: pending, active, deactivated |
| `last_login_at` | DateTime | nullable | Last successful login timestamp |
| `oauth_provider` | String(50) | nullable | Last used OAuth provider (google, microsoft) |
| `oauth_subject` | String(255) | nullable | OAuth `sub` claim for identity verification |
| `preferences_json` | Text | nullable | User preferences as JSON |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**Relationships**:
- Many-to-one with Team (user belongs to one team)
- One-to-many with ApiToken (user has many tokens)

**Indexes**:
- `uuid` (unique, for GUID lookups)
- `email` (unique, global across all teams)
- `team_id` (for team-scoped queries)
- `status` (for filtering by status)
- `is_active` (for filtering active users)
- `oauth_subject` (for OAuth identity lookup)

**Status Enum**:
```python
class UserStatus(enum.Enum):
    PENDING = "pending"        # Invited, never logged in
    ACTIVE = "active"          # Logged in at least once
    DEACTIVATED = "deactivated"  # Admin disabled
```

**State Transitions**:
```
pending ──(first OAuth login)──> active
active ──(admin deactivates)──> deactivated
deactivated ──(admin reactivates)──> active
```

**Notes**:
- `email` is globally unique across ALL teams (prevents same email in multiple teams)
- `is_active` is the functional toggle for login capability
- `status` tracks the user lifecycle for display purposes
- OAuth profile data (name, picture) synced on each login
- `oauth_subject` stores the immutable `sub` claim from the OAuth provider

---

### ApiToken

**GUID Prefix**: `tok`

Represents a programmatic access credential for API authentication. Tokens are JWT-based with the hash stored for revocation lookup.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null, indexed | UUIDv7 for GUID generation (via GuidMixin) |
| `user_id` | Integer | FK(users.id), not null, indexed | Token owner |
| `team_id` | Integer | FK(teams.id), not null, indexed | Team scope (denormalized for query efficiency) |
| `name` | String(100) | not null | Token name/description (user-provided) |
| `token_hash` | String(64) | unique, not null, indexed | SHA-256 hash of token |
| `token_prefix` | String(10) | not null | First 8 characters of token (for UI identification) |
| `scopes_json` | Text | not null, default='["*"]' | Allowed API scopes as JSON array |
| `expires_at` | DateTime | not null | Token expiration timestamp |
| `last_used_at` | DateTime | nullable | Last API call using this token |
| `is_active` | Boolean | not null, default=true | Token active status (for revocation) |
| `created_at` | DateTime | not null | Creation timestamp |

**Relationships**:
- Many-to-one with User (token belongs to one user)
- Many-to-one with Team (token scoped to one team)

**Indexes**:
- `uuid` (unique, for GUID lookups)
- `token_hash` (unique, for validation lookup)
- `user_id` (for user's token list)
- `team_id` (for team-scoped queries)
- `expires_at` (for expiration cleanup)
- `is_active` (for filtering active tokens)

**Notes**:
- Full token shown ONLY once at creation (copy-to-clipboard UI)
- `token_hash` is SHA-256 of the full JWT
- `token_prefix` allows users to identify which token is which
- `scopes_json` is prepared for future granular permissions (v1: `["*"]` only)
- `team_id` is denormalized from user for query efficiency
- Revocation sets `is_active=false` (soft delete)

---

## Existing Entities - Tenant Modification

All existing entities require a `team_id` foreign key for tenant isolation. This is a **breaking change** requiring a multi-step migration.

### Entities Requiring `team_id`

| Entity | Current | After Migration |
|--------|---------|-----------------|
| Collection | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Connector | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Pipeline | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| AnalysisResult | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Event | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| EventSeries | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Category | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Location | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Organizer | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |
| Performer | No team_id | `team_id INTEGER NOT NULL REFERENCES teams(id)` |

### Migration Strategy

The migration must be performed in stages to avoid data loss:

**Migration 1**: Create teams table
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    uuid BYTEA NOT NULL UNIQUE,  -- LargeBinary(16) for SQLite, UUID for PostgreSQL
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    settings_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_teams_uuid ON teams(uuid);
CREATE INDEX idx_teams_is_active ON teams(is_active);
```

**Migration 2**: Create users table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uuid BYTEA NOT NULL UNIQUE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    email VARCHAR(255) NOT NULL UNIQUE,  -- GLOBAL uniqueness
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(255),
    picture_url VARCHAR(1024),
    is_active BOOLEAN NOT NULL DEFAULT true,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    last_login_at TIMESTAMP,
    oauth_provider VARCHAR(50),
    oauth_subject VARCHAR(255),
    preferences_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_uuid ON users(uuid);
CREATE INDEX idx_users_team_id ON users(team_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_oauth_subject ON users(oauth_subject);
```

**Migration 3**: Create api_tokens table
```sql
CREATE TABLE api_tokens (
    id SERIAL PRIMARY KEY,
    uuid BYTEA NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    name VARCHAR(100) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    token_prefix VARCHAR(10) NOT NULL,
    scopes_json TEXT NOT NULL DEFAULT '["*"]',
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_tokens_uuid ON api_tokens(uuid);
CREATE INDEX idx_api_tokens_token_hash ON api_tokens(token_hash);
CREATE INDEX idx_api_tokens_user_id ON api_tokens(user_id);
CREATE INDEX idx_api_tokens_team_id ON api_tokens(team_id);
CREATE INDEX idx_api_tokens_expires_at ON api_tokens(expires_at);
CREATE INDEX idx_api_tokens_is_active ON api_tokens(is_active);
```

**Migration 4**: Add team_id to existing tables (nullable first)
```sql
-- Run AFTER seed script creates default team
ALTER TABLE collections ADD COLUMN team_id INTEGER;
ALTER TABLE connectors ADD COLUMN team_id INTEGER;
ALTER TABLE pipelines ADD COLUMN team_id INTEGER;
ALTER TABLE analysis_results ADD COLUMN team_id INTEGER;
ALTER TABLE events ADD COLUMN team_id INTEGER;
ALTER TABLE event_series ADD COLUMN team_id INTEGER;
ALTER TABLE categories ADD COLUMN team_id INTEGER;
ALTER TABLE locations ADD COLUMN team_id INTEGER;
ALTER TABLE organizers ADD COLUMN team_id INTEGER;
ALTER TABLE performers ADD COLUMN team_id INTEGER;
```

**Migration 5**: Populate team_id with default team
```sql
-- Execute via Python script to get default team ID
UPDATE collections SET team_id = :default_team_id;
UPDATE connectors SET team_id = :default_team_id;
UPDATE pipelines SET team_id = :default_team_id;
UPDATE analysis_results SET team_id = :default_team_id;
UPDATE events SET team_id = :default_team_id;
UPDATE event_series SET team_id = :default_team_id;
UPDATE categories SET team_id = :default_team_id;
UPDATE locations SET team_id = :default_team_id;
UPDATE organizers SET team_id = :default_team_id;
UPDATE performers SET team_id = :default_team_id;
```

**Migration 6**: Add NOT NULL constraint and indexes
```sql
ALTER TABLE collections ALTER COLUMN team_id SET NOT NULL;
ALTER TABLE collections ADD CONSTRAINT fk_collections_team FOREIGN KEY (team_id) REFERENCES teams(id);
CREATE INDEX idx_collections_team_id ON collections(team_id);
-- Repeat for all other tables...
```

---

## Entity Relationship Diagram

```
                          ┌─────────────────┐
                          │      Team       │
                          │  (GUID: ten_)   │
                          └────────┬────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
    ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
    │     User      │     │  Collection   │     │    Event      │
    │  (GUID: usr_) │     │  (GUID: col_) │     │  (GUID: evt_) │
    └───────┬───────┘     └───────────────┘     └───────────────┘
            │
            │
            ▼
    ┌───────────────┐
    │   ApiToken    │
    │  (GUID: tok_) │
    └───────────────┘

Legend:
- All entities below Team have team_id FK
- User belongs to exactly one Team
- ApiToken belongs to User and Team (team_id denormalized)
- Collection, Event, and all other entities belong to Team
```

---

## GUID Service Updates

The GuidService in `backend/src/services/guid.py` needs to be updated with new entity prefixes:

```python
ENTITY_PREFIXES = {
    # Existing
    "col": "Collection",
    "con": "Connector",
    "pip": "Pipeline",
    "res": "AnalysisResult",
    "job": "Job",
    "imp": "ImportSession",
    "evt": "Event",
    "ser": "EventSeries",
    "cat": "Category",
    "loc": "Location",
    "org": "Organizer",
    "prf": "Performer",

    # New for this feature
    "ten": "Team",
    "usr": "User",
    "tok": "ApiToken",
}
```

---

## Validation Rules

### Team Validation
- `name`: 1-255 characters, unique
- `slug`: auto-generated, 1-100 characters, unique, URL-safe (lowercase alphanumeric + hyphens)

### User Validation
- `email`: valid email format, globally unique across all teams
- `first_name`, `last_name`: 1-100 characters each (optional)
- `display_name`: 1-255 characters (optional)
- `picture_url`: valid URL format, 1-1024 characters (optional)
- `status`: must be valid UserStatus enum value

### ApiToken Validation
- `name`: 1-100 characters (user-provided description)
- `expires_at`: must be in the future at creation time
- `scopes_json`: valid JSON array (v1: only `["*"]` supported)

---

## Super Admin Configuration

Super admin status is determined by email hash, not stored in the database:

```python
# backend/src/config/super_admins.py
import hashlib

# SHA-256 hashed email addresses
SUPER_ADMIN_EMAIL_HASHES = {
    # Add hashes for super admin emails
    # hashlib.sha256("admin@example.com".lower().encode()).hexdigest()
}

def is_super_admin(email: str) -> bool:
    """Check if email belongs to a super admin."""
    normalized = email.lower().strip()
    email_hash = hashlib.sha256(normalized.encode()).hexdigest()
    return email_hash in SUPER_ADMIN_EMAIL_HASHES
```

**Rationale**: No database table needed, changes require deployment (acceptable security measure), hashing prevents email disclosure if code is compromised.
