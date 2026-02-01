# Research: Agent Setup Wizard

**Feature Branch**: `136-agent-setup-wizard`
**Date**: 2026-02-01

## R1: Release Manifest Data Model Gap (Per-Platform Artifacts)

**Problem**: The spec requires per-platform artifacts (each with its own filename, checksum, and platform identifier), but the current `ReleaseManifest` model stores a single `checksum` field and a `platforms_json` array of platform strings. This was intentionally designed for universal binaries (one binary covering multiple platforms), not for per-platform binaries.

**Decision**: Introduce a new `release_artifacts` child table.

**Rationale**:
- The wizard needs to show per-platform download links with correct filenames and checksums.
- Agent binary distribution typically produces separate binaries per platform (e.g., `shuttersense-agent-darwin-arm64`, `shuttersense-agent-linux-amd64`), each with a different checksum.
- The existing `checksum` and `platforms_json` fields on `ReleaseManifest` remain for backward compatibility (binary attestation during agent registration still uses the single checksum).
- A child `release_artifacts` table cleanly separates the "which platforms does this version support" concern (existing) from the "what is the downloadable file for each platform" concern (new).

**Alternatives considered**:
1. **Embed artifacts as JSON array in `platforms_json`** — Rejected. Mixing platform strings with artifact metadata in the same column is fragile, hard to query, and breaks the existing admin API contract.
2. **Replace `checksum`/`platforms_json` with artifacts table** — Rejected. This would be a breaking change to the existing admin release manifest API and the agent registration binary attestation flow.
3. **One `ReleaseManifest` row per platform** — Rejected. This was the original design (migration 045) but was intentionally changed to multi-platform (migration 046) to support universal binaries. Reverting would break existing data.

**Migration strategy**:
- Add `release_artifacts` table with FK to `release_manifests.id`.
- Existing manifests continue to work without artifacts (the wizard treats missing artifacts as "no download available" — graceful degradation per FR-008).
- The admin API for creating manifests gains an optional `artifacts` array. Existing clients that don't send artifacts continue to work.

## R2: Authenticated Binary Download with Signed URLs

**Problem**: Agent binaries must be downloadable from the application server with authentication. Two methods are needed: session cookie (in-browser) and signed URL (remote/headless machines).

**Decision**: HMAC-signed URLs using the existing `JWT_SECRET_KEY`.

**Rationale**:
- The download URL contains: manifest GUID, platform, expiration timestamp, and an HMAC-SHA256 signature over these fields.
- The server verifies the signature and checks expiration before serving the file.
- This approach is simpler than minting JWTs for a single-purpose download link.
- The existing `JWT_SECRET_KEY` (required, min 32 chars, already in all deployments) serves as the HMAC key — no new secrets needed.
- Session-based download uses the standard `get_tenant_context` dependency — no changes needed.

**Signed URL format**:
```
/api/agent/v1/releases/{manifest_guid}/download/{platform}?expires={unix_timestamp}&signature={hmac_hex}
```

**Signature computation**:
```
message = f"{manifest_guid}:{platform}:{expires_timestamp}"
signature = HMAC-SHA256(key=JWT_SECRET_KEY, message=message).hexdigest()
```

**Alternatives considered**:
1. **JWT-based signed URLs** — Rejected. JWTs include unnecessary overhead (header, claims structure, base64 encoding) for what is essentially a simple "is this URL valid?" check.
2. **Temporary download tokens stored in DB** — Rejected. Adds unnecessary DB writes/reads for a stateless operation. HMAC verification is stateless and faster.
3. **No authentication on downloads** — Rejected. Spec requires authenticated downloads (FR-038).

## R3: Binary Distribution Directory Configuration

**Problem**: The server needs to know where agent binaries are stored on disk to serve them.

**Decision**: New environment variable `SHUSAI_AGENT_DIST_DIR` added to `AppSettings`.

**Rationale**:
- Follows the existing pattern of `SHUSAI_SPA_DIST_PATH` for frontend static files.
- The `SHUSAI_` prefix is consistent with all other ShutterSense environment variables.
- Directory structure: `{SHUSAI_AGENT_DIST_DIR}/{version}/{filename}` (e.g., `/opt/shuttersense/agent-dist/1.0.0/shuttersense-agent-darwin-arm64`).
- If not configured, the download endpoints return appropriate errors and the wizard degrades gracefully.

