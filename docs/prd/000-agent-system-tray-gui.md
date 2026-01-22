# PRD: Agent System Tray GUI

**Issue**: TBD
**Status**: Draft
**Created**: 2026-01-22
**Last Updated**: 2026-01-22 (v1.1)
**Related Documents**:
- [021-distributed-agent-architecture.md](./021-distributed-agent-architecture.md) (Agent architecture)
- [000-remove-cli-direct-usage.md](./000-remove-cli-direct-usage.md) (Agent CLI commands)

---

## Executive Summary

This PRD proposes adding an optional graphical user interface (GUI) to the ShutterSense agent, allowing it to run as a system tray (menubar) application. The GUI provides visual status indicators, real-time log viewing, an embedded command terminal, and OS auto-start configuration—all without requiring users to interact with a terminal.

### Current State

**CLI-Only Agent:**
- Agent runs via `shuttersense-agent start` command in terminal
- Status visible only through console output
- Logs stream to stdout (lost when terminal closes)
- No auto-start mechanism (users must configure manually)
- Technical users comfortable; non-technical users challenged

**Pain Points:**
- No persistent visibility of agent status
- Logs not retained unless manually redirected
- Running agent commands requires opening terminal
- Auto-start requires platform-specific manual configuration
- Less approachable for photographers who prefer GUI tools

### What This PRD Delivers

1. **System Tray Icon**: Visual indicator of agent status (idle, running job, error, disconnected)
2. **Log Viewer**: Read-only window showing real-time agent logs
3. **Command Terminal**: Embedded interface for running agent CLI commands
4. **Auto-Start Configuration**: One-click setup for OS startup integration

---

## Background

### Problem Statement

The ShutterSense agent is designed for professional photographers who may not be comfortable with command-line interfaces. While the agent's functionality is robust, its CLI-only interface creates friction:

| Issue | Impact | Severity |
|-------|--------|----------|
| **No status visibility** | Users don't know if agent is running or healthy | High |
| **Terminal dependency** | Must keep terminal open to see logs | Medium |
| **Command complexity** | Agent commands require terminal knowledge | Medium |
| **Manual auto-start** | Platform-specific configuration needed | Medium |
| **No job progress indicator** | Cannot see when analysis is running | Low |

### Strategic Context

As ShutterSense moves toward broader adoption, reducing the technical barrier for agent setup and monitoring becomes important. A lightweight system tray GUI can:

1. **Improve Accessibility**: Non-technical users can manage the agent visually
2. **Increase Adoption**: Lower barrier to entry for photographers
3. **Enhance Trust**: Visible status builds confidence the system is working
4. **Simplify Support**: Users can easily check and report agent status

### Current Agent Architecture

The agent is built with Python 3.10+ using asyncio and Click CLI framework:

```
shuttersense-agent start
    ↓
AgentRunner.run() [async]
    ├── Heartbeat loop (every 30s)
    └── Job polling loop (every 5s)
        ├── Claim available jobs
        ├── Execute via JobExecutor
        └── Report results to server
```

**Key Characteristics (Favorable for GUI):**
- Python ecosystem has rich GUI library options
- asyncio can integrate with GUI event loops
- PyInstaller already packages cross-platform binaries
- Logging uses standard Python logging module
- Configuration centralized in AgentConfig

---

## Goals

### Primary Goals

1. **Status Visibility**: System tray icon showing agent state at a glance
2. **Log Access**: Real-time log viewer without terminal
3. **Command Access**: Run agent commands from GUI
4. **Auto-Start**: Configure OS startup from settings UI

### Secondary Goals

1. **Desktop Notifications**: Alert on job completion or errors
2. **Quick Actions**: Common operations from tray menu
3. **Settings Management**: Configure agent without editing YAML

### Non-Goals (v1)

1. **Replace Web UI**: GUI is for agent management only, not full application functionality
2. **Mobile Support**: Desktop platforms only (Windows, macOS, Linux)
3. **Remote Agent Management**: Each GUI manages only its local agent
4. **Custom Theming**: Use native OS appearance

---

## User Personas

### Primary: Professional Photographer (Alex)

