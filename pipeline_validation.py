#!/usr/bin/env python3
"""
Photo Processing Pipeline Validation Tool

Validates photo collections against user-defined processing workflows (pipelines)
defined as directed graphs of nodes. Integrates with Photo Pairing Tool to obtain
file groupings, traverses pipeline paths, and classifies images as CONSISTENT,
CONSISTENT-WITH-WARNING, PARTIAL, or INCONSISTENT.

Core Value: Automated validation of 10,000+ image groups in under 60 seconds
(with caching), enabling photographers to identify incomplete processing workflows
and assess archival readiness without manual file inspection.

Usage:
    python3 pipeline_validation.py <folder_path>
    python3 pipeline_validation.py <folder_path> --config <config_path>
    python3 pipeline_validation.py <folder_path> --force-regenerate
    python3 pipeline_validation.py --help

Author: photo-admin project
License: AGPL-3.0
Version: 1.0.0
"""

import argparse
import sys
import signal
import json
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

# Import shared utilities
from utils.config_manager import PhotoAdminConfig
from utils.report_renderer import ReportRenderer

# Import pipeline processing logic
from utils.pipeline_processor import (
    # Data structures
    NodeBase,
    CaptureNode,
    FileNode,
    ProcessNode,
    PairingNode,
    BranchingNode,
    TerminationNode,
    PipelineConfig,
    ValidationStatus,
    SpecificImage,
    ValidationResult,
    TerminationMatchResult,

    # Configuration
    load_pipeline_config,
    validate_pipeline_structure,

    # Validation
    validate_all_images,
    validate_specific_image,
    classify_validation_status,
    generate_sample_base_filename,

    # Path enumeration
    enumerate_all_paths,
    enumerate_paths_with_pairing,
    generate_expected_files,
    find_pairing_nodes_in_topological_order,
    validate_pairing_node_inputs,
    merge_two_paths,

    # Constants
    MAX_ITERATIONS,
)

# Import Photo Pairing Tool for file grouping
try:
    import photo_pairing
    PHOTO_PAIRING_AVAILABLE = True
except ImportError:
    PHOTO_PAIRING_AVAILABLE = False


# Tool version (semantic versioning)
TOOL_VERSION = "1.0.0"

# Global flag for graceful shutdown
shutdown_requested = False


# =============================================================================
# Photo Pairing Integration
# =============================================================================

# =============================================================================
# Photo Pairing Tool Integration
# =============================================================================

def load_or_generate_imagegroups(folder_path: Path, force_regenerate: bool = False) -> List[Dict[str, Any]]:
    """
    Load ImageGroups from Photo Pairing cache or generate if missing.

    This function integrates with the Photo Pairing Tool by either:
    1. Loading existing .photo_pairing_imagegroups cache file
    2. Running Photo Pairing Tool to generate ImageGroups (if cache missing)

    Args:
        folder_path: Path to folder containing photos
        force_regenerate: If True, ignore cache and regenerate from scratch

    Returns:
        List of ImageGroup dictionaries from Photo Pairing Tool

    Raises:
        FileNotFoundError: If cache doesn't exist and can't generate
        ValueError: If cache is invalid or corrupted
    """
    import photo_pairing

    cache_file = folder_path / '.photo_pairing_imagegroups'

    # If force_regenerate, run Photo Pairing Tool
    if force_regenerate or not cache_file.exists():
        print(f"Running Photo Pairing Tool to generate ImageGroups...")

        # Use photo_pairing module directly
        # Note: This assumes photo_pairing can be imported as a module
        try:
            # Get all files in folder (photo_pairing.build_imagegroups expects Path objects)
            all_files = [f for f in folder_path.iterdir() if f.is_file()]

            # Build ImageGroups using photo_pairing module
            # Returns: {'imagegroups': [...], 'invalid_files': [...]}
            result = photo_pairing.build_imagegroups(all_files, folder_path)
            imagegroups = result['imagegroups']
            invalid_files = result['invalid_files']

            if invalid_files:
                print(f"  Warning: {len(invalid_files)} invalid files skipped")

            return imagegroups
        except Exception as e:
            raise ValueError(f"Failed to generate ImageGroups: {e}")

    # Load from cache
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        imagegroups = cache_data.get('imagegroups')
        if not imagegroups:
            raise ValueError("Cache file missing 'imagegroups' field")

        return imagegroups
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid Photo Pairing cache file: {e}")


def flatten_imagegroups_to_specific_images(imagegroups: List[Dict[str, Any]]) -> List[SpecificImage]:
    """
    Flatten ImageGroups to individual SpecificImage objects.

    Each ImageGroup contains multiple separate_images (suffix-based).
    This function converts each separate_image into a SpecificImage object
    for independent validation.

    Args:
        imagegroups: List of ImageGroup dictionaries from Photo Pairing Tool

    Returns:
        List of SpecificImage objects (one per separate_image)

    Example:
        ImageGroup {
            'group_id': 'AB3D0001',
            'separate_images': {
                '': {'files': ['AB3D0001.CR3', 'AB3D0001.XMP']},
                '2': {'files': ['AB3D0001-2.CR3']},
                'HDR': {'files': ['AB3D0001-HDR.DNG']}
            }
        }

        Flattens to 3 SpecificImages:
        - unique_id='AB3D0001', suffix=''
        - unique_id='AB3D0001-2', suffix='2'
        - unique_id='AB3D0001-HDR', suffix='HDR'
    """
    specific_images = []

    for group in imagegroups:
        group_id = group['group_id']
        camera_id = group['camera_id']
        counter = group['counter']
        separate_images = group.get('separate_images', {})

        for suffix, image_data in separate_images.items():
            # Build base_filename
            if suffix:
                base_filename = f"{camera_id}{counter}-{suffix}"
            else:
                base_filename = f"{camera_id}{counter}"

            # Get actual files
            files = sorted(image_data.get('files', []))

            # Extract properties from suffix (if it contains processing methods)
            properties = [suffix] if suffix and not suffix.isdigit() else []

            # Create SpecificImage
            specific_image = SpecificImage(
                base_filename=base_filename,
                camera_id=camera_id,
                counter=counter,
                suffix=suffix,
                properties=properties,
                files=files
            )
            specific_images.append(specific_image)

    return specific_images


