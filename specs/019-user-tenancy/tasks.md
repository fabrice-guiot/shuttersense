# Tasks: Teams/Tenants and User Management with Authentication

**Input**: Design documents from `/specs/019-user-tenancy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as this is a security-critical feature (authentication, authorization, tenant isolation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- **Migrations**: `backend/src/db/migrations/versions/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and configuration

- [x] T001 Add authentication dependencies to backend/requirements.txt (authlib>=1.6.0, itsdangerous>=2.2.0, python-jose[cryptography]>=3.3.0)
- [x] T002 [P] Create OAuth configuration schema in backend/src/config/oauth.py with Google/Microsoft settings
- [x] T003 [P] Create super admin configuration in backend/src/config/super_admins.py with hashed email list and is_super_admin() function
- [x] T004 [P] Create session configuration in backend/src/config/session.py with SessionMiddleware settings
- [x] T005 [P] Add environment variables to backend/.env.example (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, SESSION_SECRET_KEY, JWT_SECRET_KEY)
- [x] T006 Update GuidService with new prefixes (ten, usr, tok) in backend/src/services/guid.py

---

## Phase 2: Foundational (Database & Core Models)

**Purpose**: Database schema and core models that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Migrations

- [x] T007 Create migration 025_create_teams_table.py in backend/src/db/migrations/versions/
- [x] T008 Create migration 026_create_users_table.py in backend/src/db/migrations/versions/
- [x] T009 Create migration 027_create_api_tokens_table.py in backend/src/db/migrations/versions/
- [x] T010 Create migration 028_add_team_id_to_existing_tables.py (add nullable team_id to collections, connectors, pipelines, analysis_results, events, event_series, categories, locations, organizers, performers) in backend/src/db/migrations/versions/

### Core Models

- [x] T011 [P] Create Team model with GuidMixin (GUID_PREFIX='ten') in backend/src/models/team.py
- [x] T012 [P] Create UserStatus enum and User model with GuidMixin (GUID_PREFIX='usr') in backend/src/models/user.py
- [x] T013 [P] Create ApiToken model with GuidMixin (GUID_PREFIX='tok') in backend/src/models/api_token.py
- [x] T014 Update backend/src/models/__init__.py to export Team, User, ApiToken, UserStatus

### Middleware Infrastructure

- [x] T015 Create TenantContext dataclass in backend/src/middleware/tenant.py
- [x] T016 Create get_tenant_context FastAPI dependency in backend/src/middleware/tenant.py
- [x] T017 [P] Add SessionMiddleware to FastAPI app in backend/src/main.py

**Checkpoint**: Foundation ready - all models created, migrations applied, session middleware configured

---

## Phase 3: User Story 8 - First Team Seeding (Priority: P1) 🎯 MVP

**Goal**: Enable first team and admin user creation for deployment bootstrap

**Independent Test**: Run seed script with team name and admin email, verify team and user created with correct GUIDs output

**Why First**: Without seeding, no users exist and auth cannot be tested. This is the bootstrap mechanism.

### Tests for User Story 8

- [x] T018 [P] [US8] Unit test for TeamService.create() in backend/tests/unit/test_team_service.py
- [x] T019 [P] [US8] Unit test for UserService.create() in backend/tests/unit/test_user_service.py
- [x] T020 [P] [US8] Integration test for seed_first_team script idempotency in backend/tests/integration/test_seed_script.py

### Implementation for User Story 8

- [x] T021 [US8] Create TeamService with create(), get_by_guid(), generate_slug() methods in backend/src/services/team_service.py
- [x] T022 [US8] Create UserService with create(), get_by_email(), get_by_guid() methods in backend/src/services/user_service.py
- [x] T023 [US8] Create seed_first_team.py CLI script with argparse (--team-name, --admin-email, --help) in backend/src/scripts/seed_first_team.py
- [x] T024 [US8] Add graceful CTRL+C handling and idempotency check to seed script

**Checkpoint**: Seed script creates first team and admin user. Can run `python -m backend.src.scripts.seed_first_team --team-name "Test" --admin-email "admin@test.com"`

---

## Phase 4: User Story 1 - OAuth Authentication (Priority: P1)

**Goal**: Enable users to authenticate via Google or Microsoft OAuth

**Independent Test**: Click OAuth login button, complete provider flow, verify redirect to dashboard with session cookie set

**Dependencies**: US8 (need seeded user to test login)

### Tests for User Story 1

