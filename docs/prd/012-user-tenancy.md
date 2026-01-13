# PRD: User Management and Multi-Tenancy

**Issue**: TBD
**Status**: Draft
**Created**: 2026-01-13
**Last Updated**: 2026-01-13
**Related Documents**:
- [Domain Model](../domain-model.md) (Section: Multi-Tenancy Model, Planned Entities)
- [007-remote-photos-completion.md](./007-remote-photos-completion.md) (Phase 8: Production Polish)

---

## Executive Summary

This PRD defines the implementation of user management and multi-tenancy for photo-admin, transforming it from a single-user localhost application into a secure, cloud-ready multi-tenant platform. Teams serve as the tenancy boundary, with complete data isolation ensuring that users can only access and modify data within their assigned Team.

### Key Design Decisions

1. **Team-Based Tenancy**: All data in the system, including Configuration, is scoped to exactly one Team
2. **OAuth-Only Authentication**: No local login - all authentication via external providers (Google Workspace, Microsoft, Social)
3. **Pre-Provisioned Users**: Users must exist in the User table before authentication succeeds - no self-registration
4. **Global Email Uniqueness**: Email addresses are unique across ALL teams (the only cross-tenant constraint)
5. **Super Admin Access**: A predefined list of hashed email addresses grants access to Team management
6. **API Authentication**: JWT-based API authentication for programmatic access

---

## Background

### Current State

Photo-admin currently operates as a single-user localhost application with:
- No authentication layer
- No user management
- No data isolation between potential users
- All data accessible to anyone with network access

### Problem Statement

For cloud deployment and multi-user scenarios, the application requires:
1. **Secure Authentication**: External OAuth providers for enterprise-grade security
2. **User Management**: Ability to invite, manage, and deactivate users within a team
3. **Data Isolation**: Complete tenant separation ensuring users only see their team's data
4. **Administrative Control**: Super admin capability for platform management

### Strategic Context

This feature is a prerequisite for:
- Cloud deployment (AWS, GCP, Azure)
- Enterprise adoption (multi-team photography studios)
- SaaS offering potential
- Compliance with data protection regulations (GDPR, CCPA)

---

## Goals

### Primary Goals

1. **Multi-Tenancy**: Implement Team-based data isolation across ALL entities
2. **OAuth Authentication**: Support Google Workspace (primary), Microsoft, and social providers
3. **User Management**: Enable user invitation, profile management, and deactivation within teams
4. **Super Admin**: Provide platform-level Team CRUD for designated administrators
5. **API Security**: JWT-based authentication for API access

### Secondary Goals

1. **Profile Synchronization**: Update user profiles from OAuth provider data
2. **Audit Trail**: Track user actions for security and compliance
3. **Session Management**: Secure session handling with appropriate timeouts
4. **Graceful Degradation**: Clear error messaging for authentication failures

### Non-Goals (v1)

1. **Role-Based Access Control (RBAC)**: All users have equal permissions within their team
2. **Cross-Team Collaboration**: No data sharing between teams
3. **Custom OAuth Providers**: Only Google, Microsoft, and major social platforms
4. **MFA Implementation**: Rely on OAuth provider's MFA capabilities
5. **User Groups/Sub-Teams**: Flat user structure within teams

---

## User Personas

### Primary: Team Administrator (Dana)

- **Current Pain**: Cannot invite team members to collaborate on photo collections
- **Desired Outcome**: Invite photographers to the team, manage their access, deactivate when they leave
- **This PRD Delivers**: User invitation via email, profile viewing, deactivation capability

### Secondary: Team Member (Alex)

- **Current Pain**: Cannot access shared team resources securely
- **Desired Outcome**: Log in with work Google account, see only team data
- **This PRD Delivers**: OAuth login, automatic profile sync, team-scoped data access

### Tertiary: Platform Administrator (Morgan)

- **Current Pain**: Cannot create new teams for onboarding clients
- **Desired Outcome**: Create teams, view team status, manage platform-wide resources
- **This PRD Delivers**: Super Admin tab for Team CRUD operations

---

## User Stories

### User Story 1: OAuth Authentication (Priority: P0 - Critical)

**As** a user
**I want to** authenticate using my Google Workspace or Microsoft account
**So that** I can securely access my team's data without managing another password