def add_metadata_files_to_specific_images(
    specific_images: List[SpecificImage],
    folder_path: Path,
    config: PhotoAdminConfig
) -> None:
    """
    Add metadata files (e.g., .xmp) to SpecificImage actual_files.

    Metadata files are not processed by Photo Pairing Tool (which focuses on
    image files only). This function scans for metadata files separately and
    adds them to matching SpecificImages based on base filename.

    Args:
        specific_images: List of SpecificImage objects to augment
        folder_path: Path to folder containing files
        config: PhotoAdminConfig with metadata_extensions

    Side effects:
        Modifies specific_images in-place by adding metadata files to actual_files
    """
    # Get metadata extensions from config (e.g., ['.xmp'])
    metadata_extensions = [ext.lower() for ext in config.metadata_extensions]

    # Scan folder for metadata files
    metadata_files = {}
    for file_path in folder_path.iterdir():
        if file_path.is_file():
            ext_lower = file_path.suffix.lower()
            if ext_lower in metadata_extensions:
                # Store relative path by base filename (for matching)
                base_name = file_path.stem  # e.g., "AO3A0003" from "AO3A0003.xmp"
                relative_path = str(file_path.relative_to(folder_path))
                if base_name not in metadata_files:
                    metadata_files[base_name] = []
                metadata_files[base_name].append(relative_path)

    # Add metadata files to matching SpecificImages
    for specific_image in specific_images:
        # Match by base_filename
        if specific_image.base_filename in metadata_files:
            for metadata_file in metadata_files[specific_image.base_filename]:
                if metadata_file not in specific_image.files:
                    specific_image.files.append(metadata_file)
            # Re-sort files after adding metadata
            specific_image.files.sort()




# =============================================================================
# Signal Handling - Graceful CTRL+C
# =============================================================================

def setup_signal_handlers():
    """
    Setup graceful CTRL+C (SIGINT) handling.

    Per constitution v1.1.0: Tools MUST handle CTRL+C gracefully with
    user-friendly messages and exit code 130.
    """
    def signal_handler(sig, frame):
        print("\n\n⚠ Operation interrupted by user (CTRL+C)")
        print("Exiting gracefully...")
        sys.exit(130)  # Standard exit code for SIGINT

    signal.signal(signal.SIGINT, signal_handler)




# =============================================================================
# CLI Argument Parsing and Prerequisite Validation
# =============================================================================

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='pipeline_validation',
        description='Photo Processing Pipeline Validation Tool',
        epilog="""
Examples:
  # Validate photo collection against pipeline
  python3 pipeline_validation.py /Users/photographer/Photos/2025-01-15

  # Use custom configuration file
  python3 pipeline_validation.py /path/to/photos --config /path/to/custom-config.yaml

  # Force regeneration (ignore all caches)
  python3 pipeline_validation.py /path/to/photos --force-regenerate

  # Show cache status without running validation
  python3 pipeline_validation.py /path/to/photos --cache-status

Workflow:
  1. Run Photo Pairing Tool first: python3 photo_pairing.py <folder>
  2. Define pipeline in config/config.yaml (processing_pipelines section)
  3. Run pipeline validation: python3 pipeline_validation.py <folder>
  4. Review HTML report: pipeline_validation_report_YYYY-MM-DD_HH-MM-SS.html

For more information, see docs/pipeline-validation.md
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional argument: folder path
    parser.add_argument(
        'folder_path',
        nargs='?',
        type=Path,
        help='Path to folder containing photos to validate'
    )

    # Optional arguments
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to custom configuration file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--force-regenerate',
        action='store_true',
        help='Ignore all cache files and regenerate from scratch'
    )

    parser.add_argument(
        '--cache-status',
        action='store_true',
        help='Show cache status without running validation'
    )

    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Delete cache files and regenerate'
    )

    parser.add_argument(
        '--output-format',
        choices=['html', 'json'],
        default='html',
        help='Output format for validation results (default: html)'
    )

    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate pipeline configuration syntax and structure without analyzing the images in the folder'
    )

    parser.add_argument(
        '--display-graph',
        action='store_true',
        help='Display pipeline graph visualization with sample filenames in HTML report. ' \
             'When used with --validate-config, generates report without requiring a folder argument.'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed information about configuration loading and validation'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {TOOL_VERSION}'
    )

    args = parser.parse_args()

    # Validate arguments
    # folder_path is optional when using --cache-status, --validate-config, or --display-graph with --validate-config
    standalone_modes = args.cache_status or args.validate_config or (args.display_graph and args.validate_config)
    if not standalone_modes and args.folder_path is None:
        parser.error('folder_path is required unless using --cache-status, --validate-config, or --display-graph with --validate-config')

    if args.folder_path and not args.folder_path.exists():
        parser.error(f"Folder does not exist: {args.folder_path}")

    if args.folder_path and not args.folder_path.is_dir():
        parser.error(f"Path is not a directory: {args.folder_path}")

    return args


def validate_prerequisites(args):
    """
    Validate that prerequisites are met before running validation.

    Args:
        args: Parsed command-line arguments

    Returns:
        bool: True if prerequisites met, False otherwise
    """
    # Check if Photo Pairing cache exists
    if args.folder_path:
        cache_file = args.folder_path / '.photo_pairing_imagegroups'
        if not cache_file.exists() and not args.force_regenerate:
            print("⚠ Error: Photo Pairing cache not found")
            print(f"  Expected: {cache_file}")
            print()
            print("Photo Pairing Tool must be run first to generate ImageGroups.")
            print()
            print("Run this command first:")
            print(f"  python3 photo_pairing.py {args.folder_path}")
            print()
            return False

    return True




# =============================================================================
# Cache Management Functions
# =============================================================================

# =============================================================================
# Cache Management Functions
# =============================================================================

def calculate_pipeline_config_hash(config_path: Path) -> str:
    """
    Calculate SHA256 hash of pipeline configuration structure.

    Uses JSON serialization with sorted keys to ensure hash is deterministic
    and insensitive to YAML formatting changes (whitespace, comments).

    Args:
        config_path: Path to config.yaml file

    Returns:
        str: SHA256 hash (64-character hexdigest)
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Extract only the processing_pipelines section for hashing
    # This ensures that changes to other config sections (photo_extensions,
    # camera_mappings, etc.) don't invalidate pipeline validation cache
    pipeline_section = config.get('processing_pipelines', {})

    # Serialize to JSON with sorted keys for deterministic hashing
    config_str = json.dumps(pipeline_section, sort_keys=True, default=str)

    return hashlib.sha256(config_str.encode()).hexdigest()


