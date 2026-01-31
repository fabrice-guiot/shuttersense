# Specification Analysis Report: Audit Trail Visibility

**Feature**: 120-audit-trail-visibility
**Date**: 2026-01-31
**Artifacts Analyzed**: spec.md, plan.md, tasks.md, contracts/, data-model.md, quickstart.md
**User Context**: "the plan: it seems low on tests"

---

## Executive Summary

The specification and plan are well-structured with thorough coverage of the feature scope. However, the user's concern is confirmed: **tasks.md has a critical gap in test coverage**. The PRD explicitly requires unit tests (NFR-400.1–400.4), the constitution mandates test coverage (Principle II), the plan references tests in its Constitution Check, and the contracts define test requirements — yet tasks.md contains **zero dedicated test-writing tasks**. Task T090 only runs existing tests and fixes regressions; it does not create any new tests.

**Verdict**: Tasks must be amended before implementation.

---

## Findings

### CRITICAL: Missing Test Tasks

| ID | Severity | Source | Finding |
|----|----------|--------|---------|
| F-001 | **CRITICAL** | Constitution II vs tasks.md | Constitution states: "All features MUST have test coverage. Tests SHOULD be written before or alongside implementation." Tasks.md contains 0 test-writing tasks out of 92. |
| F-002 | **CRITICAL** | PRD NFR-400.1 vs tasks.md | PRD requires: "Unit tests verify `created_by_user_id` is set on creation for each service." No task creates these tests. |
| F-003 | **CRITICAL** | PRD NFR-400.2 vs tasks.md | PRD requires: "Unit tests verify `updated_by_user_id` is updated on modification for each service." No task creates these tests. |
| F-004 | **CRITICAL** | PRD NFR-400.3 vs tasks.md | PRD requires: "Unit tests verify `AuditInfo` serialization in response schemas, including null user handling." No task creates these tests. |
| F-005 | **CRITICAL** | PRD NFR-400.4 vs tasks.md | PRD requires: "Frontend tests verify `<AuditTrailPopover>` renders correctly with full, partial, and null audit data." No task creates these tests. |
| F-006 | **CRITICAL** | contracts/audit-schema.md vs tasks.md | Contract specifies 5 backend test requirements (schema serialization, service create, service update, user deletion SET NULL, response integration). None appear in tasks. |
| F-007 | **CRITICAL** | contracts/frontend-components.md vs tasks.md | Contract specifies 3 frontend test requirements (AuditTrailPopover, AuditTrailSection, fallback rendering). None appear in tasks. |

### MINOR: Other Observations

| ID | Severity | Source | Finding |
|----|----------|--------|---------|
| F-008 | MINOR | plan.md vs tasks.md | Plan mentions `backend/tests/unit/test_audit.py` as a new file in project structure. This file is never created by any task. |
| F-009 | INFO | tasks.md T051 | T051 references "backend/src/schemas/collection.py" for ConnectorResponse, but connectors may have their own schema file. Verify during implementation. |
| F-010 | INFO | tasks.md T063 | T063 says "backend/src/schemas/team.py (or wherever these response schemas live)" — this uncertainty should be resolved during Phase 0 research, not during implementation. |

---

## Coverage Matrix

### Spec Requirements → Tasks

| Requirement | Covered by Task(s) | Status |
|------------|-------------------|--------|
| FR-001 (created_by attribution) | T001, T005–T018, T022–T033, T034–T048 | ✅ Covered |
| FR-002 (updated_by attribution) | T001, T005–T021, T022–T033, T034–T048 | ✅ Covered |
| FR-003 (API token attribution) | T046 (tokens.py route) | ✅ Covered |
| FR-004 (Agent attribution) | T047 (agent routes) | ✅ Covered |
| FR-005 (Agent system user) | Existing architecture | ✅ N/A |
| FR-006 (Creator preserved on update) | T022–T033 (service logic) | ✅ Covered |
| FR-007 (SET NULL on user delete) | T001, T003 (migration FK) | ✅ Covered |
| FR-008 (Audit in API responses) | T049–T064 | ✅ Covered |
| FR-009 (Backward compat) | T049–T064 (Optional field) | ✅ Covered |
| FR-010 (Modified column, 11 views) | T065, T077–T087 | ✅ Covered |
| FR-011 (Detail dialog sections) | T066, T088–T089 | ✅ Covered |
| FR-012 (Graceful null handling) | T065–T066 (component logic) | ✅ Covered |
| FR-013 (No extra API calls) | T049–T064 (embedded in response) | ✅ Covered |
| FR-014 (All 14 tenant entities) | T005–T018 | ✅ Covered |
| FR-015 (Group B entities) | T019–T021 | ✅ Covered |
| FR-016 (Display name fallback) | T065–T066 (component logic) | ✅ Covered |

### PRD Non-Functional Requirements → Tasks

