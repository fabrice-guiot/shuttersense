# Configuration

ShutterSense uses configuration to specify which file types should be treated as photos and which should have XMP sidecars. Configuration is managed through the agent and web application.

## Agent Configuration

The agent stores its configuration in a platform-specific data directory managed by `platformdirs`. Configuration is created automatically during agent registration.

```bash
# Register the agent (creates config automatically)
shuttersense-agent register \
  --server http://localhost:8000 \
  --token art_xxxxx... \
  --name "My Agent"

# Verify configuration
shuttersense-agent self-test
```

See [Agent Installation Guide](agent-installation.md) for detailed agent setup.

## Analysis Configuration

Analysis tools (PhotoStats, Photo Pairing, Pipeline Validation) use YAML-formatted configuration to specify file type settings. This configuration is managed at the team level on the ShutterSense server and automatically synced to agents.

### How Configuration Works

1. **Server-Side Management**: Configuration is defined for your team through the web application under Team Settings.
2. **Automatic Sync**: The agent fetches your team's configuration from the server before each analysis run.
3. **Local Cache**: Configuration is cached locally for offline operation (24-hour TTL).
4. **Validation**: Use `shuttersense-agent self-test` to verify the agent can reach the server and load configuration.

### Configuration Format

```yaml
# Photo Statistics Configuration

# File types that should be scanned
photo_extensions:
  - .dng      # DNG files (already contain metadata, no sidecar needed)
  - .tiff     # TIFF files (already contain metadata, no sidecar needed)
  - .tif      # TIFF files (already contain metadata, no sidecar needed)
  - .cr3      # Canon CR3 RAW (requires XMP sidecar)
  - .nef      # Nikon RAW (requires XMP sidecar)
  # Add more formats as needed

# File types that REQUIRE XMP sidecar files
# Only these will be flagged as "orphaned" if missing sidecars
require_sidecar:
  - .cr3
  - .nef
  # Note: DNG and TIFF embed metadata, so they don't need sidecars

# Valid metadata sidecar file extensions
metadata_extensions:
  - .xmp
```

### Camera Mappings and Processing Methods

For Photo Pairing analysis, you can configure camera mappings and processing method descriptions:

```yaml
camera_mappings:
  AB3D:
    - name: Canon EOS R5
      serial_number: "12345"
  XYZW:
    - name: Sony A7R5
      serial_number: "67890"

processing_methods:
  HDR: High Dynamic Range
  BW: Black and White
  Pano: Panorama
  Focus Stack: Focus Stacking
```

## Understanding File Pairing

**Key Concept**: Not all photo files need XMP sidecars!

- **DNG and TIFF** files embed their metadata internally, so they don't need sidecars
- **RAW formats** (CR3, NEF, ARW, etc.) typically require external XMP files for metadata

The `require_sidecar` setting lets you specify which formats need sidecars in YOUR workflow. Only files listed there will be flagged as "orphaned" when they lack an XMP file.

## Supported File Types

The tool is configurable and can support any RAW or image format:

- **DNG** (Adobe Digital Negative)
- **CR3** (Canon RAW)
- **NEF** (Nikon RAW)
- **ARW** (Sony RAW)
- **ORF** (Olympus RAW)
- **RW2** (Panasonic RAW)
- **PEF** (Pentax RAW)
- **RAF** (Fujifilm RAW)
- **CR2** (Canon RAW, older format)
- **TIFF/TIF** (Tagged Image File Format)

## Running Analysis

Analysis tools are executed through the agent:

```bash
# Test a local path with PhotoStats
shuttersense-agent test /path/to/photos --tool photostats

# Run analysis against a registered collection
shuttersense-agent run <collection-guid> --tool photostats

# Available tools: photostats, photo_pairing, pipeline_validation
```

## Next Steps

- See the [Agent Installation Guide](agent-installation.md) for agent setup
- See the [Installation Guide](installation.md) for web application setup
