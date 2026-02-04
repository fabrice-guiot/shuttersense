#!/bin/bash
#
# ShutterSense Production Cleanup Script
# Removes development artifacts after deployment
#
# Usage: ./production-cleanup.sh [--dry-run]
#
# This script should be run after every deployment to remove development
# artifacts that aren't needed at runtime. This reduces disk usage, improves
# security by removing source code, and eliminates potential information leakage.
#
set -euo pipefail

# Default app directory - can be overridden via environment variable
APP_DIR="${SHUTTERSENSE_APP_DIR:-/opt/shuttersense/app}"
DRY_RUN="${1:-}"

log() {
    echo "[CLEANUP] $1"
}

remove() {
    local target="$1"
    if [[ -e "$target" ]]; then
        if [[ "$DRY_RUN" == "--dry-run" ]]; then
            log "Would remove: $target"
        else
            rm -rf "$target"
            log "Removed: $target"
        fi
    fi
}

# Verify we're in the right directory
if [[ ! -d "$APP_DIR/backend" ]]; then
    echo "ERROR: $APP_DIR does not appear to be a ShutterSense installation"
    echo "       Set SHUTTERSENSE_APP_DIR environment variable to override"
    exit 1
fi

cd "$APP_DIR"

log "Starting production cleanup..."
log "App directory: $APP_DIR"
[[ "$DRY_RUN" == "--dry-run" ]] && log "DRY RUN MODE - no files will be deleted"

# =============================================================================
# 1. Development Tool Configurations
# =============================================================================
log "Removing development tool configurations..."
remove ".claude"
remove ".specify"
remove ".vscode"
remove ".idea"
remove ".ruff_cache"

# =============================================================================
# 2. Design Specifications & Documentation (keep deployment docs)
# =============================================================================
log "Removing design specifications..."
remove "specs"
remove "CLAUDE.md"
remove "CONTRIBUTING.md"
remove "CHANGELOG.md"

# =============================================================================
# 3. Test Directories
# =============================================================================
log "Removing test directories..."
remove "tests"
remove "backend/tests"
remove "agent/tests"
remove "frontend/tests"
remove ".pytest_cache"
remove "backend/.pytest_cache"
remove "agent/.pytest_cache"
remove "htmlcov"
remove "backend/htmlcov"
remove ".coverage"
remove "backend/.coverage"
remove "coverage.xml"

# =============================================================================
# 4. Frontend Source (keep only dist/)
# =============================================================================
log "Cleaning frontend (keeping dist/ only)..."
remove "frontend/src"
remove "frontend/public"
remove "frontend/node_modules"
remove "frontend/.vite"
remove "frontend/coverage"
remove "frontend/index.html"
remove "frontend/vite.config.ts"
remove "frontend/tsconfig.json"
remove "frontend/tsconfig.node.json"
remove "frontend/tailwind.config.js"
remove "frontend/postcss.config.js"
remove "frontend/eslint.config.js"
remove "frontend/package.json"
remove "frontend/package-lock.json"
remove "frontend/vitest.config.ts"
remove "frontend/components.json"

# =============================================================================
# 5. Agent Source (keep only pre-built distributions if present)
# =============================================================================
log "Cleaning agent directory..."
remove "agent/src"
remove "agent/cli"
remove "agent/tests"
remove "agent/packaging"
remove "agent/requirements.txt"
remove "agent/pyproject.toml"
remove "agent/setup.py"
# Keep agent/dist/ if pre-built binaries are present

# =============================================================================
# 6. Python Cache Files
# =============================================================================
log "Removing Python cache files..."
if [[ "$DRY_RUN" == "--dry-run" ]]; then
    # Show what would be removed
    find "$APP_DIR" -type d -name "__pycache__" 2>/dev/null | while read -r dir; do
        log "Would remove: $dir"
    done
    find "$APP_DIR" -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \) 2>/dev/null | while read -r file; do
        log "Would remove: $file"
    done
else
    find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$APP_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
    find "$APP_DIR" -type f -name "*.pyd" -delete 2>/dev/null || true
fi

# =============================================================================
# 7. Git History (optional - saves ~50MB+ but prevents git pull updates)
# =============================================================================
# Uncomment the following line to remove git history:
# remove ".git"

# =============================================================================
# 8. Miscellaneous Development Files
# =============================================================================
log "Removing miscellaneous development files..."
remove "pytest.ini"
remove "pyproject.toml"
remove "setup.py"
remove "setup.cfg"
remove ".gitignore"
remove ".gitattributes"
remove ".editorconfig"
remove ".pre-commit-config.yaml"
remove "Makefile"
remove "docker-compose.yml"
remove "docker-compose.yaml"
remove "Dockerfile"
remove ".github"
# Remove the scripts directory since we are manually copying needed scripts to 
# /opt/shuttersense/scripts/
remove "scripts"

# Remove markdown files except those in docs/
if [[ "$DRY_RUN" == "--dry-run" ]]; then
    find "$APP_DIR" -type f -name "*.md" ! -path "*/docs/*" 2>/dev/null | while read -r file; do
        log "Would remove: $file"
    done
else
    find "$APP_DIR" -type f -name "*.md" ! -path "*/docs/*" -delete 2>/dev/null || true
fi

# Remove macOS metadata files
if [[ "$DRY_RUN" == "--dry-run" ]]; then
    find "$APP_DIR" -type f -name ".DS_Store" 2>/dev/null | while read -r file; do
        log "Would remove: $file"
    done
else
    find "$APP_DIR" -type f -name ".DS_Store" -delete 2>/dev/null || true
fi

# =============================================================================
# 9. Scripts Directory (keep only production scripts)
# =============================================================================
# Note: This script removes itself from the deployed app since it's only
# needed during deployment. The canonical version lives in the git repo.
# Uncomment if you want to remove scripts after cleanup:
# remove "scripts"

# =============================================================================
# 10. Calculate Space Savings
# =============================================================================
log "Cleanup complete!"
if [[ "$DRY_RUN" != "--dry-run" ]]; then
    REMAINING_SIZE=$(du -sh "$APP_DIR" 2>/dev/null | cut -f1)
    log "Remaining application size: $REMAINING_SIZE"
fi

log "Production cleanup finished."