- **Technical Level**: Comfortable with applications, avoids terminal
- **Current Pain**: "I never know if the agent is actually running"
- **Desired Outcome**: Glance at menubar to see agent status
- **This PRD Delivers**: System tray icon with status badge

### Secondary: Studio Manager (Morgan)

- **Technical Level**: Basic computer literacy
- **Current Pain**: "I can't figure out how to make it start automatically"
- **Desired Outcome**: Check a box to enable auto-start
- **This PRD Delivers**: Settings UI with auto-start toggle

### Tertiary: Technical Power User (Jordan)

- **Technical Level**: Comfortable with CLI, prefers GUI convenience
- **Current Pain**: "Switching to terminal just to check logs is annoying"
- **Desired Outcome**: Quick access to logs and commands from tray
- **This PRD Delivers**: Log viewer and command terminal windows

---

## User Stories

### User Story 1: View Agent Status in System Tray (Priority: P0 - Critical)

**As** a user running the agent
**I want to** see the agent's status in my system tray/menubar
**So that** I know at a glance if it's running and healthy

**Acceptance Criteria:**
- System tray icon visible when agent GUI is running
- Icon changes color/appearance based on state:
  - Gray: Agent stopped
  - Green: Agent idle, connected to server
  - Yellow/Animated: Executing a job
  - Red: Error or disconnected
- Tooltip shows current status text on hover
- Left-click opens main window; right-click opens menu
- Icon persists in tray (not hidden in overflow on Windows)

**Icon States:**
```
┌─────────────────────────────────────────┐
│  System Tray Icon States                │
├─────────────────────────────────────────┤
│  ⚪ Gray      - Agent stopped           │
│  🟢 Green     - Agent idle, connected   │
│  🟡 Yellow    - Executing job           │
│  🔴 Red       - Error/disconnected      │
└─────────────────────────────────────────┘
```

**Tray Menu (Right-Click):**
```
┌─────────────────────────┐
│ ShutterSense Agent      │
├─────────────────────────┤
│ Status: Connected       │
│ Last job: 5 min ago     │
├─────────────────────────┤
│ ▶ Start Agent           │
│ ■ Stop Agent            │
├─────────────────────────┤
│ 📋 Show Logs            │
│ ⌨ Commands              │
│ ⚙ Settings              │
├─────────────────────────┤
│ ✕ Quit                  │
└─────────────────────────┘
```

**Technical Notes:**
- Use `pystray` library for cross-platform tray support
- Icon assets in PNG format (multiple sizes for different platforms)
- State changes triggered by agent events (job claimed, completed, error)
- macOS: Icon appears in menubar; Windows/Linux: System tray

---

### User Story 2: View Real-Time Agent Logs (Priority: P0 - Critical)

**As** a user troubleshooting the agent
**I want to** view the agent's logs in a window
**So that** I can see what's happening without a terminal

**Acceptance Criteria:**
- Log viewer window accessible from tray menu
- Shows same logs as CLI stdout
- Real-time updates as new logs arrive
- Scrollable with auto-scroll to bottom (toggleable)
- Log level filtering (INFO, WARNING, ERROR)
- Search/filter functionality
- Copy selected text or all logs
- Save logs to file option
- Buffer limited to prevent memory issues (last 10,000 lines)

**Log Viewer UI:**
```
┌─────────────────────────────────────────────────────┐
│  ShutterSense Agent Logs                    [_][□][X]│
├─────────────────────────────────────────────────────┤
│ Level: [All ▼]  Search: [________________] [🔍]     │
├─────────────────────────────────────────────────────┤
│ 2026-01-22 14:32:15 [INFO] Agent started            │
│ 2026-01-22 14:32:15 [INFO] Connected to server      │
│ 2026-01-22 14:32:20 [INFO] Heartbeat sent           │
│ 2026-01-22 14:32:45 [INFO] Job claimed: job_01h...  │
│ 2026-01-22 14:32:46 [INFO] Running photostats on    │
│                           "Vacation 2024"           │
│ 2026-01-22 14:33:12 [INFO] Job completed            │
│ 2026-01-22 14:33:42 [INFO] Heartbeat sent           │
│                                                     │
│ ▼ (auto-scroll enabled)                             │
├─────────────────────────────────────────────────────┤
│ [Clear] [Copy All] [Save...]        [Auto-scroll ✓] │
└─────────────────────────────────────────────────────┘
```

