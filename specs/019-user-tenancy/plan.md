# Implementation Plan: Teams/Tenants and User Management with Authentication

**Branch**: `019-user-tenancy` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-user-tenancy/spec.md`
**Related**: [PRD: User Management and Multi-Tenancy](../../docs/prd/019-user-tenancy.md)

## Summary

Transform photo-admin from a single-user localhost application into a secure, multi-tenant platform with OAuth-only authentication (Google, Microsoft). Implementation adds Team-based tenancy with complete data isolation, User management with pre-provisioning, and API token authentication for programmatic access. The top header will be wired to display authenticated user profile information (picture, email) with logout capability.

**Technical Approach**: Leverage existing GuidMixin pattern for new Team, User, and ApiToken entities. Add authentication middleware using Authlib for OAuth 2.0 + PKCE flow. Implement tenant isolation via service layer filtering (team_id injection on all queries). Create React AuthContext for frontend session management with protected routes.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, Authlib (OAuth), PyJWT, React 18.3.1, shadcn/ui, Tailwind CSS 4.x
**Storage**: PostgreSQL 12+ with JSONB columns (SQLite for tests)
**Testing**: pytest (Backend), Vitest (Frontend) - target >80% backend, >75% frontend coverage
**Target Platform**: Linux server (production), macOS/Windows (development)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: OAuth login <2s (excluding provider), API token validation <50ms, session validation <100ms
**Constraints**: Session duration 24h sliding, API token default expiration 90 days, rate limiting 10 failed logins/IP/hour
**Scale/Scope**: Multi-team deployment, ~10-50 users per team typical, all existing data tables require team_id migration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a web application feature, not a CLI tool. However, a seeding CLI script (`seed_first_team`) will be created as a standalone Python script following CLI standards.
- [x] **Testing & Quality**: Tests planned with pytest (backend) and Vitest (frontend). Coverage targets: >80% backend auth modules, >75% frontend auth components. Integration tests for complete OAuth flow.
- [x] **User-Centric Design**:
  - N/A - Not an analysis tool (no HTML report generation required)
  - Clear error messages for auth failures: "Contact your administrator", "Account inactive", "Team inactive"
  - YAGNI: No RBAC in v1, no custom OAuth providers, no MFA implementation (rely on OAuth provider)
  - Structured logging: Auth events, super admin actions, failed login attempts logged for audit
- [x] **Shared Infrastructure**: Uses existing GuidMixin pattern, follows established service/API patterns, session stored in HTTP-only cookies (standard mechanism)
- [x] **Simplicity**:
  - OAuth-only (no custom auth to maintain)
  - Pre-provisioned users only (no self-registration complexity)
  - Super admin via hashed email list (no admin tables needed)
  - Tenant filtering at service layer (not database RLS for simplicity)
- [x] **Global Unique Identifiers (GUIDs)**: New entities (Team, User, ApiToken) will use GuidMixin with prefixes `ten_`, `usr_`, `tok_`
- [x] **Single Title Pattern**: Login page and user management pages will follow TopHeader pattern (Issue #67)
- [x] **TopHeader KPI Pattern**: Users page will display user stats (total, active, pending) in header (Issue #37)

**Violations/Exceptions**: None - all principles can be followed.

## Project Structure

### Documentation (this feature)

```text
specs/019-user-tenancy/
├── plan.md              # This file
├── research.md          # Phase 0: OAuth library selection, session strategy
├── data-model.md        # Phase 1: Team, User, ApiToken entities
├── quickstart.md        # Phase 1: Development setup guide
├── contracts/           # Phase 1: API contract definitions
│   ├── auth-api.yaml    # OAuth endpoints
│   ├── users-api.yaml   # User management endpoints
│   ├── teams-api.yaml   # Team management endpoints (super admin)
│   └── tokens-api.yaml  # API token endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── team.py              # New: Team entity
│   │   ├── user.py              # New: User entity
│   │   └── api_token.py         # New: ApiToken entity
│   ├── services/
│   │   ├── auth_service.py      # New: OAuth flow, session management
│   │   ├── user_service.py      # New: User CRUD, pre-provisioning
│   │   ├── team_service.py      # New: Team CRUD (super admin)
│   │   └── token_service.py     # New: API token generation/validation
│   ├── api/
│   │   ├── auth.py              # New: /auth/* endpoints
│   │   ├── users.py             # New: /api/users/* endpoints
│   │   ├── admin/
│   │   │   └── teams.py         # New: /api/admin/teams/* endpoints
│   │   └── tokens.py            # New: /api/tokens/* endpoints
│   ├── middleware/
│   │   ├── auth.py              # New: Authentication middleware
│   │   └── tenant.py            # New: Tenant context injection
│   ├── config/
│   │   └── super_admins.py      # New: Hashed super admin emails
│   └── scripts/
│       └── seed_first_team.py   # New: CLI seeding script
├── tests/
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   ├── test_user_service.py
│   │   ├── test_team_service.py
│   │   └── test_token_service.py
│   └── integration/
│       ├── test_oauth_flow.py
│       ├── test_tenant_isolation.py
│       └── test_user_management.py
└── db/
    └── migrations/versions/
        ├── 025_create_teams_table.py
        ├── 026_create_users_table.py
        ├── 027_create_api_tokens_table.py
        └── 028_add_team_id_to_existing_tables.py

frontend/
├── src/
│   ├── contexts/
│   │   └── AuthContext.tsx      # New: Authentication state
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx    # New: OAuth login page
│   │   │   ├── OAuthButton.tsx  # New: Provider login buttons
│   │   │   └── ProtectedRoute.tsx # New: Route guard
│   │   └── layout/
│   │       └── TopHeader.tsx    # Modified: Wire to user session
│   ├── pages/
│   │   ├── ProfilePage.tsx      # New: User profile view
│   │   └── settings/
│   │       ├── UsersTab.tsx     # New: User management
│   │       ├── TeamsTab.tsx     # New: Team management (super admin)
│   │       └── ApiTokensTab.tsx # New: API token management
│   ├── hooks/
│   │   ├── useAuth.ts           # New: Auth context hook
│   │   └── useUsers.ts          # New: User management hook
│   └── services/
│       └── auth-api.ts          # New: Auth API client
└── tests/
    └── components/
        ├── LoginPage.test.tsx
        ├── ProtectedRoute.test.tsx
        └── TopHeader.test.tsx
```

**Structure Decision**: Using existing web application structure with `backend/` and `frontend/` directories. New models, services, and API routes follow established patterns. Authentication middleware added to `middleware/` directory. Super admin endpoints placed under `api/admin/` for clear separation.

## Complexity Tracking

> No violations identified - all principles can be followed.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Tenant filtering | Service layer (not RLS) | Simpler to implement/debug, RLS can be added later as defense-in-depth |
| Super admin | Hashed email list in code | No separate admin table needed, changes require deployment (acceptable for v1) |
| OAuth library | Authlib | Battle-tested, supports Google + Microsoft, handles PKCE |
| Session storage | HTTP-only cookie | Industry standard, simpler than server-side session store |
