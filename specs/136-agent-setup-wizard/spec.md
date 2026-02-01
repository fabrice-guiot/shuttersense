# Feature Specification: Agent Setup Wizard

**Feature Branch**: `136-agent-setup-wizard`
**Created**: 2026-02-01
**Status**: Draft
**Input**: User description: "GitHub issue #136 based on PRD: docs/prd/136-agent-setup-wizard.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Agent Setup via Guided Wizard (Priority: P1)

A team administrator needs to set up a new ShutterSense agent on a studio workstation. They open the Agents page, click "Agent Setup", and the wizard detects their operating system. The wizard walks them through downloading the correct agent binary, creating a registration token, running the registration command in a terminal, and starting the agent. Every terminal command is pre-populated with the correct values and can be copied with one click. The admin completes all steps without leaving the browser or consulting external documentation.

**Why this priority**: This is the core value proposition of the feature. Without the guided multi-step wizard flow, none of the other stories deliver meaningful value. It addresses the primary pain point: high-friction, multi-context agent setup.

**Independent Test**: Can be fully tested by opening the wizard, progressing through all six steps, and verifying that a registration token is created and all displayed commands contain correct, copy-ready values. Delivers the complete guided onboarding experience.

**Acceptance Scenarios**:

1. **Given** an authenticated user on the Agents page, **When** they click the "Agent Setup" button, **Then** a multi-step wizard dialog opens showing Step 1 with a step indicator displaying all six steps.
2. **Given** the wizard is on Step 1, **When** it opens, **Then** the user's operating system and architecture are auto-detected and displayed with a human-friendly label (e.g., "macOS (Apple Silicon)").
3. **Given** the wizard is on Step 2, **When** the user creates a registration token, **Then** the plaintext token is displayed with a "Copy" button and a warning that it will only be shown once.
4. **Given** the wizard is on Step 3, **When** the user views the registration command, **Then** the command includes the correct server URL and the token from Step 2, with a "Copy" button.
5. **Given** the wizard is on Step 4, **When** the user views the start command, **Then** `shuttersense-agent start` and `shuttersense-agent self-test` commands are displayed with "Copy" buttons.
6. **Given** the user clicks "Done" on Step 6 after completing the wizard, **When** the dialog closes, **Then** the Agents page refreshes its agent list and token list.

---

### User Story 2 - Download Correct Agent Binary for Detected Platform (Priority: P1)

A photographer needs to install the agent on their local machine. The wizard detects their OS and presents a download button for the matching binary. The binary is served by the application server itself through an authenticated download, and the user can verify the file checksum displayed in the wizard.

**Why this priority**: Eliminating OS mismatch errors is a primary goal. Downloading the wrong binary is a silent failure that wastes significant user time. This story is essential for the wizard to deliver real value beyond just showing CLI commands.

**Independent Test**: Can be tested by mocking different OS user agents and verifying the correct platform is detected and the correct download link is presented. The download button, checksum display, and unavailability messages can all be validated independently.

**Acceptance Scenarios**:

1. **Given** the wizard is on Step 1 and an active release manifest exists with an artifact for the detected platform, **When** the step loads, **Then** a "Download Agent" button is displayed showing the filename and checksum.
2. **Given** the wizard is on Step 1, **When** the user selects a different platform from the override dropdown, **Then** a warning is displayed stating they selected a different platform than detected, and the download link updates to the selected platform's artifact.
3. **Given** no release manifests have been published, **When** the wizard opens Step 1, **Then** a warning banner explains no builds are available and directs the user to contact their administrator, but the "Next" button remains enabled.
4. **Given** a release manifest exists but no artifact matches the selected platform, **When** the user views Step 1, **Then** an informational message explains no build is available for that platform but the user can continue.
5. **Given** the download URL does not use HTTPS (and is not localhost), **When** the wizard evaluates the URL, **Then** the download button is hidden and a security warning is displayed.
6. **Given** a download fails due to a network or HTTP error, **When** the error occurs, **Then** an inline error message is displayed with a "Retry Download" button, and the "Next" button remains enabled.
7. **Given** the user clicks "Download Agent", **When** the download is initiated, **Then** the request is authenticated using the user's existing session and the server returns the binary file only if the user is authorized.

