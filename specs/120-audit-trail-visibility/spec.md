# Feature Specification: Audit Trail Visibility

**Feature Branch**: `120-audit-trail-visibility`
**Created**: 2026-01-31
**Status**: Draft
**Input**: GitHub issue #120: Audit Trail Visibility Enhancement
**PRD**: [docs/prd/120-audit-trail-visibility.md](../../docs/prd/120-audit-trail-visibility.md)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Who Last Modified a Record in List Views (Priority: P1)

As a team member viewing any list of records (collections, connectors, events, etc.), I want to see when a record was last modified and by whom, so I can quickly understand recent changes without navigating to a detail view.

A compact "Modified" summary appears in every list view showing a relative time (e.g., "5 min ago"). Hovering over it reveals a popover card with full details: who created the record and when, and who last modified it and when.

**Why this priority**: This is the most frequently accessed audit information. Team members spend most of their time in list views and need at-a-glance attribution to understand team activity.

**Independent Test**: Can be fully tested by viewing any list page and hovering over the "Modified" column to see the audit popover. Delivers immediate accountability visibility for all 11 list views.

**Acceptance Scenarios**:

1. **Given** a list view with records, **When** the user views the table, **Then** a "Modified" column shows relative time (e.g., "5 min ago") for each row.
2. **Given** a record that has been modified, **When** the user hovers over the "Modified" column value, **Then** a popover displays: created date/time with creator name, and modified date/time with modifier name.
3. **Given** a record that has never been modified after creation, **When** the user hovers over the "Modified" column, **Then** only creation details are shown (no separate modified section).
4. **Given** a historical record created before audit tracking was enabled, **When** the user views the audit information, **Then** the user attribution shows "—" instead of a user name, and no errors occur.
5. **Given** the user is on a mobile device, **When** viewing a list in card layout, **Then** the relative time appears as a detail row in the card (no hover required; full audit info is accessible in the detail dialog).

---

### User Story 2 - Track User Attribution on Record Changes (Priority: P1)

As a team admin, I want every creation and modification of team records to automatically record which user performed the action, so I can audit team activity and identify who changed what.

When any user, API token, or agent creates or modifies a record, the system records the acting user's identity on the record itself. This applies to all tenant-scoped entities (collections, connectors, pipelines, jobs, events, categories, locations, organizers, performers, etc.).

**Why this priority**: Without backend attribution, the frontend display (User Story 1) has nothing to show. This is the foundational data requirement.

**Independent Test**: Can be tested by creating or updating a record via the web UI or API and verifying the acting user is recorded on the entity. Delivers the core audit data regardless of frontend presentation.

**Acceptance Scenarios**:

1. **Given** a logged-in user creates a new record, **When** the record is saved, **Then** the record stores the creating user's identity and the creation timestamp.
2. **Given** a logged-in user modifies an existing record, **When** the change is saved, **Then** the record's "last modified by" is updated to the current user, while the original creator remains unchanged.
3. **Given** an API token is used to create or modify a record, **When** the action is performed, **Then** the record attributes the change to the API token's associated system user (distinguishable from human users).
4. **Given** an agent completes a job or modifies a record, **When** the result is stored, **Then** the record attributes the change to the agent's associated system user.
5. **Given** a user is deleted from the system, **When** viewing records they previously created or modified, **Then** the attribution is cleared (shown as null/empty) rather than blocking the deletion.

---

### User Story 3 - View Full Audit Details in Record Detail Views (Priority: P2)

As a team member viewing a record's detail dialog, I want to see a dedicated audit section showing who created and last modified the record with full timestamps, so I have complete audit context without needing to return to the list view.

An "Audit" section at the bottom of detail dialogs displays: creation date/time and creator, modification date/time and modifier, in a clear inline format without requiring hover interaction.

**Why this priority**: Detail dialogs provide the complete context for a single record. Audit info here complements the list view summary and is essential for thorough investigation.

**Independent Test**: Can be tested by opening any record's detail dialog and verifying the audit section displays complete creation and modification attribution.

**Acceptance Scenarios**:

1. **Given** a record detail dialog is opened, **When** the dialog renders, **Then** an audit section at the bottom shows "Created [date/time] by [user]" and "Modified [date/time] by [user]".
2. **Given** a record with no modification after creation, **When** the detail dialog is viewed, **Then** both created and modified show the same timestamp and user.
3. **Given** a historical record without user attribution, **When** the detail dialog is viewed, **Then** timestamps are shown but user names display "—" instead of a name.

---

### User Story 4 - Receive Audit Data in API Responses (Priority: P2)

As a developer consuming the ShutterSense API (via API tokens), I want entity responses to include structured audit information, so I can programmatically access who created or modified records.

All entity API responses include an `audit` object containing creation and modification timestamps along with user summary information (identifier, display name, email).

**Why this priority**: API consumers need the same audit visibility as UI users. Structured audit data in responses enables downstream integrations and reporting.

**Independent Test**: Can be tested by making API requests to any entity endpoint and verifying the response includes the `audit` field with user attribution data.

**Acceptance Scenarios**:

