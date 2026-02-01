# ShutterSense Agent Build Guide

This guide documents how to build the ShutterSense Agent binary for distribution.

## Overview

The ShutterSense Agent is a lightweight binary that runs on user machines to execute photo analysis jobs. It connects to the ShutterSense server, claims jobs, executes them locally, and reports results back.

## Prerequisites

- Python 3.11 or higher
- pip package manager
- Git (for version detection)

### Platform-Specific Requirements

| Platform | Additional Requirements |
|----------|------------------------|
| macOS | Xcode Command Line Tools |
| Linux | gcc, make |
| Windows | Visual Studio Build Tools |

## Project Structure

```
agent/
├── cli/                    # CLI entry points
│   └── main.py            # Click-based CLI (shuttersense-agent command)
├── src/                   # Core agent source code
│   ├── api_client.py      # HTTP client for server communication
│   ├── polling_loop.py    # Job polling and execution loop
│   ├── job_executor.py    # Tool execution wrapper
│   ├── credential_store.py # Encrypted local credential storage
│   └── remote/            # Remote storage adapters (S3, GCS, SMB)
├── packaging/             # Build scripts
│   ├── build_macos.sh
│   ├── build_linux.sh
│   └── build_windows.sh
├── tests/                 # Test suite
└── pyproject.toml         # Package configuration
```

## Development Setup

### 1. Clone and Install

```bash
cd agent
pip install -e ".[dev]"
```

This installs the agent in editable mode with development dependencies.

### 2. Run Tests

```bash
cd agent
pytest
```

### 3. Run in Development Mode

```bash
shuttersense-agent --help
shuttersense-agent register --server http://localhost:8000 --token art_xxx --name "Dev Agent"
shuttersense-agent start
```

## Building Standalone Binaries

The agent uses PyInstaller to create standalone executables that don't require Python to be installed on the target machine.

### macOS Build

```bash
cd agent
./packaging/build_macos.sh
```

Output: `agent/dist/macos/shuttersense-agent`

This creates a universal binary that works on both Intel and Apple Silicon Macs.

### Linux Build

```bash
cd agent
./packaging/build_linux.sh
```

Output: `agent/dist/linux/shuttersense-agent`

The Linux build should be performed on the target distribution for best compatibility (e.g., Ubuntu 22.04 for general compatibility).

### Windows Build

```powershell
cd agent
.\packaging\build_windows.sh
```

Output: `agent/dist/windows/shuttersense-agent.exe`

## Build Artifacts

Each build script produces:

| File | Description |
|------|-------------|
| `shuttersense-agent[.exe]` | Standalone executable |
| `shuttersense-agent.sha256` | SHA-256 checksum for attestation |

## Binary Attestation

The server uses binary attestation to verify agent authenticity. After building:

1. Record the SHA-256 checksum from the build output
2. Create a Release Manifest in the admin UI (Settings > Release Manifests)
3. Enter the version, platforms, and checksum
4. Only agents with matching checksums can register

### Checksum Calculation

The build scripts automatically calculate and save checksums:

```bash
# macOS/Linux
shasum -a 256 dist/macos/shuttersense-agent

# Windows (PowerShell)
Get-FileHash dist\windows\shuttersense-agent.exe -Algorithm SHA256
```

## Version Management

The agent version is automatically derived from Git tags:

- **Tagged release**: `v1.2.3`
- **Development build**: `v1.2.3+g1a2b3c4.d20260121`

Version is embedded at build time via `hatch-vcs` in `pyproject.toml`.

## Dependencies

### Runtime Dependencies

| Package | Purpose |
|---------|---------|
| httpx | HTTP client for server communication |
| websockets | Real-time progress streaming |
| pydantic | Configuration and data validation |
| pydantic-settings | Settings management |
| cryptography | Encrypted credential storage |
| click | CLI framework |
| PyYAML | Configuration file parsing |
| platformdirs | Platform-specific paths |

### Build Dependencies

| Package | Purpose |
|---------|---------|
| pyinstaller | Binary packaging |
| hatchling | Build system |
| hatch-vcs | Version from Git |

## Testing the Build

After building, verify the binary works:

```bash
# Check version
./dist/macos/shuttersense-agent --version

# Verify it runs (will fail without registration, but confirms binary works)
./dist/macos/shuttersense-agent start
# Expected: Error about missing registration
```

## CI/CD Integration

For automated builds in CI:

```bash
# Install build dependencies
pip install pyinstaller

# Build for current platform
cd agent
./packaging/build_$(uname -s | tr '[:upper:]' '[:lower:]').sh

# Upload artifacts
# - Binary: dist/<platform>/shuttersense-agent
# - Checksum: dist/<platform>/shuttersense-agent.sha256
```

## Troubleshooting

### PyInstaller Hidden Import Errors

If the binary fails with import errors, add the missing module to the `--hidden-import` flags in the build script.

### Large Binary Size

The binary includes the Python runtime and all dependencies. Typical sizes:
- macOS: ~15-20 MB
- Linux: ~15-20 MB
- Windows: ~20-25 MB

### Code Signing (macOS)

For distribution outside the App Store, sign the binary:

```bash
codesign --sign "Developer ID Application: Your Name" dist/macos/shuttersense-agent
```

### Windows Defender False Positives

Unsigned Windows executables may trigger antivirus warnings. For production, sign with a code signing certificate.

## Release Checklist

1. [ ] All tests pass
2. [ ] Version tag created (e.g., `git tag v1.0.0`)
3. [ ] Build on all target platforms
4. [ ] Record checksums for each platform
5. [ ] Create Release Manifest in admin UI
6. [ ] Test registration with new binary
7. [ ] Update documentation with new version

## Related Documentation

- [Agent Installation Guide](agent-installation.md) - End-user installation guide
- [Agent Architecture](../agent/README.md) - Technical architecture details