**Acceptance Criteria:**
- Login page shows OAuth provider buttons (Google, Microsoft)
- Successful OAuth redirects to application dashboard
- OAuth profile data (name, email, picture) syncs to User record
- Failed authentication shows clear error message
- Unknown email (not pre-provisioned) shows "Contact your administrator" message
- Inactive user or inactive team shows appropriate denial message

**Technical Notes:**
- Use OAuth 2.0 Authorization Code Flow with PKCE
- Store refresh tokens encrypted in database
- Validate email domain for Google Workspace if team requires it

---

### User Story 2: User Pre-Provisioning (Priority: P0 - Critical)

**As** a team administrator
**I want to** invite users by email address before they can log in
**So that** only authorized people can access team data

**Acceptance Criteria:**
- Admin can add user with email, first name, last name
- System validates email uniqueness across ALL teams
- Invited user appears in team's user list as "Pending"
- When user authenticates via OAuth, their status changes to "Active"
- OAuth profile data (picture, display name) updates the User record
- Admin can remove a pending invitation

**Technical Notes:**
- No invitation emails in v1 (admin communicates invitation out-of-band)
- Email uniqueness enforced at database level with unique constraint

---

### User Story 3: User Management (Priority: P1)

**As** a team administrator
**I want to** view and manage users in my team
**So that** I can maintain control over who has access

**Acceptance Criteria:**
- View list of all users in team (active, pending, deactivated)
- View user details (email, name, picture, last login, created date)
- Deactivate user (soft delete - prevents login)
- Reactivate previously deactivated user
- Cannot delete users with associated data (foreign key constraint)
- Cannot deactivate self (prevent lockout)

**Technical Notes:**
- Deactivation sets `is_active=false` on User record
- Deactivated users cannot authenticate (check during OAuth callback)

---

### User Story 4: Team Management - Super Admin (Priority: P1)

**As** a super admin
**I want to** create and manage teams
**So that** I can onboard new clients and manage the platform

**Acceptance Criteria:**
- Super Admin tab visible in Settings only for authorized users
- Tab displays "Super Admin" badge next to "Teams" label
- Create new team with name and initial admin user
- View list of all teams (name, user count, created date, status)
- Deactivate team (prevents all team users from logging in)
- Reactivate team
- Cannot delete teams with data (preserve audit trail)

**Technical Notes:**
- Super Admin authorization via hashed email list in codebase
- Team deactivation cascades login denial to all team members
- Super Admin access logged for audit

---

### User Story 5: Data Tenant Isolation (Priority: P0 - Critical)

**As** a user
**I want to** see only my team's data
**So that** our data remains private and secure

**Acceptance Criteria:**
- All existing entities include `team_id` foreign key
- All API queries automatically filter by current user's team
- URLs with GUIDs from other teams return 404 (not 403, to prevent enumeration)
- Attempting to reference cross-team entities fails validation
- Configuration (Settings) is team-scoped
- Search results limited to team data

**Technical Notes:**
- Implement tenant middleware that injects team_id into all queries
- Add database-level Row Level Security (RLS) as additional safeguard
- Migration adds `team_id` to all existing tables

---

### User Story 6: API Authentication (Priority: P1)

**As** a developer
**I want to** authenticate API requests programmatically
**So that** I can integrate photo-admin with other tools

**Acceptance Criteria:**
- Generate API token from Settings > API section
- Token includes team_id claim for tenant isolation
- API requests authenticated via Bearer token
- Token can be revoked from UI
- Token expiration configurable (default: 90 days)
- Rate limiting applies to API tokens

**Technical Notes:**
- JWT tokens with HS256 signing
- Token stored as hashed value in database
- Consider refresh token pattern for long-lived integrations

---

### User Story 7: First Team Seeding (Priority: P0 - Critical)

**As** a platform deployer
**I want to** seed the first team and admin user
**So that** someone can start using the platform after deployment

**Acceptance Criteria:**
- CLI script creates initial team with specified name
- Script creates initial user with specified email
- Script output shows team GUID and user GUID
- Script is idempotent (safe to run multiple times)
- Script validates email format

**Technical Notes:**
- Script: `python -m backend.scripts.seed_first_team`
- Environment variable or CLI args for team name and admin email
- Optionally add admin email to super admin list

---

## Key Entities

### Team (New Entity)

**GUID Prefix:** `ten_`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(255) | unique, not null | Team display name |
| `slug` | String(100) | unique, not null | URL-safe identifier |
| `is_active` | Boolean | not null, default=true | Team active status |
| `settings_json` | JSONB | nullable | Team-level settings |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification |

