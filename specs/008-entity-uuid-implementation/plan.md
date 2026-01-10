# Implementation Plan: Entity UUID Implementation

**Branch**: `008-entity-uuid-implementation` | **Date**: 2026-01-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-entity-uuid-implementation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add Universal Unique Identifiers (UUIDv7) to all user-facing entities (Collection, Connector, Pipeline, AnalysisResult) to provide stable, shareable external identifiers for URLs and API integrations. External IDs use Crockford's Base32 encoding with entity-type prefixes (e.g., `col_01HGW2BBG000...`). Numeric auto-increment primary keys are retained internally for database efficiency.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Pydantic v2, React 18.3.1, Axios
**Storage**: PostgreSQL 12+ with JSONB columns (SQLite for tests)
**Testing**: pytest with fixtures, TestClient for API tests
**Target Platform**: Web application (Linux server backend, browser frontend)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: External ID lookups within 10% of numeric ID lookups (SC-002)
**Constraints**: Zero data loss during migration (SC-001), 500ms max for UI copy feedback (SC-004)
**Scale/Scope**: 4 implemented entities (Collection, Connector, Pipeline, AnalysisResult), 12+ planned entities

**New Dependencies Required**:
- Backend: `uuid7` or `edwh-uuid7` (UUIDv7 generation), `base32-crockford` (encoding)
- Frontend: TypeScript utilities for external ID parsing/validation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This feature modifies backend/frontend infrastructure, not CLI tools. CLI tools will inherit UUID support through shared models.
- [x] **Testing & Quality**: Yes - Tests planned for UUID generation, encoding/decoding, API endpoints, migration. pytest already configured with fixtures.
- [x] **User-Centric Design**:
  - N/A for HTML reports (not an analysis tool)
  - Clear error messages for invalid external IDs planned (FR-008, edge cases)
  - Implementation follows YAGNI - only implemented entities get UUIDs now
  - Logging for UUID generation/validation will be added
- [x] **Shared Infrastructure**: N/A for PhotoAdminConfig (this is database schema, not YAML config). Respects existing model patterns.
- [x] **Simplicity**: Yes - Uses existing library patterns (SQLAlchemy, Pydantic), minimal new abstractions, standard encoding library.
- [x] **Frontend UI Standards**: Copy-to-clipboard feature for external IDs (FR-010) follows existing UI patterns.

**Violations/Exceptions**: None identified.

## Project Structure

### Documentation (this feature)

```text
specs/008-entity-uuid-implementation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── external-id-api.yaml  # OpenAPI contract for external ID endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── collection.py      # Add uuid column
│   │   ├── connector.py       # Add uuid column
│   │   ├── pipeline.py        # Add uuid column
│   │   ├── analysis_result.py # Add uuid column
│   │   └── mixins/            # NEW: Shared UUID mixin
│   │       └── external_id.py # ExternalIdMixin class
│   ├── services/
│   │   └── external_id.py     # NEW: UUID generation & encoding service
│   ├── schemas/
│   │   └── external_id.py     # NEW: Pydantic models for external IDs
│   └── api/
│       ├── collections.py     # Update to accept external IDs
│       ├── connectors.py      # Update to accept external IDs
│       └── pipelines.py       # Update to accept external IDs
├── tests/
│   ├── unit/
│   │   ├── test_external_id_service.py  # NEW: UUID generation tests
│   │   └── test_api_external_ids.py     # NEW: API external ID tests
│   └── integration/
│       └── test_external_id_migration.py  # NEW: Migration tests
└── alembic/
    └── versions/
        └── xxx_add_uuid_columns.py  # NEW: Migration script

frontend/
├── src/
│   ├── utils/
│   │   └── externalId.ts      # NEW: External ID parsing/validation
│   ├── components/
│   │   └── ExternalIdBadge.tsx  # NEW: Display & copy external ID
│   ├── types/
│   │   ├── collection.ts      # Add external_id field
│   │   ├── connector.ts       # Add external_id field
│   │   └── pipeline.ts        # Add external_id field
│   ├── hooks/
│   │   └── useClipboard.ts    # NEW or extend: Copy to clipboard
│   └── pages/
│       └── [various]          # Update to use external IDs in URLs
└── tests/
    └── externalId.test.ts     # NEW: External ID utility tests
```

**Structure Decision**: Web application structure (backend + frontend). New files added in existing directories following established patterns. A new `mixins/` directory for reusable model components, and `external_id.py` files for centralized UUID logic.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations identified. The implementation follows existing patterns:
- SQLAlchemy mixin for shared UUID column (standard pattern)
- Service class for UUID generation (matches existing service pattern)
- Pydantic models for validation (matches existing schema pattern)
