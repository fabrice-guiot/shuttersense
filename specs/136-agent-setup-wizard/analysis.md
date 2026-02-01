# Cross-Artifact Consistency & Quality Analysis: Agent Setup Wizard (#136)

**Date**: 2026-02-01
**Analyst**: Claude Opus 4.5
**Status**: Complete

## Executive Summary

This analysis reviews 9 artifacts (spec.md, plan.md, tasks.md, research.md, data-model.md, contracts/active-release.md, contracts/binary-download.md, quickstart.md, and the PRD) plus the constitution for the Agent Setup Wizard feature.

### Findings Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 6 |
| MEDIUM | 8 |
| LOW | 5 |
| INFO | 4 |
| **Total** | **24** |

### Overall Quality Assessment

The artifacts are **well-structured and comprehensive**. The spec, plan, and tasks demonstrate strong traceability and the overall design is sound. The most significant issue is the **architectural evolution from PRD to spec** regarding binary distribution (static CDN vs. server-hosted with signed URLs), which was a deliberate and well-reasoned change but introduced subtle inconsistencies in terminology and contract structure. The backend surface area grew significantly from the PRD's "one new endpoint" scope to the spec's three new endpoints plus a new DB table, model, and migration. This is well-justified but should be acknowledged clearly. Constitution compliance is strong with one notable gap regarding audit trail requirements for the new ReleaseArtifact entity.

---

## Findings

### Pass 1: Duplication Detection

#### D-001 | LOW | Redundant OS detection specification across PRD and spec

**Affected artifacts**: `docs/prd/136-agent-setup-wizard.md`, `spec.md`

**Description**: The PRD contains full TypeScript implementation code for `detectPlatform()` and `checkAppleSilicon()` (lines 454-527) and `service-file-generator.ts` (lines 534-577). The spec references these as requirements (FR-004, FR-005) at the behavioral level. The plan then re-specifies these as tasks (T004, T005) with "per PRD OS Detection Logic section". This creates a three-layer chain where the PRD acts as both requirements and implementation reference.

**Recommendation**: This is acceptable as a natural PRD-to-spec-to-plan flow. However, any future changes to detection logic must be synchronized across all three. No action needed unless the PRD code samples diverge from actual implementation.

---

#### D-002 | LOW | Token step requirements stated in both spec and PRD with slightly different wording

**Affected artifacts**: `spec.md` (FR-010 through FR-013), `docs/prd/136-agent-setup-wizard.md` (FR-300.1 through FR-300.7)

**Description**: The spec's FR-010 says "optionally name the token and set its expiration (1-168 hours, default 24)" while the PRD's FR-300.3 says "set the token expiration (1-168 hours, default 24)". The spec's FR-012 says "redisplay the existing token without creating a duplicate" while the PRD's FR-300.6 goes further: "The token creation form MUST be hidden and replaced with this read-only display." The PRD is more prescriptive.

**Recommendation**: The spec intentionally abstracts away UI specifics. The plan and tasks (T022, T035) correctly reference both. No action needed, but implementers should prefer the PRD's more detailed behavioral guidance for UI specifics.

---

#### D-003 | MEDIUM | Overlapping download degradation requirements across FR-007, FR-008, FR-040, FR-041

**Affected artifacts**: `spec.md`

**Description**: FR-008 covers the case when "no release manifest exists, or no artifact matches the selected platform, or the download URL is insecure." FR-040 covers "binary file for the requested platform and version does not exist in the server's distribution directory." FR-041 covers "distribution directory is not configured or does not exist." These three requirements create overlapping error scenarios that could confuse implementers about which error message to show in which situation. The distinction between "no artifact in DB" (FR-008), "artifact exists but file missing on disk" (FR-040), and "dist dir not configured" (FR-041) needs clear mapping to specific HTTP status codes and UI behavior.

**Recommendation**: The contracts/binary-download.md does map these to specific HTTP responses (404 for missing file, 500 for unconfigured dir). However, the spec should cross-reference these more explicitly. Consider adding a degradation matrix to the spec or plan showing: condition -> HTTP status -> wizard UI behavior.

---

### Pass 2: Ambiguity Detection

#### A-001 | HIGH | "Active manifest with highest version" selection is ambiguous

**Affected artifacts**: `contracts/active-release.md` (line 95)