**Design Notes:**
- `slug` auto-generated from name, used in URLs if needed in future
- `settings_json` stores team preferences (default timezone, branding, etc.)
- Deactivated teams prevent all member logins

---

### User (New Entity)

**GUID Prefix:** `usr_`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `team_id` | Integer | FK(teams.id), not null | Team membership |
| `email` | String(255) | unique, not null | Login email (global unique) |
| `first_name` | String(100) | nullable | User's first name |
| `last_name` | String(100) | nullable | User's last name |
| `display_name` | String(255) | nullable | Display name (from OAuth or manual) |
| `picture_url` | String(1024) | nullable | Profile picture URL |
| `is_active` | Boolean | not null, default=true | Account active status |
| `status` | Enum | not null, default='pending' | `pending`, `active`, `deactivated` |
| `last_login_at` | DateTime | nullable | Last successful login |
| `oauth_provider` | String(50) | nullable | Last used OAuth provider |
| `oauth_subject` | String(255) | nullable | OAuth subject identifier |
| `preferences_json` | JSONB | nullable | User preferences |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification |

**Design Notes:**
- `email` is globally unique across ALL teams (enforced by database constraint)
- `status` tracks: `pending` (invited, never logged in), `active` (logged in at least once), `deactivated` (admin disabled)
- `is_active` is the functional toggle (false = cannot login)
- `oauth_subject` stores the `sub` claim from OAuth for identity verification

**Status State Machine:**
```
pending ──(first login)──> active
active ──(admin deactivates)──> deactivated
deactivated ──(admin reactivates)──> active
```

---

### ApiToken (New Entity)

**GUID Prefix:** `tok_`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `user_id` | Integer | FK(users.id), not null | Token owner |
| `team_id` | Integer | FK(teams.id), not null | Team scope (denormalized) |
| `name` | String(100) | not null | Token name/description |
| `token_hash` | String(255) | unique, not null | SHA-256 hash of token |
| `token_prefix` | String(10) | not null | First 8 chars for identification |
| `scopes` | JSONB | not null, default='["*"]' | Allowed API scopes |
| `expires_at` | DateTime | not null | Token expiration |
| `last_used_at` | DateTime | nullable | Last API call |
| `is_active` | Boolean | not null, default=true | Token active status |
| `created_at` | DateTime | not null | Creation timestamp |

**Design Notes:**
- Full token shown only once at creation
- `token_prefix` allows users to identify which token is which
- `scopes` prepared for future granular permissions (v1: `["*"]` only)
- Tokens inherit team_id from user for query efficiency

---

### SuperAdmin Configuration (Code-Based)

**Location:** `backend/src/config/super_admins.py`

```python
# SHA-256 hashed email addresses of super admins
# Hash format: sha256(email.lower().strip())
SUPER_ADMIN_EMAIL_HASHES = {
    # Example: hashlib.sha256("admin@example.com".encode()).hexdigest()
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    # Add more hashes as needed
}
```

**Design Notes:**
- Hashed to prevent email disclosure if codebase is compromised
- Requires code deployment to add/remove super admins
- Alternative: environment variable with comma-separated hashes

---

### Existing Entities - Tenant Modification

All existing entities require `team_id` foreign key:

| Entity | Current | After Migration |
|--------|---------|-----------------|
| Collection | No team_id | `team_id` FK, not null |
| Connector | No team_id | `team_id` FK, not null |
| Pipeline | No team_id | `team_id` FK, not null |
| PipelineHistory | No team_id | Inherits from Pipeline |
| AnalysisResult | No team_id | `team_id` FK, not null |
| Configuration | No team_id | `team_id` FK, not null |
| Event | No team_id | `team_id` FK, not null |
| EventSeries | No team_id | `team_id` FK, not null |
| Category | No team_id | `team_id` FK, not null |
| Location | No team_id | `team_id` FK, not null |
| Organizer | No team_id | `team_id` FK, not null |
| Performer | No team_id | `team_id` FK, not null |

**Migration Strategy:**
1. Create Team and User tables
2. Run seed script to create default team
3. Add `team_id` columns as nullable
4. Update all existing records to default team
5. Alter `team_id` to not null
6. Add foreign key constraints and indexes

---

## Requirements

### Functional Requirements

#### FR-100: OAuth Authentication

