# Implementation Plan: Agent Setup Wizard

**Branch**: `136-agent-setup-wizard` | **Date**: 2026-02-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/136-agent-setup-wizard/spec.md`

## Summary

Add a guided, multi-step "Agent Setup" wizard to the Agents page that walks users through the entire agent onboarding lifecycle: OS detection and binary download, registration token creation, agent registration, launch, and optional background service configuration. The wizard consolidates six previously disconnected steps into a single in-browser flow with copy-ready CLI commands.

This feature requires:
- **Backend**: A new `ReleaseArtifact` model for per-platform binary metadata, a user-accessible `GET /api/agent/v1/releases/active` endpoint, an authenticated binary download endpoint with signed URL support, and configuration for the agent binary distribution directory.
- **Frontend**: A 6-step wizard dialog with OS detection, platform override, token creation (reusing existing hook), command generation, service file generation (launchd/systemd), and dev/QA mode support.
- **Data migration**: The existing `ReleaseManifest` model stores a single checksum for all platforms. A new `release_artifacts` table is needed to store per-platform filenames and checksums, preserving backward compatibility with existing manifest data.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic (backend); React 18.3.1, shadcn/ui, Radix UI Dialog, Tailwind CSS 4.x, Lucide React (frontend)
**Storage**: PostgreSQL 12+ (production), SQLite (tests) — Alembic migrations with dialect-aware code
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Web application (browser + server)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Wizard opens within 500ms; token creation < 1s; binary download limited by network bandwidth
**Constraints**: Signed download URLs must be time-limited (1 hour default); plaintext token must never be persisted to client storage; existing admin release manifest endpoints must remain unchanged
**Scale/Scope**: 6 wizard steps, ~12 new frontend files, ~5 new/modified backend files, 1 new DB table, 1 migration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **I. Agent-Only Tool Execution**: Not applicable — this feature does not execute analysis tools. It provides a setup wizard for onboarding agents. Agent execution architecture is unchanged.
- [x] **II. Testing & Quality**: Tests planned for both backend (pytest: new endpoint, signed URL generation, binary serving, migration) and frontend (Vitest: OS detection, service file generation, wizard step navigation, dev/QA mode). Target ≥ 80% coverage for new components.
- [x] **III. User-Centric Design**: The wizard provides step-by-step guidance with clear instructions, copy-ready commands, graceful degradation when binaries are unavailable, and platform-specific service file generation. Error messages are actionable. YAGNI applied (no remote installation, no Windows service, no auto-update).
- [x] **IV. Global Unique Identifiers (GUIDs)**: New `ReleaseArtifact` entity does not need its own GUID — it is a child of `ReleaseManifest` identified by `(manifest_id, platform)`. The active manifest endpoint returns `ReleaseManifest.guid` with `rel_` prefix. Signed download URLs reference manifest GUID + platform, not internal IDs.
- [x] **V. Multi-Tenancy and Authentication**: New endpoints use `get_tenant_context` for user auth. Binary download supports session cookie auth and signed URL auth (time-limited, no tenant context needed since binaries are global). Release manifest data is global (not tenant-scoped) — consistent with existing admin endpoints.
- [x] **VI. Agent-Only Execution**: Not applicable — this feature helps users set up agents; it does not create or execute jobs.
- [x] **VII. Audit Trail & User Attribution**: `ReleaseArtifact` is a global entity (not tenant-scoped), consistent with its parent `ReleaseManifest`. Constitution VII applies to tenant-scoped entities only, so `AuditMixin` is not required. The parent manifest already has full audit tracking via `AuditMixin`. The registration token creation already has audit tracking via the existing `useRegistrationTokens` hook.

**Frontend UI Standards**:
- [x] **TopHeader KPI Pattern**: The Agents page already displays KPIs (Total Agents, Online). No new KPIs needed for the wizard — it's a modal overlay, not a page.
- [x] **Single Title Pattern**: The wizard is a Dialog (modal), not a page. No `<h1>` in content. The dialog title serves as the wizard title.

**Violations/Exceptions**: `ReleaseArtifact` is created without `GuidMixin` (Constitution IV exception); see Complexity Tracking section below for rationale.

## Project Structure

### Documentation (this feature)

```text
specs/136-agent-setup-wizard/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: developer guide
├── contracts/           # Phase 1: API contracts
│   ├── active-release.md
│   └── binary-download.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── release_artifact.py          # NEW: per-platform artifact model
│   ├── services/
│   │   ├── release_manifest_service.py  # MODIFIED: add artifact queries, signed URL generation
│   │   └── download_service.py          # NEW: binary file serving + signature verification
│   ├── api/
│   │   └── agent/
│   │       └── routes.py                # MODIFIED: add active release + download endpoints
│   ├── config/
│   │   └── settings.py                  # MODIFIED: add SHUSAI_AGENT_DIST_DIR setting
│   └── db/
│       └── migrations/versions/
│           └── 0XX_add_release_artifacts.py  # NEW: migration
└── tests/
    └── unit/
        ├── test_release_artifact.py     # NEW: model + service tests
        └── test_download_service.py     # NEW: signed URL + file serving tests