**Alternatives considered**:
1. **`AGENT_DIST_BASE_URL` as in the PRD** — The PRD assumed external CDN hosting. Since the first deployment serves binaries from the application server itself, a local directory path is more appropriate. The variable name was changed to `SHUSAI_AGENT_DIST_DIR` to match the project's naming convention and to clearly indicate it's a local filesystem path, not a URL.
2. **Relative to project root (like SPA dist)** — Not chosen as default because agent binaries are administrator-managed artifacts, not build outputs. An explicit absolute path is safer.

## R4: Dev/QA Mode Detection

**Problem**: In dev/QA environments, agent binaries may not be available. The wizard needs to show all platforms for testing while disabling downloads for missing binaries.

**Decision**: Frontend uses `import.meta.env.DEV` (already available via Vite). Backend includes a `dev_mode` flag in the active release response.

**Rationale**:
- Vite's `import.meta.env.DEV` is `true` during development (Vite dev server) and `false` in production builds. This is already used in the codebase for API request logging (`frontend/src/services/api.ts`).
- The backend adds a `dev_mode: boolean` field to the active release response, derived from `settings.debug` or absence of `SHUSAI_AGENT_DIST_DIR`. This allows the frontend to also handle QA environments that run production builds but don't have binaries configured.
- The frontend uses `import.meta.env.DEV || response.dev_mode` to determine whether to show all platforms.

**Alternatives considered**:
1. **Frontend-only detection** — Insufficient. QA environments may run production frontend builds. A backend signal is needed.
2. **Separate `SHUSAI_WIZARD_DEV_MODE` env var** — Over-engineering. The absence of a configured distribution directory is a natural signal.

## R5: Existing Frontend Patterns to Reuse

**Decision**: Reuse established patterns from the existing codebase.

**Findings**:
- **Dialog pattern**: `CreateCollectionsDialog.tsx` provides the best reference for multi-step wizards — step badges, `max-w-4xl max-h-[90vh]`, `ScrollArea`, state reset on close with 200ms delay.
- **Token creation**: `RegistrationTokenDialog.tsx` has a two-step form→token pattern. The wizard's Step 2 reuses `useRegistrationTokens().createToken` directly.
- **Copy-to-clipboard**: `useClipboard()` hook from `frontend/src/hooks/useClipboard.ts` — provides `copied` state with auto-reset and Copy→Check icon swap.
- **API service pattern**: All API functions in `frontend/src/services/agents.ts` use the shared `api` axios instance with GUID validation via `validateGuid()`.
- **Platform labels**: `PLATFORM_LABELS` mapping already exists in `frontend/src/contracts/api/release-manifests-api.ts` with human-friendly labels for all 5 platforms.
- **Dev mode detection**: `import.meta.env.DEV` used in `frontend/src/services/api.ts` for request/response logging.

## R6: Impact on Existing Agent Registration (Binary Attestation)

**Problem**: The existing agent registration flow validates `binary_checksum` against the `ReleaseManifest.checksum` field. Introducing per-platform artifacts must not break this.

**Decision**: The existing `ReleaseManifest.checksum` field and binary attestation logic remain unchanged.

**Rationale**:
- Binary attestation during `shuttersense-agent register` uses `ReleaseManifest.checksum` — a single checksum that the agent computes from its own binary and sends to the server.
- The new `release_artifacts` table is used only by the wizard for download purposes. It has its own `checksum` field per platform.
- In practice, the `ReleaseManifest.checksum` can be set to the checksum of any one of the platform binaries (or a universal binary), while `release_artifacts` stores the correct checksum for each individual platform binary.
- This decoupling means the existing registration flow is completely unaffected.

## R7: Admin API Impact (Release Manifest CRUD)

**Decision**: Extend the existing admin endpoints to support artifact management.

**Rationale**:
- `POST /api/admin/release-manifests` gains an optional `artifacts` array in the request body. If provided, the artifacts are created alongside the manifest. If omitted, behavior is unchanged.
- `GET /api/admin/release-manifests/{guid}` includes artifacts in the response.
- *(Deferred to future iteration)* A `PUT /api/admin/release-manifests/{guid}/artifacts` endpoint for managing artifacts independently (add/remove/update) is not needed for MVP — artifacts are created alongside manifests via the extended POST endpoint.
- The existing `ReleaseManifestsTab.tsx` in the admin settings UI will need minor updates to display and manage artifacts.