def get_folder_content_hash(folder_path: Path) -> str:
    """
    Get folder content hash from Photo Pairing cache.

    Reuses the file_list_hash calculated by Photo Pairing Tool to avoid
    redundant folder scanning. This hash changes when files are added,
    removed, or modified in the folder.

    Args:
        folder_path: Path to analyzed folder

    Returns:
        str: SHA256 hash of file list from Photo Pairing cache

    Raises:
        FileNotFoundError: If Photo Pairing cache doesn't exist
        KeyError: If cache is malformed (missing expected fields)
    """
    cache_path = folder_path / '.photo_pairing_imagegroups'

    if not cache_path.exists():
        raise FileNotFoundError(
            f"Photo Pairing cache not found. Run Photo Pairing Tool first.\n"
            f"Expected cache file: {cache_path}"
        )

    with open(cache_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)

    try:
        return cache_data['metadata']['file_list_hash']
    except KeyError as e:
        raise KeyError(
            f"Photo Pairing cache is malformed (missing {e}). "
            "Re-run Photo Pairing Tool to regenerate cache."
        ) from e


def calculate_validation_results_hash(validation_results: list) -> str:
    """
    Calculate SHA256 hash of validation results structure.

    Used to detect manual edits to pipeline validation cache file.
    If user manually modifies validation_results in the JSON cache,
    the hash mismatch will trigger cache invalidation.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        str: SHA256 hash (64-character hexdigest)
    """
    # Serialize to JSON with sorted keys for deterministic hashing
    data_str = json.dumps(validation_results, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()


def save_pipeline_cache(
    folder_path: Path,
    validation_results: list,
    pipeline_config_hash: str,
    folder_content_hash: str
) -> bool:
    """
    Save pipeline validation results to .pipeline_validation_cache.json file.

    Cache structure follows Photo Pairing Tool's pattern with metadata
    including all hashes for invalidation detection.

    Args:
        folder_path: Path to analyzed folder
        validation_results: List of ValidationResult dictionaries
        pipeline_config_hash: Hash of pipeline configuration
        folder_content_hash: Hash of folder file list (from Photo Pairing)

    Returns:
        bool: True if cache was saved successfully, False otherwise
    """
    try:
        cache_path = folder_path / '.pipeline_validation_cache.json'

        # Calculate validation results hash for manual edit detection
        validation_results_hash = calculate_validation_results_hash(validation_results)

        # Calculate statistics
        total_groups = len(validation_results)
        consistent_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'CONSISTENT'
        )
        partial_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'PARTIAL'
        )
        inconsistent_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'INCONSISTENT'
        )
        warning_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'CONSISTENT_WITH_WARNING'
        )

        cache_data = {
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'folder_path': str(folder_path.absolute()),
            'tool_version': TOOL_VERSION,
            'metadata': {
                'pipeline_config_hash': pipeline_config_hash,
                'folder_content_hash': folder_content_hash,
                'validation_results_hash': validation_results_hash,
                'total_groups': total_groups,
                'consistent_groups': consistent_groups,
                'partial_groups': partial_groups,
                'inconsistent_groups': inconsistent_groups,
                'warning_groups': warning_groups
            },
            'validation_results': validation_results
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, default=str)

        return True
    except (IOError, OSError, PermissionError) as e:
        print(f"⚠ Warning: Could not save cache file: {e}")
        print("  Cache will not be available for next run.")
        return False


def load_pipeline_cache(folder_path: Path) -> Optional[dict]:
    """
    Load cached pipeline validation data from .pipeline_validation_cache.json file.

    Performs basic validation (file exists, valid JSON, version compatibility).
    Does NOT validate hashes - use validate_pipeline_cache() for that.

    Args:
        folder_path: Path to folder to check for cache

    Returns:
        dict or None: Cache data if exists and valid, None otherwise
    """
    cache_path = folder_path / '.pipeline_validation_cache.json'

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠ Warning: Could not read cache file: {e}")
        print("  Cache will be ignored and regenerated.")
        return None

    # Auto-invalidate on version mismatch (no user prompt)
    if not is_cache_version_compatible(cache_data):
        cached_version = cache_data.get('tool_version', '0.0.0')
        print(f"ℹ Cache version {cached_version} incompatible with {TOOL_VERSION}")
        print("  Regenerating cache with current version...")
        return None

    return cache_data


def is_cache_version_compatible(cache_data: dict) -> bool:
    """
    Check if cache version is compatible with current tool version.

    Uses semantic versioning: major version mismatch = incompatible.
    Minor/patch version differences are backward compatible.

    Args:
        cache_data: Loaded cache dictionary

    Returns:
        bool: True if compatible, False if invalidation required
    """
    cached_version = cache_data.get('tool_version', '0.0.0')

    try:
        # Semantic versioning: Major version mismatch = incompatible
        cached_major = int(cached_version.split('.')[0])
        current_major = int(TOOL_VERSION.split('.')[0])

        if cached_major != current_major:
            return False  # Major version change = breaking change

        # Minor/patch version differences are compatible
        return True
    except (ValueError, IndexError):
        # Invalid version format - treat as incompatible
        return False


