# PRD: Agent Setup Wizard

**Issue**: [#136 — Create an 'Agent Setup' Wizard in the Agent Page](https://github.com/fabrice-guiot/shuttersense/issues/136)
**Status**: Draft
**Created**: 2026-01-31
**Last Updated**: 2026-01-31
**Related Documents**:
- [Domain Model](../domain-model.md)
- [Design System](../../frontend/docs/design-system.md)
- [Distributed Agent Architecture](./021-distributed-agent-architecture.md)

---

## Executive Summary

This PRD defines a guided, multi-step **Agent Setup Wizard** embedded in the Agents page of the ShutterSense web application. The wizard walks users through the entire agent onboarding lifecycle — from downloading the correct binary for their operating system, through registration token creation and agent registration, to optional background service configuration — all without leaving the browser.

Today, setting up an agent requires switching between the web UI (to create a registration token), a documentation page (to find the right binary and learn CLI commands), and a terminal (to run them). The wizard consolidates these steps into a single, linear flow that adapts its instructions and downloads to the detected OS.

Key design decisions:
- **OS auto-detection with manual override** — `navigator.userAgent` / `navigator.platform` is used for initial detection; the user can override if they are setting up a remote machine.
- **Frontend-only wizard UI** — No new backend endpoints are required beyond the existing registration token and release manifest APIs; all wizard logic lives in the frontend.
- **Agent binaries served from a static distribution folder** — The server hosts pre-built agent binaries at a well-known path; the wizard constructs download links from the release manifest metadata.

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

**FR-200.6**: The wizard MUST fetch the active release manifest from the backend (`GET /api/agent/v1/releases/active` or equivalent) to determine available platforms and the download URL/checksum.

**FR-200.7**: If a build exists for the selected platform, the wizard MUST display a **"Download Agent"** button that initiates a download of the binary.

**FR-200.8**: If no build exists for the selected platform, the wizard MUST display an informational message: *"No agent build is available for {platform}. Please contact your administrator."* The "Next" button MUST be disabled.

**FR-200.9**: If no release manifests exist at all (no builds uploaded yet), the wizard MUST display: *"No agent builds have been published yet. Please contact your administrator to upload agent binaries."* The "Next" button MUST be disabled.

**FR-200.10**: The download button SHOULD display the binary filename and file size when available.

**FR-200.11**: The wizard MUST display the SHA-256 checksum of the binary so the user can verify the download integrity.

#### FR-300: Step 2 — Registration Token

**FR-300.1**: Step 2 MUST replicate the existing registration token creation flow from `RegistrationTokenDialog`.

**FR-300.2**: The wizard MUST allow the user to optionally name the token (e.g., "Studio Mac Agent").

**FR-300.3**: The wizard MUST allow the user to set the token expiration (1–168 hours, default 24).

**FR-300.4**: Upon token creation, the wizard MUST display the plaintext token with a **"Copy"** button.

**FR-300.5**: The wizard MUST display a warning: *"This token will only be shown once. Copy it now."*

**FR-300.6**: If a token has already been created in this wizard session, navigating back to Step 2 and forward again MUST NOT create a duplicate token. The previously created token MUST be displayed (or a message indicating a token was already created).

**FR-300.7**: The wizard MUST NOT allow proceeding to Step 3 until a token has been created and is visible.

#### FR-400: Step 3 — Agent Registration

**FR-400.1**: Step 3 MUST display OS-specific instructions for registering the agent.

**FR-400.2**: The wizard MUST display a pre-populated, copy-ready `register` command:
```
shuttersense-agent register --server {server_url} --token {token}
```

**FR-400.3**: The `{server_url}` MUST be automatically set to the current application URL (the URL the user is accessing the web app from).

**FR-400.4**: The `{token}` MUST be the token generated in Step 2.

**FR-400.5**: For macOS and Linux, the wizard MUST include a preliminary step to make the binary executable:
```
chmod +x ./shuttersense-agent
```

**FR-400.6**: The wizard MUST display the expected output of a successful registration (e.g., *"Agent registered successfully. GUID: agt_..."*).

**FR-400.7**: Each command block MUST have its own **"Copy"** button.

#### FR-500: Step 4 — Agent Launch

**FR-500.1**: Step 4 MUST display the command to start the agent:
```
shuttersense-agent start
```

**FR-500.2**: The wizard MUST provide a brief explanation: *"This starts the agent in foreground mode. The agent will connect to the server, begin sending heartbeats, and start polling for jobs."*

**FR-500.3**: The wizard MUST display a note: *"Keep this terminal window open while the agent is running. For automatic startup, proceed to the next step to configure a background service."*

**FR-500.4**: The wizard MUST also show the `self-test` command for verifying the agent is correctly configured:
```
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

**FR-600.4**: For **macOS**, the wizard MUST generate a `launchd` property list (`.plist`) file content:
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
    <string>/tmp/shuttersense-agent.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/shuttersense-agent.stderr.log</string>
</dict>
</plist>
```

**FR-600.5**: For macOS, the wizard MUST display installation commands:
```bash
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

**FR-600.11**: The Linux service file MUST include a `{current_user}` placeholder with a default suggestion based on common conventions (e.g., the user's login name), editable by the user.

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

**NFR-300.3**: The download link for the agent binary MUST use HTTPS.

#### NFR-400: Testing

**NFR-400.1**: Unit tests MUST cover OS detection logic with mocked `navigator.userAgent` values for all supported platforms.

**NFR-400.2**: Unit tests MUST cover the service file generation logic (plist and systemd) with various binary paths.

**NFR-400.3**: Integration tests MUST verify the wizard flow from open to completion without errors.

**NFR-400.4**: Test coverage for new wizard components MUST be ≥ 80%.

#### NFR-500: Backward Compatibility

**NFR-500.1**: The existing "New Registration Token" button and `RegistrationTokenDialog` MUST remain functional and unchanged. The wizard is an additional entry point, not a replacement.

**NFR-500.2**: No backend API changes are required. The wizard MUST work with the existing `/api/agent/v1/tokens` and release manifest endpoints.

---

## Technical Approach

### Architecture Overview

The wizard is implemented entirely as a frontend component. It composes existing API calls (token creation, release manifest retrieval) into a guided multi-step flow. No new backend endpoints are needed.

```
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
|------|---------|
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
|------|--------|
| `frontend/src/pages/AgentsPage.tsx` | Add "Agent Setup" button next to existing token button |
| `frontend/src/services/agents.ts` | Add `getActiveRelease()` function (if release manifest endpoint exists) |
| `frontend/src/contracts/api/agent-api.ts` | Add release manifest types (if not already present) |

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

export function detectPlatform(): DetectedOS {
  const ua = navigator.userAgent
  const platform = navigator.platform

  if (/Mac/.test(platform)) {
    // Check for Apple Silicon via WebGL renderer or platform hints
    const isArm = /ARM/.test(ua) || checkAppleSilicon()
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
    <string>/tmp/shuttersense-agent.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/shuttersense-agent.stderr.log</string>
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
  binaryPath: string               // user-provided for service setup
  serviceUser: string              // user-provided for systemd
  skippedService: boolean
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

**Option A — Static file serving**: Agent binaries are placed in a static directory served by the web server (e.g., `/agent-dist/{version}/shuttersense-agent-{platform}`). The release manifest stores the version and platform list; the frontend constructs the download URL.

**Option B — Backend download endpoint**: A new endpoint `GET /api/agent/v1/releases/{version}/download?platform={platform}` streams the binary. This is more controlled but requires backend changes.

This PRD recommends **Option A** for simplicity, with the download URL pattern configurable via an environment variable (`AGENT_DIST_BASE_URL`). If the distribution mechanism is not yet in place, the wizard gracefully degrades (FR-200.9).

### Release Manifest API

If a release manifest list endpoint does not yet exist, a minimal one is needed:

```
GET /api/agent/v1/releases/active
```

Response:
```json
{
  "guid": "rel_01hgw2bbg...",
  "version": "1.0.0",
  "platforms": ["darwin-arm64", "darwin-amd64", "linux-amd64"],
  "checksum": "sha256:abc123...",
  "download_base_url": "https://example.com/agent-dist/1.0.0/",
  "notes": "Initial release"
}
```

The frontend constructs the download URL as:
```
{download_base_url}/shuttersense-agent-{platform}
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
1. Implement `RegisterStep.tsx` — display `chmod` + `register` commands with auto-populated server URL and token.
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
|----------|------|------|----------|
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

- **Impact**: High — wizard cannot provide a download link
- **Probability**: Medium — depends on admin having uploaded binaries
- **Mitigation**: Graceful degradation (FR-200.9) with clear messaging; wizard can still be used for token creation and CLI command reference even without a download link

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
|--------|--------|-------------|
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

- **2026-01-31 (v1.0)**: Initial draft — AI Assistant
