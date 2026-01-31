#!/bin/bash
# Build ShutterSense Agent for Linux
# Produces a standalone binary that runs without Python installed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$AGENT_DIR/dist"

echo "Building ShutterSense Agent for Linux..."

# Ensure we're in the agent directory
cd "$AGENT_DIR"

# Install build dependencies if needed
pip install -q "pyinstaller==6.18.0"

# Build the agent binary
pyinstaller \
    --name shuttersense-agent \
    --onefile \
    --console \
    --clean \
    --noconfirm \
    --distpath "$BUILD_DIR/linux" \
    --workpath "$BUILD_DIR/build" \
    --specpath "$BUILD_DIR/spec" \
    --add-data "src:src" \
    --add-data "cli:cli" \
    --hidden-import "websockets" \
    --hidden-import "httpx" \
    --hidden-import "pydantic" \
    --hidden-import "cryptography" \
    --hidden-import "click" \
    --hidden-import "yaml" \
    cli/main.py

# Calculate checksum for attestation
BINARY_PATH="$BUILD_DIR/linux/shuttersense-agent"
if [ -f "$BINARY_PATH" ]; then
    CHECKSUM=$(sha256sum "$BINARY_PATH" | cut -d' ' -f1)
    echo "$CHECKSUM" > "$BUILD_DIR/linux/shuttersense-agent.sha256"
    echo "Build complete: $BINARY_PATH"
    echo "SHA-256: $CHECKSUM"
else
    echo "Error: Binary not found at $BINARY_PATH"
    exit 1
fi
