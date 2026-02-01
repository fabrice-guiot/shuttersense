/**
 * Service file generators for the Agent Setup Wizard.
 *
 * Generates platform-specific service configuration files:
 * - macOS: launchd plist (XML)
 * - Linux: systemd unit file
 *
 * Issue #136 - Agent Setup Wizard
 */

/**
 * Generate a macOS launchd plist for the ShutterSense agent.
 *
 * The generated plist configures the agent to:
 * - Start at login (RunAtLoad)
 * - Restart automatically if it exits (KeepAlive)
 * - Log stdout/stderr to /var/log/shuttersense/
 *
 * @param binaryPath - Absolute path to the agent binary
 * @returns XML plist string
 */
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

/**
 * Generate a Linux systemd unit file for the ShutterSense agent.
 *
 * The generated unit configures the agent to:
 * - Start after network is online
 * - Restart automatically with a 10-second delay
 * - Run as the specified user
 *
 * @param binaryPath - Absolute path to the agent binary
 * @param user - Linux user to run the service as
 * @returns Systemd unit file string
 */
export function generateSystemdUnit(binaryPath: string, user: string): string {
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