**Description**: The contract states: "If multiple manifests have `is_active=true`, the endpoint returns the one with the highest version (semantic version sorting) or the most recently created one." The "or" creates ambiguity: is it semver sorting *with fallback to* creation date for equal versions, or is it an either/or choice for the implementer? Semantic version comparison is non-trivial (e.g., `1.0.0-beta.1` vs `1.0.0`). The contract does not specify whether pre-release versions are included or excluded.

**Recommendation**: Clarify to: "Returns the manifest with the highest semantic version (per semver.org ordering, excluding pre-release tags). If two manifests share the same version, the most recently created one wins." Or, more simply: "Returns the most recently activated manifest" and enforce that only one manifest can be active at a time.

---

#### A-002 | MEDIUM | Signed URL expiry period is specified inconsistently

**Affected artifacts**: `spec.md` (FR-039), `contracts/binary-download.md` (line 144), `contracts/active-release.md` (line 97)

**Description**: FR-039 says "a reasonable period (e.g., 1 hour)". The binary-download contract says `expires_in_seconds: int = 3600` (1 hour). The active-release contract says "1-hour expiry". The spec uses "e.g." phrasing which suggests the period is configurable or approximate, while the contracts hardcode 3600 seconds. Is this intended to be configurable via environment variable, or always 1 hour?

**Recommendation**: Decide whether the expiry period should be configurable (e.g., `SHUSAI_SIGNED_URL_EXPIRY_SECONDS` env var) or hardcoded. If hardcoded, remove the "e.g." from FR-039. If configurable, add a task for the setting and document the default.

---

#### A-003 | MEDIUM | Dev/QA mode detection logic has dual signals with unclear precedence

**Affected artifacts**: `research.md` (R4), `tasks.md` (T033), `contracts/active-release.md`

**Description**: Research R4 says the frontend uses `import.meta.env.DEV || response.dev_mode`. Task T033 says `import.meta.env.DEV || activeRelease.dev_mode`. The active-release contract says `dev_mode` is `true` when `SHUSAI_AGENT_DIST_DIR` is not configured. But what happens when `import.meta.env.DEV` is `true` (Vite dev server) but `dev_mode` in the response is `false` (because `SHUSAI_AGENT_DIST_DIR` IS configured in the dev environment for testing actual downloads)? The OR logic means the frontend would still show all platforms even though binaries are available. This may be intentional for development, but it could also confuse developers testing the production mode behavior locally.

**Recommendation**: Add a note to the plan clarifying the precedence: "In development, all platforms are always shown regardless of backend config, to enable full wizard path testing. To test production mode locally, build the frontend in production mode (`npm run build`)."

---

#### A-004 | MEDIUM | "Clipboard access blocked" edge case has no implementation task

**Affected artifacts**: `spec.md` (Edge Cases, line 107)

**Description**: The spec's edge case section says: "What happens when the user's browser blocks clipboard access? The 'Copy' button should gracefully degrade (e.g., select the text for manual copying) and inform the user." Task T006 (CopyableCodeBlock) does not mention clipboard fallback behavior. The existing `useClipboard()` hook (referenced in research R5) may or may not handle this case.

**Recommendation**: Add clipboard fallback handling to the acceptance criteria for T006, or create a sub-task. Check whether the existing `useClipboard()` hook already handles `navigator.clipboard` permission denial.

---

#### A-005 | LOW | `file_size` field nullability could cause display confusion

**Affected artifacts**: `data-model.md` (line 40), `contracts/active-release.md` (line 69)

**Description**: `file_size` is nullable in both the DB model and the API response ("null if unknown"). The spec's FR-007 says to display "filename and checksum" but the PRD's FR-200.10 says "display the artifact's filename and file size when available." If `file_size` is null, should the wizard show "Unknown size" or omit the size entirely? Neither the spec nor the contracts specify the frontend behavior for null file_size.

**Recommendation**: Add a note to T031 specifying display behavior: if `file_size` is null, show only the filename and checksum; do not display "0 bytes" or "Unknown".

---

### Pass 3: Underspecification Detection

#### U-001 | HIGH | No task for the `PUT /api/admin/release-manifests/{guid}/artifacts` endpoint

**Affected artifacts**: `research.md` (R7, line 119), `tasks.md`

