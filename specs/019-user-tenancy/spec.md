# Feature Specification: Teams/Tenants and User Management with Authentication

**Feature Branch**: `019-user-tenancy`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "GitHub issue #73 - Add Teams/Tenants and User Management with Authentication"
**Related**: [PRD: User Management and Multi-Tenancy](../../docs/prd/019-user-tenancy.md)

## Overview

Transform the photo-admin application from a single-user localhost application into a secure, cloud-ready multi-tenant platform. Teams serve as the tenancy boundary, with complete data isolation ensuring users can only access data within their assigned Team. All authentication is handled via OAuth providers (Google, Microsoft) with no local login capability.

## User Scenarios & Testing

### User Story 1 - OAuth Authentication (Priority: P1)

As a user, I want to authenticate using my Google Workspace or Microsoft account so that I can securely access my team's data without managing another password.

**Why this priority**: Authentication is the foundation for all other user management features. Without it, users cannot access the system, and no other features can function.

**Independent Test**: Can be fully tested by clicking OAuth login buttons and verifying successful redirect to the dashboard with user profile displayed. Delivers immediate value by enabling secure access to the application.

**Acceptance Scenarios**:

1. **Given** I am on the login page, **When** I click "Login with Google" and complete Google authentication, **Then** I am redirected to the application dashboard with my profile information visible in the top header.

2. **Given** I am on the login page, **When** I click "Login with Microsoft" and complete Microsoft authentication, **Then** I am redirected to the application dashboard with my profile information visible in the top header.

3. **Given** I authenticated via OAuth, **When** the OAuth provider returns my profile picture, **Then** the top header displays my profile picture instead of initials.

4. **Given** I authenticated via OAuth, **When** the OAuth provider returns my email, **Then** the top header displays my email address instead of the hardcoded value.

5. **Given** my email is not pre-provisioned in the system, **When** I attempt to authenticate, **Then** I see a clear message: "Contact your administrator for access."

6. **Given** my account has been deactivated by an admin, **When** I attempt to authenticate, **Then** I see a message indicating my account is inactive.

7. **Given** my team has been deactivated, **When** I attempt to authenticate, **Then** I see a message indicating my team is inactive.

---

### User Story 2 - Top Header User Integration (Priority: P1)

As an authenticated user, I want to see my profile information in the top header and access account actions so that I can manage my session and view my identity.

**Why this priority**: This directly addresses the GitHub issue #73 requirement to wire the top header to user session data. It provides immediate visual feedback of successful authentication.

**Independent Test**: Can be verified by checking the top header displays real user data (email, photo) and profile/logout menu items work correctly.

**Acceptance Scenarios**:

1. **Given** I am logged in, **When** I view the top header, **Then** I see my profile picture (or initials if no picture available) and my email address.

2. **Given** I am logged in, **When** I click on my profile area in the top header, **Then** I see a dropdown menu with "View Profile" and "Logout" options.

3. **Given** I am logged in and click "Logout", **When** the logout completes, **Then** I am redirected to the login page and my session is terminated.

4. **Given** I am logged in and click "View Profile", **When** the profile page loads, **Then** I see my account details (name, email, last login, team).

---

### User Story 3 - User Pre-Provisioning (Priority: P2)

As a team administrator, I want to invite users by email address before they can log in so that only authorized people can access team data.

**Why this priority**: This enables team growth by allowing admins to add new members. It's essential for multi-user scenarios but depends on authentication being in place first.

**Independent Test**: Can be tested by creating a user invitation, then having that user authenticate via OAuth and verify their status changes from "Pending" to "Active."

**Acceptance Scenarios**:

1. **Given** I am a team administrator, **When** I add a new user with email, first name, and last name, **Then** the user appears in the team's user list with "Pending" status.

2. **Given** I invited a user, **When** that user authenticates via OAuth for the first time, **Then** their status automatically changes to "Active" and their OAuth profile data (picture, display name) is synced.

3. **Given** I try to invite a user with an email that exists in ANY team, **When** I submit the form, **Then** I see a validation error indicating the email is already in use.

4. **Given** I invited a user who hasn't logged in yet, **When** I want to cancel the invitation, **Then** I can remove the pending user from the list.

---

### User Story 4 - User Management (Priority: P2)

As a team administrator, I want to view and manage users in my team so that I can maintain control over who has access.

**Why this priority**: Essential for ongoing team management, but only valuable after users can be invited and authenticated.

**Independent Test**: Can be tested by viewing the user list, deactivating a user, and verifying they cannot log in, then reactivating and verifying access is restored.

**Acceptance Scenarios**:

