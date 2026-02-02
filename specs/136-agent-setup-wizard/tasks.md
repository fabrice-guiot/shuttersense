# Tasks: Agent Setup Wizard

**Input**: Design documents from `/specs/136-agent-setup-wizard/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — constitution mandates testing (≥ 80% coverage target for new components).

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 and share the wizard's Step 1; they are separated so US1 (wizard shell + steps 2-6) can deliver value even without binary download infrastructure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Configuration, shared types, and utility modules that multiple stories depend on

- [x] T001 Add `SHUSAI_AGENT_DIST_DIR` setting to backend/src/config/settings.py (optional string, no default, with docstring explaining directory structure `{dir}/{version}/{filename}`)
- [x] T002 [P] Add `ActiveReleaseResponse`, `ReleaseArtifactResponse` Pydantic schemas to backend/src/api/agent/schemas.py per contracts/active-release.md
- [x] T003 [P] Add `ReleaseArtifact` and `ActiveReleaseResponse` TypeScript types to frontend/src/contracts/api/agent-api.ts per data-model.md Frontend Type Additions
- [x] T004 [P] Create OS detection utility in frontend/src/lib/os-detection.ts — export `detectPlatform()` returning `{ platform, label, confidence }` with Apple Silicon WebGL heuristic, per PRD OS Detection Logic section
- [x] T005 [P] Create service file generator utility in frontend/src/lib/service-file-generator.ts — export `generateLaunchdPlist(binaryPath)` and `generateSystemdUnit(binaryPath, user)` per PRD Service File Generation section
- [x] T006 [P] Create CopyableCodeBlock component in frontend/src/components/agents/wizard/CopyableCodeBlock.tsx — code block with per-block "Copy" button using `useClipboard()` hook, with Copy→Check visual feedback (FR-024)
- [x] T007 [P] Write unit tests for OS detection in frontend/tests/lib/os-detection.test.ts — mock `navigator.userAgent`, `navigator.platform`, and WebGL renderer for all 5 platforms + fallback case
- [x] T008 [P] Write unit tests for service file generators in frontend/tests/lib/service-file-generator.test.ts — test plist and systemd output with various binary paths including paths with spaces, and edge cases (empty path, relative path)

**Checkpoint**: Shared types, utilities, and reusable components ready. OS detection and service file generation tested independently.

---

## Phase 2: Foundational (Backend — ReleaseArtifact Model & Endpoints)

**Purpose**: Backend data model and API endpoints that the wizard frontend will consume. MUST complete before US1/US2 frontend work begins.

**⚠️ CRITICAL**: Frontend wizard steps depend on these endpoints being available.

- [x] T009 Create `ReleaseArtifact` SQLAlchemy model in backend/src/models/release_artifact.py — fields: id, manifest_id (FK CASCADE), platform, filename, checksum, file_size, created_at, updated_at; unique constraint on (manifest_id, platform); per data-model.md
- [x] T010 Add `artifacts` relationship to `ReleaseManifest` model in backend/src/models/release_manifest.py — one-to-many to ReleaseArtifact, cascade all/delete-orphan; add `artifact_platforms` property
- [x] T011 Create Alembic migration in backend/src/db/migrations/versions/ for `release_artifacts` table — dialect-aware (PostgreSQL + SQLite), with indexes on manifest_id and platform; per data-model.md Migration Plan
- [x] T012 Implement signed URL generation and verification functions in backend/src/services/download_service.py — `generate_signed_download_url()` and `verify_signed_download_url()` using HMAC-SHA256 with `JWT_SECRET_KEY`; include path traversal prevention for file resolution; per contracts/binary-download.md
- [x] T013 Implement `GET /api/agent/v1/releases/active` endpoint in backend/src/api/agent/routes.py — query active manifest with highest version, load artifacts, construct download_url and signed_url per artifact, include dev_mode flag based on SHUSAI_AGENT_DIST_DIR presence; require `get_tenant_context`; per contracts/active-release.md
- [x] T014 Implement `GET /api/agent/v1/releases/{manifest_guid}/download/{platform}` endpoint in backend/src/api/agent/routes.py — dual auth (session cookie via get_tenant_context OR signed URL query params), resolve file from `SHUSAI_AGENT_DIST_DIR/{version}/{filename}`, stream file with Content-Disposition header; per contracts/binary-download.md
- [x] T015 Extend admin `POST /api/admin/release-manifests` to accept optional `artifacts` array in backend/src/api/admin/release_manifests.py — create ReleaseArtifact rows alongside manifest; existing requests without artifacts continue to work unchanged (backward compatible)
- [x] T016 Extend admin `GET /api/admin/release-manifests/{guid}` to include artifacts in response in backend/src/api/admin/release_manifests.py
- [x] T017 [P] Write unit tests for ReleaseArtifact model and relationships in backend/tests/unit/test_release_artifact.py — CRUD, cascade delete, unique constraint, validation (platform values, checksum format, filename no slashes)
- [x] T018 [P] Write unit tests for download service in backend/tests/unit/test_download_service.py — signed URL generation/verification, expiry, path traversal prevention, HMAC constant-time comparison
- [x] T019 Write unit tests for active release and download endpoints in backend/tests/unit/test_agent_release_endpoints.py — active release with/without artifacts, dev_mode flag, download with session auth, download with signed URL, expired signature, missing file, missing dist dir

**Checkpoint**: Backend fully functional — active release endpoint returns artifacts with download URLs, binary download works with both session and signed URL auth. All backend tests pass.

---

## Phase 3: User Story 1 — Complete Agent Setup via Guided Wizard (Priority: P1) 🎯 MVP

**Goal**: User can open wizard from Agents page and walk through all 6 steps: OS detection (Step 1), token creation (Step 2), registration command (Step 3), launch command (Step 4), service setup placeholder (Step 5), and summary (Step 6). All commands are copy-ready with correct values.

**Independent Test**: Open wizard, progress through all steps, verify token is created and all CLI commands display correct server URL and token. Close wizard and verify Agents page refreshes.

### Implementation for User Story 1

- [x] T020 Create StepIndicator component in frontend/src/components/agents/wizard/StepIndicator.tsx — numbered step progress bar with titles, `aria-current="step"` for active step, responsive layout (FR-003; see PRD FR-800.4 for step title labels)
- [x] T021 Create AgentSetupWizardDialog root component in frontend/src/components/agents/AgentSetupWizardDialog.tsx — Dialog shell with WizardState management (currentStep, selectedPlatform, detectedPlatform, createdToken, tokenName, serverUrl, binaryPath, serviceUser), Back/Next/Done navigation, step rendering, min-width 640px, `max-w-4xl max-h-[90vh]` pattern from CreateCollectionsDialog; integrate StepIndicator (FR-002, FR-025, FR-028)
- [x] T022 Create TokenStep component in frontend/src/components/agents/wizard/TokenStep.tsx — reuse `useRegistrationTokens().createToken`, token name input (optional), expiration input (1-168h, default 24), display plaintext token with CopyableCodeBlock on creation, "token only shown once" warning, prevent duplicate creation on back/forward navigation by checking wizard state (FR-010 through FR-013)
- [x] T023 Create RegisterStep component in frontend/src/components/agents/wizard/RegisterStep.tsx — resolve server URL from `import.meta.env.VITE_API_BASE_URL || window.location.origin` with URL validation, display `chmod +x` for macOS/Linux, display pre-populated `shuttersense-agent register --server {url} --token {token}` command with CopyableCodeBlock, show expected successful output (FR-014 through FR-016)
- [x] T024 Create LaunchStep component in frontend/src/components/agents/wizard/LaunchStep.tsx — display `shuttersense-agent start` and `shuttersense-agent self-test` commands with CopyableCodeBlock, brief explanation text, collapsible "Previous Commands" section summarizing chmod + register commands (FR-017)
- [x] T025 Create SummaryStep component in frontend/src/components/agents/wizard/SummaryStep.tsx — recap of platform, token name, registration command; OS-dependent config/data file paths (macOS: `~/Library/Application Support/shuttersense/`, Linux: `~/.config/shuttersense/`, Windows: `%APPDATA%\shuttersense\`); "monitor agent from Agents page" reminder (FR-023; see PRD FR-700.2 for config paths, PRD FR-700.3 for monitoring reminder)
- [x] T026 Create placeholder DownloadStep component in frontend/src/components/agents/wizard/DownloadStep.tsx — display detected platform with label, platform override dropdown (all 5 platforms), override warning; fetch active release from backend; show download button or degradation messages; basic structure that US2 will enhance with full download/signed URL logic (FR-004 through FR-008)
- [x] T027 Create placeholder ServiceStep component in frontend/src/components/agents/wizard/ServiceStep.tsx — "Skip" button, basic layout that US3 will implement fully; for now show "Background service configuration — coming in next step" (FR-022)
- [x] T028 Add `getActiveRelease()` function to frontend/src/services/agents.ts — call `GET ${AGENT_API_PATH}/releases/active`, return typed `ActiveReleaseResponse`
- [x] T029 Add "Agent Setup" button to frontend/src/pages/AgentsPage.tsx — adjacent to "New Registration Token" button, using Wand2 icon, opens AgentSetupWizardDialog; on wizard close with token created, call `fetchAgents()` and `fetchTokens()` to refresh lists (FR-001, FR-027)
- [x] T030 Implement wizard close behavior in AgentSetupWizardDialog — on close via X/Escape: show confirmation if token created and not on Summary step, no confirmation if on Summary step or no token created; state reset on close with 200ms delay for animation (FR-026)

**Checkpoint**: Full 6-step wizard flow works end-to-end. User can create a token, see all CLI commands with correct values, and close the wizard. Agents page refreshes on close. Steps 1 and 5 have basic placeholders.

---

## Phase 4: User Story 2 — Download Correct Agent Binary for Detected Platform (Priority: P1)

**Goal**: Step 1 shows the correct binary download for the detected/selected platform with authenticated session download, signed URL for remote use, checksum display, and graceful degradation for all error cases.

**Independent Test**: Open wizard, verify correct platform detected, click "Download Agent" to trigger authenticated download, verify checksum is displayed, test with no manifest / no artifact / insecure URL / download failure scenarios.

### Implementation for User Story 2

- [x] T031 [US2] Enhance DownloadStep in frontend/src/components/agents/wizard/DownloadStep.tsx — display "Download Agent" button with filename and file size when artifact exists and download_url is non-null; display checksum from artifact; HTTPS validation for download_url (allow localhost exception); inline download error handling with "Retry Download" button; "Next" always enabled (FR-007 through FR-009, FR-037, FR-040)
- [x] T032 [US2] Add signed URL display to DownloadStep in frontend/src/components/agents/wizard/DownloadStep.tsx — show signed_url from artifact with "Copy Link" button and expiry note ("Link valid for 1 hour"); construct full URL for curl example by prepending `window.location.origin` to the relative signed_url path; parse `expires` query param from signed_url to display absolute expiry time; if wizard has been open > 50 minutes (signed URL nearing expiry), show warning "This link will expire soon" with a "Refresh Link" button that re-fetches the active release endpoint to obtain fresh signed URLs (FR-039)
- [x] T033 [US2] Implement dev/QA mode in DownloadStep — check `import.meta.env.DEV || activeRelease.dev_mode`; if true, show all 5 platforms regardless of artifacts; for platforms without artifacts, show disabled download button with explanatory message (FR-033, FR-034, FR-035); in production mode, only show platforms with artifacts in dropdown (FR-036)
- [x] T034 [US2] Implement in-browser download trigger in DownloadStep — on "Download Agent" click, create hidden `<a>` element with download_url (relative, session cookie sent automatically), trigger click, handle download errors (FR-038 session auth)

**Checkpoint**: Complete download experience — OS auto-detection, download button with checksum, signed URL for remote, dev/QA mode showing all platforms, graceful degradation for all error cases.

---

## Phase 5: User Story 5 — Wizard Navigation and Mid-Flow Protection (Priority: P2)

**Goal**: Token cannot be accidentally lost. Navigation back/forward preserves wizard state. Close confirmation protects irreversible actions. Keyboard navigation works.

**Independent Test**: Create token in Step 2, navigate back to Step 2 and forward, verify same token displayed. Press Escape on Step 3, verify confirmation dialog. Press Escape on Step 6, verify no confirmation.

### Implementation for User Story 5

- [x] T035 [US5] Implement token preservation in AgentSetupWizardDialog — when navigating back to Step 2 after token creation, hide the creation form and show read-only token display with "Copy" button and notice "This token was previously created in this session" (FR-012)
- [x] T036 [US5] Implement Step 2 gate in AgentSetupWizardDialog — disable "Next" button on Step 2 until token has been created and is visible in wizard state (FR-013)
- [x] T037 [US5] Add keyboard navigation to AgentSetupWizardDialog — Tab through form fields, Enter to trigger Next/Create actions, Escape to close with confirmation logic; add `aria-label` to all Copy buttons (e.g., "Copy registration command"); ensure all form inputs (token name, expiration, binary path, service user, platform dropdown) have associated `<label>` elements or `aria-label` attributes; `aria-current="step"` already handled in StepIndicator (FR-030)
- [x] T038 [US5] Verify token is in-memory only — confirm `createdToken` state is local to the component (React useState), not written to localStorage/sessionStorage/cookies; cleared on component unmount (FR-029)

**Checkpoint**: Navigation is robust — token preserved across back/forward, close confirmation protects token, keyboard-accessible, token never persisted to storage.

---

## Phase 6: User Story 3 — Configure Background Service (Priority: P2)

**Goal**: Step 5 generates correct launchd plist (macOS) or systemd unit (Linux) with user-provided binary path and displays installation commands. Windows shows unsupported message. Step is skippable.

**Independent Test**: Select macOS, enter binary path, verify generated plist XML is correct. Select Linux, enter path and username, verify systemd unit file. Select Windows, verify unsupported message. Enter relative path, verify validation error.

### Implementation for User Story 3

- [x] T039 [US3] Implement full ServiceStep in frontend/src/components/agents/wizard/ServiceStep.tsx — replace placeholder with: binary path input with OS-appropriate default (`/usr/local/bin/shuttersense-agent` for macOS/Linux, `C:\Program Files\ShutterSense\shuttersense-agent.exe` for Windows), real-time path validation (absolute path required, spaces warning), service user input for Linux (default "shuttersense"), generated service file display via CopyableCodeBlock, installation commands via CopyableCodeBlock, "Skip" button always visible (FR-018 through FR-022; see PRD FR-600.2 through FR-600.11 for UI details)
- [x] T040 [US3] Implement path validation logic in ServiceStep — validate absoluteness (starts with `/` on macOS/Linux, drive letter on Windows), OS-format matching, spaces warning (non-blocking), empty path disables generated output (FR-018; see PRD FR-600.3a for validation details)
- [x] T041 [US3] Implement macOS plist generation display in ServiceStep — call `generateLaunchdPlist(binaryPath)` from service-file-generator.ts, show in CopyableCodeBlock; display log directory creation + cp + launchctl commands with CopyableCodeBlocks (FR-019; see PRD FR-600.4 for plist template, PRD FR-600.5 for install commands)
- [x] T042 [US3] Implement Linux systemd generation display in ServiceStep — call `generateSystemdUnit(binaryPath, serviceUser)` from service-file-generator.ts, show in CopyableCodeBlock; display cp + systemctl commands with CopyableCodeBlocks (FR-020; see PRD FR-600.6 for systemd template, PRD FR-600.7 for install commands)
- [x] T043 [US3] Implement Windows unsupported message in ServiceStep — display informational alert: "Automatic background service setup for Windows is not yet supported. You can run the agent manually or use Windows Task Scheduler." (FR-021; see PRD FR-600.9)

**Checkpoint**: Full service configuration step — macOS plist, Linux systemd, Windows unsupported message, path validation with real-time feedback, skip option.

---

## Phase 7: User Story 4 — Set Up Agent on a Remote Machine (Priority: P3)

**Goal**: When user overrides platform, all wizard content adapts: download link, chmod commands, service files, config paths in summary. Signed download URL is copyable for remote use.

**Independent Test**: Override from macOS to Linux, verify chmod appears in Step 3, systemd in Step 5, Linux paths in Step 6, signed URL available in Step 1.

### Implementation for User Story 4

- [x] T044 [US4] Verify platform override propagates through all steps — ensure `selectedPlatform` from wizard state is used (not `detectedPlatform`) in RegisterStep (chmod conditional), ServiceStep (plist vs systemd vs Windows), SummaryStep (config paths); add platform override warning in DownloadStep when selected differs from detected (FR-006)
- [x] T045 [US4] Verify signed URL is prominent for overridden platforms — when platform differs from detected, emphasize the signed URL section in DownloadStep with a note: "Since you're setting up a remote machine, use this link to download the agent directly on the target machine" (US4 acceptance scenario 4)

**Checkpoint**: Remote setup fully works — all content adapts to overridden platform, signed URL prominent for remote use.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Responsive design, accessibility hardening, admin UI updates, and integration validation

- [ ] T046 [P] Implement responsive layout for wizard dialog — mobile viewport (<640px): stack content vertically, code blocks horizontally scrollable, step indicator compact mode; test at 320px, 640px, 1024px breakpoints (FR-028)
- [ ] T047 [P] Update ReleaseManifestsTab admin UI in frontend/src/components/settings/ReleaseManifestsTab.tsx — display artifacts per manifest in detail view, add artifact fields to create manifest form (optional); per research.md R7
- [ ] T048 [P] Add `SHUSAI_AGENT_DIST_DIR` to backend/.env.example with documentation comment explaining the directory structure and that it's optional (per quickstart.md)
- [ ] T049 Verify existing "New Registration Token" button and RegistrationTokenDialog are unchanged — manual regression check that the standalone token flow still works independently of the wizard (FR-031)
- [ ] T050 End-to-end smoke test — open wizard, complete all 6 steps with token creation, verify Agents page refreshes on close; test with no release manifest, with release manifest but no artifacts, with artifacts but no dist dir, with full setup
- [ ] T051 [P] Write component tests for AgentSetupWizardDialog in frontend/tests/components/agents/wizard/AgentSetupWizardDialog.test.tsx — test step navigation (Back/Next/Done), close confirmation logic (confirm when token created and not on Summary, no confirm otherwise), state reset on close, refresh callbacks on close with token created; target ≥ 80% coverage per constitution (FR-002, FR-025, FR-026, FR-027)
- [ ] T052 [P] Write component tests for DownloadStep in frontend/tests/components/agents/wizard/DownloadStep.test.tsx — test platform auto-detection display, platform override with warning, dev/QA mode showing all platforms, download button states (available, disabled, error with retry), signed URL display and expiry handling, degradation for missing manifest/artifact (FR-004 through FR-009, FR-033 through FR-036, FR-039)
- [ ] T053 [P] Write component tests for TokenStep in frontend/tests/components/agents/wizard/TokenStep.test.tsx — test token creation flow, token display with copy button, back/forward token preservation (read-only display), Next button gate until token created (FR-010 through FR-013)
- [ ] T054 [P] Write component tests for ServiceStep in frontend/tests/components/agents/wizard/ServiceStep.test.tsx — test macOS plist generation display, Linux systemd generation display, Windows unsupported message, path validation (absolute required, spaces warning, empty disables output), skip button (FR-018 through FR-022)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on T001-T003 (settings + schemas) from Phase 1
- **Phase 3 (US1)**: Depends on Phase 2 completion (needs backend endpoints available)
- **Phase 4 (US2)**: Depends on T026 (DownloadStep placeholder from US1) and Phase 2 (backend endpoints)
- **Phase 5 (US5)**: Depends on T021-T022 (wizard dialog + token step from US1)
- **Phase 6 (US3)**: Depends on T005, T027 (service generator + ServiceStep placeholder from US1)
- **Phase 7 (US4)**: Depends on T031-T033 (enhanced DownloadStep from US2) and Phase 6 (ServiceStep)
- **Phase 8 (Polish)**: Depends on all user story phases. T051-T054 (component tests) can run in parallel with each other and with T046-T050.

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 (backend). No dependency on other stories.
- **US2 (P1)**: Requires Phase 2 (backend) + DownloadStep from US1. Can parallelize with US5.
- **US5 (P2)**: Requires wizard shell from US1. Can parallelize with US2.
- **US3 (P2)**: Requires ServiceStep placeholder from US1 + service generators from Phase 1. Can parallelize with US2/US5.
- **US4 (P3)**: Requires US2 (signed URLs) and US3 (service files) to be complete.

### Within Each User Story

- Models/schemas before services
- Services before endpoints
- Backend before frontend (for API-dependent features)
- Core implementation before edge cases
- Story complete before moving to next priority

### Parallel Opportunities

Phase 1 tasks T002-T008 are all parallelizable (different files).

Phase 2 tasks T017-T019 (tests) can run in parallel with each other and alongside T009-T016 if TDD.

After Phase 2 completes:
- US1 (Phase 3) is the critical path
- US2 (Phase 4), US5 (Phase 5), and US3 (Phase 6) can start as soon as their specific dependencies from US1 are done
- US4 (Phase 7) starts after US2 and US3

---

## Parallel Example: Phase 1

```
# These 7 tasks touch different files and can all run in parallel:
T002: ActiveReleaseResponse schema in backend/src/api/agent/routes.py
T003: TypeScript types in frontend/src/contracts/api/agent-api.ts
T004: OS detection in frontend/src/lib/os-detection.ts
T005: Service file generators in frontend/src/lib/service-file-generator.ts
T006: CopyableCodeBlock in frontend/src/components/agents/wizard/CopyableCodeBlock.tsx
T007: OS detection tests in frontend/tests/lib/os-detection.test.ts
T008: Service file tests in frontend/tests/lib/service-file-generator.test.ts
```

## Parallel Example: Phase 2

```
# Backend model + migration (sequential):
T009 → T010 → T011