- [x] T025 [P] [US1] Unit test for AuthService OAuth callback handling in backend/tests/unit/test_auth_service.py
- [x] T026 [P] [US1] Integration test for complete OAuth flow (mock provider) in backend/tests/integration/test_oauth_flow.py
- [x] T027 [P] [US1] Integration test for login rejection (user not found, inactive user, inactive team) in backend/tests/integration/test_oauth_flow.py

### Implementation for User Story 1

- [x] T028 [US1] Configure Authlib OAuth client with Google provider in backend/src/auth/oauth_client.py
- [x] T029 [US1] Configure Authlib OAuth client with Microsoft provider in backend/src/auth/oauth_client.py (includes MicrosoftOAuth2App for multi-tenant issuer handling)
- [x] T030 [US1] Create AuthService with initiate_login(), handle_callback(), create_session(), validate_user() methods in backend/src/services/auth_service.py
- [x] T031 [US1] Create /auth/login endpoint (initiates OAuth flow) in backend/src/api/auth.py
- [x] T032 [US1] Create /auth/callback/{provider} endpoint (handles OAuth callback) in backend/src/api/auth.py
- [x] T033 [US1] Create /auth/me endpoint (returns current user info) in backend/src/api/auth.py
- [x] T034 [US1] Create /auth/logout endpoint (clears session) in backend/src/api/auth.py
- [x] T035 [US1] Update User record with OAuth profile data on login (display_name, picture_url, last_login_at, status→active)
- [x] T036 [US1] Register auth router in backend/src/main.py with /api/auth prefix
- [x] T037 [US1] Add rate limiting for failed login attempts (10/minute/IP) in auth endpoints

### Frontend for User Story 1

- [x] T038 [P] [US1] Create auth-api.ts with login(), logout(), getMe() API client in frontend/src/services/auth.ts
- [x] T039 [P] [US1] Create LoginPage.tsx with Google and Microsoft OAuth buttons in frontend/src/pages/LoginPage.tsx
- [x] T040 [P] [US1] Create OAuthButton.tsx reusable component in frontend/src/components/auth/OAuthButton.tsx
- [x] T041 [US1] Create AuthContext.tsx with user state, isAuthenticated, logout(), refreshSession() in frontend/src/contexts/AuthContext.tsx
- [x] T042 [US1] Create useAuth.ts hook that consumes AuthContext in frontend/src/hooks/useAuth.ts
- [x] T043 [US1] Create ProtectedRoute.tsx that redirects to /login if not authenticated in frontend/src/components/auth/ProtectedRoute.tsx
- [x] T044 [US1] Add /login route to App.tsx (public route)
- [x] T045 [US1] Wrap existing routes with ProtectedRoute in App.tsx
- [x] T046 [US1] Wrap App with AuthProvider in App.tsx (AuthRedirectHandler also added for return URL handling)

**Checkpoint**: User can click "Login with Google", complete OAuth, land on dashboard with valid session. Unauthenticated users redirected to /login.

---

## Phase 5: User Story 2 - Top Header User Integration (Priority: P1)

**Goal**: Display authenticated user's profile in TopHeader with dropdown menu for profile/logout

**Independent Test**: After login, verify TopHeader shows user's email, profile picture (or initials), and dropdown menu works

**Dependencies**: US1 (needs auth to have user session)

### Tests for User Story 2

- [x] T047 [P] [US2] Component test for TopHeader user display in frontend/tests/components/layout/TopHeader.test.tsx
- [x] T048 [P] [US2] Component test for user dropdown menu (View Profile, Logout) in frontend/tests/components/layout/TopHeader.test.tsx

### Implementation for User Story 2

- [x] T049 [US2] Update TopHeader.tsx to consume AuthContext for user data in frontend/src/components/layout/TopHeader.tsx (completed in Phase 4)
- [x] T050 [US2] Replace hardcoded values with user.display_name / user.email from AuthContext (completed in Phase 4)
- [x] T051 [US2] Update avatar to show user.picture_url or generate initials from user name
- [x] T052 [US2] Add user dropdown menu using shadcn/ui DropdownMenu with "View Profile" and "Logout" options
- [x] T053 [US2] Implement logout action that calls auth-api.logout() and redirects to /login (completed in Phase 4)
- [x] T054 [P] [US2] Create ProfilePage.tsx showing user details (name, email, team, super admin badge) in frontend/src/pages/ProfilePage.tsx
- [x] T055 [US2] Add /profile route to App.tsx (protected route)
- [x] T056 [US2] Wire "View Profile" dropdown option to navigate to /profile