def validate_pipeline_cache(
    cache_data: dict,
    config_path: Path,
    folder_path: Path
) -> dict:
    """
    Validate pipeline validation cache by comparing hashes.

    Checks three invalidation triggers:
    1. Pipeline config changed (pipeline_config_hash mismatch)
    2. Folder content changed (folder_content_hash mismatch)
    3. Cache manually edited (validation_results_hash mismatch)

    Args:
        cache_data: Dictionary loaded from cache file
        config_path: Path to current config.yaml
        folder_path: Path to analyzed folder

    Returns:
        dict: {
            'valid': bool,
            'pipeline_changed': bool,
            'folder_changed': bool,
            'cache_edited': bool
        }
    """
    if not cache_data:
        return {
            'valid': False,
            'pipeline_changed': True,
            'folder_changed': True,
            'cache_edited': False
        }

    try:
        # Check pipeline config hash
        current_pipeline_hash = calculate_pipeline_config_hash(config_path)
        cached_pipeline_hash = cache_data.get('metadata', {}).get('pipeline_config_hash', '')
        pipeline_changed = current_pipeline_hash != cached_pipeline_hash

        # Check folder content hash (from Photo Pairing cache)
        current_folder_hash = get_folder_content_hash(folder_path)
        cached_folder_hash = cache_data.get('metadata', {}).get('folder_content_hash', '')
        folder_changed = current_folder_hash != cached_folder_hash

        # Check validation results hash (detect manual edits)
        cached_validation_hash = cache_data.get('metadata', {}).get('validation_results_hash', '')
        recalculated_hash = calculate_validation_results_hash(
            cache_data.get('validation_results', [])
        )
        cache_edited = cached_validation_hash != recalculated_hash

        valid = not (pipeline_changed or folder_changed or cache_edited)

        return {
            'valid': valid,
            'pipeline_changed': pipeline_changed,
            'folder_changed': folder_changed,
            'cache_edited': cache_edited
        }
    except Exception as e:
        # Cache data is corrupted or malformed
        print(f"⚠ Warning: Cache validation failed: {e}")
        print("  Cache will be ignored and regenerated.")
        return {
            'valid': False,
            'pipeline_changed': True,
            'folder_changed': True,
            'cache_edited': True
        }


def prompt_cache_action(pipeline_changed: bool, folder_changed: bool, cache_edited: bool) -> Optional[str]:
    """
    Prompt user for action when pipeline validation cache is stale.

    Args:
        pipeline_changed: Boolean indicating if pipeline config changed
        folder_changed: Boolean indicating if folder content changed
        cache_edited: Boolean indicating if cache file was manually edited

    Returns:
        str: 'use_cache', 'regenerate', or None if cancelled
    """
    print("\n⚠ Found cached pipeline validation data")
    print("⚠ Changes detected:")
    print(f"  - Pipeline config: {'CHANGED' if pipeline_changed else 'OK'}")
    print(f"  - Folder content: {'CHANGED' if folder_changed else 'OK'}")
    print(f"  - Cache file: {'EDITED' if cache_edited else 'OK'}")
    print("\nChoose an option:")
    print("  (a) Use cached data anyway (fast, may be outdated)")
    print("  (b) Regenerate validation (slow, reflects current state)")

    try:
        choice = input("Your choice [a/b]: ").strip().lower()
        if choice == 'a':
            return 'use_cache'
        elif choice == 'b':
            return 'regenerate'
        else:
            print("Invalid choice. Please enter 'a' or 'b'.")
            return prompt_cache_action(pipeline_changed, folder_changed, cache_edited)
    except (KeyboardInterrupt, EOFError):
        print("\n\nInterrupted by user")
        return None




# =============================================================================
# HTML Report Generation Functions
# =============================================================================

# =============================================================================
# HTML Report Generation Functions
# =============================================================================

def build_graph_visualization_table(pipeline: PipelineConfig, config: PhotoAdminConfig):
    """
    Build graph visualization table for debugging pipeline traversal.

    Generates a sample base filename and shows all paths through the pipeline
    with node IDs, depth, expected files, and truncation status.

    Args:
        pipeline: PipelineConfig object
        config: PhotoAdminConfig object

    Returns:
        ReportSection with table showing path details

    Example table:
        | Path # | Node Path      | Depth | Termination Type | Expected Files    | Truncated |
        |--------|----------------|-------|------------------|-------------------|-----------|
        | 1      | capture        | 3     | Black Box        | AB3D0742.CR3      | No        |
        |        | ->raw_image_1  |       |                  | AB3D0742.XMP      |           |
        |        | ->process      |       |                  | AB3D0742-Edit.DNG |           |
        |        | ->termination  |       |                  |                   |           |
    """
    from utils.report_renderer import ReportSection

    # Generate sample base filename
    sample_base_filename = generate_sample_base_filename(config)

    # Enumerate all paths (pairing-aware)
    all_paths = enumerate_paths_with_pairing(pipeline)

    # Build table rows
    headers = ["Path #", "Node Path", "Depth", "Termination Type", "Expected Files", "Truncated"]
    rows = []

    for path in all_paths:
        # Get termination info
        termination_node = path[-1] if path else None
        if termination_node:
            termination_type = termination_node.get('term_type', 'Unknown')
            truncated = termination_node.get('truncated', False)
            truncated_str = "Yes" if truncated else "No"

            # Build node path string with newlines before arrows
            node_ids = [node.get('id', 'unknown') for node in path]
            if len(node_ids) > 0:
                # First node ID without arrow, then newline before each subsequent arrow
                node_path_parts = [node_ids[0]]
                for node_id in node_ids[1:]:
                    node_path_parts.append(f"\n-> {node_id}")
                node_path_str = "".join(node_path_parts)
            else:
                node_path_str = "(empty path)"

            # Calculate depth (all nodes except first Capture and last Termination)
            # Depth = total nodes - 2 (Capture and Termination)
            # Minimum depth is 0 (just Capture -> Termination)
            depth = max(0, len(path) - 2)

            # Generate expected files for this path with newlines between files
            expected_files = generate_expected_files(path, sample_base_filename)
            if expected_files:
                files_str = "\n".join(expected_files)
            else:
                files_str = "(no files)"

            row = [
                None,  # Path # - will be assigned after sorting
                node_path_str,
                depth,  # Keep as int for sorting
                termination_type,
                files_str,
                truncated_str
            ]
            rows.append(row)

    # Sort rows by depth (index 2) - lower depth first for easier debugging
    rows.sort(key=lambda row: row[2])

    # Assign path numbers after sorting
    for i, row in enumerate(rows, 1):
        row[0] = str(i)
        row[2] = str(row[2])  # Convert depth back to string for display

    # Build section
    section = ReportSection(
        title=f"Pipeline Graph Visualization (Sample: {sample_base_filename})",
        type="table",
        data={
            'headers': headers,
            'rows': rows
        },
        description=f"This table shows all {len(all_paths)} paths enumerated through the pipeline graph using "
                   f"sample base filename '{sample_base_filename}'. Paths are sorted by depth (low to high) for easier debugging. "
                   f"Each path shows the node traversal sequence, depth (nodes excluding Capture/Termination), "
                   f"expected files (deduplicated - only final version of each file shown), and whether the path was truncated "
                   f"due to loop limits. Use this to debug graph traversal and verify expected files."
    )

    return section


