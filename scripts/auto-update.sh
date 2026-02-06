#!/bin/bash
#
# ShutterSense Auto-Update Script
# Checks for new version tags and performs automated updates
#
# Usage: ./auto-update.sh
#
# IMPORTANT: This script should be invoked by auto-update-cron.sh, not directly
# from cron. The cron wrapper runs as root and calls this script as the
# shuttersense user, then handles the service restart as root.
#
# This script is deployed to /opt/shuttersense/scripts/.
# See docs/deployment-hostinger-kvm2.md section 15.3 for cron configuration.
#
# What it does:
#   1. Fetches new tags from the remote repository
#   2. Compares the latest tag with the currently deployed version
#   3. If a newer version exists, performs the full update process
#   4. Outputs "SERVICE_RESTART_REQUIRED" if an update was performed
#   5. Logs all output for troubleshooting
#
# What it does NOT do:
#   - Restart the service (handled by auto-update-cron.sh as root)
#   - Update nginx configuration (requires manual intervention)
#   - Handle breaking changes that need manual migration steps
#
# Update Policy:
#   By default, only minor and patch updates are applied automatically.
#   Major version updates (e.g., v1.x → v2.x) require manual intervention
#   unless AUTO_UPDATE_MAJOR is set to "true".
#
# Environment Variables (optional):
#   APP_DIR           - Application directory (default: /opt/shuttersense/app)
#   SCRIPTS_DIR       - Server scripts directory (default: /opt/shuttersense/scripts)
#   AUTO_UPDATE_MAJOR - Set to "true" to allow automatic major version updates (default: false)
#
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/shuttersense/app}"
SCRIPTS_DIR="${SCRIPTS_DIR:-/opt/shuttersense/scripts}"
AUTO_UPDATE_MAJOR="${AUTO_UPDATE_MAJOR:-false}"

# =============================================================================
# Logging
# =============================================================================

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    # Output to stdout only - cron wrapper handles file logging
    echo "[$timestamp] $1"
}

log_error() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    # Output to stderr only - cron wrapper handles file logging
    echo "[$timestamp] ERROR: $1" >&2
}

# =============================================================================
# Version Comparison
# =============================================================================

# Extract version numbers from tag (v1.2.3 -> 1 2 3)
parse_version() {
    local version=$1
    # Remove 'v' prefix and split by dots
    echo "${version#v}" | tr '.' ' '
}

# Compare two version strings (returns: 0=equal, 1=first>second, 2=first<second)
compare_versions() {
    local v1=$1
    local v2=$2

    # Handle identical versions
    if [[ "$v1" == "$v2" ]]; then
        return 0
    fi

    local v1_parts v2_parts
    read -ra v1_parts <<< "$(parse_version "$v1")"
    read -ra v2_parts <<< "$(parse_version "$v2")"

    # Compare each part
    for i in 0 1 2; do
        local p1=${v1_parts[$i]:-0}
        local p2=${v2_parts[$i]:-0}

        if [[ $p1 -gt $p2 ]]; then
            return 1
        elif [[ $p1 -lt $p2 ]]; then
            return 2
        fi
    done

    return 0
}

# Check if update is a major version change (v1.x.x → v2.x.x)
is_major_update() {
    local from_version=$1
    local to_version=$2

    local from_parts to_parts
    read -ra from_parts <<< "$(parse_version "$from_version")"
    read -ra to_parts <<< "$(parse_version "$to_version")"

    local from_major=${from_parts[0]:-0}
    local to_major=${to_parts[0]:-0}

    [[ $to_major -gt $from_major ]]
}

# =============================================================================
# Update Functions
# =============================================================================

get_current_version() {
    cd "$APP_DIR"
    # Try to get exact tag, fall back to describe
    git describe --tags --exact-match 2>/dev/null || git describe --tags 2>/dev/null || echo "v0.0.0"
}