- **FR-100.1**: Support Google OAuth 2.0 with Authorization Code Flow + PKCE
- **FR-100.2**: Support Microsoft OAuth 2.0 (Azure AD / Microsoft Account)
- **FR-100.3**: Display OAuth provider selection on login page
- **FR-100.4**: Validate user email exists in User table before granting access
- **FR-100.5**: Validate user's team is active before granting access
- **FR-100.6**: Update User record with OAuth profile data on each login
- **FR-100.7**: Store session in secure HTTP-only cookie
- **FR-100.8**: Implement CSRF protection for OAuth flow

#### FR-200: User Management

- **FR-200.1**: Create user with email, first name, last name (status: pending)
- **FR-200.2**: Validate email uniqueness across ALL teams at creation
- **FR-200.3**: Display user list filtered by team_id
- **FR-200.4**: Deactivate user (set is_active=false, status=deactivated)
- **FR-200.5**: Reactivate user (set is_active=true, status=active)
- **FR-200.6**: Prevent self-deactivation
- **FR-200.7**: Track last_login_at on each successful authentication

#### FR-300: Team Management (Super Admin)

- **FR-300.1**: Verify super admin status via hashed email comparison
- **FR-300.2**: Display "Teams" tab in Settings with "Super Admin" badge
- **FR-300.3**: Create team with name and initial admin user email
- **FR-300.4**: Generate team slug from name (lowercase, hyphens, unique)
- **FR-300.5**: List all teams with stats (user count, created date, status)
- **FR-300.6**: Deactivate team (cascades to block all user logins)
- **FR-300.7**: Reactivate team
- **FR-300.8**: Log all super admin actions for audit

#### FR-400: Tenant Isolation

- **FR-400.1**: All API queries MUST filter by authenticated user's team_id
- **FR-400.2**: Cross-team GUID access MUST return 404 (not 403)
- **FR-400.3**: Foreign key references MUST validate same team_id
- **FR-400.4**: Search endpoints MUST scope to team_id
- **FR-400.5**: Configuration endpoints MUST scope to team_id
- **FR-400.6**: File upload endpoints MUST associate with team_id
- **FR-400.7**: WebSocket connections MUST validate team_id

#### FR-500: API Authentication

- **FR-500.1**: Generate JWT token with user_id, team_id, scopes claims
- **FR-500.2**: Token expiration default: 90 days, configurable
- **FR-500.3**: Accept Bearer token in Authorization header
- **FR-500.4**: Validate token signature and expiration
- **FR-500.5**: Revoke token by setting is_active=false
- **FR-500.6**: Display token list with last_used_at and prefix
- **FR-500.7**: Show full token only once at creation (copy-to-clipboard UI)

#### FR-600: First Team Seeding

- **FR-600.1**: CLI script accepts team name and admin email as arguments
- **FR-600.2**: Script creates team with generated slug
- **FR-600.3**: Script creates user with pending status
- **FR-600.4**: Script outputs team GUID and user GUID
- **FR-600.5**: Script is idempotent (skips if team/user exists)
- **FR-600.6**: Script validates email format

---

### Non-Functional Requirements

#### NFR-100: Security

- **NFR-100.1**: OAuth tokens encrypted at rest (Fernet encryption)
- **NFR-100.2**: API tokens stored as SHA-256 hashes only
- **NFR-100.3**: Session cookies: HttpOnly, Secure, SameSite=Strict
- **NFR-100.4**: CSRF tokens on all state-changing operations
- **NFR-100.5**: Rate limiting: 10 failed logins per IP per hour
- **NFR-100.6**: Rate limiting: 1000 API requests per token per hour
- **NFR-100.7**: Super admin actions logged with timestamp and IP

#### NFR-200: Performance

- **NFR-200.1**: Team_id indexed on all tenant-scoped tables
- **NFR-200.2**: User lookup by email indexed
- **NFR-200.3**: Token lookup by hash indexed
- **NFR-200.4**: Login latency < 2 seconds (excluding OAuth provider)
- **NFR-200.5**: API token validation < 50ms

#### NFR-300: Reliability

- **NFR-300.1**: OAuth token refresh handles provider downtime gracefully
- **NFR-300.2**: Session expiration: 24 hours (sliding)
- **NFR-300.3**: Database transaction isolation for user creation
- **NFR-300.4**: Graceful handling of OAuth provider errors

#### NFR-400: Testing