**Description**: Research R7 mentions: "A new `PUT /api/admin/release-manifests/{guid}/artifacts` endpoint allows managing artifacts independently (add/remove/update)." However, no task in tasks.md covers this endpoint. Tasks T015 and T016 extend the existing admin POST and GET endpoints, but independent artifact CRUD is not addressed. Without this endpoint, the only way to manage artifacts is to recreate the entire manifest.

**Recommendation**: Either add a task for the PUT artifacts endpoint, or explicitly document in the plan that this endpoint is deferred to a future iteration and is not needed for MVP. If deferred, update research.md R7 to note this.

---

#### U-002 | HIGH | No task for frontend wizard component tests

**Affected artifacts**: `tasks.md`, `quickstart.md` (line 114)

**Description**: The quickstart references `frontend/tests/components/agents/wizard/` for wizard component tests, and the plan's project structure mentions `wizard/` under `frontend/tests/`. However, no specific task in tasks.md creates wizard component tests. T007 and T008 cover utility tests. T017-T019 cover backend tests. But there are no T-numbers for testing the individual step components (DownloadStep, TokenStep, RegisterStep, etc.) or the AgentSetupWizardDialog itself. The constitution mandates >= 80% coverage for new components.

**Recommendation**: Add tasks for wizard component tests, at minimum:
- Test for AgentSetupWizardDialog (navigation, state management, close confirmation)
- Test for TokenStep (creation, back/forward preservation)
- Test for DownloadStep (platform detection, dev mode, error states)
- Test for ServiceStep (plist generation, systemd generation, validation)

Task T050 is an "end-to-end smoke test" but this is manual, not automated.

---

#### U-003 | HIGH | Signed URL handling on the frontend is underspecified

**Affected artifacts**: `tasks.md` (T032), `spec.md` (FR-039)

**Description**: T032 says "show signed_url from artifact with 'Copy Link' button and expiry note." But the signed URL is generated server-side at the time of the `GET /api/agent/v1/releases/active` call. If the user stays on Step 1 for more than 1 hour, the signed URL expires. There is no task or specification for:
1. Displaying the remaining validity time of the signed URL (countdown or absolute expiry)
2. Refreshing the signed URL if it expires while the wizard is open
3. How the `curl` command example should be formatted (the contract shows a full absolute URL with `https://your-server.com/...` but the `signed_url` field is a relative path)

**Recommendation**: Add to T032 or create a new task:
- Display the expiry timestamp alongside the signed URL
- If the wizard has been open > 50 minutes, show a warning "This link will expire soon"
- For the curl example, prepend `window.location.origin` to the relative signed_url to construct the full URL
- Consider adding a "Refresh Link" button that re-fetches the active release

---

#### U-004 | MEDIUM | No validation rules specified for token name input

**Affected artifacts**: `spec.md` (FR-010), `tasks.md` (T022)

**Description**: FR-010 says the user can "optionally name the token" but specifies no validation rules for the name. Can it be empty? What is the max length? Are special characters allowed? The existing RegistrationTokenDialog may already have validation, but this should be explicitly stated since T022 is building a new component.

**Recommendation**: Add a note to T022: "Token name validation follows existing RegistrationTokenDialog rules. If no rules exist, enforce: optional, max 100 characters, trimmed whitespace."

---

#### U-005 | MEDIUM | No specification for version format validation in file path resolution

**Affected artifacts**: `contracts/binary-download.md` (lines 193-206)

**Description**: The binary download endpoint resolves files at `{SHUSAI_AGENT_DIST_DIR}/{manifest.version}/{artifact.filename}`. The contract mentions path traversal prevention for filename but does not explicitly mention version validation. A malicious or malformed version string (e.g., `../../etc/passwd`) in the manifest could be exploited. While the manifest data comes from the admin API (trusted), defense-in-depth requires validation.

**Recommendation**: T012 mentions "path traversal prevention for file resolution" which is good. Ensure the implementation validates both the version string and the filename, and that the resolved absolute path is verified to be a child of `SHUSAI_AGENT_DIST_DIR`. This should be made explicit in the task description.

---

### Pass 4: Constitution Alignment

#### C-001 | CRITICAL | ReleaseArtifact does not use GuidMixin, violating Constitution IV unless explicitly justified

**Affected artifacts**: `plan.md` (Constitution Check, line 36), `data-model.md` (line 59), `.specify/memory/constitution.md` (line 149)

