# ShutterSense Agent Build Guide

This guide documents how to build the ShutterSense Agent binary for distribution.

## Overview

The ShutterSense Agent is a lightweight binary that runs on user machines to execute photo analysis jobs. It connects to the ShutterSense server, claims jobs, executes them locally, and reports results back.

The agent is packaged with PyInstaller into a standalone executable that bundles its own Python runtime. End users do not need Python installed.

## Prerequisites

- Python 3.12 or higher
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
│   ├── build_all.sh       # Auto-detects platform and builds
│   ├── build_macos.sh
│   ├── build_linux.sh
│   └── build_windows.sh
├── tests/                 # Test suite
├── .venv/                 # Agent virtual environment (NOT checked in)
└── pyproject.toml         # Package configuration and dependencies
```

## Development Setup

> **Important:** The agent MUST use its own virtual environment, separate from the backend's `venv/`. The agent is distributed as a standalone binary — its dependencies must match what PyInstaller bundles, not what the backend server uses. Mixing environments masks missing dependencies that will cause failures in the deployed binary.

### 1. Create an Isolated Agent venv

```bash
cd agent

# Create a dedicated virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install agent with dev dependencies
pip install -e ".[dev]"
```

### 2. Run Tests

```bash
cd agent
source .venv/bin/activate
pytest
```

### 3. Run in Development Mode

```bash
source agent/.venv/bin/activate
shuttersense-agent --help
shuttersense-agent register --server http://localhost:8000 --token art_xxx --name "Dev Agent"
shuttersense-agent start
```

## Building Standalone Binaries

The agent uses PyInstaller to create standalone executables that don't require Python to be installed on the target machine. The build Python and its SSL libraries are bundled into the binary.

> **Note:** The build scripts use the active Python interpreter. Make sure `python3` points to the correct version (3.12+) before building. The build Python becomes the runtime bundled into the binary.

### macOS Build

```bash
cd agent
source .venv/bin/activate
pip install -e ".[build]"
./packaging/build_macos.sh
```

Output: `agent/dist/<version>/shuttersense-agent-darwin-<arch>`

### Linux Build

```bash
cd agent
source .venv/bin/activate
pip install -e ".[build]"
./packaging/build_linux.sh
```

Output: `agent/dist/<version>/shuttersense-agent-linux-<arch>`

The Linux build should be performed on the target distribution for best compatibility (e.g., Ubuntu 22.04 for general compatibility).

### Windows Build

```powershell
cd agent
.venv\Scripts\activate
pip install -e ".[build]"
.\packaging\build_windows.sh
```

Output: `agent/dist/<version>/shuttersense-agent-windows-amd64.exe`

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
shasum -a 256 dist/<version>/shuttersense-agent-darwin-arm64

# Windows (PowerShell)
Get-FileHash dist\<version>\shuttersense-agent-windows-amd64.exe -Algorithm SHA256
```

## Version Management

The agent version is automatically derived from Git tags:

- **Tagged release**: `v1.2.3`
- **Development build**: `v1.2.3+g1a2b3c4.d20260121`

Version is embedded at build time via `hatch-vcs` in `pyproject.toml`.

## Dependencies

### Runtime Dependencies (bundled into binary)

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
| boto3 | AWS S3 storage adapter |
| google-cloud-storage | GCS storage adapter |
| smbprotocol | SMB/CIFS storage adapter |

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
./dist/<version>/shuttersense-agent-darwin-arm64 --version

# Verify it runs (will fail without registration, but confirms binary works)
./dist/<version>/shuttersense-agent-darwin-arm64 self-test
# Expected: Error about missing registration
```

## CI/CD Integration

For automated builds in CI:

```bash
cd agent

# Create isolated build environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[build]"

# Build for current platform
./packaging/build_all.sh

# Upload artifacts
# - Binary: dist/<version>/shuttersense-agent-<platform>
# - Checksum: dist/<version>/shuttersense-agent-<platform>.sha256
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
codesign --sign "Developer ID Application: Your Name" dist/<version>/shuttersense-agent-darwin-arm64
```

### Windows Defender False Positives

Unsigned Windows executables may trigger antivirus warnings. For production, sign with a code signing certificate.

### SSL/TLS Certificate Errors

If the agent fails with SSL certificate errors (e.g., `match_hostname` failures), the Python used for the build may have an OpenSSL mismatch. Verify the build Python has consistent OpenSSL headers and runtime:

```bash
python3 -c "import ssl; print('Compile-time:', ssl.OPENSSL_VERSION_INFO); print('Runtime:', ssl.OPENSSL_VERSION)"
```

The `OPENSSL_VERSION_INFO` major version (compile-time) should match the `OPENSSL_VERSION` major version (runtime). For example, both should be 3.x. A mismatch (compile-time says 1.1.1 but runtime says 3.x) means Python was compiled against wrong headers — rebuild Python.

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