def build_kpi_cards(validation_results: list) -> List:
    """
    Build KPI cards for executive summary statistics.

    Shows overall status plus per-termination statistics.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        List of KPICard objects for report context
    """
    from utils.report_renderer import KPICard

    total_groups = len(validation_results)

    # Count by overall status
    consistent = sum(1 for r in validation_results if r.get('status') == 'CONSISTENT')
    partial = sum(1 for r in validation_results if r.get('status') == 'PARTIAL')
    inconsistent = sum(1 for r in validation_results if r.get('status') == 'INCONSISTENT')
    warning = sum(1 for r in validation_results if r.get('status') == 'CONSISTENT_WITH_WARNING')

    # Collect per-termination statistics
    termination_stats = {}
    for result in validation_results:
        for match in result.get('termination_matches', []):
            term_type = match.get('termination_type')
            match_status = match.get('status')

            if term_type not in termination_stats:
                termination_stats[term_type] = {
                    'type': term_type,
                    'consistent': 0,
                    'partial': 0,
                    'inconsistent': 0,
                    'warning': 0
                }

            if match_status == 'CONSISTENT':
                termination_stats[term_type]['consistent'] += 1
            elif match_status == 'PARTIAL':
                termination_stats[term_type]['partial'] += 1
            elif match_status == 'INCONSISTENT':
                termination_stats[term_type]['inconsistent'] += 1
            elif match_status == 'CONSISTENT_WITH_WARNING':
                termination_stats[term_type]['warning'] += 1

    kpis = [
        KPICard(
            title="Total Image Groups",
            value=str(total_groups),
            status="info",
            icon="📊"
        ),
        KPICard(
            title="Overall Consistent",
            value=str(consistent),
            status="success",
            unit=f"{(consistent/total_groups*100):.1f}%" if total_groups > 0 else "0%",
            icon="✓",
            tooltip="Groups consistent with ALL termination methods"
        ),
    ]

    # Add per-termination KPIs (Ready, Partial, With Warnings)
    for term_type, stats in sorted(termination_stats.items()):

        # Ready KPI (CONSISTENT + CONSISTENT-WITH-WARNING)
        term_ready = stats['consistent'] + stats['warning']
        kpis.append(
            KPICard(
                title=f"{term_type} Ready",
                value=str(term_ready),
                status="success" if term_ready == total_groups else "warning",
                unit=f"{(term_ready/total_groups*100):.1f}%" if total_groups > 0 else "0%",
                icon="📦",
                tooltip=f"Groups ready for {term_type} (CONSISTENT or CONSISTENT-WITH-WARNING)"
            )
        )

        # Partial KPI (if any partial groups)
        if stats['partial'] > 0:
            kpis.append(
                KPICard(
                    title=f"{term_type} Partial",
                    value=str(stats['partial']),
                    status="warning",
                    unit=f"{(stats['partial']/total_groups*100):.1f}%" if total_groups > 0 else "0%",
                    icon="⚠",
                    tooltip=f"Groups partially ready for {term_type} (missing some files)"
                )
            )

        # With Warnings KPI (if any warnings)
        if stats['warning'] > 0:
            kpis.append(
                KPICard(
                    title=f"{term_type} With Warnings",
                    value=str(stats['warning']),
                    status="warning",
                    unit=f"{(stats['warning']/total_groups*100):.1f}%" if total_groups > 0 else "0%",
                    icon="⚠",
                    tooltip=f"Groups ready for {term_type} but with extra files"
                )
            )

    return kpis


def build_status_distribution_chart(validation_results: list):
    """
    Build pie chart showing status distribution.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        ReportSection with pie chart data
    """
    from utils.report_renderer import ReportSection

    # Count by status
    status_counts = {
        'CONSISTENT': sum(1 for r in validation_results if r.get('status') == 'CONSISTENT'),
        'PARTIAL': sum(1 for r in validation_results if r.get('status') == 'PARTIAL'),
        'INCONSISTENT': sum(1 for r in validation_results if r.get('status') == 'INCONSISTENT'),
        'CONSISTENT-WITH-WARNING': sum(1 for r in validation_results if r.get('status') == 'CONSISTENT_WITH_WARNING')
    }

    # Filter out zero counts
    filtered_counts = {k: v for k, v in status_counts.items() if v > 0}

    # Chart data with 'values' key (required by base template)
    chart_data = {
        'labels': list(filtered_counts.keys()),
        'values': list(filtered_counts.values()),
        'colors': [
            'rgba(16, 185, 129, 0.8)',   # Green for CONSISTENT
            'rgba(239, 68, 68, 0.8)',    # Red for PARTIAL
            'rgba(220, 38, 38, 0.8)',    # Dark red for INCONSISTENT
            'rgba(245, 158, 11, 0.8)'    # Amber for CONSISTENT-WITH-WARNING
        ][:len(filtered_counts)]
    }

    return ReportSection(
        title="Status Distribution",
        type="chart_pie",
        data=chart_data,
        description="Distribution of validation statuses across all image groups"
    )