---

### User Story 3 - Configure Background Service (Priority: P2)

After registering the agent, the administrator wants it to start automatically on boot. On Step 5, the wizard asks for the binary path on the target machine (with an OS-appropriate default), generates the correct service configuration file (launchd plist for macOS, systemd unit for Linux), and displays the installation commands. The admin copies the generated file and commands to configure automatic startup.

**Why this priority**: Background service setup is optional but high-value. Most users want agents to run persistently. Without wizard guidance, this step requires platform-specific research and is the most common source of support requests. However, the wizard delivers value even without this step (users can run the agent in foreground mode).

**Independent Test**: Can be tested by entering a binary path, verifying the generated service file content is correct for the selected OS, and confirming installation commands are displayed with "Copy" buttons.

**Acceptance Scenarios**:

1. **Given** the wizard is on Step 5 with macOS selected, **When** the user enters a binary path, **Then** a launchd plist file is generated with the correct binary path and displayed in a copyable code block, along with installation commands.
2. **Given** the wizard is on Step 5 with Linux selected, **When** the user enters a binary path and a service username, **Then** a systemd service unit file is generated with the correct binary path and username, displayed in a copyable code block.
3. **Given** the wizard is on Step 5 with Windows selected, **When** the step loads, **Then** a message informs the user that automatic background service setup for Windows is not yet supported.
4. **Given** the wizard is on Step 5, **When** the user decides not to configure a service, **Then** they can skip the step and proceed to the summary.
5. **Given** the user enters a relative path for the binary, **When** the path is validated, **Then** an error message explains the path must be absolute and provides an example.
6. **Given** the user enters a path with spaces, **When** the path is validated, **Then** a non-blocking warning indicates the path contains spaces and will be properly handled in the generated file.

---

### User Story 4 - Set Up Agent on a Remote Machine (Priority: P3)

A team administrator is setting up an agent on a remote Linux NAS server from their macOS laptop. The wizard detects macOS but the admin overrides the platform selection to "Linux (x86_64)". All subsequent instructions, commands, download links, and service files adapt to the overridden platform. The admin copies the commands and runs them on the remote machine via SSH.

**Why this priority**: Remote setup is a secondary use case. Most initial setups happen on the same machine running the browser. However, for team administrators managing multiple machines, this override capability prevents the wizard from being limited to local-only setups.

**Independent Test**: Can be tested by overriding the detected OS and verifying all wizard content (download link, chmod commands, service files) adapts to the selected platform.

**Acceptance Scenarios**:

1. **Given** the wizard detects macOS, **When** the user overrides the platform to "Linux (x86_64)", **Then** a warning is displayed about the platform mismatch, and all subsequent steps show Linux-specific instructions.
2. **Given** the user overrides to Linux, **When** they reach Step 3, **Then** the `chmod +x` command is included before the registration command.
3. **Given** the user overrides to Linux, **When** they reach Step 5, **Then** a systemd service file is generated (not a launchd plist).
4. **Given** the user overrides to a remote platform, **When** they view Step 1, **Then** the wizard provides a time-limited signed download link that can be copied and used on the remote machine (e.g., via `curl` or `wget`) without requiring a browser session on that machine.

---

### User Story 5 - Wizard Navigation and Mid-Flow Protection (Priority: P2)

A user opens the wizard and progresses to Step 3 where they have already created a registration token. They accidentally click the browser's close button or press Escape. A confirmation dialog warns them that unsaved progress will be lost. They cancel and continue the wizard. If they navigate back to Step 2 and forward again, the previously created token is still displayed without creating a duplicate.

**Why this priority**: Token creation is an irreversible action (the plaintext token is only visible in this session). Protecting users from accidental data loss and preventing duplicate token creation are essential for a trustworthy wizard experience.

**Independent Test**: Can be tested by creating a token in Step 2, navigating back and forward, and verifying the same token is displayed. Close confirmation can be tested by pressing Escape mid-flow.

**Acceptance Scenarios**:

1. **Given** a user is on Step 3 and has created a token, **When** they press Escape, **Then** a confirmation dialog asks if they are sure, warning that unsaved progress will be lost.
2. **Given** a user is on Step 6 (Summary), **When** they press Escape, **Then** the wizard closes without a confirmation prompt.
3. **Given** a user created a token in Step 2, **When** they navigate back to Step 2 and then forward again, **Then** the previously created token is redisplayed without making a new API call.
4. **Given** a user is on Step 1 and has not created a token, **When** they close the wizard, **Then** no confirmation prompt is shown.
5. **Given** a user has not yet created a token, **When** they try to proceed past Step 2, **Then** the "Next" button is disabled until a token is created.

---

### Edge Cases

- What happens when the browser does not support WebGL (used for Apple Silicon detection)? The wizard falls back to a lower-confidence detection and always allows manual override.
- What happens when the server's API base URL configuration is invalid or missing? The wizard displays an error on Step 3 explaining it cannot determine the server URL, and disables the register command's "Copy" button.
- What happens when the user's browser blocks clipboard access? The "Copy" button should gracefully degrade (e.g., select the text for manual copying) and inform the user.
- What happens when the release manifest API endpoint returns an error? The wizard degrades gracefully, hiding the download button and showing a warning, but allowing progression through remaining steps.
- What happens when a token expires during a long wizard session? The token remains in wizard state; the user will encounter an error only at registration time in the terminal. The wizard displays the token expiration time in Step 2 so users are aware.
- What happens when a signed download link expires before the user uses it on the remote machine? The download request is rejected with a clear "link expired" error. The user must return to the wizard in their browser to generate a fresh signed link.
- What happens in dev/QA environments where agent binaries are not available for all platforms? The wizard detects the development environment and shows all five platform options regardless of which binaries exist, allowing QA reviewers to test all wizard paths. Download buttons for missing binaries are disabled with a clear explanation that the binary is unavailable in this environment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Agents page MUST display an "Agent Setup" button adjacent to the existing "New Registration Token" button, available to all authenticated users with access to the Agents page.
- **FR-002**: The button MUST open a multi-step wizard dialog (modal) with six steps: Download Agent, Create Token, Register Agent, Start Agent, Background Service (optional), and Summary.
- **FR-003**: The wizard MUST display a step indicator (progress bar or numbered steps) showing the current step, step titles, and total steps.
- **FR-004**: The wizard MUST auto-detect the user's operating system and architecture on open, mapping it to one of: `darwin-arm64`, `darwin-amd64`, `linux-amd64`, `linux-arm64`, `windows-amd64`.
- **FR-005**: The wizard MUST display the detected platform with a human-friendly label and allow the user to override it via a dropdown of all available platforms.
- **FR-006**: When the user overrides the detected platform, the wizard MUST display a warning about the platform mismatch.
- **FR-007**: The wizard MUST retrieve the active release manifest from a user-accessible endpoint and display a download button for the matching platform artifact, including filename and checksum.
- **FR-008**: If no release manifest exists, or no artifact matches the selected platform, or the download URL is insecure, the wizard MUST display an appropriate informational or warning message while keeping the "Next" button enabled.
- **FR-009**: If a download fails, the wizard MUST display an inline error with a "Retry Download" button while keeping the "Next" button enabled.
- **FR-010**: The token creation step MUST allow the user to optionally name the token and set its expiration (1-168 hours, default 24).
- **FR-011**: Upon token creation, the wizard MUST display the plaintext token with a "Copy" button and a warning that it will only be shown once.
- **FR-012**: If a token was already created in this wizard session, navigating back to the token step MUST redisplay the existing token without creating a duplicate.
- **FR-013**: The wizard MUST NOT allow proceeding past the token step until a token has been created.
- **FR-014**: The registration step MUST display OS-specific instructions including a pre-populated, copy-ready `register` command with the correct server URL and token.
- **FR-015**: For macOS and Linux, the registration step MUST include a `chmod +x` command for the binary.
- **FR-016**: The server URL in the register command MUST be resolved from the application's API base URL configuration, falling back to the current page origin, and MUST be validated as a well-formed URL.
- **FR-017**: The launch step MUST display the `start` and `self-test` commands and a collapsible "Previous Commands" section summarizing earlier commands.
- **FR-018**: The background service step MUST allow the user to provide the full binary path (with OS-appropriate default suggestion) and validate that the path is absolute.
- **FR-019**: For macOS, the service step MUST generate a launchd plist file with the provided binary path and display installation commands.
- **FR-020**: For Linux, the service step MUST generate a systemd service unit file with the provided binary path and a user-provided service username (default: "shuttersense"), and display installation commands.
- **FR-021**: For Windows, the service step MUST display a message that automatic background service setup is not yet supported.
- **FR-022**: The service step MUST be skippable.
- **FR-023**: The summary step MUST display a recap of the setup (platform, token name, registration command) and OS-dependent configuration and data storage file paths.
- **FR-024**: All terminal commands and generated files MUST be displayed in code blocks with individual "Copy" buttons that provide visual feedback (e.g., checkmark for 2 seconds).
- **FR-025**: The wizard MUST have "Back" and "Next" navigation buttons; "Back" hidden on Step 1, "Next" replaced with "Done" on the final step.
- **FR-026**: Closing the wizard mid-flow MUST prompt a confirmation dialog unless the user is on the Summary step or no token has been created.
- **FR-027**: On wizard close (via "Done" or X button), if a token was created, the Agents page MUST refresh its agent list and token list.
- **FR-028**: The wizard dialog MUST be at least 640px wide on desktop; on mobile viewports (<640px), content MUST stack vertically and code blocks MUST scroll horizontally.
- **FR-029**: The plaintext registration token MUST NOT be persisted in any client-side storage; it MUST only exist in component state for the wizard session duration.
- **FR-030**: The wizard MUST be keyboard-navigable (Tab through fields, Enter to proceed, Escape to close with confirmation) and include accessible labels on all interactive elements.
- **FR-031**: The existing "New Registration Token" button and its dialog MUST remain functional and unchanged.
- **FR-032**: The system MUST provide a read-only, user-accessible endpoint to retrieve the active release manifest (including per-platform artifacts with filename and checksum, and a download base URL derived from server configuration).