# Then services + endpoints (sequential within, parallel across):
T012: download_service.py (can start after T009)
T013: active release endpoint (depends on T009, T010, T012)
T014: download endpoint (depends on T009, T012)

# Tests can run in parallel:
T017: model tests
T018: download service tests
T019: endpoint tests
```

---

## Implementation Strategy

### MVP First (US1 Only — Phases 1-3)

1. Complete Phase 1: Setup (shared types, utilities, CopyableCodeBlock)
2. Complete Phase 2: Backend (ReleaseArtifact model, endpoints, migration)
3. Complete Phase 3: User Story 1 (full 6-step wizard with placeholder Steps 1 & 5)
4. **STOP and VALIDATE**: Open wizard, create token, verify all commands correct
5. Deploy/demo — wizard is usable even without binary downloads

### Full Delivery (Phases 1-8)

1. Phases 1-3 → MVP wizard
2. Phase 4 (US2) → Real binary downloads with signed URLs
3. Phases 5-6 (US5 + US3) → Navigation protection + service file generation
4. Phase 7 (US4) → Remote machine support
5. Phase 8 → Polish, responsive, admin UI

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US1 delivers a complete 6-step wizard even with placeholder download and service steps
- Backend Phase 2 is the critical bottleneck — all frontend work depends on it
- CopyableCodeBlock is used by 5 of 6 steps — build it early in Phase 1
- The existing `useRegistrationTokens().createToken` hook is reused directly — no new token API code needed
- `PLATFORM_LABELS` mapping already exists in `release-manifests-api.ts` — reuse for human-friendly labels