def build_chart_sections(validation_results: list) -> List:
    """
    Build chart sections for visualizations.

    Creates overall status distribution chart, then one per termination.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        List of ReportSection objects with chart data
    """
    from utils.report_renderer import ReportSection
    sections = []

    status_colors = {
        'CONSISTENT': 'rgba(75, 192, 192, 0.8)',
        'CONSISTENT-WITH-WARNING': 'rgba(255, 159, 64, 0.8)',
        'PARTIAL': 'rgba(255, 206, 86, 0.8)',
        'INCONSISTENT': 'rgba(255, 99, 132, 0.8)'
    }

    # 1. Overall Status Distribution Chart (worst status across all terminations)
    overall_stats = {}
    for result in validation_results:
        status = result.get('status')
        overall_stats[status] = overall_stats.get(status, 0) + 1

    # Filter out zero values
    filtered_overall = {str(k): int(v) for k, v in overall_stats.items() if v > 0}

    if filtered_overall:
        overall_chart_data = {
            'labels': list(filtered_overall.keys()),
            'values': list(filtered_overall.values()),
            'colors': [status_colors.get(status, 'rgba(128, 128, 128, 0.8)')
                      for status in filtered_overall.keys()]
        }

        sections.append(ReportSection(
            title="Status Distribution - Overall",
            type="chart_pie",
            data=overall_chart_data,
            description="Overall status (worst across all termination methods)"
        ))

    # 2. Per-Termination Status Distribution Charts
    termination_stats = {}
    for result in validation_results:
        for match in result.get('termination_matches', []):
            term_type = match.get('termination_type')
            match_status = match.get('status')

            if term_type not in termination_stats:
                termination_stats[term_type] = {
                    'type': term_type,
                    'CONSISTENT': 0,
                    'PARTIAL': 0,
                    'INCONSISTENT': 0,
                    'CONSISTENT-WITH-WARNING': 0
                }

            if match_status in termination_stats[term_type]:
                termination_stats[term_type][match_status] += 1

    # Create one pie chart per termination
    for term_type, stats in sorted(termination_stats.items()):

        # Filter out zero values and ensure JSON serializable (exclude 'type' key)
        filtered_stats = {str(k): int(v) for k, v in stats.items()
                         if k != 'type' and v > 0}

        if not filtered_stats:
            # Skip if no data for this termination
            continue

        chart_data = {
            'labels': list(filtered_stats.keys()),
            'values': list(filtered_stats.values()),
            'colors': [status_colors.get(status, 'rgba(128, 128, 128, 0.8)')
                      for status in filtered_stats.keys()]
        }

        sections.append(ReportSection(
            title=f"Status Distribution - {term_type}",
            type="chart_pie",
            data=chart_data,
            description=f"Status distribution for {term_type} archival method"
        ))

    return sections


def build_table_sections(validation_results: list) -> List:
    """
    Build table sections for detailed group information.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        List of ReportSection objects with table data
    """
    from utils.report_renderer import ReportSection

    sections = []

    # Group results by status
    by_status = {
        'CONSISTENT': [],
        'CONSISTENT_WITH_WARNING': [],
        'PARTIAL': [],
        'INCONSISTENT': []
    }

    for result in validation_results:
        status = result.get('status', 'INCONSISTENT')
        by_status[status].append(result)

    # Create table for each status with groups
    status_order = ['CONSISTENT', 'CONSISTENT_WITH_WARNING', 'PARTIAL', 'INCONSISTENT']
    status_labels = {
        'CONSISTENT': 'Consistent Groups',
        'CONSISTENT_WITH_WARNING': 'Groups with Warnings',
        'PARTIAL': 'Partial Groups (Missing Files)',
        'INCONSISTENT': 'Inconsistent Groups'
    }

    for status in status_order:
        groups = by_status[status]
        if not groups:
            continue

        # Build table rows (list of lists for base template)
        rows = []
        for group in groups:
            termination_matches = group.get('termination_matches', [])

            # For PARTIAL groups: show each PARTIAL termination match as separate row
            # (Don't show CONSISTENT matches in the PARTIAL table)
            if status == 'PARTIAL':
                # Filter to only PARTIAL matches
                partial_matches = [m for m in termination_matches if m.get('status') == 'PARTIAL']
                matches_to_show = partial_matches if partial_matches else termination_matches[:1]
            else:
                # For other statuses, show first match
                matches_to_show = termination_matches[:1]

            for match in matches_to_show:
                termination_type = match.get('termination_type', 'Unknown')
                expected_files = match.get('expected_files', [])
                actual_files = match.get('actual_files', [])
                missing_files = match.get('missing_files', [])
                extra_files = match.get('extra_files', [])

                group_id = group.get('unique_id', group.get('group_id', 'Unknown'))

                # Build file list with symbols (plain text, no HTML)
                files_list = []
                for f in actual_files:
                    files_list.append(f'✓ {f}')
                for f in missing_files:
                    files_list.append(f'✗ {f}')
                for f in extra_files:
                    files_list.append(f'⚠ {f}')

                # Join with newlines for display
                files_display = '\n'.join(files_list) if files_list else '(no files)'

                row = [
                    group_id,
                    match.get('status', status),  # Show per-match status
                    termination_type,
                    len(expected_files),
                    len(actual_files),
                    len(missing_files),
                    len(extra_files),
                    files_display
                ]
                rows.append(row)

        table_data = {
            'headers': ['Group ID', 'Status', 'Termination', 'Expected', 'Actual', 'Missing', 'Extra', 'Files'],
            'rows': rows
        }

        sections.append(ReportSection(
            title=status_labels[status],
            type="table",
            data=table_data,
            description=f"{len(groups)} group(s) with {status} status",
            collapsible=True
        ))

    return sections