get_latest_remote_tag() {
    cd "$APP_DIR"
    # Get tags sorted by version (descending), take the first one
    # Accepts both v1.2 and v1.2.3 formats
    git tag --sort=-v:refname | grep -E '^v[0-9]+(\.[0-9]+){1,2}$' | head -1
}

perform_update() {
    local target_version=$1

    log "Starting update to $target_version..."

    cd "$APP_DIR"

    # Step 1: Hard reset to the target version
    log "Step 1/6: Resetting to $target_version..."
    git reset --hard "$target_version"

    # Step 2: Update backend dependencies
    log "Step 2/6: Updating backend dependencies..."
    source venv/bin/activate
    pip install --quiet -r backend/requirements.txt

    # Step 3: Set environment for migrations
    log "Step 3/6: Loading environment..."
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a

    # Step 4: Rebuild frontend
    log "Step 4/6: Rebuilding frontend..."
    cd frontend
    npm ci --silent
    npm run build
    cd ..

    # Step 5: Run database migrations
    log "Step 5/6: Running database migrations..."
    cd backend
    alembic upgrade head
    cd ..

    # Step 6: Update maintenance scripts and run cleanup
    log "Step 6/6: Updating maintenance scripts and cleaning up..."
    # Copy all scripts EXCEPT auto-update scripts (can't overwrite running scripts)
    # - auto-update.sh: copied by cron wrapper after this script finishes
    # - auto-update-cron.sh: never auto-updated (rarely changes, requires manual update)
    local script_basename
    for script in scripts/*.sh; do
        script_basename=$(basename "$script")
        if [[ "$script_basename" != "auto-update.sh" && "$script_basename" != "auto-update-cron.sh" ]]; then
            cp "$script" "$SCRIPTS_DIR/"
        fi
    done
    chmod +x "$SCRIPTS_DIR"/*.sh
    "$SCRIPTS_DIR/production-cleanup.sh"

    log "Update to $target_version completed successfully!"
    log "SERVICE_RESTART_REQUIRED"
}

# =============================================================================
# Main
# =============================================================================

main() {
    log "=========================================="
    log "ShutterSense Auto-Update Check"
    log "=========================================="

    # Verify app directory exists
    if [[ ! -d "$APP_DIR/.git" ]]; then
        log_error "App directory $APP_DIR is not a git repository"
        exit 1
    fi

    cd "$APP_DIR"

    # Get current version
    local current_version
    current_version=$(get_current_version)
    log "Current version: $current_version"

    # Fetch latest tags from remote
    log "Fetching tags from remote..."
    git fetch origin --tags --quiet

    # Get latest available tag
    local latest_version
    latest_version=$(get_latest_remote_tag)

    if [[ -z "$latest_version" ]]; then
        log "No release tags found in repository"
        exit 0
    fi

    log "Latest available version: $latest_version"

    # Compare versions
    set +e
    compare_versions "$latest_version" "$current_version"
    local comparison=$?
    set -e

    case $comparison in
        0)
            log "Already running the latest version ($current_version)"
            ;;
        1)
            log "New version available: $latest_version (current: $current_version)"

            # Check if this is a major version update
            if is_major_update "$current_version" "$latest_version"; then
                if [[ "$AUTO_UPDATE_MAJOR" == "true" ]]; then
                    log "Major version update detected - AUTO_UPDATE_MAJOR is enabled, proceeding..."
                    perform_update "$latest_version"
                else
                    log "SKIPPED: Major version update detected ($current_version → $latest_version)"
                    log "Major updates may contain breaking changes and require manual intervention."
                    log "To update manually: cd $APP_DIR && git fetch --tags && git reset --hard $latest_version"
                    log "To enable automatic major updates: export AUTO_UPDATE_MAJOR=true"
                fi
            else
                perform_update "$latest_version"
            fi
            ;;
        2)
            log "Current version ($current_version) is ahead of latest tag ($latest_version)"
            log "This may indicate a development build or pre-release. No action taken."
            ;;
    esac

    log "Auto-update check complete"
    log ""
}

# Run main function (cron wrapper handles logging to file)
main 2>&1