**Technical Notes:**
- Custom logging handler captures logs and emits to GUI
- Thread-safe queue for log messages (agent thread → GUI thread)
- Syntax highlighting for log levels (colors: INFO=default, WARN=yellow, ERROR=red)
- Window state (position, size) persisted in config

---

### User Story 3: Run Agent Commands from GUI (Priority: P1)

**As** a user who wants to run agent commands
**I want to** type commands in a GUI terminal
**So that** I don't need to open a separate terminal application

**Acceptance Criteria:**
- Command terminal window accessible from tray menu
- Input field for typing commands
- Command history (up/down arrows)
- Output area showing command results
- Supports all agent subcommands (collections, test, run, sync, etc.)
- Tab completion or command suggestions (optional enhancement)
- Prevents running `start` or `gui` commands (already running)
- Clear button to reset output
- Access to `--help` for all commands

**Command Terminal UI:**
```
┌─────────────────────────────────────────────────────┐
│  Agent Commands                             [_][□][X]│
├─────────────────────────────────────────────────────┤
│ $ shuttersense-agent collections list               │
│                                                     │
│ Collections bound to this agent (agt_01hgw2bbg...): │
│                                                     │
│   GUID              NAME            STATUS          │
│   col_01hgw2bbg001  Vacation 2024   Accessible     │
│   col_01hgw2bbg002  Wedding 2024    Accessible     │
│                                                     │
│ 2 collections total                                 │
│                                                     │
│ $ shuttersense-agent test /photos/2024              │
│                                                     │
│ Testing path: /photos/2024                          │
│   Checking accessibility... OK (1,247 files found)  │
│   Running photostats... OK                          │
│                                                     │
├─────────────────────────────────────────────────────┤
│ $ shuttersense-agent _                              │
│                                                     │
│ Available: collections, test, run, sync, config     │
├─────────────────────────────────────────────────────┤
│                                        [Run] [Clear]│
└─────────────────────────────────────────────────────┘
```

**Technical Notes:**
- Execute commands via subprocess (same binary, different args)
- Capture stdout/stderr and display in output area
- Command validation before execution
- Timeout handling for long-running commands
- Input field supports paste and standard text editing

---

### User Story 4: Configure Auto-Start on OS Startup (Priority: P1)

**As** a user who wants the agent always running
**I want to** enable auto-start from settings
**So that** the agent starts when my computer boots

**Acceptance Criteria:**
- Settings window accessible from tray menu
- Toggle for "Start agent when computer starts"
- Toggle for "Start minimized to system tray"
- Shows current configuration (server URL, agent name)
- Platform-appropriate auto-start mechanism:
  - macOS: LaunchAgent plist
  - Linux: XDG autostart desktop file
  - Windows: Registry or Startup folder
- Handles permission requirements gracefully
- Verify auto-start is working (test button or status indicator)

**Settings UI:**
```
┌─────────────────────────────────────────────────────┐
│  Settings                                   [_][□][X]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  Startup                                            │
│  ─────────────────────────────────────────────────  │
│  ☑ Start agent when computer starts                │
│  ☑ Start minimized to system tray                  │
│                                                     │
│  Notifications                                      │
│  ─────────────────────────────────────────────────  │
│  ☑ Show notification when job completes            │
│  ☐ Show notification on errors only                │
│                                                     │
│  Agent Information                                  │
│  ─────────────────────────────────────────────────  │
│  Server:  https://api.shuttersense.ai              │
│  Agent:   agt_01hgw2bbg... (My Workstation)        │
│  Status:  Connected                                 │
│                                                     │
├─────────────────────────────────────────────────────┤
│                              [Cancel]  [Save]       │
└─────────────────────────────────────────────────────┘
```

**Platform-Specific Auto-Start:**

