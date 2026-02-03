#!/bin/bash
# Build ShutterSense Agent for all available platforms
# This script builds for the current platform and outputs checksums for Release Manifests
#
# Output structure: dist/{version}/shuttersense-agent-{platform}
# Example: dist/v1.0.0/shuttersense-agent-darwin-arm64

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$AGENT_DIR/dist"

# Detect current platform
detect_platform() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)

    case "$os" in
        darwin)
            case "$arch" in
                arm64) echo "darwin-arm64" ;;
                x86_64) echo "darwin-amd64" ;;
                *) echo "darwin-unknown" ;;
            esac
            ;;
        linux)
            case "$arch" in
                aarch64|arm64) echo "linux-arm64" ;;
                x86_64) echo "linux-amd64" ;;
                *) echo "linux-unknown" ;;
            esac
            ;;
        mingw*|msys*|cygwin*)
            echo "windows-amd64"
            ;;
        *)
            echo "unknown-$arch"
            ;;
    esac
}

# Get version from environment or Git (same logic as individual build scripts)
get_version() {
    if [ -n "$SHUSAI_VERSION" ]; then
        echo "$SHUSAI_VERSION"
        return
    fi

    cd "$AGENT_DIR/.."
    local version=$(git describe --tags --long --always 2>/dev/null || echo "")
    if [ -n "$version" ]; then
        # Parse: v1.2.3-0-ga1b2c3d (on tag) or v1.2.3-5-ga1b2c3d (5 commits after)
        if [[ "$version" =~ ^(.+)-([0-9]+)-g([a-f0-9]+)$ ]]; then
            local tag="${BASH_REMATCH[1]}"
            local commits="${BASH_REMATCH[2]}"
            local hash="${BASH_REMATCH[3]}"
            if [ "$commits" = "0" ]; then
                echo "$tag"
            else
                echo "${tag}-dev.${commits}+${hash}"
            fi
        else
            # Just a commit hash (no tags)
            local hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            echo "v0.0.0-dev+$hash"
        fi
    else
        echo "v0.0.0-dev+unknown"
    fi
}

# Build for current platform
build_current_platform() {
    local platform=$(detect_platform)
    local os_part=${platform%%-*}

    echo "=========================================="
    echo "Building ShutterSense Agent"
    echo "Platform: $platform"
    echo "=========================================="
    echo ""

    case "$os_part" in
        darwin)
            "$SCRIPT_DIR/build_macos.sh"
            ;;
        linux)
            "$SCRIPT_DIR/build_linux.sh"
            ;;
        windows)
            "$SCRIPT_DIR/build_windows.sh"
            ;;
        *)
            echo "Error: Unsupported platform: $platform"
            exit 1
            ;;
    esac
}

# Print release summary
print_summary() {
    local version=$(get_version)
    local platform=$(detect_platform)
    local version_dir="$BUILD_DIR/$version"

    echo ""
    echo "=========================================="
    echo "Build Summary"
    echo "=========================================="
    echo ""
    echo "Version: $version"
    echo "Platform: $platform"
    echo ""
    echo "Release Manifest Information"
    echo "----------------------------"
    echo "Use these values when creating a Release Manifest:"
    echo ""

    # Find all checksums in the version directory
    if [ -d "$version_dir" ]; then
        for checksum_file in "$version_dir"/*.sha256; do
            if [ -f "$checksum_file" ]; then
                local checksum=$(cat "$checksum_file")
                local binary_name=$(basename "$checksum_file" .sha256)
                local binary_path="$version_dir/$binary_name"

                # Extract platform from filename (shuttersense-agent-{platform})
                local artifact_platform=$(echo "$binary_name" | sed 's/shuttersense-agent-//')

                echo "Artifact:"
                echo "  Platform: $artifact_platform"
                echo "  Filename: $binary_name"
                echo "  Path: $binary_path"
                echo "  SHA-256: $checksum"
                echo ""
            fi
        done
    else
        echo "Warning: No build artifacts found in $version_dir"
        echo ""
    fi

    echo "=========================================="
    echo "Next Steps"
    echo "=========================================="
    echo ""
    echo "1. Create a Release Manifest in the admin UI:"
    echo "   Settings > Release Manifests > Create New"
    echo ""
    echo "2. Enter the version and checksum(s) above"
    echo ""
    echo "3. Copy binaries to SHUSAI_AGENT_DIST_DIR:"
    echo "   cp -r $version_dir /path/to/agent-dist/"
    echo ""
    echo "4. The agent wizard will serve binaries from:"
    echo "   {SHUSAI_AGENT_DIST_DIR}/$version/{filename}"
    echo ""
}

# Main
main() {
    echo "ShutterSense Agent Build Script"
    echo ""

    # Create dist directory
    mkdir -p "$BUILD_DIR"

    # Build for current platform
    build_current_platform

    # Print summary
    print_summary
}

main "$@"
