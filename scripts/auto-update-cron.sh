#!/bin/bash
#
# ShutterSense Auto-Update Cron Wrapper
# This script is designed to run from root's crontab to orchestrate auto-updates.
#
# Usage: This script should be run as root via cron
#
# Example crontab entry (as root):
#   0 4 * * * /opt/shuttersense/scripts/auto-update-cron.sh
#
# What it does:
#   1. Runs the auto-update.sh script as the shuttersense user
#   2. If an update was performed, copies updated auto-update.sh and restarts service
#
# NOTE: This script is NOT auto-updated (it's running during the update process).
# If changes are made to this file, manually copy it to the server:
#   scp scripts/auto-update-cron.sh root@server:/opt/shuttersense/scripts/
#
# This separation is necessary because:
#   - The update process (git, npm, pip) should run as the application user
#   - The service restart requires root privileges
#
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/shuttersense/app}"
SCRIPTS_DIR="${SCRIPTS_DIR:-/opt/shuttersense/scripts}"
LOG_FILE="${LOG_FILE:-/var/log/shuttersense/auto-update.log}"
SERVICE_USER="${SERVICE_USER:-shuttersense}"
AUTO_UPDATE_MAJOR="${AUTO_UPDATE_MAJOR:-false}"

# =============================================================================
# Logging
# =============================================================================

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [cron-wrapper] $1" | tee -a "$LOG_FILE"
}

log_error() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [cron-wrapper] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Ensure log directory and file exist with proper permissions
    # This must happen before any log() calls to avoid root-owned log files
    mkdir -p "$(dirname "$LOG_FILE")"
    chown "$SERVICE_USER":"$SERVICE_USER" "$(dirname "$LOG_FILE")" 2>/dev/null || true
    touch "$LOG_FILE"
    chown "$SERVICE_USER":"$SERVICE_USER" "$LOG_FILE" 2>/dev/null || true
    chmod 644 "$LOG_FILE" 2>/dev/null || true

    # Verify we're running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi

    # Verify the auto-update script exists
    if [[ ! -x "$SCRIPTS_DIR/auto-update.sh" ]]; then
        log_error "Auto-update script not found or not executable: $SCRIPTS_DIR/auto-update.sh"
        exit 1
    fi

    log "Starting auto-update check..."

    # Run the auto-update script as the service user and capture output
    local update_output
    local update_exit_code=0

    # Pass through environment variables to the child script
    update_output=$(su - "$SERVICE_USER" -c "APP_DIR='$APP_DIR' SCRIPTS_DIR='$SCRIPTS_DIR' AUTO_UPDATE_MAJOR='$AUTO_UPDATE_MAJOR' '$SCRIPTS_DIR/auto-update.sh'" 2>&1) || update_exit_code=$?

    # Write captured output to log file
    echo "$update_output" >> "$LOG_FILE"

    # Check if the update script failed
    if [[ $update_exit_code -ne 0 ]]; then
        log_error "Auto-update script failed with exit code $update_exit_code"
        exit $update_exit_code
    fi

    # Check if a service restart is required (indicated by SERVICE_RESTART_REQUIRED in output)
    if echo "$update_output" | grep -q "SERVICE_RESTART_REQUIRED"; then
        # Copy auto-update.sh now (couldn't be done mid-execution)
        # Note: auto-update-cron.sh is NOT auto-updated (rarely changes, and it's currently running)
        if [[ -f "$APP_DIR/scripts/auto-update.sh" ]]; then
            cp "$APP_DIR/scripts/auto-update.sh" "$SCRIPTS_DIR/"
            chmod +x "$SCRIPTS_DIR/auto-update.sh"
            log "Updated auto-update.sh"
        fi

        log "Update completed, restarting shuttersense service..."
        systemctl restart shuttersense

        if systemctl is-active --quiet shuttersense; then
            log "Service restarted successfully"
        else
            log_error "Service failed to start after update!"
            log "Checking service status..."
            systemctl status shuttersense --no-pager || true
            exit 1
        fi
    else
        log "No update performed, service restart not needed"
    fi

    log "Auto-update cron job complete"
}

main "$@"
