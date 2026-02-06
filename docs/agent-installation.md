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

Create `/Library/LaunchDaemons/ai.shuttersense.agent.plist`:

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
        <string>/usr/local/bin/shuttersense-agent</string>
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

Install and start the service:
```bash
# Create log directory
sudo mkdir -p /var/log/shuttersense

# Copy plist to LaunchDaemons
sudo cp ai.shuttersense.agent.plist /Library/LaunchDaemons/

# Load the service
sudo launchctl load /Library/LaunchDaemons/ai.shuttersense.agent.plist
```

Manage the service:
```bash
# Check status
sudo launchctl list | grep shuttersense

# Stop the service
sudo launchctl unload /Library/LaunchDaemons/ai.shuttersense.agent.plist

# View logs
tail -f /var/log/shuttersense/shuttersense-agent.stdout.log
```

#### Log Rotation (newsyslog)

macOS logs do not rotate automatically. Create `/etc/newsyslog.d/shuttersense.conf`:

```
# logfile                                          mode  count  size   when  flags
/var/log/shuttersense/shuttersense-agent.stdout.log 644   7      1024   *     J
/var/log/shuttersense/shuttersense-agent.stderr.log 644   7      1024   *     J
```

This configuration:
- Rotates logs when they reach 1 MB (`size` column, in KB)
- Keeps 7 rotated files (`count` column)
- Compresses rotated files with bzip2 (`J` flag)

Install the configuration:
```bash
sudo cp shuttersense.conf /etc/newsyslog.d/

# Verify configuration is valid
sudo newsyslog -vn
```

### Linux (systemd)

Create `/etc/systemd/system/shuttersense-agent.service`:

```ini
[Unit]
Description=ShutterSense Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/shuttersense-agent start
Restart=always
RestartSec=10
User=shuttersense

[Install]
WantedBy=multi-user.target
```

Create a service user and install:
```bash
# Create a dedicated service user (no home directory, no login shell)
sudo useradd --system --no-create-home shuttersense

# Copy the service file
sudo cp shuttersense-agent.service /etc/systemd/system/

# Reload systemd, enable, and start
sudo systemctl daemon-reload
sudo systemctl enable shuttersense-agent
sudo systemctl start shuttersense-agent
```

Manage the service:
```bash
# Check status
sudo systemctl status shuttersense-agent

# View logs (journald handles rotation automatically)
sudo journalctl -u shuttersense-agent -f

# Stop the service
sudo systemctl stop shuttersense-agent
```

> **Note:** On Linux, systemd's journald manages log rotation automatically. No additional configuration is required.

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create a new task
3. Set trigger: "At startup"
4. Set action: Start `shuttersense-agent.exe` with argument `start`
5. Enable "Run whether user is logged on or not"

> **Note:** Task Scheduler does not capture stdout/stderr. Check the application logs at `%APPDATA%\shuttersense-agent\logs\agent.log` for debugging.

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

**When running as a service:**
```bash
# macOS (launchd service logs)
tail -f /var/log/shuttersense/shuttersense-agent.stdout.log
tail -f /var/log/shuttersense/shuttersense-agent.stderr.log

# Linux (journald)
sudo journalctl -u shuttersense-agent -f
```

**Application logs (all platforms):**
```bash
# macOS
tail -f ~/Library/Application\ Support/shuttersense-agent/logs/agent.log

# Linux
tail -f ~/.config/shuttersense-agent/logs/agent.log

# Windows (PowerShell)
Get-Content -Wait "$env:APPDATA\shuttersense-agent\logs\agent.log"
```

## Uninstalling

### macOS

```bash
# Stop and unload the service
sudo launchctl unload /Library/LaunchDaemons/ai.shuttersense.agent.plist

# Remove service files
sudo rm /Library/LaunchDaemons/ai.shuttersense.agent.plist
sudo rm /etc/newsyslog.d/shuttersense.conf

# Remove logs
sudo rm -rf /var/log/shuttersense

# Remove binary
sudo rm /usr/local/bin/shuttersense-agent

# Remove configuration
rm -rf ~/Library/Application\ Support/shuttersense-agent
```

### Linux

```bash
# Stop and disable the service
sudo systemctl stop shuttersense-agent
sudo systemctl disable shuttersense-agent

# Remove service file
sudo rm /etc/systemd/system/shuttersense-agent.service
sudo systemctl daemon-reload

# Remove service user (optional)
sudo userdel shuttersense

# Remove binary
sudo rm /usr/local/bin/shuttersense-agent

# Remove configuration
rm -rf ~/.config/shuttersense-agent
```

### Windows

1. Remove the scheduled task from Task Scheduler
2. Delete the binary (`shuttersense-agent.exe`)
3. Delete configuration: `%APPDATA%\shuttersense-agent`

### Web UI

Remove the agent from the web application:
1. Navigate to **Settings** > **Agents**
2. Click the delete button for the agent

## Security Notes

- Agent credentials are stored encrypted on disk
- Agents communicate with the server over HTTPS
- Agents only access collections they're authorized for
- Registration tokens are single-use and time-limited

## Related Documentation

- [Agent Build Guide](agent-build.md) - For developers building the agent
