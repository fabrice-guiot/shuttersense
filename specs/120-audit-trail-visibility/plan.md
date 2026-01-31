# Implementation Plan: Audit Trail Visibility

**Branch**: `120-audit-trail-visibility` | **Date**: 2026-01-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/120-audit-trail-visibility/spec.md`
**PRD**: [docs/prd/120-audit-trail-visibility.md](../../docs/prd/120-audit-trail-visibility.md)

## Summary

Add user attribution to all tenant-scoped entities by tracking who created and last modified each record. Backend: add `created_by_user_id` and `updated_by_user_id` FK columns via an AuditMixin, update service create/update methods to accept `user_id`, add `AuditInfo` to all entity API responses. Frontend: create a reusable `<AuditTrailPopover>` for the "Modified" column in all 11 list views, and an `<AuditTrailSection>` for detail dialogs. Column-level tracking (not a separate audit log table) — simplest approach satisfying all requirements.

## Technical Context

**Language/Version**: Python 3.10+ (backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic (backend); React 18.3.1, shadcn/ui, Radix UI Popover, Tailwind CSS 4.x (frontend)
**Storage**: PostgreSQL 12+ (production), SQLite (tests) — Alembic migrations with dialect-aware code
**Testing**: pytest (backend), frontend component tests
**Target Platform**: Web application (server + browser)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: List API response time increase <10% from adding audit user joins
**Constraints**: Eager-loaded relationships (lazy="joined") to avoid N+1 queries; nullable columns for historical data; backward-compatible API responses
**Scale/Scope**: 17 entity types, 11 list views, 2+ detail dialogs, ~12 services, ~17 route handlers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] **Agent-Only Tool Execution**: N/A — This feature does not involve tool execution or CLI commands. It modifies the web application backend and frontend only.
- [X] **Testing & Quality**: Tests planned for AuditMixin behavior, service user_id attribution, schema serialization, and frontend components. pytest configured for backend.
- [X] **User-Centric Design**:
  - N/A for analysis tools (no HTML reports).
  - Graceful null handling for historical records (display "—").
  - YAGNI: Column-level tracking only, no full audit log table.
  - Structured logging already present in service methods.
- [X] **Global Unique Identifiers (GUIDs)**: AuditUserSummary uses `guid` (usr_xxx) for user identification in API responses. No internal IDs exposed.
- [X] **Multi-Tenancy and Authentication**: All audit columns are on tenant-scoped entities. Attribution uses `ctx.user_id` from TenantContext (already resolves correctly for session, API token, and agent auth).
- [X] **Agent-Only Execution**: Agent-facing endpoints pass `agent.system_user_id` to service methods. No job execution changes.
- [X] **Shared Infrastructure**: N/A — No PhotoAdminConfig or config schema changes.
- [X] **Simplicity**: AuditMixin is the simplest reusable approach for adding 2 columns + 2 relationships to 14 models. Single migration for all tables.

**Violations/Exceptions**: None.

## Project Structure

### Documentation (this feature)

```text
specs/120-audit-trail-visibility/
├── plan.md              # This file
├── research.md          # Phase 0 output — technical decisions
├── data-model.md        # Phase 1 output — AuditMixin, affected entities
├── quickstart.md        # Phase 1 output — integration scenarios
├── contracts/           # Phase 1 output — API and frontend contracts
│   ├── audit-schema.md  # AuditInfo, AuditUserSummary schemas
│   └── frontend-components.md  # Popover, Section component specs
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── mixins/
│   │   │   └── audit.py              # NEW: AuditMixin class
│   │   ├── collection.py             # MODIFIED: Add AuditMixin
│   │   ├── connector.py              # MODIFIED: Add AuditMixin
│   │   ├── pipeline.py               # MODIFIED: Add AuditMixin
│   │   ├── job.py                    # MODIFIED: Add AuditMixin
│   │   ├── analysis_result.py        # MODIFIED: Add AuditMixin
│   │   ├── event.py                  # MODIFIED: Add AuditMixin
│   │   ├── event_series.py           # MODIFIED: Add AuditMixin
│   │   ├── category.py               # MODIFIED: Add AuditMixin
│   │   ├── location.py               # MODIFIED: Add AuditMixin
│   │   ├── organizer.py              # MODIFIED: Add AuditMixin
│   │   ├── performer.py              # MODIFIED: Add AuditMixin
│   │   ├── configuration.py          # MODIFIED: Add AuditMixin
│   │   ├── push_subscription.py      # MODIFIED: Add AuditMixin
│   │   ├── notification.py           # MODIFIED: Add AuditMixin
│   │   ├── agent.py                  # MODIFIED: Add updated_by_user_id
│   │   ├── api_token.py              # MODIFIED: Add updated_by_user_id
│   │   └── agent_registration_token.py  # MODIFIED: Add updated_by_user_id
│   ├── schemas/
│   │   └── audit.py                  # NEW: AuditInfo, AuditUserSummary
│   ├── services/                     # MODIFIED: Add user_id to create/update methods
│   ├── api/                          # MODIFIED: Pass ctx.user_id to services
│   └── db/migrations/versions/
│       └── 058_add_audit_user_columns.py  # NEW: Migration
└── tests/
    └── unit/
        └── test_audit.py             # NEW: Audit attribution tests

frontend/
├── src/
│   ├── contracts/api/
│   │   └── audit-api.ts              # NEW: AuditInfo, AuditUserSummary types
│   ├── components/
│   │   └── ui/
│   │       └── audit-trail-popover.tsx  # NEW: AuditTrailPopover, AuditTrailSection
│   ├── pages/                        # MODIFIED: 11 list views + 2 detail dialogs
│   └── ...
```

**Structure Decision**: Web application structure (backend + frontend). This feature spans both layers: database schema and service layer (backend), UI components and list views (frontend).

## Complexity Tracking

No constitution violations. The AuditMixin is the standard SQLAlchemy mixin pattern already used in the project (GuidMixin). The single migration touching 17 tables is necessary to maintain schema consistency — splitting into per-table migrations would be more complex without benefit.
