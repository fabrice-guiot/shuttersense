# ShutterSense Agent Installation Guide

The ShutterSense Agent is required to process photo analysis jobs. It runs on your computer and executes analysis tools against your photo collections.

## Why Do I Need an Agent?

ShutterSense uses a distributed architecture where:

- The **web application** (server) manages your collections, schedules jobs, and stores results
- The **agent** (runs on your machine) executes the actual photo analysis

This design allows the agent to access your local files directly and keeps your photos under your control.

## System Requirements

- **Operating System**: macOS 10.15+, Windows 10+, or Linux (Ubuntu 20.04+ recommended)
- **Disk Space**: 50 MB for the agent binary
- **Network**: Internet connection to reach the ShutterSense server

## Installation

### Step 1: Download the Agent

Download the agent binary for your platform from the ShutterSense server:

| Platform | Download |
|----------|----------|
| macOS (Intel/Apple Silicon) | `shuttersense-agent-macos` |
| Windows | `shuttersense-agent-windows.exe` |
| Linux | `shuttersense-agent-linux` |

### Step 2: Make Executable (macOS/Linux)

On macOS and Linux, make the downloaded file executable:

```bash
chmod +x shuttersense-agent
```

### Step 3: Get a Registration Token

1. Log into the ShutterSense web application
2. Navigate to **Settings** > **Agents**
3. Click **Generate Token**
4. Copy the token (starts with `art_`)

Registration tokens are single-use and expire after 24 hours.

### Step 4: Register the Agent

Run the registration command with your server URL and token:

```bash
./shuttersense-agent register \
  --server https://your-shuttersense-server.com \
  --token art_01abc123... \
  --name "My Home Computer"
```

Replace:
- `https://your-shuttersense-server.com` with your actual server URL
- `art_01abc123...` with your registration token
- `"My Home Computer"` with a descriptive name for this agent

You'll see a success message when registration completes.

### Step 5: Start the Agent

```bash
./shuttersense-agent start
```

The agent will:
1. Connect to the ShutterSense server
2. Start polling for jobs
3. Execute jobs assigned to it
4. Report results back to the server

Leave the agent running while you want jobs to be processed.

## Running as a Background Service

### macOS (launchd)

Create `~/Library/LaunchAgents/ai.shuttersense.agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.shuttersense.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/shuttersense-agent</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/ai.shuttersense.agent.plist
```

### Linux (systemd)

Create `~/.config/systemd/user/shuttersense-agent.service`:

```ini
[Unit]
Description=ShutterSense Agent
After=network.target

[Service]
ExecStart=/path/to/shuttersense-agent start
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Enable and start:
```bash
systemctl --user daemon-reload
systemctl --user enable shuttersense-agent
systemctl --user start shuttersense-agent
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create a new task
3. Set trigger: "At startup"
4. Set action: Start `shuttersense-agent.exe` with argument `start`
5. Enable "Run whether user is logged on or not"

## Configuration

Agent configuration is stored in:

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Application Support/shuttersense-agent/` |
| Linux | `~/.config/shuttersense-agent/` |
| Windows | `%APPDATA%\shuttersense-agent\` |

Configuration files:
- `config.yaml` - Server URL and agent settings
- `agent.key` - Agent authentication credentials (encrypted)

## Agent Status

Check agent status in the web application:

1. Navigate to **Settings** > **Agents**
2. Your agent should appear with status "Online"
3. The Agent Pool indicator in the header shows available agents

## Binding Collections to Agents

Local filesystem collections must be bound to specific agents:

1. Navigate to **Collections**
2. Select or create a collection with a local path
3. In **Bound Agent**, select your agent
4. Jobs for this collection will only run on the bound agent

Cloud storage collections (S3, GCS) can run on any agent.

## Troubleshooting

### Agent Shows "Offline"

- Ensure the agent is running: `./shuttersense-agent start`
- Check network connectivity to the server
- Verify the server URL is correct in the agent config

### Registration Failed

- Token may have expired (valid for 24 hours)
- Token may have already been used (single-use)
- Generate a new token and try again

### Jobs Not Processing

- Check that the agent is online in the web UI
- For local collections, ensure the agent is bound to the collection
- Check that the collection path is accessible to the agent

### Permission Errors

The agent needs read access to analyze collections. Ensure the user running the agent has permission to read the photo directories.

### Logs

View agent logs for debugging:

```bash
# macOS/Linux
tail -f ~/.config/shuttersense-agent/logs/agent.log

# Windows
type %APPDATA%\shuttersense-agent\logs\agent.log
```

## Uninstalling

1. Stop the agent:
   - If running manually: Ctrl+C
   - If running as service: Stop the service

2. Remove the binary

3. Remove configuration (optional):
   - macOS: `rm -rf ~/Library/Application\ Support/shuttersense-agent`
   - Linux: `rm -rf ~/.config/shuttersense-agent`
   - Windows: Delete `%APPDATA%\shuttersense-agent`

4. Remove the agent from the web UI:
   - Navigate to **Settings** > **Agents**
   - Click the delete button for the agent

## Security Notes

- Agent credentials are stored encrypted on disk
- Agents communicate with the server over HTTPS
- Agents only access collections they're authorized for
- Registration tokens are single-use and time-limited

## Related Documentation

- [Agent Build Guide](agent-build.md) - For developers building the agent