**Checkpoint**: GitHub issue #73 complete - TopHeader shows real user data, logout works, profile page accessible

---

## Phase 6: User Story 6 - Data Tenant Isolation (Priority: P1)

**Goal**: Ensure all data queries are scoped to user's team_id

**Independent Test**: Create data in Team A, login as Team B user, verify Team A data not visible; try direct GUID access, verify 404

**Dependencies**: US1 (needs auth for team_id context)

### Tests for User Story 6

- [x] T057 [P] [US6] Integration test for tenant isolation on Collection endpoints in backend/tests/integration/test_tenant_isolation.py
- [x] T058 [P] [US6] Integration test for tenant isolation on Event endpoints in backend/tests/integration/test_tenant_isolation.py
- [x] T059 [P] [US6] Integration test for cross-team GUID access returns 404 (not 403) in backend/tests/integration/test_tenant_isolation.py
- [x] T060 [P] [US6] Integration test for new entities auto-assigned to user's team in backend/tests/integration/test_tenant_isolation.py

### Implementation for User Story 6

- [x] T061 [US6] Create authentication middleware that validates session and injects TenantContext in backend/src/middleware/auth.py
- [x] T062 [US6] Create require_auth FastAPI dependency that returns 401 if not authenticated in backend/src/middleware/auth.py
- [x] T063 [US6] Update CollectionService to accept TenantContext and filter by team_id in backend/src/services/collection_service.py
- [x] T064 [US6] Update ConnectorService to accept TenantContext and filter by team_id in backend/src/services/connector_service.py
- [x] T065 [US6] Update PipelineService to accept TenantContext and filter by team_id in backend/src/services/pipeline_service.py
- [x] T066 [US6] Update EventService to accept TenantContext and filter by team_id in backend/src/services/event_service.py
- [x] T067 [US6] Update CategoryService to accept TenantContext and filter by team_id in backend/src/services/category_service.py
- [x] T068 [US6] Update LocationService to accept TenantContext and filter by team_id in backend/src/services/location_service.py
- [x] T069 [US6] Update OrganizerService to accept TenantContext and filter by team_id in backend/src/services/organizer_service.py
- [x] T070 [US6] Update PerformerService to accept TenantContext and filter by team_id in backend/src/services/performer_service.py
- [x] T071 [US6] Update all API routes to use require_auth dependency and pass TenantContext to services
- [x] T072 [US6] Ensure cross-team GUID access returns None (404) not raises 403 in all get_by_guid methods

**Checkpoint**: All existing data is isolated by team. Cross-team access returns 404. New entities auto-assigned to user's team.

---

## Phase 7: User Story 3 - User Pre-Provisioning (Priority: P2)

**Goal**: Allow team admins to invite users by email before they can login

**Independent Test**: Admin invites user@example.com, user appears as "Pending", user logs in via OAuth, status becomes "Active"

**Dependencies**: US1 (needs auth), US6 (needs tenant isolation)

### Tests for User Story 3

- [x] T073 [P] [US3] Unit test for UserService.invite() with email validation in backend/tests/unit/test_user_service.py
- [x] T074 [P] [US3] Integration test for global email uniqueness (reject duplicate across teams) in backend/tests/integration/test_user_management.py
- [x] T075 [P] [US3] Integration test for pending user activation on first OAuth login in backend/tests/integration/test_user_management.py

### Implementation for User Story 3

- [x] T076 [US3] Add invite() method to UserService with global email uniqueness check in backend/src/services/user_service.py
- [x] T077 [US3] Add delete_pending() method to UserService (only pending users can be deleted) in backend/src/services/user_service.py
- [x] T078 [US3] Create user Pydantic schemas (InviteUserRequest, UserResponse, UserListResponse) in backend/src/schemas/user.py
- [x] T079 [US3] Create POST /api/users endpoint for inviting users in backend/src/api/users.py
- [x] T080 [US3] Create GET /api/users endpoint for listing team users in backend/src/api/users.py
- [x] T081 [US3] Create DELETE /api/users/{guid} endpoint for removing pending users in backend/src/api/users.py
- [x] T082 [US3] Register users router in backend/src/main.py with /api prefix
- [x] T083 [P] [US3] Create useUsers.ts hook with invite(), listUsers(), deleteUser() in frontend/src/hooks/useUsers.ts
- [x] T084 [P] [US3] Create users-api.ts API client in frontend/src/services/users-api.ts

**Checkpoint**: Admin can invite users, pending users appear in list, can delete pending invitations

---