- **NFR-400.1**: Backend test coverage > 80% for auth modules
- **NFR-400.2**: Frontend test coverage > 75% for auth components
- **NFR-400.3**: Integration tests for complete OAuth flow (mocked provider)
- **NFR-400.4**: Tenant isolation tests verify cross-team blocking

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Login Page  │  │  User Mgmt  │  │  Settings (Super Admin) │ │
│  │ (OAuth)     │  │  Page       │  │  Teams Tab              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Auth Middleware                          │   │
│  │  - JWT validation                                         │   │
│  │  - Session cookie validation                               │   │
│  │  - Team ID injection into request context                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │AuthService  │  │ UserService │  │  TeamService            │ │
│  │- OAuth flow │  │ - CRUD      │  │  - CRUD (super admin)   │ │
│  │- JWT issue  │  │ - team scope│  │  - status management    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Tenant Filter (SQLAlchemy Event)          │   │
│  │  - Automatically adds team_id to all queries              │   │
│  │  - Validates cross-team references                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQLAlchemy ORM
┌──────────────────────────▼──────────────────────────────────────┐
│                    PostgreSQL Database                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   teams     │  │   users     │  │  api_tokens             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │    All Existing Tables (with team_id FK added)           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### OAuth Flow

```
┌────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   User     │     │   Frontend   │     │    Backend      │     │ OAuth Provider│
└─────┬──────┘     └──────┬───────┘     └───────┬─────────┘     └──────┬───────┘
      │                   │                     │                      │
      │ 1. Click "Login   │                     │                      │
      │    with Google"   │                     │                      │
      │──────────────────>│                     │                      │
      │                   │                     │                      │
      │                   │ 2. GET /auth/login  │                      │
      │                   │    ?provider=google │                      │
      │                   │────────────────────>│                      │
      │                   │                     │                      │
      │                   │ 3. Redirect URL     │                      │
      │                   │    (with state,     │                      │
      │                   │     code_verifier)  │                      │
      │                   │<────────────────────│                      │
      │                   │                     │                      │
      │ 4. Redirect to    │                     │                      │
      │    OAuth Provider │                     │                      │
      │<──────────────────│                     │                      │
      │                   │                     │                      │
      │ 5. Login at       │                     │                      │
      │    Provider       │                     │                      │
      │──────────────────────────────────────────────────────────────>│
      │                   │                     │                      │
      │ 6. Redirect with  │                     │                      │
      │    auth code      │                     │                      │
      │<──────────────────────────────────────────────────────────────│
      │                   │                     │                      │
      │ 7. GET /auth/     │                     │                      │
      │    callback?code= │                     │                      │
      │──────────────────>│                     │                      │
      │                   │                     │                      │
      │                   │ 8. POST /auth/      │                      │
      │                   │    callback         │                      │
      │                   │────────────────────>│                      │
      │                   │                     │                      │
      │                   │                     │ 9. Exchange code    │
      │                   │                     │    for tokens       │
      │                   │                     │────────────────────>│
      │                   │                     │                      │
      │                   │                     │ 10. Tokens +        │
      │                   │                     │     user info       │
      │                   │                     │<────────────────────│
      │                   │                     │                      │
      │                   │                     │ 11. Validate user   │
      │                   │                     │     exists & active │
      │                   │                     │     team active     │
      │                   │                     │                      │
      │                   │ 12. Set session     │                      │
      │                   │     cookie + redirect│                     │
      │                   │<────────────────────│                      │
      │                   │                     │                      │
      │ 13. Dashboard     │                     │                      │
      │     loaded        │                     │                      │
      │<──────────────────│                     │                      │
```

### Tenant Isolation Implementation

**SQLAlchemy Event-Based Filtering:**

```python
# backend/src/middleware/tenant.py
from sqlalchemy import event
from sqlalchemy.orm import Query

def apply_tenant_filter(query: Query, team_id: int) -> Query:
    """Apply team_id filter to all tenant-scoped models."""
    for entity in query.column_descriptions:
        model = entity.get("entity")
        if model and hasattr(model, "team_id"):
            query = query.filter(model.team_id == team_id)
    return query

# Applied via FastAPI dependency injection
def get_tenant_context(request: Request) -> TenantContext:
    """Extract tenant context from authenticated session."""
    user = request.state.user
    return TenantContext(team_id=user.team_id, user_id=user.id)
```

**Service Layer Pattern:**