#### Authenticated Binary Download Requirements

- **FR-037**: The application server MUST serve agent binaries directly from a designated local directory on the server, organized by release version (e.g., `{agent_dist_directory}/{version}/{artifact_filename}`). The server administrator places pre-built binaries in this directory. This is the primary distribution mechanism for the initial deployment; external CDN distribution may be supported in the future.
- **FR-038**: The binary download endpoint MUST require authentication. An unauthenticated request MUST be rejected. Two authentication methods MUST be supported:
  - **Session-based**: The user's existing browser session (cookie) is verified. This is the default method when the user clicks the "Download Agent" button in the wizard.
  - **Signed download link**: A time-limited, tamper-proof download URL that can be used without a browser session. This allows users to copy the link and use it on a remote or headless machine (e.g., via `curl` or `wget`).
- **FR-039**: The wizard MUST display the signed download link alongside the "Download Agent" button, with a "Copy Link" action and a note indicating the link's validity period. The link MUST expire after a reasonable period (e.g., 1 hour) and become unusable afterward.
- **FR-040**: If the binary file for the requested platform and version does not exist in the server's distribution directory, the download endpoint MUST return an appropriate error. The wizard MUST handle this error per FR-009 (inline error with retry).
- **FR-041**: The release manifest endpoint (FR-032) MUST construct download URLs that point to the application server's own binary download endpoint. If the distribution directory is not configured or does not exist, the download URLs MUST be omitted and the wizard MUST degrade gracefully per FR-008.

#### Dev/QA Mode Requirements

- **FR-033**: When running in a development or QA environment, the wizard MUST display all five supported platforms (`darwin-arm64`, `darwin-amd64`, `linux-amd64`, `linux-arm64`, `windows-amd64`) in the platform dropdown and as selectable options, regardless of whether the active release manifest contains artifacts for those platforms.
- **FR-034**: In dev/QA mode, if the user selects a platform for which no binary artifact exists in the release manifest, the download button MUST be disabled (not hidden) and display a message such as: *"Agent binary for {platform} is not available in this environment. This is expected in development/QA — the wizard flow can still be tested without downloading."*
- **FR-035**: In dev/QA mode, all other wizard steps (token creation, registration commands, launch commands, service file generation, summary) MUST remain fully functional for all platforms, so QA reviewers can exercise the complete wizard flow for any OS without needing actual binaries.
- **FR-036**: In production mode, the platform dropdown MUST only show platforms for which an artifact exists in the active release manifest (existing behavior per FR-007 and FR-008).