def build_report_context(
    validation_results: list,
    scan_path: str,
    scan_start: datetime,
    scan_end: datetime,
    pipeline: Optional[PipelineConfig] = None,
    config: Optional[PhotoAdminConfig] = None,
    display_graph: bool = False
) -> 'ReportContext':
    """
    Build complete ReportContext from validation results.

    Args:
        validation_results: List of ValidationResult dictionaries
        scan_path: Path to scanned folder
        scan_start: Scan start timestamp
        scan_end: Scan end timestamp
        pipeline: Optional PipelineConfig for graph visualization
        config: Optional PhotoAdminConfig for graph visualization
        display_graph: Whether to include graph visualization section

    Returns:
        ReportContext ready for template rendering
    """
    from utils.report_renderer import ReportContext

    scan_duration = (scan_end - scan_start).total_seconds()

    # Build KPIs
    kpis = build_kpi_cards(validation_results)

    # Build sections
    sections = []

    # Add graph visualization section if requested
    if display_graph and pipeline and config:
        graph_section = build_graph_visualization_table(pipeline, config)
        sections.append(graph_section)

    sections.extend(build_chart_sections(validation_results))
    sections.extend(build_table_sections(validation_results))

    return ReportContext(
        tool_name="Pipeline Validation Tool",
        tool_version=TOOL_VERSION,
        scan_path=scan_path,
        scan_timestamp=scan_start,
        scan_duration=scan_duration,
        kpis=kpis,
        sections=sections,
        warnings=[],
        errors=[]
    )


def generate_html_report(
    validation_results: list,
    output_dir: Path,
    scan_path: str,
    scan_start: datetime,
    scan_end: datetime,
    pipeline: Optional[PipelineConfig] = None,
    config: Optional[PhotoAdminConfig] = None,
    display_graph: bool = False
) -> Path:
    """
    Generate HTML report with timestamped filename.

    Args:
        validation_results: List of ValidationResult dictionaries
        output_dir: Directory where report should be saved
        scan_path: Path to scanned folder
        scan_start: Scan start timestamp
        scan_end: Scan end timestamp
        pipeline: Optional PipelineConfig for graph visualization
        config: Optional PhotoAdminConfig for graph visualization
        display_graph: Whether to include graph visualization section

    Returns:
        Path to generated HTML report
    """
    from utils.report_renderer import ReportRenderer

    # Build report context
    context = build_report_context(
        validation_results=validation_results,
        scan_path=scan_path,
        scan_start=scan_start,
        scan_end=scan_end,
        pipeline=pipeline,
        config=config,
        display_graph=display_graph
    )

    # Generate timestamped filename
    timestamp_str = scan_start.strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"pipeline_validation_report_{timestamp_str}.html"
    report_path = Path(output_dir) / report_filename

    # Render report using ReportRenderer
    renderer = ReportRenderer()
    renderer.render_report(
        context=context,
        template_name="pipeline_validation.html.j2",
        output_path=str(report_path)
    )

    return report_path




# =============================================================================
# Main Function
# =============================================================================