| Platform | Mechanism | Location |
|----------|-----------|----------|
| macOS | LaunchAgent | `~/Library/LaunchAgents/ai.shuttersense.agent.plist` |
| Linux | XDG autostart | `~/.config/autostart/shuttersense-agent.desktop` |
| Windows | Registry | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |

**Technical Notes:**
- Detect platform and use appropriate mechanism
- Generate correct file format for each platform
- Handle permission issues (especially macOS Gatekeeper)
- Store preference in agent config file
- Verify file creation succeeded before showing enabled state

---

### User Story 5: Receive Desktop Notifications (Priority: P2)

**As** a user working on other tasks
**I want to** receive notifications when jobs complete
**So that** I know when analysis results are ready

**Acceptance Criteria:**
- Desktop notification on job completion (success)
- Desktop notification on job failure (error)
- Notification shows job name/collection and outcome
- Click notification to open web UI (if possible)
- Configurable: can disable or set to errors-only
- Respects OS notification settings (Do Not Disturb, etc.)

**Notification Examples:**
```
┌─────────────────────────────────────────┐
│ 🟢 Job Completed                        │
│ PhotoStats analysis finished for        │
│ "Vacation 2024"                         │
│                                         │
│ [View Results]              2 min ago   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🔴 Job Failed                           │
│ Photo Pairing failed for                │
│ "Wedding 2024"                          │
│ Error: Path not accessible              │
│                                         │
│ [View Logs]                 Just now    │
└─────────────────────────────────────────┘
```

**Technical Notes:**
- Use `plyer` library for cross-platform notifications
- Or native: `osascript` (macOS), `notify-send` (Linux), `win10toast` (Windows)
- Queue notifications if multiple jobs complete rapidly
- Include action buttons where platform supports

---

## Requirements

### Functional Requirements

#### System Tray

- **FR-001**: Display system tray icon when GUI mode is active
- **FR-002**: Update icon based on agent state (stopped, idle, running, error)
- **FR-003**: Show tooltip with current status on hover
- **FR-004**: Provide right-click context menu with common actions
- **FR-005**: Left-click opens main window or brings to focus

#### Log Viewer

- **FR-010**: Display real-time agent logs in scrollable view
- **FR-011**: Support log level filtering (INFO, WARNING, ERROR)
- **FR-012**: Provide search/filter functionality
- **FR-013**: Support copy and save operations
- **FR-014**: Limit buffer to 10,000 lines to prevent memory issues
- **FR-015**: Toggle auto-scroll behavior

#### Command Terminal

- **FR-020**: Execute agent CLI commands from GUI input
- **FR-021**: Display command output in scrollable view
- **FR-022**: Maintain command history (up/down navigation)
- **FR-023**: Prevent execution of `start` and `gui` commands
- **FR-024**: Provide command suggestions or help access

#### Auto-Start

- **FR-030**: Detect operating system and use appropriate mechanism
- **FR-031**: Create/remove auto-start entry based on user preference
- **FR-032**: Store preference in agent configuration
- **FR-033**: Handle permission errors gracefully with user guidance
- **FR-034**: Support "start minimized" option

#### Notifications

- **FR-040**: Send desktop notification on job completion
- **FR-041**: Send desktop notification on job failure
- **FR-042**: Make notifications configurable (on/off, errors-only)
- **FR-043**: Respect OS notification settings

### Non-Functional Requirements

#### Performance

- **NFR-001**: GUI startup time under 2 seconds
- **NFR-002**: Log viewer handles 10,000+ lines without lag
- **NFR-003**: Icon updates within 500ms of state change
- **NFR-004**: Memory usage under 100MB for GUI components

#### Compatibility

- **NFR-010**: Support Windows 10/11
- **NFR-011**: Support macOS 12+ (Monterey and later)
- **NFR-012**: Support Linux with common desktop environments (GNOME, KDE, XFCE)
- **NFR-013**: Work with PyInstaller-packaged binaries

#### Usability

- **NFR-020**: Native look and feel on each platform
- **NFR-021**: Keyboard shortcuts for common actions
- **NFR-022**: Window positions and sizes persisted
- **NFR-023**: Accessible (screen reader compatible where possible)

---

## Technical Approach

### Technology Stack