### Key Entities

- **Release Manifest**: Represents a published set of agent binaries for a given version. Contains a version string, an optional download base URL (derived from server configuration at response time), optional release notes, and a collection of platform-specific artifacts.
- **Release Artifact**: Represents a single agent binary for a specific platform. Contains the platform identifier, filename, and a checksum for integrity verification. Belongs to a Release Manifest.
- **Registration Token**: A time-limited, single-use credential that allows an agent to register with the server. Has an optional user-provided name and a configurable expiration period.
- **Signed Download Link**: A time-limited, tamper-proof URL that grants access to a specific agent binary without requiring a browser session. Contains the target version and platform, a validity window, and a signature that prevents tampering. Used primarily for downloading binaries on remote or headless machines.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the full agent setup (from clicking "Agent Setup" to a registered, running agent) in under 5 minutes without consulting external documentation.
- **SC-002**: More than 80% of wizard starts result in a successfully registered agent within 1 hour.
- **SC-003**: Agent setup-related support requests decrease by 50% compared to the pre-wizard baseline.
- **SC-004**: Fewer than 30% of wizard sessions are abandoned before reaching the Summary step.
- **SC-005**: 95% of users who complete the wizard report the correct platform was auto-detected (or they successfully overrode it without issues).
- **SC-006**: The wizard opens within 500 milliseconds of the button click.

## Assumptions

- **Agent binary distribution directory**: The application server hosts agent binaries from a local directory configured by the server administrator. Binaries are organized by version within this directory (e.g., `{configured_directory}/{version}/shuttersense-agent-darwin-arm64`). The server administrator is responsible for placing pre-built binaries in this directory structure. The build pipeline for creating these binaries is outside the scope of this feature. The binary filenames and checksums are stored in the release manifest's per-platform artifacts. In the initial deployment, the application server is the sole source for all static resources (frontend assets and agent binaries). Future deployments may support external CDN distribution, but this is not required for the first iteration.
- **Dev/QA mode**: In development and QA environments, agent binaries may not be available for all (or any) platforms. The wizard detects the application environment mode and adapts its behavior: all platform options are shown to enable full wizard flow testing, but download actions are disabled for missing binaries with a clear message explaining this is expected in non-production environments. This ensures QA reviewers can validate the wizard's UI, navigation, token creation, command generation, and service file generation for every OS without requiring a complete binary distribution setup.
- The existing token creation API endpoint is reused; no changes to the token creation flow are needed.
- OS detection using browser APIs (navigator.userAgent, navigator.platform, WebGL renderer) provides sufficient accuracy for the major OS families (macOS, Linux, Windows) with manual override as a safety net.
- Windows background service setup (NSSM / Task Scheduler) is deferred to a future iteration. The wizard acknowledges this limitation.
- The wizard does not perform remote installation. It provides instructions and commands the user manually executes on the target machine.
- Standard session-based authentication (existing) is sufficient for accessing the wizard and the release manifest endpoint. Binary downloads additionally support time-limited signed URLs for use on remote or headless machines where a browser session is not available.

## Dependencies

- Active release manifest data must exist in the system for the download step to provide binary downloads (the wizard degrades gracefully without it).
- The server administrator must configure the agent binary distribution directory and place pre-built binaries in it, organized by version (e.g., `{directory}/{version}/shuttersense-agent-darwin-arm64`). If this directory is not configured or is empty, the wizard degrades gracefully — all non-download steps remain functional.
- The application server must have a signing secret available for generating and verifying time-limited signed download URLs.
- The existing registration token API must be available and functional.
- The application must expose an environment mode indicator so the wizard can distinguish production from dev/QA environments and adjust platform display behavior accordingly.