def main():
    """Main entry point for pipeline validation tool."""
    # Setup signal handlers for graceful CTRL+C
    setup_signal_handlers()

    # Parse command-line arguments
    args = parse_arguments()

    print(f"Pipeline Validation Tool v{TOOL_VERSION}")

    # Handle --validate-config mode (config validation only, no photo validation)
    if args.validate_config:
        print("Configuration Validation Mode")
        print("=" * 60)
        print()

        # Load configuration
        if args.verbose:
            print("Loading configuration file...")
        config = PhotoAdminConfig(config_path=args.config)
        print(f"Configuration file: {config.config_path}")
        print()

        # Validate pipeline configuration structure (YAML structure only)
        is_valid, errors = config.validate_pipeline_config_structure(
            pipeline_name='default',
            verbose=args.verbose
        )

        if not is_valid:
            print("\n✗ Configuration validation FAILED\n")
            print("Errors found:")
            for error in errors:
                print(f"  • {error}")
            print()
            return 1

        # If structure is valid, try loading the pipeline (tests node parsing)
        try:
            if args.verbose:
                print("\nLoading and parsing pipeline nodes...")
            pipeline = load_pipeline_config(config, pipeline_name='default', verbose=args.verbose)

            # Validate pipeline logic (graph structure, references, etc.)
            if args.verbose:
                print("\nValidating pipeline logic (node references, graph structure)...")
            validation_errors = validate_pipeline_structure(pipeline, config)

            if validation_errors:
                print("\n✗ Pipeline logic validation FAILED\n")
                print("Errors found:")
                for error in validation_errors:
                    print(f"  • {error}")
                print()
                return 1

            print("\n✓ Configuration validation PASSED\n")
            print(f"  Pipeline: default")
            print(f"  Nodes: {len(pipeline.nodes)}")
            print(f"  Capture nodes: {len([n for n in pipeline.nodes if isinstance(n, CaptureNode)])}")
            print(f"  File nodes: {len([n for n in pipeline.nodes if isinstance(n, FileNode)])}")
            print(f"  Process nodes: {len([n for n in pipeline.nodes if isinstance(n, ProcessNode)])}")
            print(f"  Pairing nodes: {len([n for n in pipeline.nodes if isinstance(n, PairingNode)])}")
            print(f"  Branching nodes: {len([n for n in pipeline.nodes if isinstance(n, BranchingNode)])}")
            print(f"  Termination nodes: {len([n for n in pipeline.nodes if isinstance(n, TerminationNode)])}")
            print()

            # If --display-graph is also specified, generate HTML report with graph visualization
            if args.display_graph:
                print("Generating graph visualization report...")
                scan_start = datetime.now()

                # Enumerate paths to measure performance (will be called again in report generation)
                _ = enumerate_paths_with_pairing(pipeline)

                scan_end = datetime.now()

                # Generate empty validation results (graph visualization only)
                validation_results_dict = []

                try:
                    report_path = generate_html_report(
                        validation_results=validation_results_dict,
                        output_dir=Path.cwd(),
                        scan_path="(config validation mode - no folder scanned)",
                        scan_start=scan_start,
                        scan_end=scan_end,
                        pipeline=pipeline,
                        config=config,
                        display_graph=True
                    )
                    print(f"  ✓ HTML report generated: {report_path}")
                    print()
                except Exception as e:
                    print(f"  ⚠ Warning: HTML report generation failed: {e}")
                    print()

            return 0

        except ValueError as e:
            print(f"\n✗ Configuration validation FAILED\n")
            print(f"Error: {e}")
            print()
            return 1

    # Normal validation mode - validate prerequisites
    if not validate_prerequisites(args):
        sys.exit(1)

    print(f"Analyzing: {args.folder_path}")
    print()

    # Load configuration and data
    print("Loading configuration...")
    config = PhotoAdminConfig(config_path=args.config)

    # Load pipeline configuration using PhotoAdminConfig (per constitution)
    try:
        pipeline = load_pipeline_config(config, pipeline_name='default', verbose=args.verbose)
        print(f"  Loaded {len(pipeline.nodes)} pipeline nodes")
        print(f"  Using pipeline: default")
    except ValueError as e:
        # Error message is generated by PhotoAdminConfig (per constitution)
        print(f"⚠ Error loading pipeline configuration:\n")
        print(e)
        print()
        return 1
    print()

    # Track scan timestamps for report
    scan_start = datetime.now()

    # Load Photo Pairing results
    print("Loading Photo Pairing results...")
    imagegroups = load_or_generate_imagegroups(args.folder_path, force_regenerate=args.force_regenerate)
    print(f"  Loaded {len(imagegroups)} image groups")

    # Flatten ImageGroups to individual SpecificImages for validation
    specific_images = flatten_imagegroups_to_specific_images(imagegroups)
    print(f"  Flattened to {len(specific_images)} specific images")

    # Add metadata files (e.g., .xmp) to SpecificImages
    # Metadata files are not included by Photo Pairing Tool (which focuses on image files)
    add_metadata_files_to_specific_images(specific_images, args.folder_path, config)
    print()

    # Validate images against pipeline
    print("Validating images against pipeline...")
    validation_results = validate_all_images(specific_images, pipeline, show_progress=True)

    scan_end = datetime.now()

    print()
    print(f"  Validated {len(validation_results)} images")
    print()

    # Display summary statistics
    status_counts = {
        ValidationStatus.CONSISTENT: 0,
        ValidationStatus.CONSISTENT_WITH_WARNING: 0,
        ValidationStatus.PARTIAL: 0,
        ValidationStatus.INCONSISTENT: 0
    }

    for result in validation_results:
        # Count the most severe status across all terminations
        worst_status = ValidationStatus.CONSISTENT
        for term_match in result.termination_matches:
            if term_match.status.value > worst_status.value:
                worst_status = term_match.status
        status_counts[worst_status] += 1

    # Calculate per-termination statistics
    termination_stats = {}
    for result in validation_results:
        for term_match in result.termination_matches:
            term_type = term_match.termination_type
            match_status = term_match.status

            if term_type not in termination_stats:
                termination_stats[term_type] = {
                    'type': term_type,
                    'consistent': 0,
                    'warning': 0,
                    'partial': 0,
                    'inconsistent': 0
                }

            if match_status == ValidationStatus.CONSISTENT:
                termination_stats[term_type]['consistent'] += 1
            elif match_status == ValidationStatus.CONSISTENT_WITH_WARNING:
                termination_stats[term_type]['warning'] += 1
            elif match_status == ValidationStatus.PARTIAL:
                termination_stats[term_type]['partial'] += 1
            elif match_status == ValidationStatus.INCONSISTENT:
                termination_stats[term_type]['inconsistent'] += 1

    total_images = len(validation_results)

    print("Validation Summary:")
    print(f"  Overall Status (worst across all terminations):")
    print(f"    ✓ Consistent: {status_counts[ValidationStatus.CONSISTENT]}")
    print(f"    ⚠ Consistent with warnings: {status_counts[ValidationStatus.CONSISTENT_WITH_WARNING]}")
    print(f"    ⚠ Partial: {status_counts[ValidationStatus.PARTIAL]}")
    print(f"    ✗ Inconsistent: {status_counts[ValidationStatus.INCONSISTENT]}")
    print()

    print("  Per-Termination Statistics:")
    for term_type, stats in sorted(termination_stats.items()):
        ready_count = stats['consistent'] + stats['warning']
        ready_pct = (ready_count / total_images * 100) if total_images > 0 else 0
        print(f"    {term_type}: {ready_count}/{total_images} ready ({ready_pct:.1f}%)")
        print(f"      ✓ Consistent: {stats['consistent']}, "
              f"⚠ Warning: {stats['warning']}, "
              f"⚠ Partial: {stats['partial']}, "
              f"✗ Inconsistent: {stats['inconsistent']}")
    print()

    # Generate HTML report
    print("Generating HTML report...")

    # Convert ValidationResult objects to dictionaries for report functions
    validation_results_dict = []
    for result in validation_results:
        # Determine worst status across all terminations
        worst_status = ValidationStatus.CONSISTENT
        for term_match in result.termination_matches:
            if term_match.status.value > worst_status.value:
                worst_status = term_match.status

        # Convert termination matches to dictionaries
        termination_matches_dict = []
        for term_match in result.termination_matches:
            termination_matches_dict.append({
                'termination_type': term_match.termination_type,
                'status': term_match.status.name,
                'expected_files': term_match.expected_files,
                'actual_files': term_match.actual_files,
                'missing_files': term_match.missing_files,
                'extra_files': term_match.extra_files
            })

        # Extract group_id from base_filename (remove any suffix)
        # E.g., "AB3D0001-2" -> "AB3D0001"
        group_id = f"{result.camera_id}{result.counter}"

        validation_results_dict.append({
            'unique_id': result.base_filename,  # Use base_filename as unique_id
            'group_id': group_id,
            'status': worst_status.name,
            'termination_matches': termination_matches_dict
        })

    # Generate HTML report (in current working directory, like other tools)
    try:
        report_path = generate_html_report(
            validation_results=validation_results_dict,
            output_dir=Path.cwd(),
            scan_path=str(args.folder_path),
            scan_start=scan_start,
            scan_end=scan_end,
            pipeline=pipeline,
            config=config,
            display_graph=args.display_graph
        )
        print(f"  ✓ HTML report generated: {report_path}")
        print()
    except Exception as e:
        print(f"  ⚠ Warning: HTML report generation failed: {e}")
        print()

    print("✓ Pipeline validation complete")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