**Description**: The constitution states: "New database entities MUST add GuidMixin" (line 159) and "All entities in presentation layers (APIs, URLs, UI) MUST be identified exclusively by GUIDs" (line 207). The plan's constitution check (line 36) says: "New `ReleaseArtifact` entity does not need its own GUID -- it is a child of `ReleaseManifest` identified by `(manifest_id, platform)`."

The justification is reasonable (artifacts are always accessed through their parent, have no independent lifecycle). However, the constitution uses "MUST" language, and the plan's Complexity Tracking section (line 121) says "No constitution violations identified" rather than documenting this as an explicit exception. Constitution governance (line 530) states: "Any violations MUST be explicitly justified in the implementation plan's 'Complexity Tracking' section."

**Recommendation**: Add an entry to the Complexity Tracking table in plan.md:

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| `ReleaseArtifact` without `GuidMixin` | Child entity always accessed via parent manifest GUID + platform composite key. No independent lifecycle, no external references, no URL routing by artifact ID. Constitution IV exception justified by YAGNI. | Adding `GuidMixin` -- rejected as no use case requires independent artifact references. |

Also update the "No constitution violations identified" note to: "One documented exception: ReleaseArtifact without GuidMixin (see table)."

---

#### C-002 | HIGH | ReleaseArtifact audit trail compliance is incomplete

**Affected artifacts**: `plan.md` (Constitution Check, line 39), `data-model.md`, `.specify/memory/constitution.md` (lines 356-424)

**Description**: Constitution VII requires: "All tenant-scoped entities MUST include `created_by_user_id` and `updated_by_user_id` columns" and "New entities MUST use `AuditMixin`." The plan argues (line 39): "ReleaseArtifact inherits audit context from its parent ReleaseManifest."

However, the constitution applies to "tenant-scoped entities." Release manifests (and artifacts) are explicitly global, not tenant-scoped (data-model.md line 61: "Release manifests (and their artifacts) are global -- not tenant-scoped"). Therefore, Constitution VII technically does not apply to ReleaseArtifact.

The issue is that the plan's justification is imprecise. It says "inherits audit context from parent" rather than the correct argument: "ReleaseArtifact is not tenant-scoped, therefore Constitution VII does not apply." This imprecision could set a bad precedent for future entities.

**Recommendation**: Update the Constitution Check for VII in plan.md to: "`ReleaseArtifact` is a global entity (not tenant-scoped), consistent with its parent `ReleaseManifest`. Constitution VII applies to tenant-scoped entities only, so `AuditMixin` is not required. The parent manifest already has full audit tracking."

---

### Pass 5: Coverage Gap Analysis

#### G-001 | HIGH | Spec FR references in tasks use non-existent FR numbers from the PRD

**Affected artifacts**: `tasks.md`, `spec.md`

**Description**: Several tasks reference FR numbers that exist in the PRD but not in the spec:
- T020 references `FR-800.4` (PRD number)
- T039 references `FR-600.2 through FR-600.11` (PRD numbers)
- T040 references `FR-600.3a` (PRD number)
- T041 references `FR-600.4, FR-600.5` (PRD numbers)
- T042 references `FR-600.6, FR-600.7` (PRD numbers)
- T043 references `FR-600.9` (PRD numbers)
- T025 references `FR-700.2, FR-700.3` (PRD numbers)
- T021 references `FR-002, FR-025, FR-028` (spec numbers -- correct)
- T026 references `FR-004 through FR-008` (spec numbers -- correct)

The spec uses a flat numbering scheme (FR-001 through FR-041) while the PRD uses a hierarchical scheme (FR-100.1, FR-200.1, etc.). Tasks inconsistently reference both. This makes traceability difficult.

**Recommendation**: Standardize all task FR references to use the spec's FR-001 through FR-041 numbering. When the spec does not cover a PRD-level detail (e.g., specific plist template content), reference the PRD section explicitly: "per PRD FR-600.4."

---

#### G-002 | MEDIUM | FR-030 (accessibility) is only partially covered by tasks

**Affected artifacts**: `spec.md` (FR-030), `tasks.md` (T037)