**Recommended Stack:**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| System Tray | `pystray` | Lightweight, cross-platform, minimal deps |
| GUI Toolkit | `PySide6` (Qt) | Native look, rich widgets, LGPL license |
| Notifications | `plyer` | Cross-platform notification abstraction |
| Icons | PNG/SVG | Multiple sizes for different platforms |

**Alternative (Minimal Footprint):**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| System Tray | `pystray` | Same as above |
| GUI Toolkit | `tkinter` | Built into Python, zero extra deps |
| Notifications | Native commands | `osascript`, `notify-send`, `powershell` |

### Architecture Overview

```
agent/
├── src/
│   ├── main.py                    # Existing agent runner
│   ├── gui/                       # NEW: GUI module
│   │   ├── __init__.py
│   │   ├── app.py                 # Main GUI application
│   │   ├── tray.py                # System tray management
│   │   ├── windows/
│   │   │   ├── log_viewer.py      # Log viewer window
│   │   │   ├── command_terminal.py # Command terminal window
│   │   │   └── settings.py        # Settings window
│   │   ├── autostart/
│   │   │   ├── __init__.py        # Platform detection
│   │   │   ├── macos.py           # LaunchAgent management
│   │   │   ├── linux.py           # XDG autostart management
│   │   │   └── windows.py         # Registry management
│   │   ├── notifications.py       # Desktop notifications
│   │   └── assets/
│   │       └── icons/
│   │           ├── icon-idle.png
│   │           ├── icon-running.png
│   │           ├── icon-error.png
│   │           └── icon-stopped.png
│   └── ...
├── cli/
│   ├── main.py                    # Existing CLI entry
│   └── gui_cmd.py                 # NEW: 'gui' subcommand
└── pyproject.toml                 # Add [gui] optional deps
```

### Entry Points

```bash
# CLI mode (existing) - terminal required
shuttersense-agent start

# GUI mode (new) - no terminal needed
shuttersense-agent gui

# Or with flag
shuttersense-agent start --gui
```

### Thread Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GUI Application                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │   Main Thread   │         │    Agent Thread         │   │
│  │   (GUI/Qt)      │◄───────►│    (asyncio loop)       │   │
│  │                 │  Queue  │                         │   │
│  │  - Tray icon    │         │  - Heartbeat loop       │   │
│  │  - Windows      │         │  - Job polling          │   │
│  │  - User input   │         │  - Job execution        │   │
│  └─────────────────┘         └─────────────────────────┘   │
│           │                            │                    │
│           │    ┌───────────────────┐   │                    │
│           └───►│  Thread-Safe      │◄──┘                    │
│                │  Communication    │                        │
│                │  - Log queue      │                        │
│                │  - State events   │                        │
│                │  - Command queue  │                        │
│                └───────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
gui = [
    "pystray>=0.19",
    "Pillow>=10.0",           # Icon manipulation
    "PySide6>=6.5",           # Qt bindings (or use tkinter)
    "plyer>=2.1",             # Cross-platform notifications
]
```

**Bundle Size Impact:**
- PySide6: +50-80MB to binary
- tkinter alternative: +0MB (built into Python)
- pystray + Pillow: +2MB

### Auto-Start File Formats

Auto-start files MUST use the actual running binary path, not hardcoded paths. The agent provides a helper function to detect the correct path:

**Binary Path Detection (`get_agent_binary_path`):**
```python
import sys
import os

