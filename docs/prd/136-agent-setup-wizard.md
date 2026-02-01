# PRD: Agent Setup Wizard

**Issue**: [#136 — Create an 'Agent Setup' Wizard in the Agent Page](https://github.com/fabrice-guiot/shuttersense/issues/136)
**Status**: Draft
**Created**: 2026-01-31
**Last Updated**: 2026-01-31
**Related Documents**:
- [Domain Model](../domain-model.md)
- [Design System](../../frontend/docs/design-system.md)
- [Distributed Agent Architecture](./021-distributed-agent-architecture.md)

> **Note — Architectural Revision**: The binary distribution approach described in this PRD (`AGENT_DIST_BASE_URL` pointing to a static CDN/file server) was revised during the specification phase. The implementation uses `SHUSAI_AGENT_DIST_DIR` (a local server directory) with authenticated binary downloads and HMAC-signed URLs for remote access. See `specs/136-agent-setup-wizard/spec.md` FR-037 through FR-041 and `specs/136-agent-setup-wizard/contracts/binary-download.md` for the current design. The PRD's `download_base_url` field in the API response has been replaced with per-artifact `download_url` and `signed_url` fields, and a top-level `dev_mode` flag was added.

---

## Executive Summary

This PRD defines a guided, multi-step **Agent Setup Wizard** embedded in the Agents page of the ShutterSense web application. The wizard walks users through the entire agent onboarding lifecycle — from downloading the correct binary for their operating system, through registration token creation and agent registration, to optional background service configuration — all without leaving the browser.

Today, setting up an agent requires switching between the web UI (to create a registration token), a documentation page (to find the right binary and learn CLI commands), and a terminal (to run them). The wizard consolidates these steps into a single, linear flow that adapts its instructions and downloads to the detected OS.

Key design decisions:
- **OS auto-detection with manual override** — `navigator.userAgent` / `navigator.platform` is used for initial detection; the user can override if they are setting up a remote machine.
- **Primarily frontend wizard UI with one new backend endpoint** — All wizard logic lives in the frontend. This feature requires adding one new read-only backend endpoint (`GET /api/agent/v1/releases/active`) that does not exist today; the existing release manifest endpoints at `/api/admin/release-manifests` require super-admin privileges and cannot be called by regular users.
- **Agent binaries served from a static distribution folder** — The server hosts pre-built agent binaries at a well-known path configured via the `AGENT_DIST_BASE_URL` environment variable; the wizard constructs download links from the release manifest metadata returned by the new endpoint.

---

## Background

### Current State

Agent onboarding currently involves the following manual steps:

1. Navigate to the **Agents** page in the web app.
2. Click **New Registration Token** and copy the generated token.
3. Download the correct agent binary for the target OS (currently undocumented in the UI).
4. Open a terminal and run `shuttersense-agent register --server <URL> --token <TOKEN>`.
5. Run `shuttersense-agent start` to launch the agent.
6. (Optionally) configure a system service (launchd on macOS, systemd on Linux) for automatic startup.

Users must piece together information from documentation, the web UI, and the CLI `--help` output. There is no in-app guidance for steps 3–6.

### Affected Files (Existing)

- `frontend/src/pages/AgentsPage.tsx` — Agents list page with the "New Registration Token" button
- `frontend/src/components/agents/RegistrationTokenDialog.tsx` — Current token creation dialog
- `frontend/src/services/agents.ts` — Agent API service
- `frontend/src/hooks/useAgents.ts` — Agent hooks
- `frontend/src/contracts/api/agent-api.ts` — Agent API contracts
- `backend/src/models/release_manifest.py` — Release manifest model (platforms, checksums)
- `backend/src/api/agent/routes.py` — Agent API routes

### Problem Statement

- **High friction**: Setting up an agent requires context-switching between the browser, documentation, and a terminal across 6+ distinct steps.
- **Error-prone OS matching**: Users must manually identify the correct binary for their OS and architecture. Downloading the wrong binary is a silent failure that surfaces only at registration time.
- **No service setup guidance**: Background service configuration (launchd, systemd) is undocumented and platform-specific, leading most users to run agents in foreground-only mode.
- **Disconnected token flow**: The existing token dialog shows the token and a generic CLI command but offers no continuity into subsequent steps.

### Strategic Context

ShutterSense's distributed architecture relies on agents for all job execution (Issue #90). Reducing agent setup friction directly increases agent adoption, which in turn increases the platform's processing capacity and value to teams. A guided wizard is the highest-impact UX improvement for new team onboarding.

---

## Goals

### Primary Goals

1. **Reduce agent setup time** — Consolidate all setup steps into a single wizard flow that can be completed in under 5 minutes.
2. **Eliminate OS mismatch errors** — Auto-detect the user's OS and architecture and present only the correct binary download.
3. **Provide copy-ready CLI commands** — Every terminal command shown in the wizard is pre-populated with actual values (server URL, token) and copyable with one click.
4. **Guide background service setup** — Offer platform-specific service file generation (launchd `.plist`, systemd `.service`) with installation instructions.

### Secondary Goals

5. **Educate users** — Each wizard step includes a brief explanation of what is happening and why, building user understanding of the agent model.
6. **Support remote machine setup** — Allow users to manually select a different OS than detected, for cases where the target machine is not the browser machine.

### Non-Goals

- **Automated remote installation** — The wizard does not SSH into or remotely install agents on other machines. It provides instructions the user copies to the target machine.
- **Auto-update mechanism** — The wizard covers initial setup only. Agent auto-update is a separate feature.
- **Windows service setup** — Windows background service configuration (NSSM / Task Scheduler) is deferred to a future iteration due to complexity; the wizard will note this limitation.
- **Agent binary build pipeline** — This PRD assumes agent binaries are already built and available in the distribution folder. The CI/CD pipeline for building them is out of scope.

---

## User Personas

### Team Administrator

Sets up the ShutterSense infrastructure for their team. Needs to provision agents on one or more machines (studio workstations, NAS servers). Comfortable with terminal commands but appreciates guided workflows that reduce documentation lookups.

### Photographer / End User

May need to set up an agent on their personal machine to process local photo collections. Less comfortable with CLI tools. Needs clear, step-by-step instructions with minimal jargon.

---

## Requirements

### Functional Requirements

#### FR-100: Wizard Entry Point

**FR-100.1**: The Agents page (`AgentsPage.tsx`) MUST display an **"Agent Setup"** button adjacent to the existing "New Registration Token" button.

**FR-100.2**: The button MUST open a multi-step wizard dialog (modal).

**FR-100.3**: The button SHOULD use the `Wand2` (or similar guidance-oriented) Lucide icon to visually differentiate it from the token button.

**FR-100.4**: The button MUST be available to all authenticated users with access to the Agents page (same authorization as "New Registration Token").

#### FR-200: Step 1 — OS Detection & Download

**FR-200.1**: On wizard open, the wizard MUST auto-detect the user's operating system and architecture using `navigator.userAgent` and/or `navigator.platform`.

**FR-200.2**: The detected platform MUST be mapped to a ShutterSense platform identifier from the set: `darwin-arm64`, `darwin-amd64`, `linux-amd64`, `linux-arm64`, `windows-amd64`.

**FR-200.3**: The wizard MUST display the detected OS with a human-friendly label (e.g., "macOS (Apple Silicon)", "Linux (x86_64)") and a corresponding OS icon.

**FR-200.4**: The user MUST be able to override the detected OS by selecting from a dropdown of all available platforms.

**FR-200.5**: When the user overrides the OS, the wizard MUST display a warning: *"You selected a different platform than detected. Make sure this matches the machine where you will install the agent."*

**FR-200.6**: The wizard MUST fetch the active release manifest from a **new** user-accessible endpoint `GET /api/agent/v1/releases/active` (see [Release Manifest API](#release-manifest-api)). The existing admin endpoints at `/api/admin/release-manifests` require super-admin privileges and are not suitable for regular wizard users. The response contains an `artifacts` array with per-platform entries, each specifying `platform`, `filename`, and `checksum`.

**FR-200.7**: If a matching artifact exists for the selected platform in the manifest's `artifacts` array **and** `download_base_url` is non-null **and** passes the HTTPS check (FR-200.7a), the wizard MUST display a **"Download Agent"** button that initiates a download of the binary using `{download_base_url}/{artifact.filename}`. If `download_base_url` is `null` (server's `AGENT_DIST_BASE_URL` env var is not configured), the wizard MUST hide the download button and show the same warning banner as FR-200.9.

**FR-200.7a**: Before enabling the download button, the wizard MUST validate that `download_base_url` starts with `https://` and parses as a well-formed URL. If the check fails (e.g., `http://` or malformed), the wizard MUST NOT show the download button and MUST display a warning: *"The agent download URL is not served over HTTPS. Downloads are disabled for security. Contact your administrator to configure a secure distribution URL."* The "Next" button MUST remain enabled (same degradation as FR-200.9). **Exception**: `http://localhost` and `http://127.0.0.1` are permitted for local development environments.

**FR-200.7b**: If the download initiated by the "Download Agent" button (FR-200.7) fails due to a network error, HTTP error (e.g., 404 Not Found, 500 Server Error), or CORS restriction, the wizard MUST display an inline error message: *"Download failed: {error_details}. Verify the distribution URL is correct and accessible."* The wizard MUST replace the "Download Agent" button with a **"Retry Download"** button that re-attempts the same request. A secondary note MUST read: *"If the problem persists, contact your administrator."* The "Next" button MUST remain enabled so the user can continue the wizard even if the download must be obtained through other means.

**FR-200.8**: If no matching artifact exists for the selected platform, the wizard MUST display an informational message: *"No agent build is available for {platform}. You can continue to create a registration token and view CLI commands, but you will need to obtain the agent binary separately. Contact your administrator."* The "Next" button MUST remain enabled so the user can proceed with the remaining wizard steps (consistent with the graceful-degradation behavior of FR-200.9).

**FR-200.9**: If no release manifests exist at all (no builds uploaded yet), the wizard MUST display a warning banner: *"No agent builds have been published yet. You can continue to create a registration token and view CLI commands, but you will need to obtain the agent binary separately. Contact your administrator to upload agent binaries."* The "Next" button MUST remain enabled so the user can proceed with the token-creation and CLI-reference steps of the wizard.

**FR-200.10**: The download button SHOULD display the artifact's `filename` and file size when available.

**FR-200.11**: The wizard MUST display the per-platform `checksum` from the matching artifact so the user can verify download integrity.

#### FR-300: Step 2 — Registration Token

**FR-300.1**: Step 2 MUST replicate the existing registration token creation flow from `RegistrationTokenDialog`.

**FR-300.2**: The wizard MUST allow the user to optionally name the token (e.g., "Studio Mac Agent").

**FR-300.3**: The wizard MUST allow the user to set the token expiration (1–168 hours, default 24).

**FR-300.4**: Upon token creation, the wizard MUST display the plaintext token with a **"Copy"** button.

**FR-300.5**: The wizard MUST display a warning: *"This token will only be shown once. Copy it now."*

**FR-300.6**: If a token has already been created in this wizard session, navigating back to Step 2 and forward again MUST NOT create a duplicate token. The wizard MUST redisplay the previously created plaintext token value with a **"Copy"** button and a notice: *"This token was previously created in this session — store it securely now."* The token creation form MUST be hidden and replaced with this read-only display. The token value MUST remain accessible (not masked behind a "Show" toggle) because the user may need to copy it again for the registration step.

**FR-300.7**: The wizard MUST NOT allow proceeding to Step 3 until a token has been created and is visible.

#### FR-400: Step 3 — Agent Registration

**FR-400.1**: Step 3 MUST display OS-specific instructions for registering the agent.

**FR-400.2**: The wizard MUST display a pre-populated, copy-ready `register` command:
```bash
shuttersense-agent register --server {server_url} --token {token}
```

**FR-400.3**: The `{server_url}` MUST be resolved from the application's API base URL configuration (e.g., the `apiBaseUrl` value already used by the frontend HTTP client in `frontend/src/services/`). If the config value is not set, `window.location.origin` MUST be used as a fallback. Before substitution, the resolved URL MUST be validated (well-formed URL with scheme) and normalized (trailing slashes stripped). If validation fails (malformed URL), the wizard MUST display an error: *"Cannot determine the server URL. Check the application's API base URL configuration."* and MUST disable the register command's "Copy" button. The `{server_url}` placeholder MUST NOT be substituted with an invalid value.

**FR-400.4**: The `{token}` MUST be the token generated in Step 2.

**FR-400.5**: For macOS and Linux, the wizard MUST include a preliminary step to make the binary executable:
```bash
chmod +x ./shuttersense-agent
```

**FR-400.6**: The wizard MUST display the expected output of a successful registration (e.g., *"Agent registered successfully. GUID: agt_..."*).

**FR-400.7**: Each command block MUST have its own **"Copy"** button.

#### FR-500: Step 4 — Agent Launch

**FR-500.1**: Step 4 MUST display the command to start the agent:
```bash
shuttersense-agent start
```

**FR-500.2**: The wizard MUST provide a brief explanation: *"This starts the agent in foreground mode. The agent will connect to the server, begin sending heartbeats, and start polling for jobs."*

**FR-500.3**: The wizard MUST display a note: *"Keep this terminal window open while the agent is running. For automatic startup, proceed to the next step to configure a background service."*

**FR-500.4**: The wizard MUST also show the `self-test` command for verifying the agent is correctly configured:
```bash
shuttersense-agent self-test
```

**FR-500.5**: All commands from previous steps (chmod, register) MUST be summarized in a collapsible "Previous Commands" section for reference.

#### FR-600: Step 5 — Background Service Setup (Optional)

**FR-600.1**: Step 5 MUST be clearly marked as **optional** and allow the user to skip it.

**FR-600.2**: The wizard MUST ask the user to provide the full path to the agent binary on the target machine (e.g., `/usr/local/bin/shuttersense-agent`).

**FR-600.3**: The wizard MUST provide a sensible default path suggestion based on the selected OS:
- macOS: `/usr/local/bin/shuttersense-agent`
- Linux: `/usr/local/bin/shuttersense-agent`
- Windows: `C:\Program Files\ShutterSense\shuttersense-agent.exe`

**FR-600.3a**: The wizard MUST validate the binary path entered in FR-600.2 / FR-600.3 with real-time feedback as the user types:
- **Absoluteness**: The path MUST be absolute — starting with `/` on macOS/Linux or a drive letter (e.g., `C:\`) on Windows. Relative paths MUST be rejected with: *"Path must be absolute (e.g., /usr/local/bin/shuttersense-agent)."*
- **OS format**: The path MUST match the OS-specific format for the selected platform. Forward slashes for macOS/Linux; backslashes (or forward slashes) for Windows.
- **Spaces warning**: If the path contains spaces, the wizard MUST display a non-blocking warning: *"Path contains spaces. It will be properly quoted/escaped in the generated service file."* The wizard MUST ensure the generated plist and systemd files handle the path correctly (no additional escaping needed for plist XML; systemd `ExecStart` does not require quoting for paths with spaces).
- **Empty path**: If the field is empty, the "Generate" / service file display MUST be disabled with a prompt to enter the path.

**FR-600.4**: For **macOS**, the wizard MUST generate a `launchd` property list (`.plist`) file content. Log paths MUST use persistent locations that survive reboots (not `/tmp`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.shuttersense.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{binary_path}</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/shuttersense/shuttersense-agent.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/shuttersense/shuttersense-agent.stderr.log</string>
</dict>
</plist>
```

**FR-600.5**: For macOS, the wizard MUST display installation commands. The commands MUST create the log directory with appropriate ownership before loading the plist:
```bash
# Create the log directory
sudo mkdir -p /var/log/shuttersense
sudo chown root:wheel /var/log/shuttersense
sudo chmod 755 /var/log/shuttersense

# Save the plist file
sudo cp ai.shuttersense.agent.plist /Library/LaunchDaemons/

# Load and start the service
sudo launchctl load /Library/LaunchDaemons/ai.shuttersense.agent.plist

# Verify the service is running
sudo launchctl list | grep shuttersense
```

**FR-600.6**: For **Linux**, the wizard MUST generate a `systemd` service unit file:
```ini
[Unit]
Description=ShutterSense Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={binary_path} start
Restart=always
RestartSec=10
User={current_user}

[Install]
WantedBy=multi-user.target
```

**FR-600.7**: For Linux, the wizard MUST display installation commands:
```bash
# Save the service file
sudo cp shuttersense-agent.service /etc/systemd/system/

# Reload systemd, enable and start
sudo systemctl daemon-reload
sudo systemctl enable shuttersense-agent
sudo systemctl start shuttersense-agent

# Verify the service is running
sudo systemctl status shuttersense-agent
```

**FR-600.8**: The generated service file content MUST be displayed in a code block with a **"Copy"** button.

**FR-600.9**: For **Windows**, the wizard MUST display a message: *"Automatic background service setup for Windows is not yet supported. You can run the agent manually or use Windows Task Scheduler."* This is a known limitation (see Non-Goals).

**FR-600.10**: The `{binary_path}` placeholder in all generated files MUST be replaced with the path the user provided in FR-600.2.

**FR-600.11**: The Linux systemd service file requires a `User=` value (the `{current_user}` placeholder in FR-600.6). The wizard MUST NOT attempt to auto-detect the browser user's OS login name. Instead, the wizard MUST present a **"Service User"** text input pre-filled with the suggested default `shuttersense`, clearly labeled: *"Enter the Linux username the agent will run as (default: shuttersense)."* The field MUST be editable so the user can replace it with their actual username. The input MUST be non-empty before the service file is generated.

#### FR-700: Step 6 — Summary & Completion

**FR-700.1**: The final step MUST display a summary of what was set up:
- Platform selected
- Token name (if provided)
- Registration command used

**FR-700.2**: The wizard MUST display OS-dependent configuration and data storage locations:
- **macOS**:
  - Config: `~/Library/Application Support/shuttersense/agent-config.yaml`
  - Data: `~/Library/Application Support/shuttersense/data/`
- **Linux**:
  - Config: `~/.config/shuttersense/agent-config.yaml`
  - Data: `~/.local/share/shuttersense/data/`
- **Windows**:
  - Config: `%APPDATA%\shuttersense\agent-config.yaml`
  - Data: `%APPDATA%\shuttersense\data\`

**FR-700.3**: The wizard MUST include a reminder: *"You can monitor this agent's status and health from the Agents page."*

**FR-700.4**: The wizard MUST display a **"Done"** button that closes the dialog.

**FR-700.5**: On closing (via "Done" or the X button), if a token was created, the Agents page MUST refresh its agent list and token list.

#### FR-800: Wizard Navigation & UX

**FR-800.1**: The wizard MUST display a step indicator (progress bar or numbered steps) showing the current step and total steps.

**FR-800.2**: The wizard MUST have **"Back"** and **"Next"** (or **"Continue"**) buttons for navigation between steps.

**FR-800.3**: The **"Back"** button MUST be hidden on Step 1. The **"Next"** button MUST be replaced with **"Done"** on the final step.

**FR-800.4**: Step titles MUST be visible in the step indicator. Suggested titles:
1. Download Agent
2. Create Token
3. Register Agent
4. Start Agent
5. Background Service *(optional)*
6. Summary

**FR-800.5**: The wizard dialog MUST be large enough to display code blocks without horizontal scrolling on desktop (minimum width: 640px).

**FR-800.6**: On mobile viewports (< 640px), the wizard MUST stack content vertically and code blocks MUST be horizontally scrollable.

**FR-800.7**: Closing the wizard mid-flow (via X button or Escape) MUST prompt a confirmation: *"Are you sure? Any unsaved progress will be lost."* — unless the user is on Step 6 (Summary) or no token has been created yet.

**FR-800.8**: All "Copy" buttons MUST provide visual feedback on click (e.g., icon changes to a checkmark for 2 seconds).

### Non-Functional Requirements

#### NFR-100: Performance

**NFR-100.1**: The wizard MUST open within 500ms of the button click (no heavy data fetching on open; release manifest can be fetched lazily in Step 1).

**NFR-100.2**: Token creation (Step 2) MUST complete within the existing API latency bounds (< 1s).

#### NFR-200: Accessibility

**NFR-200.1**: The wizard MUST be keyboard-navigable (Tab through form fields, Enter to proceed, Escape to close with confirmation).

**NFR-200.2**: All copy buttons MUST have accessible labels (e.g., `aria-label="Copy registration command"`).

**NFR-200.3**: The step indicator MUST use `aria-current="step"` for the active step.

**NFR-200.4**: Code blocks MUST use `<pre><code>` semantics for screen readers.

#### NFR-300: Security

**NFR-300.1**: The plaintext registration token MUST NOT be persisted in localStorage, sessionStorage, or any client-side storage. It MUST only exist in component state for the duration of the wizard session.

**NFR-300.2**: The wizard MUST NOT embed the API key or any post-registration secret. The API key is displayed only in the terminal by the agent CLI.

**NFR-300.3**: The download link for the agent binary MUST use HTTPS. Enforced by the frontend validation in FR-200.7a; `http://localhost` and `http://127.0.0.1` are exempt for local development.

#### NFR-400: Testing

**NFR-400.1**: Unit tests MUST cover OS detection logic with mocked `navigator.userAgent` values for all supported platforms.

**NFR-400.2**: Unit tests MUST cover the service file generation logic (plist and systemd) with various binary paths.

**NFR-400.3**: Integration tests MUST verify the wizard flow from open to completion without errors.

**NFR-400.4**: Test coverage for new wizard components MUST be ≥ 80%.

#### NFR-500: Backward Compatibility

**NFR-500.1**: The existing "New Registration Token" button and `RegistrationTokenDialog` MUST remain functional and unchanged. The wizard is an additional entry point, not a replacement.

**NFR-500.2**: The wizard MUST work with the existing `/api/agent/v1/tokens` endpoint for token creation. One new backend endpoint is required: `GET /api/agent/v1/releases/active` (read-only, standard user auth) to expose the active release manifest without requiring super-admin privileges. See [Release Manifest API](#release-manifest-api) for details.

---

## Technical Approach

### Architecture Overview

The wizard is implemented primarily as a frontend component. It composes API calls (token creation, release manifest retrieval) into a guided multi-step flow. One new backend endpoint is required: a read-only, user-accessible `GET /api/agent/v1/releases/active` to expose the active release manifest without requiring super-admin privileges (see [Release Manifest API](#release-manifest-api)).

```text
┌─────────────────────────────────────────────────────────┐
│  AgentsPage                                             │
│  ┌───────────────────┐  ┌────────────────────────────┐  │
│  │ New Reg. Token btn │  │ Agent Setup btn (NEW)      │  │
│  └───────────────────┘  └────────────────────────────┘  │
│                              │                          │
│                              ▼                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  AgentSetupWizardDialog (NEW)                    │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │ Step Indicator (1-6)                       │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │ Step Content (dynamic)                     │  │   │
│  │  │  • DownloadStep                            │  │   │
│  │  │  • TokenStep                               │  │   │
│  │  │  • RegisterStep                            │  │   │
│  │  │  • LaunchStep                              │  │   │
│  │  │  • ServiceStep                             │  │   │
│  │  │  • SummaryStep                             │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │ Navigation (Back / Next / Done)            │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### New Files

| File | Purpose |
| ------ | ------- |
| `frontend/src/components/agents/AgentSetupWizardDialog.tsx` | Root wizard dialog component with step state management |
| `frontend/src/components/agents/wizard/DownloadStep.tsx` | Step 1: OS detection + binary download |
| `frontend/src/components/agents/wizard/TokenStep.tsx` | Step 2: Registration token creation |
| `frontend/src/components/agents/wizard/RegisterStep.tsx` | Step 3: Agent registration instructions |
| `frontend/src/components/agents/wizard/LaunchStep.tsx` | Step 4: Agent launch instructions |
| `frontend/src/components/agents/wizard/ServiceStep.tsx` | Step 5: Background service setup (optional) |
| `frontend/src/components/agents/wizard/SummaryStep.tsx` | Step 6: Summary and completion |
| `frontend/src/components/agents/wizard/StepIndicator.tsx` | Reusable step progress indicator |
| `frontend/src/components/agents/wizard/CopyableCodeBlock.tsx` | Code block with copy button (if not already available) |
| `frontend/src/lib/os-detection.ts` | OS detection utility |
| `frontend/src/lib/service-file-generator.ts` | launchd plist and systemd unit file generators |

### Modified Files

| File | Change |
| ------ | ------ |
| `frontend/src/pages/AgentsPage.tsx` | Add "Agent Setup" button next to existing token button |
| `frontend/src/services/agents.ts` | Add `getActiveRelease()` function calling the new user-accessible endpoint |
| `frontend/src/contracts/api/agent-api.ts` | Add `ReleaseManifest` and `ReleaseArtifact` types (if not already present) |
| `backend/src/api/agent/routes.py` | Add `GET /api/agent/v1/releases/active` (read-only, standard user auth) |
| `backend/src/api/agent/schemas.py` | Add `ActiveReleaseResponse` and `ReleaseArtifactResponse` schemas |

### OS Detection Logic

```typescript
// frontend/src/lib/os-detection.ts

export type Platform =
  | 'darwin-arm64'
  | 'darwin-amd64'
  | 'linux-amd64'
  | 'linux-arm64'
  | 'windows-amd64'

export interface DetectedOS {
  platform: Platform
  label: string       // Human-friendly, e.g. "macOS (Apple Silicon)"
  confidence: 'high' | 'low'
}

/**
 * Attempt Apple Silicon detection via WebGL renderer string.
 * Returns true if the GPU is a known Apple Silicon GPU, false otherwise.
 * This is a best-effort heuristic — the user can always override manually.
 */
function checkAppleSilicon(): boolean {
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    if (!gl) return false
    const debugExt = (gl as WebGLRenderingContext).getExtension('WEBGL_debug_renderer_info')
    if (!debugExt) return false
    const renderer = (gl as WebGLRenderingContext).getParameter(debugExt.UNMASKED_RENDERER_WEBGL)
    // Apple Silicon GPUs report "Apple M1", "Apple M2", "Apple GPU", etc.
    return /Apple (M\d|GPU)/i.test(renderer)
  } catch {
    return false
  }
}

export function detectPlatform(): DetectedOS {
  const ua = navigator.userAgent
  const platform = navigator.platform

  if (/Mac/.test(platform)) {
    // Heuristic: check userAgent for ARM hints, then probe WebGL renderer
    const isArm = /ARM|aarch64|arm64/i.test(ua) || checkAppleSilicon()
    return {
      platform: isArm ? 'darwin-arm64' : 'darwin-amd64',
      label: isArm ? 'macOS (Apple Silicon)' : 'macOS (Intel)',
      confidence: 'high',
    }
  }

  if (/Linux/.test(platform)) {
    const isArm = /aarch64|arm64/i.test(ua)
    return {
      platform: isArm ? 'linux-arm64' : 'linux-amd64',
      label: isArm ? 'Linux (ARM64)' : 'Linux (x86_64)',
      confidence: 'high',
    }
  }

  if (/Win/.test(platform)) {
    return {
      platform: 'windows-amd64',
      label: 'Windows (x86_64)',
      confidence: 'high',
    }
  }

  // Fallback
  return {
    platform: 'linux-amd64',
    label: 'Linux (x86_64)',
    confidence: 'low',
  }
}
```

### Service File Generation

```typescript
// frontend/src/lib/service-file-generator.ts

export function generateLaunchdPlist(binaryPath: string): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.shuttersense.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>${binaryPath}</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/shuttersense/shuttersense-agent.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/shuttersense/shuttersense-agent.stderr.log</string>
</dict>
</plist>`
}

export function generateSystemdUnit(
  binaryPath: string,
  user: string
): string {
  return `[Unit]
Description=ShutterSense Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${binaryPath} start
Restart=always
RestartSec=10
User=${user}

[Install]
WantedBy=multi-user.target`
}
```

### Wizard State Management

```typescript
// Inside AgentSetupWizardDialog.tsx

interface WizardState {
  currentStep: number              // 0-indexed
  selectedPlatform: Platform | null
  detectedPlatform: DetectedOS | null
  platformOverridden: boolean
  releaseManifest: ReleaseManifest | null
  createdToken: string | null      // plaintext token (in-memory only)
  tokenName: string | null
  serverUrl: string | null         // null = invalid config (see getServerUrl)
  binaryPath: string               // user-provided for service setup
  serviceUser: string              // user-provided for systemd
  skippedService: boolean
}

/**
 * Resolve the server URL for the register command.
 * Reads the app-level API base URL config (apiBaseUrl) used by the
 * frontend HTTP client. Falls back to window.location.origin when
 * the config value is not set. Returns null if the value cannot be
 * parsed as a valid URL — callers MUST treat null as "invalid API
 * base URL", display an error, and disable register-command generation.
 */
function getServerUrl(): string | null {
  const configured = import.meta.env.VITE_API_BASE_URL  // or appConfig.apiBaseUrl
    || window.location.origin
  try {
    const url = new URL(configured)
    return url.origin              // scheme + host, no trailing slash
  } catch {
    return null                    // malformed URL — surface error in UI
  }
}

const WIZARD_STEPS = [
  { key: 'download',  title: 'Download Agent',     optional: false },
  { key: 'token',     title: 'Create Token',       optional: false },
  { key: 'register',  title: 'Register Agent',     optional: false },
  { key: 'launch',    title: 'Start Agent',        optional: false },
  { key: 'service',   title: 'Background Service', optional: true  },
  { key: 'summary',   title: 'Summary',            optional: false },
] as const
```

### Backend: Agent Binary Distribution

The wizard requires agent binaries to be downloadable. This PRD assumes one of the following distribution mechanisms exists (or will be set up independently):

**Option A — Static file serving**: Agent binaries are placed in a static directory served by the web server (e.g., `/agent-dist/{version}/shuttersense-agent-{platform}`). The backend reads the `AGENT_DIST_BASE_URL` environment variable, appends the manifest's `version` to form `download_base_url`, and returns it alongside the per-platform `artifacts` array. The frontend constructs the final download URL as `download_base_url` + `artifact.filename`.

**Option B — Backend download endpoint**: A new endpoint `GET /api/agent/v1/releases/{version}/download?platform={platform}` streams the binary. This is more controlled but requires backend changes.

This PRD recommends **Option A** for simplicity, with the download URL pattern configurable via an environment variable (`AGENT_DIST_BASE_URL`). If no release manifests have been published, the wizard gracefully degrades per FR-200.9: it warns the user that no binary is available for download but allows them to continue through the remaining wizard steps (token creation, CLI commands, service setup).

### Release Manifest API

The existing release manifest endpoints live under `/api/admin/release-manifests` and require super-admin authentication. Regular users accessing the wizard cannot call those endpoints. A new **read-only, user-accessible** endpoint is required in the agent API namespace:

```text
GET /api/agent/v1/releases/active
```

The `download_base_url` field in the response is **not** stored in the `ReleaseManifest` model. The backend MUST construct it at response time by combining the `AGENT_DIST_BASE_URL` environment variable with the manifest's `version` field (e.g., `{AGENT_DIST_BASE_URL}/{version}/`). If `AGENT_DIST_BASE_URL` is not set, the field MUST be `null` and the frontend MUST hide the download button (same UX as FR-200.9).

Response:
```json
{
  "guid": "rel_01hgw2bbg...",
  "version": "1.0.0",
  "download_base_url": "https://cdn.example.com/agent-dist/1.0.0/",
  "artifacts": [
    {
      "platform": "darwin-arm64",
      "filename": "shuttersense-agent-darwin-arm64",
      "checksum": "sha256:a1b2c3d4..."
    },
    {
      "platform": "darwin-amd64",
      "filename": "shuttersense-agent-darwin-amd64",
      "checksum": "sha256:e5f6a7b8..."
    },
    {
      "platform": "linux-amd64",
      "filename": "shuttersense-agent-linux-amd64",
      "checksum": "sha256:c9d0e1f2..."
    }
  ],
  "notes": "Initial release"
}
```

The frontend constructs the download URL as:
```text
{download_base_url}/{artifact.filename}
```

---

## Implementation Plan

### Phase 1: Foundation (OS Detection + Wizard Shell)

**Tasks:**
1. Create `frontend/src/lib/os-detection.ts` with platform detection and mapping.
2. Create `StepIndicator.tsx` component for the wizard progress bar.
3. Create `CopyableCodeBlock.tsx` component (if not already available).
4. Create `AgentSetupWizardDialog.tsx` with step state management, navigation (Back/Next/Done), and close confirmation.
5. Add "Agent Setup" button to `AgentsPage.tsx`.
6. Write unit tests for OS detection logic.

**Checkpoint:** Wizard opens, displays step indicator, navigates between empty steps.

### Phase 2: Download & Token Steps

**Tasks:**
1. Implement `DownloadStep.tsx` — fetch release manifest, display detected OS, allow override, show download button or unavailability message.
2. Implement `TokenStep.tsx` — reuse token creation logic from `RegistrationTokenDialog`, display token with copy button, prevent duplicate creation.
3. Add `getActiveRelease()` to `frontend/src/services/agents.ts` and corresponding types.
4. Write unit tests for download step (mocked manifest responses) and token step (mocked API).

**Checkpoint:** User can detect OS, download binary, and create a token within the wizard.

### Phase 3: Registration & Launch Steps

**Tasks:**
1. Implement `RegisterStep.tsx` — display `chmod` + `register` commands with server URL read from app config (`apiBaseUrl`, falling back to `window.location.origin`) and token from wizard state.
2. Implement `LaunchStep.tsx` — display `start` and `self-test` commands, collapsible "Previous Commands" section.
3. Write unit tests for command generation with various server URLs and token values.

**Checkpoint:** Steps 3 and 4 display correct, copy-ready commands for each OS.

### Phase 4: Service Setup & Summary

**Tasks:**
1. Create `frontend/src/lib/service-file-generator.ts` with plist and systemd generators.
2. Implement `ServiceStep.tsx` — binary path input, generated service file display, installation commands, skip option.
3. Implement `SummaryStep.tsx` — setup summary, config file paths, completion message.
4. Handle wizard close → refresh agent list and token list.
5. Write unit tests for service file generation, summary rendering.

**Checkpoint:** Full wizard flow from Step 1 to Step 6 is functional.

### Phase 5: Polish & Accessibility

**Tasks:**
1. Add keyboard navigation (Tab, Enter, Escape).
2. Add ARIA attributes to step indicator and copy buttons.
3. Test responsive layout on mobile viewports.
4. Add close confirmation dialog for mid-flow exits.
5. Integration test: full wizard flow end-to-end.

**Checkpoint:** Wizard is accessible, responsive, and polished.

---

## Alternatives Considered

| Approach | Pros | Cons | Decision |
| -------- | ---- | ---- | -------- |
| **Multi-step wizard dialog (chosen)** | Guided flow, no page navigation, reuses existing APIs | Larger dialog component, more frontend code | **Selected** — best balance of UX and implementation cost |
| **Dedicated setup page (`/agents/setup`)** | More screen real estate, URL-shareable | Breaks modal pattern used elsewhere, requires routing changes | Rejected — unnecessary for a one-time flow |
| **Expandable inline guide on Agents page** | No dialog, always visible | Clutters the page, poor mobile experience | Rejected — too intrusive for a one-time action |
| **External documentation link** | Zero frontend work | High user friction, context switching, no pre-populated values | Rejected — contradicts the goal of reducing friction |

---

## Risks and Mitigation

### R-1: OS detection inaccuracy

- **Impact**: Medium — user downloads wrong binary
- **Probability**: Low — `navigator.platform` is reliable for OS family; architecture detection (ARM vs x86) is less reliable
- **Mitigation**: Always allow manual override (FR-200.4); display detected platform prominently so users can verify; binary attestation at registration time catches mismatches

### R-2: No release manifests available

- **Impact**: Medium — wizard cannot provide a download link, but remains functional for token creation and CLI command reference
- **Probability**: Medium — depends on admin having uploaded binaries
- **Mitigation**: Graceful degradation (FR-200.9): the wizard displays a warning banner on Step 1 but does **not** block progression. Users can still complete Steps 2–6 (token creation, registration commands, launch instructions, service setup, and summary). The warning directs users to contact their administrator for the binary. Step 1's "Download Agent" button is hidden when no manifest is available, but "Next" remains enabled.

### R-3: Token expires before user completes setup

- **Impact**: Low — user must create a new token
- **Probability**: Low — default 24h expiration is generous for a setup flow
- **Mitigation**: Display expiration time in Step 2; if the wizard is left open for extended periods, the token is still valid until its expiration

### R-4: Service file configuration errors

- **Impact**: Medium — agent fails to start as a service
- **Probability**: Low — generated files use standard templates
- **Mitigation**: Show verification commands (FR-600.5, FR-600.7) so users can immediately check service status; include troubleshooting notes

---

## Success Metrics

| Metric | Target | Measurement |
| ------ | ------ | ----------- |
| Agent setup completion rate | > 80% of wizard starts result in a successfully registered agent within 1 hour | Backend: track registration events correlated with wizard-created tokens |
| Time from wizard open to agent online | < 5 minutes for experienced users | Timestamp delta: token created_at → agent first heartbeat |
| Support requests for agent setup | 50% reduction vs. pre-wizard baseline | Support ticket categorization |
| Wizard abandonment rate | < 30% | Frontend analytics: wizard open vs. wizard "Done" button clicks |

---

## Future Enhancements

- **Windows service setup** — Add NSSM or Windows Task Scheduler configuration generation once demand is validated.
- **Agent auto-update** — Extend the wizard or create a separate flow for updating existing agents to new versions.
- **One-click install script** — Generate a platform-specific shell script (bash/PowerShell) that automates download, chmod, register, and service setup in a single command.
- **QR code for mobile setup** — Generate a QR code containing the server URL and token for easy transfer to another device.
- **Wizard analytics** — Track step-by-step completion rates to identify drop-off points.
- **Remote agent provisioning** — SSH-based or push-based agent installation for advanced users with fleet management needs.

---

## Revision History

- **2026-01-31 (v1.5)**: Add FR-200.7b (download error handling with retry); FR-200.8 keeps Next enabled (consistent degradation); FR-300.6 always redisplays token; FR-600.3a (binary path validation); persistent plist log paths; FR-600.11 clarifies Linux User default; implement `checkAppleSilicon()` — AI Assistant
- **2026-01-31 (v1.4)**: Remove backend ambiguity (endpoint is new, not pre-existing); add HTTPS validation for download URLs (FR-200.7a); make `getServerUrl` return `null` on invalid URL instead of throwing, with caller error handling in FR-400.3 — AI Assistant
- **2026-01-31 (v1.3)**: Clarify `download_base_url` is derived at runtime from `AGENT_DIST_BASE_URL` env var + version, not a DB field; handle `null` case in FR-200.7 — AI Assistant
- **2026-01-31 (v1.2)**: Clarify release manifest endpoint: new user-accessible `GET /api/agent/v1/releases/active` required (existing admin endpoints need super-admin auth) — AI Assistant
- **2026-01-31 (v1.1)**: Config-based server URL, allow wizard progression without manifests, per-platform artifacts schema, MD040/MD060 fixes — AI Assistant
- **2026-01-31 (v1.0)**: Initial draft — AI Assistant
