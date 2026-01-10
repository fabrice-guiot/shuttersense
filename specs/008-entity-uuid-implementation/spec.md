# Feature Specification: Entity UUID Implementation

**Feature Branch**: `008-entity-uuid-implementation`
**Created**: 2026-01-09
**Status**: Draft
**Input**: GitHub Issue #42 - Add UUID to every relevant objects

## Overview

This feature adds Universal Unique Identifiers (UUIDs) to all user-facing entities in the Photo-Admin application. UUIDs provide stable, shareable identifiers for URLs and external integrations while maintaining efficient numeric primary keys internally.

**Why UUIDs?**
- **URL-safe identifiers**: Users can bookmark and share links that remain stable
- **External integration**: Third-party systems can reference entities without exposing internal IDs
- **Security**: Sequential internal IDs cannot be guessed from external identifiers
- **Future-proofing**: Enables distributed systems and cross-database references

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Access Entity via External ID (Priority: P1)

As a user, I want to access any entity (Collection, Connector, Pipeline) using a human-readable external identifier in URLs, so that I can bookmark, share, and reference specific entities reliably.

**Why this priority**: This is the core user-facing value - all other features depend on having external IDs available in URLs and API responses.

**Independent Test**: Can be fully tested by navigating to `/collections/col_01HGW2BBG000000` and verifying the correct collection loads. Delivers immediate value for bookmarking and sharing.

**Acceptance Scenarios**:

1. **Given** a Collection with internal ID 5 and external ID `col_01HGW2BBG0000000000000005`, **When** user navigates to `/collections/col_01HGW2BBG0000000000000005`, **Then** the collection details page loads correctly
2. **Given** a user copies a Collection URL containing the external ID, **When** another user (with appropriate access) opens that URL, **Then** they see the same collection
3. **Given** an invalid external ID format, **When** user navigates to `/collections/invalid_id`, **Then** system displays a clear "not found" message

---

### User Story 2 - API External ID Support (Priority: P1)

As an API consumer, I want to use external IDs in API requests and receive them in responses, so that I can integrate with external systems without exposing internal database IDs.

**Why this priority**: Essential for any external integration and critical for API usability alongside P1 URL support.

**Independent Test**: Can be tested by calling `GET /api/collections/{external_id}` and verifying correct response. Enables external tool integration immediately.

**Acceptance Scenarios**:

1. **Given** a valid external ID, **When** calling `GET /api/collections/{external_id}`, **Then** the API returns the collection with external ID in the response
2. **Given** an API list response, **When** requesting `GET /api/collections`, **Then** each entity includes its external ID in the response
3. **Given** an API create request, **When** a new entity is created via `POST /api/collections`, **Then** the response includes the newly generated external ID

---

### User Story 3 - Display External ID in UI (Priority: P2)

As a user, I want to see and copy the external ID of any entity from its detail page, so that I can reference it in external systems or share it with others.

**Why this priority**: Enhances usability by making external IDs discoverable, but the core URL/API functionality works without this.

**Independent Test**: Can be tested by opening any entity detail page and verifying the external ID is displayed with a copy button.

**Acceptance Scenarios**:

1. **Given** a Collection detail page, **When** user views the page, **Then** the external ID is displayed in a readable format
2. **Given** an external ID displayed on the page, **When** user clicks the copy button, **Then** the external ID is copied to clipboard with confirmation feedback
3. **Given** any entity type (Collection, Connector, Pipeline), **When** viewing its detail page, **Then** the external ID format matches the entity type prefix (col_, con_, pip_)

---

### User Story 4 - Backward Compatibility (Priority: P2)

As an existing user, I want my existing bookmarks and integrations to continue working after the UUID implementation, so that I don't lose access to my data.

**Why this priority**: Critical for user trust but implementation can be phased - existing numeric URLs can temporarily redirect.

**Independent Test**: Can be tested by accessing an entity via the old numeric URL format and verifying it still works or redirects appropriately.

**Acceptance Scenarios**:

1. **Given** an existing numeric URL `/collections/5`, **When** user accesses this URL after UUID implementation, **Then** the request redirects to the new external ID URL or continues to work
2. **Given** an API call using internal ID `GET /api/collections/5`, **When** called during transition period, **Then** the API returns the collection with a deprecation warning header