| NFR | Covered by Task(s) | Status |
|-----|-------------------|--------|
| NFR-100.1 (< 10% response time) | T001 (lazy="joined") | ⚠️ Implicit only |
| NFR-100.2 (Single query joins) | T001 (lazy="joined") | ⚠️ Implicit only |
| NFR-200.1 (No internal ID exposure) | T002 (AuditUserSummary uses guid) | ✅ Covered |
| NFR-300.1 (Backward compat) | T050–T063 (Optional audit field) | ✅ Covered |
| NFR-300.2 (Frontend fallback) | T077 (fallback pattern) | ✅ Covered |
| NFR-300.3 (Agent API unaffected) | T047 (agent routes) | ✅ Covered |
| **NFR-400.1** (Service create tests) | **None** | ❌ **MISSING** |
| **NFR-400.2** (Service update tests) | **None** | ❌ **MISSING** |
| **NFR-400.3** (Schema serialization tests) | **None** | ❌ **MISSING** |
| **NFR-400.4** (Frontend component tests) | **None** | ❌ **MISSING** |

### Constitution Principle Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Agent-Only Tool Execution | ✅ Pass | N/A for this feature |
| **II. Testing & Quality** | ❌ **FAIL** | Zero test-writing tasks. Constitution: "All features MUST have test coverage." |
| III. User-Centric Design | ✅ Pass | Graceful null handling, popover UX |
| IV. GUIDs | ✅ Pass | AuditUserSummary uses guid field |
| V. Multi-Tenancy | ✅ Pass | Audit columns on tenant-scoped entities, ctx.user_id from TenantContext |
| VI. Agent-Only Execution | ✅ Pass | Agent system_user_id attribution |

---

## Recommended Test Tasks (to add to tasks.md)

Based on the PRD (NFR-400), contracts (audit-schema.md, frontend-components.md), and constitution (Principle II), the following test tasks should be added:

### Backend Tests (insert after T003, before T004)

**T003a** — Create backend/tests/unit/test_audit_mixin.py with tests for:
- AuditMixin columns exist on a model (created_by_user_id, updated_by_user_id)
- FK constraint to users table
- SET NULL behavior when referenced user is deleted
- Nullable columns (historical data compatibility)

**T003b** — Create backend/tests/unit/test_audit_schemas.py with tests for:
- AuditUserSummary serialization from User model (guid, display_name, email)
- AuditInfo serialization with full data (both users present)
- AuditInfo serialization with null users (historical records)
- AuditInfo helper function from model instance
- AuditInfo with mixed null (created_by present, updated_by null)

### Service Attribution Tests (insert in Phase 2, after service tasks)

**T033a** — Add user attribution tests to existing service test files (or create backend/tests/unit/test_audit_attribution.py) covering at minimum:
- CollectionService: created_by_user_id set on create, updated_by_user_id updated on update, created_by_user_id preserved on update
- At least 2 other representative services (e.g., EventService, PipelineService) with same create/update/preserve pattern
- Service methods work with user_id=None (backward compat, no crash)

### API Response Tests (insert in Phase 3, after schema tasks)

**T064a** — Create backend/tests/unit/test_audit_responses.py (or add to existing integration tests) covering:
- Entity API response includes audit field with created_by/updated_by user summaries
- Historical entity response has audit.created_by = null (no error)
- Audit field coexists with existing created_at/updated_at top-level fields

### Frontend Component Tests (insert in Phase 4, after T066)

**T066a** — Create frontend tests for AuditTrailPopover:
- Renders relative time trigger with correct text
- Popover displays created date/time and user name
- Popover displays modified date/time and user name
- Handles null created_by/updated_by (displays "—")
- Hides modified section when created_at === updated_at

**T066b** — Create frontend tests for AuditTrailSection:
- Renders created and modified rows with full timestamps
- Shows user display_name, falls back to email
- Handles null users with "—"
- Same-timestamp handling

---

## Metrics

| Metric | Value |
|--------|-------|
| Total tasks in tasks.md | 92 |
| Functional requirements covered | 16/16 (100%) |
| NFR requirements covered | 7/11 (64%) — 4 test NFRs missing |
| Constitution principles aligned | 5/6 (83%) — Principle II fails |
| Critical findings | 7 |
| Minor findings | 1 |
| Info findings | 2 |
| Recommended new tasks | 5-6 |

---

## Conclusion

The feature design is solid — the AuditMixin approach, schema contracts, component specs, and integration scenarios are thorough and consistent. The single gap is test coverage: **zero of the 92 tasks create new tests**, despite the PRD, contracts, and constitution all explicitly requiring them. Adding the recommended 5-6 test tasks (approximately 5 new tasks spanning backend unit, service attribution, API response, and frontend component tests) will resolve all critical findings and bring the plan into full constitution compliance.

**Recommendation**: Update tasks.md with the test tasks listed above before proceeding to `/speckit.implement`.