```python
# All service methods receive tenant context
class CollectionService:
    def list(self, db: Session, ctx: TenantContext) -> list[Collection]:
        return db.query(Collection).filter(
            Collection.team_id == ctx.team_id
        ).all()

    def get_by_guid(self, db: Session, ctx: TenantContext, guid: str) -> Collection | None:
        collection = db.query(Collection).filter(
            Collection.external_id == parse_guid(guid)
        ).first()

        # Return None (404) if wrong team, not 403
        if collection and collection.team_id != ctx.team_id:
            return None
        return collection
```

### Data Model Updates

**GUID Prefix Registration:**

```python
# backend/src/services/guid.py - Add to ENTITY_PREFIXES
ENTITY_PREFIXES = {
    # ... existing ...
    "ten": "Team",
    "usr": "User",
    "tok": "ApiToken",
}
```

**Database Migration Sequence:**

```sql
-- Migration 1: Create teams table
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    external_id UUID NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    settings_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Migration 2: Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    external_id UUID NOT NULL UNIQUE,
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
    preferences_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_team_id ON users(team_id);
CREATE INDEX idx_users_email ON users(email);

-- Migration 3: Create api_tokens table
CREATE TABLE api_tokens (
    id SERIAL PRIMARY KEY,
    external_id UUID NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    name VARCHAR(100) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    token_prefix VARCHAR(10) NOT NULL,
    scopes JSONB NOT NULL DEFAULT '["*"]',
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_tokens_token_hash ON api_tokens(token_hash);
CREATE INDEX idx_api_tokens_user_id ON api_tokens(user_id);

-- Migration 4: Add team_id to existing tables
-- (Run after seed script creates default team)
ALTER TABLE collections ADD COLUMN team_id INTEGER;
ALTER TABLE connectors ADD COLUMN team_id INTEGER;
ALTER TABLE pipelines ADD COLUMN team_id INTEGER;
ALTER TABLE analysis_results ADD COLUMN team_id INTEGER;
ALTER TABLE configurations ADD COLUMN team_id INTEGER;
ALTER TABLE events ADD COLUMN team_id INTEGER;
ALTER TABLE event_series ADD COLUMN team_id INTEGER;
ALTER TABLE categories ADD COLUMN team_id INTEGER;
ALTER TABLE locations ADD COLUMN team_id INTEGER;
ALTER TABLE organizers ADD COLUMN team_id INTEGER;
ALTER TABLE performers ADD COLUMN team_id INTEGER;

-- Migration 5: Populate team_id with default team (run after seed)
-- UPDATE collections SET team_id = (SELECT id FROM teams LIMIT 1);
-- ... repeat for all tables ...

-- Migration 6: Add NOT NULL and FK constraints
ALTER TABLE collections
    ALTER COLUMN team_id SET NOT NULL,
    ADD CONSTRAINT fk_collections_team FOREIGN KEY (team_id) REFERENCES teams(id);
-- ... repeat for all tables ...

-- Migration 7: Add indexes for tenant queries
CREATE INDEX idx_collections_team_id ON collections(team_id);
CREATE INDEX idx_connectors_team_id ON connectors(team_id);
-- ... repeat for all tables ...
```

### API Endpoints

#### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/login` | Initiate OAuth flow (query: provider) |
| GET | `/auth/callback` | OAuth callback handler |
| POST | `/auth/logout` | Clear session cookie |
| GET | `/auth/me` | Get current user info |
| POST | `/auth/refresh` | Refresh session |

#### User Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List team users |
| POST | `/api/users` | Create/invite user |
| GET | `/api/users/{guid}` | Get user details |
| PATCH | `/api/users/{guid}` | Update user |
| POST | `/api/users/{guid}/deactivate` | Deactivate user |
| POST | `/api/users/{guid}/reactivate` | Reactivate user |
| GET | `/api/users/stats` | User statistics for TopHeader |

#### Team Management Endpoints (Super Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/teams` | List all teams |
| POST | `/api/admin/teams` | Create team |
| GET | `/api/admin/teams/{guid}` | Get team details |
| PATCH | `/api/admin/teams/{guid}` | Update team |
| POST | `/api/admin/teams/{guid}/deactivate` | Deactivate team |
| POST | `/api/admin/teams/{guid}/reactivate` | Reactivate team |

#### API Token Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tokens` | List user's API tokens |
| POST | `/api/tokens` | Create new token |
| DELETE | `/api/tokens/{guid}` | Revoke token |