def get_agent_binary_path() -> str:
    """
    Return the absolute path to the agent binary.

    - Frozen (PyInstaller): Returns sys.executable (the packaged binary)
    - Development mode: Returns os.path.abspath(sys.argv[0])

    This path is used when generating auto-start entries to ensure
    the correct binary is launched on OS startup.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return sys.executable
    else:
        # Running as Python script (dev mode)
        return os.path.abspath(sys.argv[0])
```

**macOS LaunchAgent (`ai.shuttersense.agent.plist`):**

Generated dynamically with `{binary_path}` from `get_agent_binary_path()`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.shuttersense.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{binary_path}</string>
        <string>gui</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

**Linux XDG Autostart (`shuttersense-agent.desktop`):**

Generated dynamically with `{binary_path}` from `get_agent_binary_path()`:

```ini
[Desktop Entry]
Type=Application
Name=ShutterSense Agent
Exec={binary_path} gui
Icon=shuttersense-agent
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
```

**Windows Registry:**

Generated dynamically with `{binary_path}` from `get_agent_binary_path()`:

```
Key: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
Name: ShutterSenseAgent
Value: "{binary_path}" gui
```

**Implementation Notes:**
- All auto-start generation code MUST use `get_agent_binary_path()` instead of hardcoded paths
- The helper handles both PyInstaller-frozen binaries and development mode
- Paths with spaces are properly quoted in Windows registry and work correctly in plist/desktop files

---

## Implementation Plan

### Phase 1: Core Tray Application (Priority: P0)

**Estimated Tasks: ~20**

**Agent GUI Module (15 tasks):**
1. Create `agent/src/gui/` module structure
2. Implement `TrayIcon` class with pystray
3. Create icon assets (idle, running, error, stopped states)
4. Implement state change notifications from agent to GUI
5. Create thread-safe communication queue
6. Implement tray context menu
7. Add `gui` subcommand to CLI
8. Integrate agent runner with GUI event loop
9. Handle graceful shutdown from tray
10. Implement tooltip updates
11. Add Start/Stop agent controls to menu
12. Unit tests for tray functionality
13. Integration tests for state transitions

**Dependencies (5 tasks):**
1. Add `pystray` to optional dependencies
2. Add `Pillow` for icon handling
3. Configure PyInstaller for GUI mode
4. Test packaging on all platforms

**Checkpoint:** Agent runs in system tray with status icon and basic menu.

---

### Phase 2: Log Viewer Window (Priority: P0)

**Estimated Tasks: ~15**

**Log Viewer (12 tasks):**
1. Create `LogViewerWindow` class
2. Implement custom logging handler for GUI capture
3. Create thread-safe log queue
4. Implement log display widget with scrolling
5. Add log level filtering
6. Add search/filter functionality
7. Implement copy and save operations
8. Add auto-scroll toggle
9. Implement buffer limit (10,000 lines)
10. Persist window position/size
11. Unit tests for log viewer
12. Integration tests with agent logging

**Checkpoint:** Users can view real-time logs in a window.

---

### Phase 3: Command Terminal (Priority: P1)

**Estimated Tasks: ~15**

**Command Terminal (12 tasks):**
1. Create `CommandTerminalWindow` class
2. Implement command input field
3. Implement command history (up/down)
4. Execute commands via subprocess
5. Capture and display stdout/stderr
6. Add command validation (block `start`, `gui`)
7. Implement clear functionality
8. Add help/suggestions display
9. Handle command timeout
10. Persist window position/size
11. Unit tests for command execution
12. Integration tests with agent commands

**Checkpoint:** Users can run agent commands from GUI.

---

### Phase 4: Settings and Auto-Start (Priority: P1)

**Estimated Tasks: ~20**

**Settings Window (8 tasks):**
1. Create `SettingsWindow` class
2. Implement preference toggles
3. Display agent information (read-only)
4. Save preferences to config file
5. Load preferences on startup
6. Unit tests for settings

**Auto-Start (12 tasks):**
1. Create `autostart/` module with platform detection
2. Implement macOS LaunchAgent management
3. Implement Linux XDG autostart management
4. Implement Windows Registry management
5. Handle permission errors gracefully
6. Add "Start minimized" functionality
7. Test on macOS (including Gatekeeper)
8. Test on Windows 10/11
9. Test on Linux (GNOME, KDE)
10. Integration tests for auto-start

**Checkpoint:** Users can enable auto-start from settings.

---

### Phase 5: Notifications and Polish (Priority: P2)

**Estimated Tasks: ~12**

**Notifications (6 tasks):**
1. Implement notification service
2. Send notification on job completion
3. Send notification on job failure
4. Add notification preferences
5. Handle notification click actions
6. Test on all platforms

**Polish (6 tasks):**
1. Add keyboard shortcuts
2. Improve accessibility
3. Add "About" dialog
4. Create user documentation
5. Performance optimization
6. Final testing and bug fixes

**Checkpoint:** Complete GUI with notifications and polish.

---

## Risks and Mitigation

### Risk 1: Platform-Specific Bugs

- **Impact**: High - GUI may not work correctly on all platforms
- **Probability**: Medium
- **Mitigation**: Test early on all three platforms; use CI for automated testing; prioritize one platform for MVP

### Risk 2: PyInstaller Bundle Size

- **Impact**: Medium - Large download size may deter users
- **Probability**: High (with PySide6)
- **Mitigation**: Offer tkinter-based minimal version; use `--exclude-module` aggressively; consider separate GUI download

### Risk 3: macOS Security Restrictions

- **Impact**: Medium - Gatekeeper may block unsigned app
- **Probability**: High
- **Mitigation**: Code signing required for distribution; clear documentation for "Allow" process; notarization for App Store

### Risk 4: Thread Safety Issues

- **Impact**: High - Crashes or hangs due to race conditions
- **Probability**: Medium
- **Mitigation**: Use thread-safe queues; minimize shared state; comprehensive testing; Qt's signal/slot mechanism

---

## Security Considerations

### Code Signing

- macOS and Windows binaries should be code-signed
- Notarization required for macOS distribution outside App Store
- Consider certificate costs in distribution planning

### Auto-Start Permissions

- LaunchAgent: No special permissions required
- Windows Registry: May trigger UAC on some systems
- Linux: Standard user permissions sufficient

### Command Execution

- Command terminal executes same binary (no privilege escalation)
- Input validation prevents shell injection
- Commands run with user's permissions

---

## Success Metrics

### Adoption Metrics

- **M1**: 50% of agent installations use GUI mode within 6 months
- **M2**: 70% of GUI users enable auto-start

### Quality Metrics

- **M3**: GUI crash rate below 0.1%
- **M4**: Startup time under 2 seconds (95th percentile)

### User Satisfaction

- **M5**: Support tickets related to "agent not running" decrease by 50%
- **M6**: Positive feedback on GUI usability

---

## Dependencies

### External Dependencies

- `pystray` - System tray support
- `Pillow` - Icon manipulation
- `PySide6` or `tkinter` - GUI toolkit
- `plyer` - Cross-platform notifications (optional)

### Internal Dependencies

- Agent architecture (021-distributed-agent-architecture)
- Agent CLI commands (000-remove-cli-direct-usage)

---

## Appendix

### A. Command Reference

| Menu Action | Keyboard Shortcut | Description |
|-------------|-------------------|-------------|
| Show Logs | `Ctrl+L` / `Cmd+L` | Open log viewer window |
| Commands | `Ctrl+K` / `Cmd+K` | Open command terminal |
| Settings | `Ctrl+,` / `Cmd+,` | Open settings window |
| Quit | `Ctrl+Q` / `Cmd+Q` | Stop agent and exit |

### B. Icon Specifications

| Platform | Sizes Required | Format |
|----------|----------------|--------|
| macOS | 16x16, 32x32, 64x64 @1x and @2x | PNG (template image) |
| Windows | 16x16, 32x32, 48x48, 256x256 | ICO |
| Linux | 16x16, 22x22, 24x24, 32x32, 48x48 | PNG |

### C. Alternative: Minimal tkinter Implementation

For users who prefer smaller bundle size:

```toml
[project.optional-dependencies]
gui-minimal = [
    "pystray>=0.19",
    "Pillow>=10.0",
    # tkinter is built-in, no extra dependency
]
```

Bundle size difference: ~80MB smaller than PySide6 version.

---

## Revision History

- **2026-01-22 (v1.1)**: Dynamic binary path detection for auto-start
  - Added `get_agent_binary_path()` helper specification
  - Auto-start files now use detected binary path instead of hardcoded paths
  - Handles PyInstaller frozen binaries and development mode
  - Updated macOS plist, Linux desktop, and Windows registry examples

- **2026-01-22 (v1.0)**: Initial draft
  - Defined system tray GUI for agent
  - Specified log viewer, command terminal, auto-start features
  - Outlined phased implementation plan
  - Estimated 80-85 tasks across 5 phases
