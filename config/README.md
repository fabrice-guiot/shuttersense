# Configuration Directory

This directory contains configuration files for the ShutterSense CLI tools.

## Files

- **template-config.yaml**: Template configuration file with all available options and examples
- **config.yaml**: Your personal configuration file (gitignored, not committed to version control)

## Getting Started

To create your own configuration:

```bash
cp template-config.yaml config.yaml
```

Then edit `config.yaml` to customize the file extensions for your workflow.

## Configuration Options

The configuration file allows you to specify:

- **photo_extensions**: List of file extensions that should be considered photo files
- **metadata_extensions**: List of file extensions for metadata sidecar files (typically .xmp)

See `template-config.yaml` for a complete example with many RAW format options.
