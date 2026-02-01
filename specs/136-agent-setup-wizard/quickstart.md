# Quickstart: Agent Setup Wizard

**Feature Branch**: `136-agent-setup-wizard`
**Date**: 2026-02-01

## Prerequisites

- Python 3.11+ with backend dependencies installed
- Node.js 18+ with frontend dependencies installed
- PostgreSQL running (or SQLite for local dev)
- Backend and frontend dev servers running

## Development Setup

### 1. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates the new `release_artifacts` table.

### 2. Configure Agent Distribution Directory (Optional)

For testing actual binary downloads, create a distribution directory:

```bash
# Create the directory structure
mkdir -p /tmp/shuttersense-agent-dist/1.0.0

# Create dummy binaries for testing
echo "dummy-darwin-arm64" > /tmp/shuttersense-agent-dist/1.0.0/shuttersense-agent-darwin-arm64
echo "dummy-linux-amd64" > /tmp/shuttersense-agent-dist/1.0.0/shuttersense-agent-linux-amd64

# Set the environment variable
export SHUSAI_AGENT_DIST_DIR=/tmp/shuttersense-agent-dist
```

If `SHUSAI_AGENT_DIST_DIR` is not set, the wizard operates in **dev mode**: all platforms are shown in the dropdown, but download buttons are disabled with an explanatory message. This is the expected behavior for development and QA environments.

### 3. Create a Release Manifest with Artifacts

Use the admin API (requires super admin session) to create a manifest:

```bash
curl -X POST http://localhost:8000/api/admin/release-manifests \
  -H "Content-Type: application/json" \
  -b "session=<your-session-cookie>" \
  -d '{
    "version": "1.0.0",
    "platforms": ["darwin-arm64", "linux-amd64"],
    "checksum": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    "is_active": true,
    "notes": "Test release",
    "artifacts": [
      {
        "platform": "darwin-arm64",
        "filename": "shuttersense-agent-darwin-arm64",
        "checksum": "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
      },
      {
        "platform": "linux-amd64",
        "filename": "shuttersense-agent-linux-amd64",
        "checksum": "sha256:b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3"
      }
    ]
  }'
```

### 4. Test the Wizard

1. Open the web app and navigate to the **Agents** page.
2. Click the **"Agent Setup"** button (next to "New Registration Token").
3. The wizard opens. Verify:
   - **Step 1**: OS is auto-detected. If `SHUSAI_AGENT_DIST_DIR` is configured and artifacts exist, the download button is active. Otherwise, a dev-mode message is shown.
   - **Step 2**: Token creation form. Create a token and verify the copy button works.
   - **Step 3**: Registration command is pre-populated with the server URL and your token.
   - **Step 4**: Start and self-test commands are displayed.
   - **Step 5**: Service file generator works for macOS (plist) and Linux (systemd).
   - **Step 6**: Summary shows the setup recap.

## Testing the Wizard in Dev/QA Mode

When `SHUSAI_AGENT_DIST_DIR` is **not set** (the default for local development):

- The active release endpoint returns `"dev_mode": true`.
- The wizard shows all 5 platform options regardless of which artifacts exist in the manifest.
- Download buttons are disabled with the message: "Agent binary for {platform} is not available in this environment."
- All other steps (token creation, commands, service files) work normally for any selected platform.

This allows QA reviewers to exercise every wizard path without needing actual agent binaries on disk.

## Running Tests

### Backend Tests

```bash
# Run all release artifact and download service tests
python3 -m pytest backend/tests/unit/test_release_artifact.py -v
python3 -m pytest backend/tests/unit/test_download_service.py -v
```

### Frontend Tests

```bash
cd frontend

# Run OS detection tests
npx vitest run src/tests/lib/os-detection.test.ts

# Run service file generator tests
npx vitest run src/tests/lib/service-file-generator.test.ts

# Run wizard component tests
npx vitest run src/tests/components/agents/wizard/
```

## Key Files Reference

### Backend

| File | Purpose |
|------|---------|
| `backend/src/models/release_artifact.py` | ReleaseArtifact SQLAlchemy model |
| `backend/src/services/download_service.py` | Binary file serving + signed URL logic |
| `backend/src/api/agent/routes.py` | Active release + download endpoints |
| `backend/src/config/settings.py` | `SHUSAI_AGENT_DIST_DIR` setting |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/components/agents/AgentSetupWizardDialog.tsx` | Root wizard dialog with state management |
| `frontend/src/components/agents/wizard/*.tsx` | Individual step components |
| `frontend/src/lib/os-detection.ts` | Browser OS/architecture detection |
| `frontend/src/lib/service-file-generator.ts` | launchd plist + systemd unit generators |
| `frontend/src/services/agents.ts` | `getActiveRelease()` API function |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SHUSAI_AGENT_DIST_DIR` | No | Not set | Absolute path to agent binary distribution directory. If not set, binary downloads are disabled and wizard operates in dev/QA mode. |
| `JWT_SECRET_KEY` | Yes (existing) | — | Used for signed download URL generation (HMAC-SHA256). Already required for API token authentication. |