1. **Given** an API request to any entity endpoint, **When** the response is returned, **Then** it includes an `audit` object with `created_at`, `created_by`, `updated_at`, and `updated_by` fields.
2. **Given** a record with user attribution, **When** the API response is returned, **Then** `created_by` and `updated_by` contain user summary (identifier, display name, email).
3. **Given** a historical record without attribution, **When** the API response is returned, **Then** `created_by` and `updated_by` are null (not errors).
4. **Given** an existing API integration, **When** the new audit field is added, **Then** existing `created_at` and `updated_at` top-level fields remain unchanged for backward compatibility.

---

### Edge Cases

- What happens when viewing records created before audit tracking was enabled? Attribution fields display "—" or null gracefully.
- How does the system handle a deleted user's attribution? The foreign key uses SET NULL, so attribution is cleared rather than blocking user deletion.
- What if an agent has no associated system user? Agent registration must create a system user, ensuring this case cannot occur.
- What happens on mobile where hover is unavailable? The relative time is shown in card layout; full audit details are accessible in the detail dialog.
- What if a record is only created but never updated? The modified timestamp matches the created timestamp, and the popover shows only creation details.
- What about bulk operations? Bulk mutations attribute all changes to the requesting user; individual item-level tracking within a bulk operation is not required.
- What if the API response is consumed before the frontend is updated? The `audit` field is additive and optional; old frontend code ignores it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST record the acting user's identity when any tenant-scoped record is created (`created_by` attribution).
- **FR-002**: System MUST record the acting user's identity when any tenant-scoped record is modified (`updated_by` attribution).
- **FR-003**: System MUST attribute changes made via API tokens to the token's associated system user, using the same mechanism as session-based attribution (no special-casing in the attribution flow).
- **FR-004**: System MUST attribute changes made by agents to the agent's associated system user.
- **FR-005**: System MUST ensure every registered agent has an associated system user before the agent can authenticate and perform actions.
- **FR-006**: System MUST preserve the original creator attribution when a record is subsequently modified (creator never changes after initial creation).
- **FR-007**: System MUST clear user attribution (set to null) when the attributed user is deleted, rather than blocking user deletion.
- **FR-008**: System MUST include structured audit information (creation/modification timestamps and user summaries) in all entity API responses.
- **FR-009**: System MUST retain existing top-level `created_at` and `updated_at` fields in API responses for backward compatibility.
- **FR-010**: System MUST display a "Modified" column in all 11 list view tables showing relative time with a hover popover for full audit details.
- **FR-011**: System MUST display an audit trail section in all detail dialogs showing creation and modification details inline.
- **FR-012**: System MUST gracefully handle records without user attribution (historical data) by displaying "—" or null instead of errors.
- **FR-013**: System MUST not introduce additional API calls when users interact with audit information in the UI (all data is included in the entity response).
- **FR-014**: System MUST apply audit tracking to all tenant-scoped entities: collections, connectors, pipelines, jobs, analysis results, events, event series, categories, locations, organizers, performers, configurations, push subscriptions, and notifications.
- **FR-015**: System MUST add modification tracking to entities that already have creation tracking (agents, API tokens, agent registration tokens).
- **FR-016**: User attribution in list views MUST show the user's display name (falling back to email) in the audit popover.

### Key Entities

- **Audit Attribution**: Metadata attached to every tenant-scoped entity recording the creator and last modifier. Contains references to the acting user's identity and timestamps.
- **Audit User Summary**: A minimal representation of a user for audit display purposes, containing the user's identifier, display name, and email.
- **Audit Info**: A structured object combining creation and modification timestamps with their respective user summaries, included in every entity API response.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tenant-scoped entities (17 entity types) have user attribution fields after the database schema update.
- **SC-002**: All new records created after deployment have non-null creator attribution when created by an authenticated user, API token, or agent.
- **SC-003**: All 11 list view tables display the "Modified" column with a working hover popover showing full audit details.
- **SC-004**: All detail dialogs display the audit trail section with creation and modification attribution.
- **SC-005**: API response time for list endpoints increases by no more than 10% compared to pre-implementation baseline.
- **SC-006**: Historical records (created before this feature) display gracefully with "—" for missing user attribution, with zero errors.
- **SC-007**: The audit display uses a single reusable component across all 11 list views, ensuring consistent presentation.

## Assumptions

- The existing `TenantContext` middleware already resolves `user_id` correctly for both session and API token authentication paths.
- API token system users already exist in the data model (`ApiToken.system_user_id`).
- Agent system users already exist or will be created during agent registration (`Agent.system_user_id`).
- The `formatRelativeTime()` and `formatDateTime()` utility functions already exist in the frontend.
- Existing shadcn/ui Popover component is available and configured.
- No data backfill is required for historical records in v1 (null attribution is acceptable).

## Scope Boundaries

### In Scope
- Column-level user attribution (created_by, updated_by) on all tenant-scoped entities
- API response schema additions for audit information
- Frontend audit popover for list views and audit section for detail dialogs
- Database migration for all affected tables

### Out of Scope
- Full audit log table with field-level change history
- Dedicated audit log API endpoint
- Undo/rollback capabilities based on audit trail
- Email notifications when records are modified
- Bulk operation per-item attribution
- Data backfill for historical records
