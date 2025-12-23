# Configuration

**Configuration is required** to run this tool. The tool uses a YAML configuration file to specify which file types should be treated as photos and which should have XMP sidecars.

## First-Time Setup

When you run the tool for the first time without a configuration file, it will:

1. **Automatically detect** that no configuration exists
2. **Prompt you** to create one from the template
3. **Create the config file** for you if you accept (just press Enter)

Example:
```
$ python photo_stats.py /path/to/photos

No configuration file found.
Template found at: config/template-config.yaml

Would you like to create a configuration file at: config/config.yaml
Create config file? [Y/n]:

✓ Configuration file created: config/config.yaml

You can now modify this file to customize file type settings for your needs.
The tool will use this configuration for all future runs.
```

## Manual Configuration Setup

You can also manually create your configuration:

```bash
cp config/template-config.yaml config/config.yaml
```

Then edit `config/config.yaml` to customize the file extensions for your needs.

**Note:** The `config/config.yaml` file is ignored by git, so your personal configuration won't be committed.

## Configuration File Locations

The tool will automatically look for configuration files in the following locations (in order):
1. `config/config.yaml` in the current directory
2. `config.yaml` in the current directory
3. `~/.photo_stats_config.yaml` in your home directory
4. `config/config.yaml` in the script directory

You can also explicitly specify a configuration file as the third command-line argument:

```bash
python photo_stats.py /path/to/photos report.html config/custom-config.yaml
```

## Configuration File Format

The configuration file uses YAML format with three key sections:

1. **photo_extensions**: All file types to scan and count
2. **require_sidecar**: File types that MUST have XMP sidecars (orphaned if missing)
3. **metadata_extensions**: Valid sidecar file extensions

See `config/template-config.yaml` for a complete example:

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

## Understanding File Pairing

**Key Concept**: Not all photo files need XMP sidecars!

- **DNG and TIFF** files embed their metadata internally, so they don't need sidecars
- **RAW formats** (CR3, NEF, ARW, etc.) typically require external XMP files for metadata

The `require_sidecar` setting lets you specify which formats need sidecars in YOUR workflow. Only files listed there will be flagged as "orphaned" when they lack an XMP file.

## Template Configuration

The template file (`config/template-config.yaml`) provides default settings:
- **Photo extensions**: `.dng`, `.tiff`, `.tif`, `.cr3`
- **Require sidecar**: `.cr3` only
- **Metadata extensions**: `.xmp`

You can uncomment additional format options in the template or add your own custom extensions.

## Supported File Types

The tool is configurable and can support any RAW or image format. Additional formats that can be added via the configuration file include:

- **NEF** (Nikon RAW)
- **ARW** (Sony RAW)
- **ORF** (Olympus RAW)
- **RW2** (Panasonic RAW)
- **PEF** (Pentax RAW)
- **RAF** (Fujifilm RAW)
- **CR2** (Canon RAW, older format)
- **RAW**, **CRW**, and other manufacturer-specific formats

## Next Steps

After configuring the tool, see the [PhotoStats documentation](photostats.md) to learn how to use it.