---

## Implementation Plan

### Phase 1: Foundation (Priority: P0)

**Duration**: 2-3 weeks

**Tasks:**

1. **Database Schema**
   - Create Team model with GuidMixin
   - Create User model with GuidMixin
   - Create ApiToken model with GuidMixin
   - Database migrations for new tables
   - Update ENTITY_PREFIXES in guid.py

2. **Seeding Script**
   - CLI script: `seed_first_team`
   - Create default team
   - Create initial admin user (pending status)
   - Idempotent execution

3. **Tenant Migration**
   - Add team_id to all existing models
   - Migration to add columns (nullable initially)
   - Migration to populate default team_id
   - Migration to add NOT NULL constraints
   - Add indexes for team_id columns

**Checkpoint**: Database ready for multi-tenancy, seed script functional

---

### Phase 2: OAuth Authentication (Priority: P0)

**Duration**: 2-3 weeks

**Tasks:**

1. **Backend OAuth Implementation**
   - AuthService with OAuth 2.0 + PKCE
   - Google OAuth provider
   - Microsoft OAuth provider
   - Session management (secure cookies)
   - User validation (exists, active, team active)
   - Profile sync on login

2. **Frontend Login UI**
   - Login page component
   - OAuth provider buttons
   - Error state handling
   - Redirect after successful login

3. **Auth Middleware**
   - JWT/Session validation
   - Request context injection (user, team_id)
   - Protected route decorator
   - Rate limiting for failed logins

**Checkpoint**: Users can authenticate via Google/Microsoft OAuth

---

### Phase 3: Tenant Isolation (Priority: P0)

**Duration**: 2 weeks

**Tasks:**

1. **Service Layer Updates**
   - Add TenantContext parameter to all services
   - Update all queries to filter by team_id
   - Cross-team GUID access returns 404
   - Foreign key validation (same team)

2. **API Endpoint Updates**
   - Inject TenantContext via dependency
   - Update all existing endpoints
   - Validate team_id on create/update

3. **Testing**
   - Unit tests for tenant filtering
   - Integration tests for cross-team blocking
   - API tests for 404 vs 403 behavior

**Checkpoint**: Complete data isolation between teams

---

### Phase 4: User Management (Priority: P1)

**Duration**: 1-2 weeks

**Tasks:**

1. **Backend User CRUD**
   - UserService implementation
   - Create user (invite) endpoint
   - List users (team-scoped)
   - Deactivate/reactivate endpoints
   - Self-deactivation prevention

2. **Frontend User Management**
   - Users page (Settings section)
   - User list with status badges
   - Invite user dialog
   - Deactivate/reactivate actions
   - TopHeader KPI integration

**Checkpoint**: Team admins can manage users

---

### Phase 5: Super Admin (Priority: P1)

**Duration**: 1-2 weeks

**Tasks:**

1. **Super Admin Authorization**
   - Hashed email list configuration
   - SuperAdmin middleware/decorator
   - Audit logging for admin actions

2. **Backend Team CRUD**
   - TeamService implementation
   - Create team with initial admin
   - List all teams
   - Deactivate/reactivate team

3. **Frontend Super Admin UI**
   - Teams tab in Settings (conditional)
   - "Super Admin" badge styling
   - Team list with stats
   - Create team dialog
   - Deactivate/reactivate actions

**Checkpoint**: Super admins can manage teams

---

### Phase 6: API Authentication (Priority: P1)

**Duration**: 1 week

**Tasks:**

1. **Backend Token Management**
   - ApiTokenService implementation
   - JWT generation with claims
   - Token validation middleware
   - Token revocation

2. **Frontend Token UI**
   - API Tokens section in Settings
   - Create token dialog (show once)
   - Token list with metadata
   - Revoke token action

**Checkpoint**: Users can generate and use API tokens

---

### Phase 7: Polish and Testing (Priority: P1)

**Duration**: 1-2 weeks

**Tasks:**

1. **Security Hardening**
   - CSRF protection verification
   - Rate limiting tuning
   - Input validation review
   - Security header audit

2. **Documentation**
   - API documentation update
   - User guide for authentication
   - Admin guide for team management
   - CLAUDE.md update

3. **Testing Completion**
   - Coverage target verification (>80% backend, >75% frontend)
   - End-to-end flow testing
   - Performance testing
   - Security testing