frontend/
├── src/
│   ├── components/
│   │   └── agents/
│   │       ├── AgentSetupWizardDialog.tsx   # NEW: root wizard dialog
│   │       └── wizard/
│   │           ├── StepIndicator.tsx         # NEW: step progress bar
│   │           ├── CopyableCodeBlock.tsx     # NEW: code block with copy button
│   │           ├── DownloadStep.tsx          # NEW: Step 1
│   │           ├── TokenStep.tsx             # NEW: Step 2
│   │           ├── RegisterStep.tsx          # NEW: Step 3
│   │           ├── LaunchStep.tsx            # NEW: Step 4
│   │           ├── ServiceStep.tsx           # NEW: Step 5
│   │           └── SummaryStep.tsx           # NEW: Step 6
│   ├── lib/
│   │   ├── os-detection.ts                  # NEW: platform detection utility
│   │   └── service-file-generator.ts        # NEW: plist/systemd generators
│   ├── services/
│   │   └── agents.ts                        # MODIFIED: add getActiveRelease(), getSignedDownloadUrl()
│   ├── contracts/api/
│   │   └── agent-api.ts                     # MODIFIED: add ActiveRelease, ReleaseArtifact types
│   └── pages/
│       └── AgentsPage.tsx                   # MODIFIED: add "Agent Setup" button
└── tests/
    ├── lib/
    │   ├── os-detection.test.ts             # NEW
    │   └── service-file-generator.test.ts   # NEW
    └── components/agents/
        └── wizard/                          # NEW: wizard component tests
```

**Structure Decision**: Web application pattern (backend + frontend). All new backend code follows existing conventions in `backend/src/`. All new frontend components go under `frontend/src/components/agents/wizard/` to keep the wizard self-contained. Utility functions in `frontend/src/lib/` follow the existing pattern for shared logic.

## Complexity Tracking

> One documented exception: `ReleaseArtifact` without `GuidMixin` (Constitution IV — acknowledged in Constitution Check Violations/Exceptions above; see table below for full rationale). All other choices follow existing patterns.

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| New `release_artifacts` table instead of modifying `platforms_json` | Per-platform filenames and checksums require normalized storage. JSON inside a JSON column would be fragile and hard to query. | Storing artifacts as JSON array in `ReleaseManifest.platforms_json` — rejected because it couples unrelated concerns and makes individual platform queries inefficient. |
| Signed URL via HMAC rather than JWT | Download signatures are simple (manifest GUID + platform + expiry). A lightweight HMAC signature is simpler than minting a full JWT for this purpose. Reuses the existing `JWT_SECRET_KEY` as the signing key. | JWT-based signed URLs — rejected as over-engineered for a single-purpose download link. |
| `ReleaseArtifact` without `GuidMixin` (Constitution IV exception) | Child entity always accessed via parent manifest GUID + platform composite key. No independent lifecycle, no external references, no URL routing by artifact ID. Constitution IV requires `GuidMixin` on new database entities, but this entity is never exposed independently in APIs or URLs — it is always nested within its parent `ReleaseManifest` response. Exception justified by YAGNI (Constitution: "Simplicity First"). | Adding `GuidMixin` to artifacts — rejected as no use case requires independent artifact references. |