1. **Given** I am a team administrator, **When** I view the Users page, **Then** I see a list of all users in my team showing status (active, pending, deactivated), email, name, and last login.

2. **Given** I select an active user, **When** I click "Deactivate", **Then** the user's status changes to "Deactivated" and they can no longer log in.

3. **Given** I select a deactivated user, **When** I click "Reactivate", **Then** the user's status changes to "Active" and they can log in again.

4. **Given** I am viewing my own user record, **When** I look at available actions, **Then** I do NOT see a "Deactivate" option (cannot deactivate self).

---

### User Story 5 - Team Management (Priority: P3)

As a super admin (platform administrator), I want to create and manage teams so that I can onboard new clients and manage the platform.

**Why this priority**: Only relevant for platform operators, not end users. Teams must exist for users to be assigned, but initial teams can be created via seeding scripts.

**Independent Test**: Can be tested by a super admin creating a new team, adding an initial admin, and verifying that admin can log in and access only their team's data.

**Acceptance Scenarios**:

1. **Given** I am a super admin, **When** I navigate to Settings, **Then** I see a "Teams" tab with a "Super Admin" badge.

2. **Given** I am in the Teams tab, **When** I view the list, **Then** I see all teams in the system with name, user count, created date, and status.

3. **Given** I click "Create Team", **When** I enter a team name and initial admin email, **Then** a new team is created with that admin user in "Pending" status.

4. **Given** I select an active team, **When** I click "Deactivate", **Then** the team is deactivated and ALL team members are blocked from logging in.

5. **Given** I am a regular user (not super admin), **When** I navigate to Settings, **Then** I do NOT see the "Teams" tab.

---

### User Story 6 - Data Tenant Isolation (Priority: P1)

As a user, I want to see only my team's data so that our data remains private and secure from other teams.

**Why this priority**: Critical security requirement that must be enforced from the beginning. Data leakage between teams would be a serious security breach.

**Independent Test**: Can be tested by creating data in Team A, logging in as Team B user, and verifying Team A's data is not visible or accessible via direct URL.

**Acceptance Scenarios**:

1. **Given** I am logged in as a Team A user, **When** I view collections, events, or any other data, **Then** I only see data belonging to Team A.

2. **Given** I know a GUID from Team B's data, **When** I try to access it directly via URL, **Then** I receive a "Not Found" response (404, not 403).

3. **Given** I create a new collection, event, or other entity, **When** it is saved, **Then** it is automatically associated with my team.

4. **Given** I search for data, **When** results are returned, **Then** only my team's data appears in the results.

---

### User Story 7 - API Token Authentication (Priority: P3)

As a developer, I want to authenticate API requests programmatically so that I can integrate photo-admin with other tools.

**Why this priority**: Enables automation and integrations, but most users will use the web UI directly. Lower priority for initial release.

**Independent Test**: Can be tested by generating a token, using it in an API request, and verifying the request succeeds and returns team-scoped data.

**Acceptance Scenarios**:

1. **Given** I am logged in, **When** I go to Settings > API and click "Generate Token", **Then** a new token is created and displayed once (with copy-to-clipboard).

2. **Given** I have an API token, **When** I make an API request with Bearer token authentication, **Then** the request succeeds and returns only my team's data.

3. **Given** I have a token I want to revoke, **When** I click "Revoke" in the token list, **Then** the token is disabled and future requests with it fail.

4. **Given** my API token has expired, **When** I make an API request with it, **Then** I receive an authentication error.

---

### User Story 8 - First Team Seeding (Priority: P1)

As a platform deployer, I want to seed the first team and admin user so that someone can start using the platform after deployment.

**Why this priority**: Critical for initial deployment. Without this, no one can access the system.

**Independent Test**: Can be tested by running the seed script and verifying the team and user are created with correct attributes.

**Acceptance Scenarios**:

1. **Given** a fresh deployment, **When** I run the seed script with team name and admin email, **Then** a team and pending user are created.

2. **Given** I run the seed script, **When** it completes, **Then** I see the team GUID and user GUID in the output.

3. **Given** the team already exists, **When** I run the seed script again with the same data, **Then** it completes without errors (idempotent).

---

### Edge Cases

- What happens when a user's OAuth session expires during active use? System should gracefully redirect to login with a clear message.
- What happens when an OAuth provider is temporarily unavailable? Clear error message with retry option.
- What happens when a user is deactivated while they have an active session? Session should be invalidated on next request.
- What happens when a team is deactivated while users have active sessions? All team sessions should be invalidated.
- What happens when the same email tries to register in multiple teams? Validation prevents this (global email uniqueness).
- What happens when a super admin tries to deactivate the last active team? System should allow it (teams can be reactivated).

## Requirements

### Functional Requirements