## Phase 8: User Story 4 - User Management (Priority: P2)

**Goal**: Allow team admins to view, deactivate, and reactivate users

**Independent Test**: View user list, deactivate a user, verify they cannot login, reactivate, verify login works again

**Dependencies**: US3 (needs users to manage)

### Tests for User Story 4

- [x] T085 [P] [US4] Unit test for UserService.deactivate() and reactivate() in backend/tests/unit/test_user_service.py
- [x] T086 [P] [US4] Integration test for cannot deactivate self in backend/tests/integration/test_user_management.py
- [x] T087 [P] [US4] Integration test for deactivated user cannot login in backend/tests/integration/test_oauth_flow.py

### Implementation for User Story 4

- [x] T088 [US4] Add deactivate() method to UserService (cannot deactivate self) in backend/src/services/user_service.py
- [x] T089 [US4] Add reactivate() method to UserService in backend/src/services/user_service.py
- [x] T090 [US4] Create POST /api/users/{guid}/deactivate endpoint in backend/src/api/users.py
- [x] T091 [US4] Create POST /api/users/{guid}/reactivate endpoint in backend/src/api/users.py
- [x] T092 [US4] Create GET /api/users/stats endpoint for TopHeader KPIs in backend/src/api/users.py
- [x] T093 [US4] Add deactivateUser(), reactivateUser() to useUsers.ts hook in frontend/src/hooks/useUsers.ts
- [x] T094 [US4] (Modified) Create TeamPage with user list table and action buttons in frontend/src/pages/TeamPage.tsx
- [x] T095 [US4] (Modified) Add Team to user dropdown menu in TopHeader instead of Settings tab
- [x] T096 [US4] Implement TopHeader KPI stats for Team page using useHeaderStats in frontend/src/pages/TeamPage.tsx

**Checkpoint**: User management complete - list users, invite, deactivate, reactivate, delete pending

---

## Phase 9: User Story 5 - Team Management (Priority: P3)

**Goal**: Allow super admins to create and manage teams

**Independent Test**: Super admin sees Teams tab, creates new team with admin, that admin can login to their team

**Dependencies**: US1 (needs auth), US3/US4 (builds on user management)

### Tests for User Story 5

- [x] T097 [P] [US5] Unit test for TeamService.create_with_admin() in backend/tests/unit/test_team_service.py
- [x] T098 [P] [US5] Integration test for super admin authorization (403 for non-super-admin) in backend/tests/integration/test_teams_api.py
- [x] T099 [P] [US5] Integration test for team deactivation blocks all member logins in backend/tests/integration/test_teams_api.py

### Implementation for User Story 5

- [x] T100 [US5] Add list_all(), deactivate(), reactivate() methods to TeamService in backend/src/services/team_service.py (methods already existed)
- [x] T101 [US5] Add create_with_admin() method to TeamService (creates team + pending admin user) in backend/src/services/team_service.py
- [x] T102 [US5] Create require_super_admin FastAPI dependency using is_super_admin() in backend/src/middleware/auth.py (already existed)
- [x] T103 [US5] Create team Pydantic schemas (CreateTeamRequest, TeamResponse, TeamListResponse, TeamStatsResponse) in backend/src/schemas/team.py
- [x] T104 [US5] Create backend/src/api/admin/__init__.py for admin routes module
- [x] T105 [US5] Create GET /api/admin/teams endpoint (list all teams) in backend/src/api/admin/teams.py
- [x] T106 [US5] Create POST /api/admin/teams endpoint (create team) in backend/src/api/admin/teams.py
- [x] T107 [US5] Create POST /api/admin/teams/{guid}/deactivate endpoint in backend/src/api/admin/teams.py
- [x] T108 [US5] Create POST /api/admin/teams/{guid}/reactivate endpoint in backend/src/api/admin/teams.py
- [x] T109 [US5] Create GET /api/admin/teams/stats endpoint for KPIs in backend/src/api/admin/teams.py
- [x] T110 [US5] Register admin teams router in backend/src/main.py with /api/admin prefix
- [x] T111 [P] [US5] Create teams-api.ts API client for admin endpoints in frontend/src/services/teams-api.ts
- [x] T112 [P] [US5] Create useTeams.ts hook with createTeam(), listTeams(), deactivateTeam(), reactivateTeam() in frontend/src/hooks/useTeams.ts
- [x] T113 [US5] Create TeamsTab.tsx with team list and actions (super admin only) in frontend/src/components/settings/TeamsTab.tsx
- [x] T114 [US5] Add TeamsTab to Settings page (conditionally visible for super admin with badge) in frontend/src/pages/SettingsPage.tsx
- [x] T115 [US5] Update AuthContext to expose isSuperAdmin flag in frontend/src/contexts/AuthContext.tsx (useIsSuperAdmin hook already existed)