**Description**: FR-030 requires: "keyboard-navigable (Tab through fields, Enter to proceed, Escape to close with confirmation) and include accessible labels on all interactive elements." T037 covers keyboard navigation and aria-labels for Copy buttons. However, FR-030's "accessible labels on all interactive elements" extends to:
- Platform dropdown (aria-label)
- Token name input (aria-label or associated label)
- Expiration input (aria-label or associated label)
- Binary path input (aria-label or associated label)
- Service user input (aria-label or associated label)
- Back/Next/Done buttons (should be clear by default)

T037 only mentions "aria-label to all Copy buttons" and "aria-current=step" for StepIndicator. The form field labels are not explicitly tasked.

**Recommendation**: Expand T037 or add acceptance criteria: "All form inputs (token name, expiration, binary path, service user, platform dropdown) MUST have associated `<label>` elements or `aria-label` attributes."

---

#### G-003 | LOW | No explicit task for FR-016 (server URL resolution and validation)

**Affected artifacts**: `spec.md` (FR-016), `tasks.md` (T023)

**Description**: FR-016 says: "The server URL in the register command MUST be resolved from the application's API base URL configuration, falling back to the current page origin, and MUST be validated as a well-formed URL." T023 mentions `import.meta.env.VITE_API_BASE_URL || window.location.origin` with URL validation. While the implementation is described in T023, there is no dedicated test for server URL resolution edge cases (malformed VITE_API_BASE_URL, missing env var, URL with trailing slashes, URL with path components).

**Recommendation**: Add URL resolution test cases to the wizard component tests (see U-002). Test cases should include: undefined env var, empty string, malformed URL, URL with trailing slashes, URL with path (e.g., `https://example.com/api`).

---

### Pass 6: Cross-Document Inconsistency

#### X-001 | HIGH | PRD uses `AGENT_DIST_BASE_URL` (external URL) while spec/plan use `SHUSAI_AGENT_DIST_DIR` (local directory)

**Affected artifacts**: `docs/prd/136-agent-setup-wizard.md` (lines 632-636), `spec.md` (FR-037), `plan.md` (line 77), `research.md` (R3)

**Description**: This is the most significant architectural evolution between PRD and spec:

- **PRD**: Uses `AGENT_DIST_BASE_URL` as an external URL (e.g., `https://cdn.example.com/agent-dist/`). The frontend constructs download URLs as `{download_base_url}/{artifact.filename}`. Downloads are unauthenticated from a static CDN.
- **Spec**: Uses `SHUSAI_AGENT_DIST_DIR` as a local filesystem path. The server itself serves binaries through an authenticated endpoint. Signed URLs replace CDN access for remote machines.

Research R3 documents this change and its rationale. The spec adds FR-037 through FR-041 for the new approach. However:

1. The PRD's response schema includes `download_base_url` as a top-level field. The spec/contracts remove this and instead include `download_url` and `signed_url` per artifact.
2. The PRD's FR-200.7 references `download_base_url` which no longer exists in the spec.
3. The plan says "Primarily frontend wizard UI with one new backend endpoint" in the PRD summary, but the actual scope is three new endpoints (active release, binary download, extended admin) plus a new DB table.

This is an intentional evolution but creates confusion if someone reads the PRD as authoritative.

**Recommendation**: Add a prominent note at the top of the PRD (or in the Revision History) stating: "Note: The binary distribution architecture was revised during specification. The PRD's `AGENT_DIST_BASE_URL` approach (static CDN) was replaced with `SHUSAI_AGENT_DIST_DIR` (server-hosted with authenticated downloads and signed URLs). See spec.md FR-037 through FR-041 for the current design." This prevents future readers from being misled by the PRD's architecture section.

---

#### X-002 | MEDIUM | PRD response schema differs from contract schema

**Affected artifacts**: `docs/prd/136-agent-setup-wizard.md` (lines 648-672), `contracts/active-release.md` (lines 32-56)

**Description**: The PRD's response schema includes:
```json
{
  "guid": "...",
  "version": "...",
  "download_base_url": "https://cdn.example.com/agent-dist/1.0.0/",
  "artifacts": [{ "platform": "...", "filename": "...", "checksum": "..." }],
  "notes": "..."
}
```

The contract's response schema includes:
```json
{
  "guid": "...",
  "version": "...",
  "artifacts": [{ "platform": "...", "filename": "...", "checksum": "...", "file_size": ..., "download_url": "...", "signed_url": "..." }],
  "notes": "...",
  "dev_mode": false
}
```