#### Authentication

- **FR-001**: System MUST support Google OAuth 2.0 with Authorization Code Flow + PKCE
- **FR-002**: System MUST support Microsoft OAuth 2.0 (Azure AD / Microsoft Account)
- **FR-003**: System MUST display OAuth provider selection on the login page
- **FR-004**: System MUST validate that user email exists in the User table before granting access
- **FR-005**: System MUST validate that user's team is active before granting access
- **FR-006**: System MUST update User record with OAuth profile data (name, email, picture) on each login
- **FR-007**: System MUST store session in secure HTTP-only cookie
- **FR-008**: System MUST implement CSRF protection for OAuth flow

#### Top Header Integration

- **FR-009**: Top header MUST display user's profile picture (from OAuth) when available
- **FR-010**: Top header MUST display user's initials when no profile picture is available
- **FR-011**: Top header MUST display user's email address (from session data)
- **FR-012**: Top header MUST provide dropdown menu with "View Profile" and "Logout" options
- **FR-013**: "Logout" action MUST clear session and redirect to login page

#### User Management

- **FR-014**: System MUST allow admins to create users with email, first name, and last name (status: pending)
- **FR-015**: System MUST validate email uniqueness across ALL teams at user creation
- **FR-016**: System MUST display user list filtered by current user's team
- **FR-017**: System MUST allow deactivation of users (set status to deactivated)
- **FR-018**: System MUST allow reactivation of users (set status to active)
- **FR-019**: System MUST prevent users from deactivating themselves
- **FR-020**: System MUST track last login timestamp on each successful authentication

#### Team Management (Super Admin)

- **FR-021**: System MUST verify super admin status via hashed email comparison
- **FR-022**: System MUST display "Teams" tab in Settings only for super admins (with badge)
- **FR-023**: System MUST allow super admins to create teams with name and initial admin email
- **FR-024**: System MUST generate URL-safe team slug from name
- **FR-025**: System MUST display all teams with user count, created date, and status
- **FR-026**: System MUST allow super admins to deactivate teams (blocks all member logins)
- **FR-027**: System MUST allow super admins to reactivate teams
- **FR-028**: System MUST log all super admin actions for audit

#### Tenant Isolation

- **FR-029**: All API queries MUST filter by authenticated user's team_id
- **FR-030**: Cross-team GUID access MUST return 404 (not 403) to prevent enumeration
- **FR-031**: Foreign key references MUST validate same team_id
- **FR-032**: Search endpoints MUST scope results to team_id
- **FR-033**: All new entities MUST be automatically associated with user's team_id

#### API Authentication

- **FR-034**: System MUST allow users to generate JWT API tokens with team_id claim
- **FR-035**: System MUST allow configurable token expiration (default: 90 days)
- **FR-036**: System MUST accept Bearer token authentication in Authorization header
- **FR-037**: System MUST allow token revocation from UI
- **FR-038**: System MUST show full token only once at creation

#### Seeding

- **FR-039**: CLI script MUST accept team name and admin email as arguments
- **FR-040**: CLI script MUST be idempotent (safe to run multiple times)
- **FR-041**: CLI script MUST output team GUID and user GUID

### Key Entities

- **Team**: Represents a tenancy boundary (organization/company). Has name, slug, active status, and settings. All data in the system belongs to exactly one Team.

- **User**: Represents a person who can access the system. Belongs to exactly one Team. Has email (globally unique), name, profile picture URL, status (pending/active/deactivated), and OAuth provider information.

- **ApiToken**: Represents a programmatic access credential. Belongs to a User and Team. Has hashed token value, expiration, and revocation status.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete OAuth login in under 30 seconds (excluding OAuth provider time)
- **SC-002**: 100% of data queries are automatically scoped to user's team (verified by test suite)
- **SC-003**: Cross-team GUID access returns 404 in 100% of cases (no information leakage)
- **SC-004**: Team administrators can invite and manage users without technical support
- **SC-005**: Super admins can create and manage teams without database access
- **SC-006**: API tokens can be generated and used without additional documentation
- **SC-007**: User profile information (photo, email) displays correctly in top header after login
- **SC-008**: Logout action completes and redirects to login page within 2 seconds

## Assumptions

- OAuth provider credentials (Google, Microsoft) will be configured in environment variables
- Users have existing Google Workspace or Microsoft accounts
- Email addresses are reliable identifiers for users (no shared email accounts)
- Teams are the only tenancy boundary needed (no sub-teams or cross-team sharing in v1)
- Super admin list is managed via code deployment (acceptable for initial release)
- Session duration of 24 hours (sliding) is appropriate for this application
- API token default expiration of 90 days is appropriate
