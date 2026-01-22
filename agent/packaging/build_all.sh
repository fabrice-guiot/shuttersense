#!/bin/bash
# Build ShutterSense Agent for all available platforms
# This script builds for the current platform and outputs checksums for Release Manifests

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

# Get version from git
get_version() {
    cd "$AGENT_DIR/.."
    if git describe --tags --exact-match 2>/dev/null; then
        return
    fi
    # Development version with commit hash
    local tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    local commits=$(git rev-list --count "${tag}..HEAD" 2>/dev/null || echo "0")
    local hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo "${tag}+${commits}.${hash}"
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
    local os_part=${platform%%-*}

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

    # Find all checksums
    for checksum_file in "$BUILD_DIR"/*/*.sha256; do
        if [ -f "$checksum_file" ]; then
            local binary_dir=$(dirname "$checksum_file")
            local dir_name=$(basename "$binary_dir")
            local checksum=$(cat "$checksum_file")
            local binary_name=$(basename "$checksum_file" .sha256)

            echo "Platform: $dir_name"
            echo "Binary: $binary_dir/$binary_name"
            echo "SHA-256: $checksum"
            echo ""
        fi
    done

    echo "=========================================="
    echo "Next Steps"
    echo "=========================================="
    echo ""
    echo "1. Create a Release Manifest in the admin UI:"
    echo "   Settings > Release Manifests > Create New"
    echo ""
    echo "2. Enter the version and checksum(s) above"
    echo ""
    echo "3. Distribute the binary to users"
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