Key differences: (1) `download_base_url` removed from top level, (2) `download_url` and `signed_url` added per artifact, (3) `file_size` added per artifact, (4) `dev_mode` added at top level, (5) PRD artifacts have no `file_size`, `download_url`, or `signed_url`. The contract is the authoritative version, but the PRD is misleading.

**Recommendation**: Same as X-001 -- add a deprecation note to the PRD's Release Manifest API section.

---

#### X-003 | MEDIUM | Plan references "FR-800.4" but spec has no FR-800 series

**Affected artifacts**: `tasks.md` (T020, line 65)

**Description**: T020 references "FR-800.4" which is a PRD requirement number (FR-800.4: step titles visible in indicator). The spec does not use the FR-800 numbering -- it uses FR-003 for the step indicator. The task should reference FR-003 from the spec, not FR-800.4 from the PRD.

**Recommendation**: Update T020 to reference FR-003 from spec.md. This is a subset of the broader issue in G-001.

---

#### X-004 | LOW | Data-model.md shows `ReleaseArtifact` without `team_id` but doesn't reference why

**Affected artifacts**: `data-model.md` (line 61)

**Description**: The data model notes "No team_id: Release manifests (and their artifacts) are global -- not tenant-scoped." This is correct and consistent with the constitution analysis. However, the data model does not reference the constitution's tenant isolation requirement (V) to explain why this is an acceptable deviation. A reader unfamiliar with the project might question why a new entity lacks team_id.

**Recommendation**: Add a brief reference: "Global scope is consistent with the existing `ReleaseManifest` model and does not violate Constitution V (tenant isolation applies to tenant-scoped entities only)."

---

#### X-005 | LOW | quickstart.md test paths don't match plan.md project structure

**Affected artifacts**: `quickstart.md` (lines 110-117), `plan.md` (lines 109-114)

**Description**: The quickstart shows test paths as:
- `frontend/src/tests/lib/os-detection.test.ts`
- `frontend/src/tests/components/agents/wizard/`

The plan shows:
- `frontend/tests/lib/os-detection.test.ts`
- `frontend/tests/components/agents/wizard/`

The difference is `frontend/src/tests/` vs `frontend/tests/`. This affects whether tests live inside or outside the `src/` directory.

**Recommendation**: Verify the existing test directory convention in the codebase and standardize. Update whichever document is incorrect.

---

#### X-006 | INFO | Plan mentions `useClipboard()` hook but doesn't verify it handles all CopyableCodeBlock requirements

**Affected artifacts**: `plan.md`, `research.md` (R5)

**Description**: Research R5 identifies `useClipboard()` from `frontend/src/hooks/useClipboard.ts` as providing "copied state with auto-reset and Copy->Check icon swap." T006 references this. However, the spec requires "visual feedback (e.g., checkmark for 2 seconds)" -- the existing hook's auto-reset timing should be verified to match the 2-second requirement.

**Recommendation**: During T006 implementation, verify the `useClipboard()` hook's auto-reset duration matches the 2-second spec requirement. If it differs, adjust.

---

#### X-007 | INFO | research.md R7 mentions PUT endpoint for independent artifact management that's nowhere else

**Affected artifacts**: `research.md` (R7, line 119)