**Checkpoint**: Super admins can create teams, deactivate/reactivate teams. Regular users don't see Teams tab.

---

## Phase 10: User Story 7 - API Token Authentication (Priority: P3)

**Goal**: Allow users to generate JWT API tokens for programmatic access via System Users

**Independent Test**: Generate token, use it with curl/httpie, verify API returns team-scoped data

**Dependencies**: US6 (needs tenant isolation for token scoping)

**Security Requirements**:
- API tokens MUST NOT grant access to super admin endpoints (`/api/admin/*`)
- API tokens are associated with System Users (not human users) to avoid breakage when humans are deactivated
- System Users cannot log in via OAuth and cannot be managed via user management UI

### System User Model Changes

- [x] T116a [US7] Add UserType enum (human, system) to backend/src/models/user.py
- [x] T116b [US7] Update ApiToken model with system_user_id (FK to system user) and created_by_user_id (FK to human creator) in backend/src/models/api_token.py
- [x] T116c [US7] Block system users from OAuth login in backend/src/services/auth_service.py (reject if user_type=system)
- [x] T116d [US7] Filter system users from user management UI - update GET /api/users to exclude user_type=system in backend/src/api/users.py
- [x] T116e [US7] Create migration 030_add_user_type_and_update_api_tokens.py for UserType enum and ApiToken FK changes

### Tests for User Story 7