---

### Edge Cases

- What happens when an external ID prefix doesn't match the endpoint (e.g., `con_xxx` used at `/collections/` endpoint)? System should return a clear error indicating entity type mismatch.
- How does system handle UUIDs for entities that were created before this feature? Migration generates UUIDs for all existing entities at deployment time.
- What happens if UUID generation fails during entity creation? Entity creation fails with appropriate error; no entity is created with a missing UUID.
- How are deleted entities handled - can their external IDs be reused? External IDs are never reused; deleted entity IDs return "not found" permanently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a UUIDv7 for every new user-facing entity at creation time
- **FR-002**: System MUST encode external IDs using Crockford's Base32 format with entity-type prefixes
- **FR-003**: System MUST store the UUID internally as a 16-byte binary field for storage efficiency
- **FR-004**: System MUST maintain numeric auto-increment primary keys for internal database operations
- **FR-005**: System MUST accept external IDs in all API endpoints that reference entities
- **FR-006**: System MUST include external IDs in all API responses that return entities
- **FR-007**: System MUST use external IDs in all user-facing URLs for entity navigation
- **FR-008**: System MUST validate external ID format before processing (correct prefix, valid Base32)
- **FR-009**: System MUST migrate existing entities to have UUIDs upon feature deployment
- **FR-010**: System MUST provide a copy-to-clipboard action for external IDs in entity detail views

### Entity-Prefix Mapping

The following prefixes are defined for each entity type:

| Entity Type     | Prefix | Implemented Status                      |
|-----------------|--------|-----------------------------------------|
| Collection      | `col_` | Implemented                             |
| Connector       | `con_` | Implemented                             |
| Pipeline        | `pip_` | Implemented                             |
| PipelineHistory | N/A    | Internal only (no external ID needed)   |
| AnalysisResult  | `res_` | Implemented                             |
| Configuration   | N/A    | Internal only (no external ID needed)   |
| Event           | `evt_` | Planned                                 |
| User            | `usr_` | Planned                                 |
| Team            | `tea_` | Planned                                 |
| Camera          | `cam_` | Planned                                 |
| Album           | `alb_` | Planned                                 |
| Image           | `img_` | Planned                                 |
| File            | `fil_` | Planned                                 |
| Workflow        | `wfl_` | Planned                                 |
| Location        | `loc_` | Planned                                 |
| Organizer       | `org_` | Planned                                 |
| Performer       | `prf_` | Planned                                 |
| Agent           | `agt_` | Future                                  |

### Key Entities

- **External ID (UUID)**: A unique, immutable identifier for each user-facing entity. Composed of UUIDv7 (time-ordered) encoded as Crockford's Base32 with a 3-4 character entity-type prefix and underscore separator.
  - Example format: `col_01HGW2BBG0000000000000000`
  - Properties: immutable once assigned, globally unique, time-ordered (sortable), human-readable

- **Affected Entities (Current)**: Collection, Connector, Pipeline, AnalysisResult
  - These entities currently exist in the database and will require schema migration

- **Affected Entities (Future)**: Event, User, Team, Camera, Album, Image, File, Workflow, Location, Organizer, Performer, Agent
  - These entities will include UUID fields when implemented

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing entities have UUIDs generated within the migration process, with zero data loss
- **SC-002**: Users can access any entity via its external ID URL with response time comparable to numeric ID access (within 10% difference)
- **SC-003**: All API responses include external IDs for every entity returned
- **SC-004**: External ID copy action works across all supported browsers with visual confirmation within 500ms
- **SC-005**: Invalid external ID requests return appropriate error responses with clear messaging
- **SC-006**: 100% of newly created entities have valid UUIDs immediately available after creation

## Assumptions

- The puidv7-js library (or Python equivalent) will be evaluated and selected during implementation
- UUIDv7 provides sufficient time-ordering for the application's needs (millisecond precision)
- Crockford's Base32 encoding is case-insensitive (both upper and lower case accepted)
- Internal-only entities (Configuration, PipelineHistory) do not require external IDs as they are not user-addressable
- The transition period for backward compatibility with numeric IDs will be determined during implementation planning
