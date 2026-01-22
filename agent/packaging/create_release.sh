#!/bin/bash
# Create a release package for ShutterSense Agent
# Packages built binaries with checksums and documentation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$AGENT_DIR/dist"
RELEASE_DIR="$BUILD_DIR/release"

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

# Collect all built binaries
collect_binaries() {
    local version=$1
    local release_name="shuttersense-agent-${version}"
    local package_dir="$RELEASE_DIR/$release_name"

    echo "Creating release package: $release_name"

    # Clean and create release directory
    rm -rf "$package_dir"
    mkdir -p "$package_dir"

    # Copy README
    cp "$AGENT_DIR/README.md" "$package_dir/"

    # Copy binaries by platform
    local platforms_found=0

    for platform_dir in "$BUILD_DIR"/*/; do
        local platform=$(basename "$platform_dir")

        # Skip non-platform directories
        case "$platform" in
            build|spec|release|__pycache__)
                continue
                ;;
        esac

        # Find binary in this platform directory
        for binary in "$platform_dir"shuttersense-agent*; do
            if [ -f "$binary" ] && [[ ! "$binary" == *.sha256 ]]; then
                local binary_name=$(basename "$binary")
                local target_dir="$package_dir/$platform"

                mkdir -p "$target_dir"
                cp "$binary" "$target_dir/"
                cp "${binary}.sha256" "$target_dir/" 2>/dev/null || true

                echo "  - $platform/$binary_name"
                platforms_found=$((platforms_found + 1))
            fi
        done
    done

    if [ $platforms_found -eq 0 ]; then
        echo "Error: No binaries found in $BUILD_DIR"
        echo "Run build_all.sh first to build the agent"
        exit 1
    fi

    echo ""
    return 0
}

# Generate checksums file
generate_checksums() {
    local version=$1
    local release_name="shuttersense-agent-${version}"
    local package_dir="$RELEASE_DIR/$release_name"
    local checksums_file="$package_dir/CHECKSUMS.txt"

    echo "Generating checksums file..."

    {
        echo "ShutterSense Agent $version"
        echo "=========================="
        echo ""
        echo "SHA-256 Checksums"
        echo "-----------------"
        echo ""
    } > "$checksums_file"

    for platform_dir in "$package_dir"/*/; do
        local platform=$(basename "$platform_dir")

        for sha_file in "$platform_dir"*.sha256; do
            if [ -f "$sha_file" ]; then
                local checksum=$(cat "$sha_file")
                local binary_name=$(basename "$sha_file" .sha256)
                echo "$checksum  $platform/$binary_name" >> "$checksums_file"
            fi
        done
    done

    echo ""
    echo "Binary Attestation"
    echo "------------------"
    echo ""
    echo "To enable binary attestation, create a Release Manifest in the" >> "$checksums_file"
    echo "ShutterSense admin UI (Settings > Release Manifests) with:" >> "$checksums_file"
    echo "" >> "$checksums_file"
    echo "  Version: $version" >> "$checksums_file"
    echo "  Platforms: [select all platforms in this release]" >> "$checksums_file"
    echo "  Checksum: [use the appropriate checksum from above]" >> "$checksums_file"
    echo "" >> "$checksums_file"
    echo "Note: Universal binaries (e.g., macOS) have one checksum for" >> "$checksums_file"
    echo "multiple platforms. Configure the manifest with all supported" >> "$checksums_file"
    echo "platforms for that checksum." >> "$checksums_file"

    echo "  - $checksums_file"
}

# Create archive
create_archive() {
    local version=$1
    local release_name="shuttersense-agent-${version}"
    local package_dir="$RELEASE_DIR/$release_name"

    echo ""
    echo "Creating archives..."

    cd "$RELEASE_DIR"

    # Create tar.gz
    tar -czf "${release_name}.tar.gz" "$release_name"
    echo "  - ${release_name}.tar.gz"

    # Create zip
    if command -v zip &> /dev/null; then
        zip -rq "${release_name}.zip" "$release_name"
        echo "  - ${release_name}.zip"
    fi

    cd - > /dev/null
}

# Print summary
print_summary() {
    local version=$1
    local release_name="shuttersense-agent-${version}"

    echo ""
    echo "=========================================="
    echo "Release Package Created"
    echo "=========================================="
    echo ""
    echo "Version: $version"
    echo "Location: $RELEASE_DIR/"
    echo ""
    echo "Contents:"
    ls -la "$RELEASE_DIR/${release_name}"* 2>/dev/null | while read line; do
        echo "  $line"
    done
    echo ""
    echo "Next steps:"
    echo "1. Upload archives to release hosting"
    echo "2. Create Release Manifest in admin UI"
    echo "3. Update documentation with download links"
    echo ""
}

# Main
main() {
    echo "ShutterSense Agent Release Packager"
    echo ""

    local version=$(get_version)

    # Clean version string for filename (remove + and other special chars)
    local clean_version=$(echo "$version" | tr '+' '-' | tr ':' '-')

    echo "Version: $version"
    echo ""

    # Create release directory
    mkdir -p "$RELEASE_DIR"

    # Collect binaries
    collect_binaries "$clean_version"

    # Generate checksums
    generate_checksums "$clean_version"

    # Create archives
    create_archive "$clean_version"

    # Print summary
    print_summary "$clean_version"
}

main "$@"