**Description**: Research R7 states: "A new `PUT /api/admin/release-manifests/{guid}/artifacts` endpoint allows managing artifacts independently." This endpoint appears in no other artifact (not in tasks.md, not in contracts/, not in plan.md's project structure, not in spec.md). It appears to be a research-phase idea that was not carried forward.

**Recommendation**: Either remove this from research.md (since it was not adopted), or add a "Deferred" note. Since research.md is a historical record of decisions, adding "(Deferred to future iteration)" is the cleaner approach.

---

#### X-008 | INFO | Spec edge case about WebGL mentions "lower-confidence detection" but confidence is only 'high' | 'low'

**Affected artifacts**: `spec.md` (Edge Cases, line 105), PRD (line 467)

**Description**: The spec says: "The wizard falls back to a lower-confidence detection." The PRD's `DetectedOS` interface has `confidence: 'high' | 'low'`. The actual behavior for WebGL failure is: macOS is detected as `darwin-amd64` (Intel) with `high` confidence since the `checkAppleSilicon()` function returns `false`. There is no "lower-confidence" state for this specific case -- the confidence is still `high` because the OS family is correctly detected, only the architecture might be wrong.

**Recommendation**: This is a minor wording inconsistency in the spec's edge case description. The actual behavior (defaulting to Intel when WebGL fails) is correct. The edge case text could be refined to: "The wizard defaults to Intel architecture when Apple Silicon detection fails, and always allows manual override."

---

#### X-009 | INFO | `hmac.new` in contracts/binary-download.md should be `hmac.new` (correct Python)

**Affected artifacts**: `contracts/binary-download.md` (lines 152, 181)

**Description**: The code sample uses `hmac.new()` which is the correct Python API. This is informational -- no issue found. The code is syntactically correct.

**Recommendation**: No action needed.

---

## Coverage Matrix

### Spec Requirements (FR-001 through FR-041) to Task Mapping

| Requirement | Description | Task(s) | Status |
|-------------|-------------|---------|--------|
| FR-001 | "Agent Setup" button on Agents page | T029 | Covered |
| FR-002 | Multi-step wizard dialog with 6 steps | T021 | Covered |
| FR-003 | Step indicator with progress | T020 | Covered |
| FR-004 | OS auto-detection | T004 | Covered |
| FR-005 | Platform display + override dropdown | T026, T033 | Covered |
| FR-006 | Platform override warning | T044 | Covered |
| FR-007 | Active release manifest + download button | T013, T026, T028, T031 | Covered |
| FR-008 | Degradation for missing manifest/artifact/insecure URL | T026, T031 | Covered |
| FR-009 | Download failure handling + retry | T031 | Covered |
| FR-010 | Token name and expiration inputs | T022 | Covered |
| FR-011 | Plaintext token display + copy + warning | T022 | Covered |
| FR-012 | Token preservation on back navigation | T035 | Covered |
| FR-013 | Block proceeding past Step 2 without token | T036 | Covered |
| FR-014 | OS-specific registration instructions + command | T023 | Covered |
| FR-015 | chmod +x for macOS/Linux | T023 | Covered |
| FR-016 | Server URL resolution + validation | T023 | Covered |
| FR-017 | Launch commands + collapsible previous commands | T024 | Covered |
| FR-018 | Binary path input + validation | T039, T040 | Covered |
| FR-019 | macOS launchd plist generation | T005, T041 | Covered |
| FR-020 | Linux systemd unit generation | T005, T042 | Covered |
| FR-021 | Windows unsupported message | T043 | Covered |
| FR-022 | Service step skippable | T039 | Covered |
| FR-023 | Summary step recap | T025 | Covered |
| FR-024 | Copy buttons with visual feedback | T006 | Covered |
| FR-025 | Back/Next/Done navigation | T021 | Covered |
| FR-026 | Close confirmation logic | T030 | Covered |
| FR-027 | Page refresh on wizard close | T029 | Covered |
| FR-028 | Responsive layout (min 640px, mobile stack) | T021, T046 | Covered |
| FR-029 | Token not persisted in client storage | T038 | Covered |
| FR-030 | Keyboard navigation + accessible labels | T037 | Partial (see G-002) |
| FR-031 | Existing token button unchanged | T049 | Covered |
| FR-032 | User-accessible active release endpoint | T013 | Covered |
| FR-033 | Dev/QA mode: show all platforms | T033 | Covered |
| FR-034 | Dev/QA mode: disabled download for missing binaries | T033 | Covered |
| FR-035 | Dev/QA mode: all steps functional | T033 | Covered |
| FR-036 | Production mode: only show platforms with artifacts | T033 | Covered |
| FR-037 | Server serves binaries from local directory | T014 | Covered |
| FR-038 | Binary download authentication (session + signed URL) | T012, T014 | Covered |
| FR-039 | Signed URL display in wizard | T032 | Covered |
| FR-040 | Missing binary file error handling | T014, T031 | Covered |
| FR-041 | Download URLs from manifest endpoint + degradation | T013, T026 | Covered |

**Coverage summary**: 40 of 41 requirements have full task coverage. FR-030 has partial coverage (keyboard navigation covered; comprehensive form field labels need explicit task).

### Unmapped Tasks (Potential Scope Creep Check)

| Task | Description | Mapped to FR? | Notes |
|------|-------------|---------------|-------|
| T001 | SHUSAI_AGENT_DIST_DIR setting | FR-037 (infrastructure) | Valid supporting task |
| T002 | Pydantic schemas | FR-032 (infrastructure) | Valid supporting task |
| T003 | TypeScript types | FR-032 (infrastructure) | Valid supporting task |
| T007 | OS detection tests | FR-004 (testing) | Valid test task |
| T008 | Service file generator tests | FR-019, FR-020 (testing) | Valid test task |
| T009 | ReleaseArtifact model | FR-032 (infrastructure) | Valid supporting task |
| T010 | Manifest-artifact relationship | FR-032 (infrastructure) | Valid supporting task |
| T011 | DB migration | FR-032 (infrastructure) | Valid supporting task |
| T015 | Admin POST extend for artifacts | No direct FR | Supporting admin functionality (R7) |
| T016 | Admin GET extend for artifacts | No direct FR | Supporting admin functionality (R7) |
| T017-T019 | Backend tests | Testing | Valid test tasks |
| T044-T045 | Remote platform verification | US4 acceptance scenarios | Valid |
| T046-T050 | Polish tasks | Various FRs | Valid cross-cutting tasks |
| T047 | Admin UI update for artifacts | No direct FR | Supporting admin functionality (R7) |
| T048 | .env.example update | No direct FR | DevEx improvement |

**Scope creep assessment**: T015, T016, and T047 extend the admin API/UI for artifact management. These are not directly required by any spec FR but are necessary for administrators to create manifests with artifacts. This is a reasonable implicit dependency, not scope creep.

---

## Constitution Compliance Summary

| Principle | Pass/Fail | Notes |
|-----------|-----------|-------|
| I. Agent-Only Tool Execution | PASS | Not applicable -- wizard does not execute analysis tools |
| II. Testing & Quality | PASS with caveat | Test tasks exist for utilities and backend. **Caveat**: No explicit tasks for frontend wizard component tests (see U-002). Coverage target (>= 80%) may not be met without them. |
| III. User-Centric Design | PASS | Comprehensive graceful degradation, copy-ready commands, platform-specific guidance, actionable error messages |
| IV. Global Unique Identifiers | PASS with documented exception | ReleaseArtifact lacks GuidMixin. Justified in plan but not in Complexity Tracking table as required (see C-001). Fix: add to Complexity Tracking. |
| V. Multi-Tenancy & Authentication | PASS | Active release endpoint uses `get_tenant_context`. Download endpoint supports session + signed URL auth. Release data is global (not tenant-scoped), consistent with existing model. |
| VI. Agent-Only Execution | PASS | Not applicable -- wizard helps set up agents, does not execute jobs |
| VII. Audit Trail & User Attribution | PASS | ReleaseArtifact is global (not tenant-scoped), so AuditMixin is not required. Plan justification should be more precise (see C-002). |
| Frontend: TopHeader KPI Pattern | PASS | Wizard is a modal overlay, not a page. No new KPIs needed. |
| Frontend: Single Title Pattern | PASS | Wizard uses Dialog title. No `<h1>` in content. |

---

## Appendix: Artifact Quality Ratings

| Artifact | Quality | Notes |
|----------|---------|-------|
| spec.md | High | Clear requirements, good edge cases, clean FR numbering. Minor gap: accessibility details (FR-030). |
| plan.md | High | Strong constitution check, good complexity tracking, clear project structure. Minor gaps: exception documentation in Complexity Tracking. |
| tasks.md | High | Excellent parallelization annotations, clear phase dependencies. Gaps: missing wizard component tests, mixed FR numbering from spec vs PRD. |
| research.md | High | All decisions well-documented with alternatives. Minor: R7 mentions endpoint not carried forward to tasks. |
| data-model.md | High | Clear entity diagram, complete field definitions, good migration plan. |
| contracts/active-release.md | High | Complete request/response documentation, behavior notes, schema definitions. Minor: ambiguous multi-active-manifest selection. |
| contracts/binary-download.md | High | Thorough auth flow, security constraints, code samples. |
| quickstart.md | Medium-High | Good developer guide. Minor: test paths inconsistent with plan. |
| PRD | Medium-High | Comprehensive but now architecturally outdated regarding binary distribution. Needs a deprecation note for the CDN approach. |