**Checkpoint**: Production-ready authentication and tenancy

---

## Risks and Mitigation

### Risk 1: OAuth Provider Complexity

- **Impact**: High - Different providers have different quirks
- **Probability**: Medium
- **Mitigation**: Use battle-tested library (Authlib), extensive testing with real providers, fallback error handling

### Risk 2: Migration Data Integrity

- **Impact**: High - Existing data could be orphaned or corrupted
- **Probability**: Low (with careful migration)
- **Mitigation**: Multi-step migration, backup before migration, validation scripts, rollback plan

### Risk 3: Tenant Isolation Leakage

- **Impact**: Critical - Data breach between teams
- **Probability**: Low (with defense in depth)
- **Mitigation**: Service layer filtering, database RLS as backup, extensive testing, security review

### Risk 4: Session Security

- **Impact**: High - Session hijacking possible
- **Probability**: Low (with proper implementation)
- **Mitigation**: Secure cookie settings, CSRF protection, session rotation, audit logging

### Risk 5: Super Admin Abuse

- **Impact**: Medium - Platform-wide impact
- **Probability**: Low (limited admin set)
- **Mitigation**: Audit logging, hashed email list (requires deployment), minimum privilege principle

---

## Open Questions

1. **OAuth Provider Priority**: Should we support additional providers (Apple, GitHub) in v1?
2. **Session Duration**: 24-hour sliding session - is this appropriate for all use cases?
3. **Token Expiration**: 90-day default - should teams be able to customize?
4. **Email Validation**: Should we send verification emails for invited users?
5. **Team Deletion**: Soft delete only, or allow hard delete for empty teams?
6. **User Transfer**: Should users be transferable between teams (future)?
7. **Backup Codes**: Should we provide backup access method if OAuth fails?
8. **IP Allowlisting**: Should teams be able to restrict login to specific IPs?

---

## Testing Strategy

### Unit Tests

- AuthService: OAuth flow, token generation, session management
- UserService: CRUD operations, validation, status transitions
- TeamService: CRUD operations, status cascade
- TenantContext: Filtering, validation

### Integration Tests

- Complete OAuth flow (mocked provider)
- User lifecycle (invite → login → deactivate)
- Cross-team isolation verification
- API token authentication flow

### Security Tests

- SQL injection via user input
- Cross-team GUID access
- Session fixation/hijacking
- CSRF protection verification
- Rate limiting effectiveness

---

## Dependencies

### External Dependencies

- **Authlib**: OAuth 2.0 library for Python
- **PyJWT**: JWT encoding/decoding
- **Google OAuth**: Google Cloud Console credentials
- **Microsoft OAuth**: Azure AD app registration

### Internal Dependencies

- Database infrastructure (PostgreSQL)
- Existing GuidMixin pattern
- Frontend auth context provider (new)
- Backend request context (enhanced)

---

## Appendix

### A. Super Admin Email Hash Generation

```python
import hashlib

def generate_admin_hash(email: str) -> str:
    """Generate SHA-256 hash for super admin email."""
    normalized = email.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()

# Example usage:
# print(generate_admin_hash("admin@example.com"))
```

### B. Environment Variables

```bash
# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440  # 24 hours

# Session Configuration
SESSION_SECRET_KEY=your-session-secret
SESSION_EXPIRE_HOURS=24
```

### C. Related Issues

| Issue | Title | Relevance |
|-------|-------|-----------|
| #42 | Add UUID to every relevant object | GUID standard applies to Team, User, ApiToken |
| #24 | Remote Photo collections persistence | First feature requiring tenant isolation |
| #39 | Calendar Events | Event entities need team_id migration |

### D. Glossary

| Term | Definition |
|------|------------|
| **OAuth** | Open Authorization - delegated access protocol |
| **PKCE** | Proof Key for Code Exchange - OAuth security extension |
| **JWT** | JSON Web Token - compact, signed token format |
| **Tenant** | Isolated data boundary (Team) |
| **GUID** | Global Unique Identifier in format `{prefix}_{base32}` |
| **Super Admin** | Platform administrator with cross-tenant access |

---

## Revision History

- **2026-01-13 (v1.0)**: Initial draft
  - Defined Team and User entities with GUID prefixes
  - Specified OAuth-only authentication approach
  - Detailed tenant isolation requirements
  - Outlined super admin functionality
  - Defined API token authentication
  - Created 7-phase implementation plan
