#!/usr/bin/env python3
"""
Configuration Manager for Photo Administration Tools

This module provides configuration loading and management for the photo-admin toolbox.
It handles YAML configuration files with automatic discovery, interactive creation,
and user prompts for missing camera/method mappings.

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
    """Manages configuration loading and updates for photo-admin tools."""

    def __init__(self, config_path=None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Optional explicit path to config file.
                        If None, will search standard locations.
        """
        self._config_path = None
        self._config = self._load_config(config_path)

    def _load_config(self, config_path=None):
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = self._find_config_file()

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self._config_path = Path(config_path)
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
        script_dir = Path(__file__).parent.parent  # Go up from utils/ to root

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
        script_dir = Path(__file__).parent.parent  # Go up from utils/ to root
        template_paths = [
            cwd / 'config' / 'template-config.yaml',
            script_dir / 'config' / 'template-config.yaml'
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
                    self._config_path = Path(config_path)
                    return config

            except Exception as e:
                print(f"\nError: Could not create configuration file: {e}")
                sys.exit(1)
        else:
            print("\nConfiguration file creation cancelled.")
            print("The tool requires a configuration file to run.")
            print(f"You can manually copy the template: cp {template_path} {config_path}")
            sys.exit(1)

    def _save_config(self):
        """Save current configuration back to file."""
        if not self._config_path:
            raise RuntimeError("Cannot save config: config path not set")

        with open(self._config_path, 'w') as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, sort_keys=False)

    def prompt_camera_info(self, camera_id):
        """
        Prompt user for camera information.

        Args:
            camera_id: 4-character camera ID

        Returns:
            dict: {'name': str, 'serial_number': str} or None if user cancels
        """
        print(f"\nFound new camera ID: {camera_id}")
        try:
            name = input(f"  Camera name: ").strip()
            if not name:
                name = f"Unknown Camera {camera_id}"
                print(f"  Using placeholder: {name}")

            serial = input(f"  Serial number (optional, press Enter to skip): ").strip()

            return {'name': name, 'serial_number': serial}
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            return None

    def prompt_processing_method(self, method_keyword):
        """
        Prompt user for processing method description.

        Args:
            method_keyword: The processing method keyword from filename

        Returns:
            str: Description or None if user cancels
        """
        print(f"\nFound new processing method: {method_keyword}")
        try:
            description = input(f"  Description: ").strip()
            if not description:
                description = f"Processing Method {method_keyword}"
                print(f"  Using placeholder: {description}")

            return description
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            return None

    def ensure_camera_mapping(self, camera_id):
        """
        Ensure camera mapping exists, prompting user if needed.

        Args:
            camera_id: 4-character camera ID

        Returns:
            dict: Camera info {'name': str, 'serial_number': str} or None if cancelled
        """
        if camera_id in self.camera_mappings:
            # Already exists
            return self.camera_mappings[camera_id][0] if self.camera_mappings[camera_id] else {}

        # Need to prompt user
        info = self.prompt_camera_info(camera_id)
        if info is None:
            return None

        # Save to config
        if 'camera_mappings' not in self._config:
            self._config['camera_mappings'] = {}

        # Store as list for future compatibility
        self._config['camera_mappings'][camera_id] = [{
            'name': info['name'],
            'serial_number': info['serial_number']
        }]

        self._save_config()
        return info

    def ensure_processing_method(self, method_keyword):
        """
        Ensure processing method description exists, prompting user if needed.

        Args:
            method_keyword: The processing method keyword from filename

        Returns:
            str: Description or None if cancelled
        """
        if method_keyword in self.processing_methods:
            # Already exists
            return self.processing_methods[method_keyword]

        # Need to prompt user
        description = self.prompt_processing_method(method_keyword)
        if description is None:
            return None

        # Save to config
        if 'processing_methods' not in self._config:
            self._config['processing_methods'] = {}

        self._config['processing_methods'][method_keyword] = description

        self._save_config()
        return description

    def update_camera_mappings(self, camera_updates):
        """
        Update config file with new camera mappings.

        Args:
            camera_updates: dict of {camera_id: {'name': str, 'serial_number': str}}
        """
        if 'camera_mappings' not in self._config:
            self._config['camera_mappings'] = {}

        for camera_id, info in camera_updates.items():
            # Store as list for future compatibility
            self._config['camera_mappings'][camera_id] = [{
                'name': info['name'],
                'serial_number': info['serial_number']
            }]

        self._save_config()

    def update_processing_methods(self, method_updates):
        """
        Update config file with new processing method descriptions.

        Args:
            method_updates: dict of {method_keyword: description}
        """
        if 'processing_methods' not in self._config:
            self._config['processing_methods'] = {}

        for keyword, description in method_updates.items():
            self._config['processing_methods'][keyword] = description

        self._save_config()

    def reload(self):
        """Reload configuration from file."""
        if self._config_path:
            with open(self._config_path, 'r') as f:
                self._config = yaml.safe_load(f)

    @property
    def config_path(self):
        """Get the path to the config file."""
        return self._config_path

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
    def camera_mappings(self):
        """Get the camera ID mappings dictionary."""
        return self._config.get('camera_mappings', {})

    @property
    def processing_methods(self):
        """Get the processing method descriptions dictionary."""
        return self._config.get('processing_methods', {})

    @property
    def processing_pipelines(self):
        """Get the processing pipelines configuration."""
        return self._config.get('processing_pipelines', {})

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

    # =============================================================================
    # Pipeline Validation Tool - Pipeline Configuration Methods
    # =============================================================================

    def get_processing_pipelines(self):
        """
        Get the processing_pipelines section from configuration.

        Returns:
            dict: Processing pipelines configuration, or empty dict if not present
        """
        return self._config.get('processing_pipelines', {})

    def list_available_pipelines(self):
        """
        List all available pipeline names in the configuration.

        Returns:
            list: List of pipeline names (e.g., ['default', 'v2', 'experimental'])
        """
        pipelines = self.get_processing_pipelines()
        return list(pipelines.keys()) if pipelines else []

    def get_pipeline_config(self, pipeline_name='default', verbose=False):
        """
        Get a specific pipeline configuration by name.

        Args:
            pipeline_name: Name of the pipeline to retrieve (default: 'default')
            verbose: If True, print detailed loading information

        Returns:
            dict: Pipeline configuration with 'nodes' list

        Raises:
            ValueError: If processing_pipelines section missing or pipeline not found
        """
        if verbose:
            print(f"  Loading pipeline configuration: {pipeline_name}")

        # Check if processing_pipelines section exists
        pipelines = self.get_processing_pipelines()
        if not pipelines:
            error_msg = self._get_missing_pipelines_error_message()
            raise ValueError(error_msg)

        # Check if specific pipeline exists
        if pipeline_name not in pipelines:
            available = self.list_available_pipelines()
            raise ValueError(
                f"Pipeline '{pipeline_name}' not found in configuration.\n"
                f"Available pipelines: {', '.join(available)}\n\n"
                f"Add a '{pipeline_name}' pipeline to your config.yaml:\n"
                f"{self._get_pipeline_example()}"
            )

        pipeline_config = pipelines[pipeline_name]

        if verbose:
            nodes_count = len(pipeline_config.get('nodes', []))
            print(f"  Found {nodes_count} nodes in pipeline '{pipeline_name}'")

        return pipeline_config

    def validate_pipeline_config_structure(self, pipeline_name='default', verbose=False):
        """
        Validate that a pipeline configuration has the correct basic structure.

        This validates the YAML structure only (not the pipeline logic).
        Returns errors for missing sections, invalid types, etc.

        Args:
            pipeline_name: Name of the pipeline to validate
            verbose: If True, print detailed validation information

        Returns:
            tuple: (is_valid: bool, errors: List[str])
        """
        errors = []

        if verbose:
            print(f"\nValidating pipeline configuration structure: {pipeline_name}")

        # Check processing_pipelines section exists
        pipelines = self.get_processing_pipelines()
        if not pipelines:
            errors.append("Missing 'processing_pipelines' section in configuration file")
            if verbose:
                print("  ✗ Missing 'processing_pipelines' section")
            return (False, errors)

        if verbose:
            print(f"  ✓ Found 'processing_pipelines' section")
            available = self.list_available_pipelines()
            print(f"  ✓ Available pipelines: {', '.join(available)}")

        # Check specific pipeline exists
        if pipeline_name not in pipelines:
            available = self.list_available_pipelines()
            errors.append(
                f"Pipeline '{pipeline_name}' not found. "
                f"Available: {', '.join(available)}"
            )
            if verbose:
                print(f"  ✗ Pipeline '{pipeline_name}' not found")
            return (False, errors)

        if verbose:
            print(f"  ✓ Pipeline '{pipeline_name}' exists")

        # Check pipeline has 'nodes' key
        pipeline_config = pipelines[pipeline_name]
        if 'nodes' not in pipeline_config:
            errors.append(f"Pipeline '{pipeline_name}' missing 'nodes' list")
            if verbose:
                print(f"  ✗ Missing 'nodes' list in pipeline")
            return (False, errors)

        if verbose:
            print(f"  ✓ Pipeline has 'nodes' list")

        # Check nodes is a list
        nodes = pipeline_config['nodes']
        if not isinstance(nodes, list):
            errors.append(f"Pipeline '{pipeline_name}' 'nodes' must be a list, got {type(nodes).__name__}")
            if verbose:
                print(f"  ✗ 'nodes' is not a list")
            return (False, errors)

        if verbose:
            print(f"  ✓ 'nodes' is a list with {len(nodes)} items")

        # Check nodes list is not empty
        if len(nodes) == 0:
            errors.append(f"Pipeline '{pipeline_name}' has empty 'nodes' list")
            if verbose:
                print(f"  ✗ 'nodes' list is empty")
            return (False, errors)

        if verbose:
            print(f"  ✓ 'nodes' list is not empty")

        # Detailed validation of node structure with type-specific requirements
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"Node at index {i} is not a dictionary")
                if verbose:
                    print(f"  ✗ Node {i}: not a dictionary")
                continue

            # Check base required fields (all nodes need these)
            base_required_fields = ['id', 'type', 'name']
            missing_fields = [f for f in base_required_fields if f not in node]
            if missing_fields:
                errors.append(
                    f"Node at index {i} missing required fields: {', '.join(missing_fields)}"
                )
                if verbose:
                    print(f"  ✗ Node {i}: missing fields {missing_fields}")
                continue  # Can't check type-specific fields without 'type'

            node_type = node.get('type')
            node_id = node.get('id')

            # Check type-specific required fields
            type_specific_errors = []

            if node_type == 'File':
                if 'extension' not in node:
                    type_specific_errors.append("missing 'extension' (required for File nodes)")

            elif node_type == 'Process':
                if 'method_ids' not in node:
                    type_specific_errors.append("missing 'method_ids' (required for Process nodes)")

            elif node_type == 'Pairing':
                if 'pairing_type' not in node:
                    type_specific_errors.append("missing 'pairing_type' (required for Pairing nodes, e.g., HDR, Panorama)")
                if 'input_count' not in node:
                    type_specific_errors.append("missing 'input_count' (required for Pairing nodes, number of input files)")

            elif node_type == 'Branching':
                if 'condition_description' not in node:
                    type_specific_errors.append("missing 'condition_description' (required for Branching nodes)")

            elif node_type == 'Termination':
                if 'termination_type' not in node:
                    type_specific_errors.append("missing 'termination_type' (required for Termination nodes)")

            elif node_type == 'Capture':
                # Capture nodes only need base fields
                pass

            else:
                type_specific_errors.append(f"unknown node type '{node_type}' (must be: Capture, File, Process, Pairing, Branching, or Termination)")

            if type_specific_errors:
                for error in type_specific_errors:
                    errors.append(f"Node {i} ({node_id}): {error}")
                if verbose:
                    print(f"  ✗ Node {i} ({node_id}): {', '.join(type_specific_errors)}")
            elif verbose:
                print(f"  ✓ Node {i} ({node_id}, {node_type}): valid structure")

        if errors:
            return (False, errors)

        if verbose:
            print(f"\n✓ Pipeline '{pipeline_name}' configuration structure is valid")

        return (True, [])

    def _get_missing_pipelines_error_message(self):
        """
        Get a helpful error message when processing_pipelines section is missing.

        Returns:
            str: Formatted error message with example
        """
        return (
            "Missing 'processing_pipelines' section in configuration file.\n\n"
            f"Please add a processing_pipelines section to {self.config_path}:\n\n"
            f"{self._get_pipeline_example()}\n"
            f"See config/template-config.yaml for a complete example."
        )

    def _get_pipeline_example(self):
        """
        Get an example pipeline configuration snippet.

        Returns:
            str: Example YAML configuration
        """
        return """processing_pipelines:
  default:
    nodes:
      - id: capture
        type: Capture
        name: Camera Capture
        output: [raw_file, xmp_file]

      - id: raw_file
        type: File
        name: Canon Raw File
        extension: .CR3
        output: [processing_step]

      - id: xmp_file
        type: File
        name: XMP Metadata
        extension: .XMP
        output: []

      - id: processing_step
        type: Process
        name: DNG Conversion
        method_ids: [DxO_DeepPRIME_XD2s]
        output: [dng_file]

      - id: dng_file
        type: File
        name: DNG File
        extension: .DNG
        output: [termination]

      - id: termination
        type: Termination
        name: Archive Ready
        termination_type: Black Box Archive
        output: []"""
