#!/usr/bin/env python3
"""
Configuration Manager for Photo Administration Tools

This module provides configuration loading and management for the photo-admin toolbox.
It handles YAML configuration files with automatic discovery and interactive creation.

Copyright (C) 2024 Fabrice Guiot

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import sys
from pathlib import Path
import yaml


class PhotoAdminConfig:
    """Manages configuration loading for photo-admin tools."""

    def __init__(self, config_path=None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Optional explicit path to config file.
                        If None, will search standard locations.
        """
        self._config = self._load_config(config_path)

    def _load_config(self, config_path=None):
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = self._find_config_file()

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    print(f"Loaded configuration from: {config_path}")
                    return config
            except Exception as e:
                print(f"Error: Could not load config from {config_path}: {e}")
                sys.exit(1)

        # No config file found - check for template and offer to create
        return self._handle_missing_config()

    def _find_config_file(self):
        """
        Search for config file in standard locations.

        Returns:
            Path object if found, None otherwise.
        """
        # Start with current working directory, then fall back to script location
        cwd = Path.cwd()
        script_dir = Path(__file__).parent

        possible_paths = [
            cwd / 'config' / 'config.yaml',
            cwd / 'config.yaml',
            Path.home() / '.photo_stats_config.yaml',
        ]

        # Only add script location if we're actually in/near the script directory
        # or if there's no local config directory (to support installed package usage)
        if not (cwd / 'config').exists() or cwd == script_dir or script_dir in cwd.parents:
            possible_paths.append(script_dir / 'config' / 'config.yaml')

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _handle_missing_config(self):
        """Handle missing configuration file by offering to create from template."""
        # Look for template file in current working directory first, then script location
        cwd = Path.cwd()
        template_paths = [
            cwd / 'config' / 'template-config.yaml',
            Path(__file__).parent / 'config' / 'template-config.yaml'
        ]

        template_path = None
        for path in template_paths:
            if path.exists():
                template_path = path
                break

        if not template_path:
            print("\nError: Configuration template file not found.")
            print("The tool does not appear to be properly installed.")
            print("Please refer to the README for installation instructions:")
            print("  https://github.com/fabrice-guiot/photo-admin/blob/main/README.md")
            sys.exit(1)

        # Determine where to create the config file
        config_dir = Path('config')
        if not config_dir.exists():
            config_dir = template_path.parent

        config_path = config_dir / 'config.yaml'

        print("\nNo configuration file found.")
        print(f"Template found at: {template_path}")
        print(f"\nWould you like to create a configuration file at: {config_path}")

        # Prompt user for confirmation
        response = input("Create config file? [Y/n]: ").strip().lower()

        if response in ('', 'y', 'yes'):
            try:
                # Ensure config directory exists
                config_dir.mkdir(parents=True, exist_ok=True)

                # Copy template to config.yaml
                import shutil
                shutil.copy(template_path, config_path)

                print(f"\n✓ Configuration file created: {config_path}")
                print("\nYou can now modify this file to customize file type settings for your needs.")
                print("The tool will use this configuration for all future runs.")

                # Load the newly created config
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config

            except Exception as e:
                print(f"\nError: Could not create configuration file: {e}")
                sys.exit(1)
        else:
            print("\nConfiguration file creation cancelled.")
            print("The tool requires a configuration file to run.")
            print(f"You can manually copy the template: cp {template_path} {config_path}")
            sys.exit(1)

    @property
    def photo_extensions(self):
        """Get the set of photo file extensions."""
        return set(self._config.get('photo_extensions', []))

    @property
    def metadata_extensions(self):
        """Get the set of metadata file extensions."""
        return set(self._config.get('metadata_extensions', []))

    @property
    def require_sidecar(self):
        """Get the set of extensions that require sidecar files."""
        return set(self._config.get('require_sidecar', []))

    @property
    def raw_config(self):
        """Get the raw configuration dictionary."""
        return self._config

    def get(self, key, default=None):
        """
        Get a configuration value by key.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
