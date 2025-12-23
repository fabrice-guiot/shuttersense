# Installation

This guide covers installing the photo-admin toolbox.

## Requirements

- Python 3.x
- pip package manager
- Git (for cloning the repository)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/fabrice-guiot/photo-admin.git
cd photo-admin
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Verify Installation

To verify that the installation was successful, you can run:

```bash
python photo_stats.py --help
```

This should display usage information without any errors.

## Next Steps

After installation, you'll need to configure the tool before first use. See the [Configuration Guide](configuration.md) for details on setting up your configuration file.

## Development Installation

If you plan to contribute to the project or run tests, install the development dependencies:

```bash
pip install -r requirements.txt
```

Then you can run the test suite:

```bash
python -m pytest tests/ -v
```

For more information on testing, see the Development section in the main [README](../README.md).