- [x] T117 [P] [US7] Unit test for TokenService.generate() and validate() in backend/tests/unit/test_token_service.py
- [x] T118 [P] [US7] Integration test for Bearer token authentication in backend/tests/integration/test_api_tokens.py
- [x] T119 [P] [US7] Integration test for token revocation in backend/tests/integration/test_api_tokens.py
- [x] T120 [P] [US7] Integration test for expired token rejection in backend/tests/integration/test_api_tokens.py
- [x] T121 [P] [US7] Integration test for API token CANNOT access /api/admin/* endpoints in backend/tests/integration/test_api_tokens.py
- [x] T122 [P] [US7] Integration test for system user cannot OAuth login in backend/tests/integration/test_api_tokens.py

### Implementation for User Story 7

- [x] T123 [US7] Create TokenService with generate(), validate(), revoke(), list_tokens() methods in backend/src/services/token_service.py (generate creates system user + token atomically)
- [x] T124 [US7] Create token Pydantic schemas (CreateTokenRequest, TokenResponse, TokenCreatedResponse, TokenListResponse) in backend/src/schemas/token.py
- [x] T125 [US7] Create GET /api/tokens endpoint (list current user's tokens) in backend/src/api/tokens.py
- [x] T126 [US7] Create POST /api/tokens endpoint (generate new token, return full token once) in backend/src/api/tokens.py
- [x] T127 [US7] Create DELETE /api/tokens/{guid} endpoint (revoke token and deactivate system user) in backend/src/api/tokens.py
- [x] T128 [US7] Create POST /api/tokens/validate endpoint for testing tokens in backend/src/api/tokens.py
- [x] T129 [US7] Register tokens router in backend/src/main.py with /api prefix
- [x] T130 [US7] Update _authenticate_api_token() in backend/src/middleware/tenant.py to validate JWT and return TenantContext with is_api_token=True and is_super_admin=False (always)
- [x] T131 [US7] Update require_super_admin() in backend/src/middleware/tenant.py to reject API token auth (check is_api_token and return 403 "API tokens cannot access admin endpoints")
- [x] T132 [P] [US7] Create tokens-api.ts API client in frontend/src/services/tokens-api.ts
- [x] T133 [P] [US7] Create useTokens.ts hook with generateToken(), listTokens(), revokeToken() in frontend/src/hooks/useTokens.ts
- [x] T134 [US7] Create ApiTokensTab.tsx with token list and generate button (copy-to-clipboard) in frontend/src/components/settings/ApiTokensTab.tsx
- [x] T135 [US7] Add ApiTokensTab to Settings page in frontend/src/pages/SettingsPage.tsx
- [x] T135b [US7] Add Bearer token security scheme to OpenAPI spec for /docs and /redoc in backend/src/main.py

**Checkpoint**: Users can generate API tokens, use them for programmatic access, revoke tokens. API tokens cannot access admin endpoints. System users are invisible in user management. OpenAPI docs show Authorize button for testing with API tokens.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, cleanup, and validation

### Migration Finalization

- [x] T136 Create migration 031_populate_team_id_and_enforce_not_null.py (populate existing data with default team, add NOT NULL constraint) in backend/src/db/migrations/versions/

### Documentation & Validation

- [x] T136b Update constitution.md (v1.5.0) with Core Principle V: Multi-Tenancy and Authentication in .specify/memory/constitution.md
- [x] T136c Update CLAUDE.md with Architecture Principle 6: Multi-Tenancy and Authentication requirements
- [x] T137 [P] Update backend/src/schemas/__init__.py to export all new schemas
- [x] T138 [P] Add structured logging for auth events (login success/failure, logout) in backend/src/services/auth_service.py
- [x] T139 [P] Add structured logging for super admin actions in backend/src/api/admin/teams.py
- [x] T140 [P] Update frontend/src/services/api.ts to handle 401 responses and redirect to login
- [x] T141 Run quickstart.md validation - verify all setup steps work end-to-end (fixed OAuth callback URLs)
- [x] T142 Run full test suite and verify >80% backend coverage (1403 tests pass)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **US8 Seeding (Phase 3)**: Depends on Foundational - bootstrap mechanism
- **US1 OAuth (Phase 4)**: Depends on US8 (needs user to test login)
- **US2 TopHeader (Phase 5)**: Depends on US1 (needs session data)
- **US6 Tenant Isolation (Phase 6)**: Depends on US1 (needs auth middleware)
- **US3 Pre-Provisioning (Phase 7)**: Depends on US1, US6
- **US4 User Management (Phase 8)**: Depends on US3
- **US5 Team Management (Phase 9)**: Depends on US1, US3, US4
- **US7 API Tokens (Phase 10)**: Depends on US6
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies (Summary)

```
US8 (Seeding) ← Foundation
     ↓
US1 (OAuth Auth) ← needs seeded user
     ↓
     ├──→ US2 (TopHeader) ← needs session
     │
     └──→ US6 (Tenant Isolation) ← needs auth middleware
              ↓
              ├──→ US3 (Pre-Provision) ← needs tenant context
              │         ↓
              │    US4 (User Mgmt) ← builds on US3
              │         ↓
              │    US5 (Team Mgmt) ← builds on US3/US4
              │
              └──→ US7 (API Tokens) ← needs tenant isolation
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All tasks marked [P] can run in parallel (different files, no dependencies)
- After US1 complete: US2, US6 can start in parallel
- After US6 complete: US3, US7 can start in parallel

---

## Parallel Example: Phase 2 Foundation

```bash
# Launch all migrations in sequence (dependencies):
T007: Create teams migration
T008: Create users migration (depends on teams)
T009: Create api_tokens migration (depends on users)
T010: Add team_id migration (depends on teams)

# Launch all models in parallel [P]:
T011 [P]: Create Team model
T012 [P]: Create User model
T013 [P]: Create ApiToken model

# Then complete remaining:
T014: Update models/__init__.py
T015-T17: Middleware setup
```

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests in parallel [P]:
T025 [P] [US1]: Unit test for AuthService
T026 [P] [US1]: Integration test for OAuth flow
T027 [P] [US1]: Integration test for login rejection
```

---

## Implementation Strategy

### MVP First (P1 User Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US8 - Seeding (bootstrap)
4. Complete Phase 4: US1 - OAuth Auth
5. Complete Phase 5: US2 - TopHeader Integration (GitHub issue #73)
6. Complete Phase 6: US6 - Tenant Isolation
7. **STOP and VALIDATE**: Test all P1 stories independently
8. Deploy/demo if ready - **This is the MVP!**

### Incremental Delivery

1. **MVP**: Setup + Foundation + US8 + US1 + US2 + US6 → OAuth login, TopHeader wired, tenant isolation
2. **+P2**: Add US3 + US4 → User pre-provisioning and management
3. **+P3**: Add US5 + US7 → Team management and API tokens
4. Each increment adds value without breaking previous functionality

### Suggested MVP Scope

**Minimum Viable Product (P1 stories only)**:
- Seed first team (US8)
- OAuth login with Google/Microsoft (US1)
- TopHeader shows real user data (US2)
- All data isolated by team (US6)

**Total tasks in MVP**: ~70 tasks (Phases 1-6)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Security-critical: OAuth PKCE, HTTP-only cookies, tenant isolation, 404 for cross-team access
