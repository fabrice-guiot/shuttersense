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
 * Escape XML special characters in a string.
 *
 * @param str - String to escape
 * @returns Escaped string safe for XML interpolation
 */
function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

/**
 * Generate a macOS launchd plist for the ShutterSense agent.
 *
 * The generated plist configures the agent to:
 * - Start at boot (RunAtLoad)
 * - Restart automatically if it exits (KeepAlive)
 * - Log stdout/stderr to /var/log/shuttersense/
 * - Use SHUSAI_CONFIG_PATH to point to user's config (required for LaunchDaemons)
 *
 * LaunchDaemons run as root, so the config path must be explicitly set to the
 * user's config location since ~ expands to /var/root instead of /Users/<username>.
 *
 * @param binaryPath - Absolute path to the agent binary
 * @param username - macOS username (used to build config path)
 * @returns XML plist string
 */
export function generateLaunchdPlist(binaryPath: string, username: string): string {
  const safePath = escapeXml(binaryPath)
  const safeUsername = escapeXml(username.trim())
  const configPath = `/Users/${safeUsername}/Library/Application Support/shuttersense/agent-config.yaml`
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.shuttersense.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>${safePath}</string>
        <string>start</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>SHUSAI_CONFIG_PATH</key>
        <string>${configPath}</string>
    </dict>
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
/**
 * Generate a macOS newsyslog configuration for log rotation.
 *
 * The generated configuration:
 * - Rotates logs when they reach 1 MB
 * - Keeps 7 rotated files
 * - Compresses rotated files with bzip2
 *
 * @returns newsyslog configuration string
 */
export function generateNewsyslogConfig(): string {
  return `# ShutterSense Agent log rotation configuration
# logfile                                          mode  count  size   when  flags
/var/log/shuttersense/shuttersense-agent.stdout.log 644   7      1024   *     J
/var/log/shuttersense/shuttersense-agent.stderr.log 644   7      1024   *     J`
}

export function generateSystemdUnit(binaryPath: string, user: string): string {
  const trimmedUser = user.trim()
  return `[Unit]
Description=ShutterSense Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart="${binaryPath}" start
Restart=always
RestartSec=10
User=${trimmedUser}

[Install]
WantedBy=multi-user.target`
}
