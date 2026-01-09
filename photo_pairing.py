#!/usr/bin/env python3
"""
Photo Pairing Tool - Analyze photo filenames and generate analytics reports

This tool analyzes photo collections based on filename patterns to:
- Group related files (same photo in different formats)
- Track camera usage
- Identify processing methods applied
- Generate interactive HTML reports with visualizations
- Find non-compliant filenames for cleanup

Copyright (C) 2024 Fabrice Guiot

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import argparse
import os
import sys
import signal
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from utils.config_manager import PhotoAdminConfig
from utils.filename_parser import FilenameParser
from version import __version__


# Tool version from centralized version management
TOOL_VERSION = __version__


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    global shutdown_requested
    shutdown_requested = True
    print("\n\nOperation interrupted by user")
    print("Exiting gracefully without saving cache...")
    sys.exit(130)  # Standard exit code for SIGINT


def scan_folder(folder_path, extensions):
    """
    Scan folder for files with specified extensions (case-insensitive).

    Args:
        folder_path: Path object for the folder to scan
        extensions: Set of file extensions to include (e.g., {'.dng', '.cr3'})

    Yields:
        Path: Full path to each matching file
    """
    # Normalize extensions to lowercase for comparison
    normalized_extensions = {ext.lower() for ext in extensions}

    # Scan all files and check extension case-insensitively
    try:
        for file_path in folder_path.rglob('*'):
            try:
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    if file_ext in normalized_extensions:
                        yield file_path
            except (PermissionError, OSError) as e:
                # Skip files we can't access
                print(f"⚠ Warning: Cannot access {file_path}: {e}")
                continue
    except (PermissionError, OSError) as e:
        # Fatal error accessing the folder itself
        print(f"Error: Cannot scan folder {folder_path}: {e}")
        raise


def build_imagegroups(files, folder_path):
    """
    Build ImageGroup structure from list of file paths.

    Args:
        files: List of Path objects
        folder_path: Base folder Path for calculating relative paths

    Returns:
        dict: {
            'imagegroups': list of ImageGroup dictionaries,
            'invalid_files': list of invalid file dictionaries
        }
    """
    groups = defaultdict(lambda: {
        'group_id': '',
        'camera_id': '',
        'counter': '',
        'separate_images': defaultdict(lambda: {'files': [], 'properties': set()})
    })

    invalid_files = []

    for file_path in files:
        filename = file_path.name

        # Validate filename
        is_valid, error_reason = FilenameParser.validate_filename(filename)

        if not is_valid:
            invalid_files.append({
                'filename': filename,
                'path': str(file_path.relative_to(folder_path)),
                'reason': error_reason
            })
            continue

        # Parse filename
        parsed = FilenameParser.parse_filename(filename)
        group_id = parsed['camera_id'] + parsed['counter']

        # Initialize group if first file
        if not groups[group_id]['group_id']:
            groups[group_id]['group_id'] = group_id
            groups[group_id]['camera_id'] = parsed['camera_id']
            groups[group_id]['counter'] = parsed['counter']

        # Determine which separate image this file belongs to
        separate_image_id = ''  # Default: base image
        processing_methods = []

        for prop in parsed['properties']:
            prop_type = FilenameParser.detect_property_type(prop)
            if prop_type == 'separate_image':
                # First numeric property becomes the separate image ID
                if separate_image_id == '':
                    separate_image_id = prop
                else:
                    # Later numeric properties are treated as processing methods (unusual but valid)
                    processing_methods.append(prop)
            else:
                processing_methods.append(prop)

        # Add file to appropriate separate image
        relative_path = str(file_path.relative_to(folder_path))
        groups[group_id]['separate_images'][separate_image_id]['files'].append(relative_path)

        # Add processing methods (deduplicated via set)
        for method in processing_methods:
            groups[group_id]['separate_images'][separate_image_id]['properties'].add(method)

    # Convert to final structure
    imagegroups = []
    for group_id, group_data in sorted(groups.items()):
        # Convert separate_images defaultdict to regular dict with properties as lists
        separate_images_dict = {}
        for sep_id, sep_data in group_data['separate_images'].items():
            separate_images_dict[sep_id] = {
                'files': sorted(sep_data['files']),
                'properties': sorted(list(sep_data['properties']))
            }

        imagegroups.append({
            'group_id': group_data['group_id'],
            'camera_id': group_data['camera_id'],
            'counter': group_data['counter'],
            'separate_images': separate_images_dict
        })

    return {
        'imagegroups': imagegroups,
        'invalid_files': invalid_files
    }


def calculate_file_list_hash(folder_path, extensions):
    """
    Calculate SHA256 hash of sorted relative file paths.

    Args:
        folder_path: Path object for the folder
        extensions: Set of file extensions to include

    Returns:
        str: SHA256 hash (hexdigest)
    """
    # Normalize extensions to lowercase
    normalized_extensions = {ext.lower() for ext in extensions}

    # Collect all file paths
    files = []
    try:
        for file_path in folder_path.rglob('*'):
            try:
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    if file_ext in normalized_extensions:
                        # Store relative path as string
                        files.append(str(file_path.relative_to(folder_path)))
            except (PermissionError, OSError):
                # Skip files we can't access (consistent with scan_folder)
                continue
    except (PermissionError, OSError) as e:
        print(f"Error: Cannot scan folder for hash calculation: {e}")
        raise

    # Sort for consistency
    files.sort()

    # Create hash from sorted list
    file_list_str = '\n'.join(files)
    return hashlib.sha256(file_list_str.encode()).hexdigest()


def calculate_imagegroups_hash(imagegroups):
    """
    Calculate SHA256 hash of ImageGroup structure.

    Args:
        imagegroups: List of ImageGroup dictionaries

    Returns:
        str: SHA256 hash (hexdigest)
    """
    # Convert to JSON with sorted keys for consistency
    # Use default=str to handle Path objects
    data_str = json.dumps(imagegroups, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()


def save_cache(folder_path, imagegroups, invalid_files, file_list_hash):
    """
    Save ImageGroup structure to .photo_pairing_imagegroups cache file.

    Args:
        folder_path: Path object for the analyzed folder
        imagegroups: List of ImageGroup dictionaries
        invalid_files: List of invalid file dictionaries
        file_list_hash: Pre-calculated hash of file list

    Returns:
        bool: True if cache was saved successfully, False otherwise
    """
    try:
        cache_path = folder_path / '.photo_pairing_imagegroups'

        # Calculate imagegroups hash
        imagegroups_hash = calculate_imagegroups_hash(imagegroups)

        # Calculate statistics
        total_files = sum(
            sum(len(img['files']) for img in group['separate_images'].values())
            for group in imagegroups
        )
        total_images = sum(len(group['separate_images']) for group in imagegroups)

        cache_data = {
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'folder_path': str(folder_path.absolute()),
            'tool_version': TOOL_VERSION,
            'metadata': {
                'file_list_hash': file_list_hash,
                'imagegroups_hash': imagegroups_hash,
                'total_files': total_files,
                'total_groups': len(imagegroups),
                'total_images': total_images,
                'total_invalid_files': len(invalid_files)
            },
            'imagegroups': imagegroups,
            'invalid_files': invalid_files
        }

        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2, default=str)

        return True
    except (IOError, OSError, PermissionError) as e:
        print(f"⚠ Warning: Could not save cache file: {e}")
        print("  Cache will not be available for next run.")
        return False


def load_cache(folder_path):
    """
    Load cached ImageGroup data from .photo_pairing_imagegroups file.

    Args:
        folder_path: Path object for the folder to check

    Returns:
        dict or None: Cache data if exists and valid JSON, None otherwise
    """
    cache_path = folder_path / '.photo_pairing_imagegroups'

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        return cache_data
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠ Warning: Could not read cache file: {e}")
        print("  Cache will be ignored and regenerated.")
        return None


def validate_cache(cache_data, current_file_list_hash):
    """
    Validate cached data by comparing hashes.

    Args:
        cache_data: Dictionary loaded from cache file
        current_file_list_hash: Hash of current folder's file list

    Returns:
        dict: {
            'valid': bool,
            'folder_changed': bool,
            'cache_edited': bool
        }
    """
    if not cache_data:
        return {'valid': False, 'folder_changed': True, 'cache_edited': False}

    try:
        # Check folder content hash
        cached_file_list_hash = cache_data.get('metadata', {}).get('file_list_hash', '')
        folder_changed = cached_file_list_hash != current_file_list_hash

        # Check imagegroups hash (detect manual edits)
        cached_imagegroups_hash = cache_data.get('metadata', {}).get('imagegroups_hash', '')
        recalculated_hash = calculate_imagegroups_hash(cache_data.get('imagegroups', []))
        cache_edited = cached_imagegroups_hash != recalculated_hash

        valid = not folder_changed and not cache_edited

        return {
            'valid': valid,
            'folder_changed': folder_changed,
            'cache_edited': cache_edited
        }
    except Exception as e:
        # Cache data is corrupted or malformed
        print(f"⚠ Warning: Cache validation failed: {e}")
        print("  Cache will be ignored and regenerated.")
        return {'valid': False, 'folder_changed': True, 'cache_edited': True}


def prompt_cache_action(folder_changed, cache_edited):
    """
    Prompt user for action when cache is stale.

    Args:
        folder_changed: Boolean indicating if folder content changed
        cache_edited: Boolean indicating if cache file was manually edited

    Returns:
        str: 'use_cache' or 're_analyze' or None if cancelled
    """
    print("\n⚠ Found cached analysis data")
    print("⚠ Changes detected:")
    print(f"  - Folder content: {'CHANGED' if folder_changed else 'OK'}")
    print(f"  - Cache file: {'EDITED' if cache_edited else 'OK'}")
    print("\nChoose an option:")
    print("  (a) Use cached data anyway (fast, ignores changes)")
    print("  (b) Re-analyze folder (slow, reflects current state)")

    try:
        choice = input("Your choice [a/b]: ").strip().lower()
        if choice == 'a':
            return 'use_cache'
        elif choice == 'b':
            return 're_analyze'
        else:
            print("Invalid choice. Please enter 'a' or 'b'.")
            return prompt_cache_action(folder_changed, cache_edited)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return None




def calculate_analytics(imagegroups, camera_mappings, processing_methods):
    """
    Calculate analytics from ImageGroups.

    Args:
        imagegroups: List of ImageGroup dictionaries
        camera_mappings: Dictionary of camera ID -> list of camera info
        processing_methods: Dictionary of method keyword -> description

    Returns:
        dict: {
            'camera_usage': {...},
            'method_usage': {...},
            'statistics': {...}
        }
    """
    # Camera usage
    camera_usage = defaultdict(lambda: {'name': '', 'serial_number': '', 'image_count': 0, 'group_count': 0})

    for group in imagegroups:
        camera_id = group['camera_id']
        # Get camera info - handle both array and object formats defensively
        # Database may store as: dict, [dict], or [[dict]] depending on source
        raw_camera_info = camera_mappings.get(camera_id)
        camera_info = raw_camera_info
        # Unwrap lists until we get a dict or None
        while isinstance(camera_info, list):
            camera_info = camera_info[0] if camera_info else None
        if not isinstance(camera_info, dict):
            camera_info = {}

        camera_usage[camera_id]['name'] = camera_info.get('name', f'Unknown Camera {camera_id}')
        camera_usage[camera_id]['serial_number'] = camera_info.get('serial_number', '')
        camera_usage[camera_id]['group_count'] += 1
        camera_usage[camera_id]['image_count'] += len(group['separate_images'])

    # Method usage
    method_usage = defaultdict(lambda: {'description': '', 'image_count': 0})

    for group in imagegroups:
        for sep_img_data in group['separate_images'].values():
            for method in sep_img_data['properties']:
                method_usage[method]['description'] = processing_methods.get(method, f'Unknown Method {method}')
                method_usage[method]['image_count'] += 1

    # Statistics
    total_files = sum(
        sum(len(img['files']) for img in group['separate_images'].values())
        for group in imagegroups
    )
    total_groups = len(imagegroups)
    total_images = sum(len(group['separate_images']) for group in imagegroups)

    max_files = max((
        sum(len(img['files']) for img in group['separate_images'].values())
        for group in imagegroups
    ), default=0)

    statistics = {
        'total_files_scanned': total_files,
        'total_groups': total_groups,
        'total_images': total_images,
        'avg_files_per_group': total_files / total_groups if total_groups > 0 else 0,
        'max_files_per_group': max_files,
        'cameras_used': len(camera_usage),
        'processing_methods_used': len(method_usage)
    }

    return {
        'camera_usage': dict(camera_usage),
        'method_usage': dict(method_usage),
        'statistics': statistics
    }


def generate_html_report(analytics, invalid_files, output_path, folder_path, scan_duration):
    """
    Generate HTML report with analytics and visualizations using centralized templates.

    Args:
        analytics: Dictionary with camera_usage, method_usage, statistics
        invalid_files: List of invalid file dictionaries
        output_path: Path where to save the HTML report
        folder_path: Path object for the analyzed folder
        scan_duration: Time taken to scan in seconds (float)
    """
    from utils.report_renderer import (
        ReportRenderer,
        ReportContext,
        KPICard,
        ReportSection,
        WarningMessage
    )

    try:
        stats = analytics['statistics']
        camera_usage = analytics['camera_usage']
        method_usage = analytics['method_usage']

        # Build KPI cards from statistics
        kpis = [
            KPICard(
                title="Total Groups",
                value=str(stats['total_groups']),
                status="success",
                unit="groups",
                tooltip="Number of photo groups detected"
            ),
            KPICard(
                title="Total Images",
                value=str(stats['total_images']),
                status="success",
                unit="images",
                tooltip="Number of primary image files found"
            ),
            KPICard(
                title="Total Files",
                value=str(stats['total_files_scanned']),
                status="info",
                unit="files",
                tooltip="All files scanned including sidecars"
            ),
            KPICard(
                title="Avg Files/Group",
                value=f"{stats['avg_files_per_group']:.1f}",
                status="info",
                unit="files/group"
            ),
            KPICard(
                title="Cameras Used",
                value=str(stats['cameras_used']),
                status="info",
                unit="cameras"
            ),
            KPICard(
                title="Processing Methods",
                value=str(stats['processing_methods_used']),
                status="info",
                unit="methods"
            ),
            KPICard(
                title="Invalid Files",
                value=str(len(invalid_files)),
                status="danger" if invalid_files else "success",
                unit="files",
                tooltip="Files with non-standard filenames"
            )
        ]

        # Build report sections
        sections = []

        # Camera Usage Chart
        if camera_usage:
            camera_labels = [f"{info['name']} ({cam_id})" for cam_id, info in sorted(camera_usage.items())]
            camera_counts = [info['image_count'] for _, info in sorted(camera_usage.items())]

            sections.append(ReportSection(
                title="Camera Usage - Images per Camera",
                type="chart_bar",
                data={
                    "labels": camera_labels,
                    "values": camera_counts
                },
                description="Distribution of images across cameras"
            ))

        # Camera Usage Table
        if camera_usage:
            camera_rows = []
            for cam_id, info in sorted(camera_usage.items()):
                camera_rows.append([
                    cam_id,
                    info['name'],
                    info['serial_number'] or 'N/A',
                    str(info['group_count']),
                    str(info['image_count'])
                ])

            sections.append(ReportSection(
                title="Camera Details",
                type="table",
                data={
                    "headers": ["Camera ID", "Camera Name", "Serial Number", "Groups", "Images"],
                    "rows": camera_rows
                }
            ))

        # Processing Methods Chart
        if method_usage:
            method_labels = [f"{info['description']} ({keyword})" for keyword, info in sorted(method_usage.items())]
            method_counts = [info['image_count'] for _, info in sorted(method_usage.items())]

            sections.append(ReportSection(
                title="Processing Methods - Images per Method",
                type="chart_bar",
                data={
                    "labels": method_labels,
                    "values": method_counts
                },
                description="Distribution of images by processing method"
            ))

        # Processing Methods Table
        if method_usage:
            method_rows = []
            for keyword, info in sorted(method_usage.items()):
                method_rows.append([
                    keyword,
                    info['description'],
                    str(info['image_count'])
                ])

            sections.append(ReportSection(
                title="Processing Method Details",
                type="table",
                data={
                    "headers": ["Method", "Description", "Images"],
                    "rows": method_rows
                }
            ))

        # Invalid Files Table
        if invalid_files:
            invalid_rows = []
            for invalid in invalid_files:
                invalid_rows.append([
                    invalid['filename'],
                    invalid['reason']
                ])

            sections.append(ReportSection(
                title="Invalid Files",
                type="table",
                data={
                    "headers": ["Filename", "Reason"],
                    "rows": invalid_rows
                },
                description=f"{len(invalid_files)} files did not match the expected naming pattern"
            ))

        # Filename Format Requirements (static documentation)
        format_html = """
        <div class="info-box">
            <p>Photo files must follow this naming convention:</p>
            <p style="font-family: monospace; font-size: 1.1em; background: #f5f5f5; padding: 10px; border-left: 4px solid var(--color-primary);">
                <strong>{CAMERA_ID}{COUNTER}[-{PROPERTY}]*{.extension}</strong>
            </p>
            <ul style="line-height: 1.8;">
                <li><strong>CAMERA_ID</strong>: Exactly 4 uppercase alphanumeric characters [A-Z0-9]
                    <br><span style="color: #666; font-size: 0.9em;">Examples: AB3D, XYZW, R5M2</span>
                </li>
                <li><strong>COUNTER</strong>: Exactly 4 digits from 0001 to 9999 (0000 not allowed)
                    <br><span style="color: #666; font-size: 0.9em;">Examples: 0001, 0042, 1234, 9999</span>
                </li>
                <li><strong>PROPERTY</strong> (optional): One or more dash-prefixed properties
                    <br><span style="color: #666; font-size: 0.9em;">• Can contain letters, digits, spaces, and underscores</span>
                    <br><span style="color: #666; font-size: 0.9em;">• Numeric properties indicate separate images (e.g., -2, -3)</span>
                    <br><span style="color: #666; font-size: 0.9em;">• Alphanumeric properties indicate processing methods (e.g., -HDR, -BW)</span>
                    <br><span style="color: #666; font-size: 0.9em;">Examples: -HDR, -2, -HDR_BW, -Focus Stack</span>
                </li>
                <li><strong>Extension</strong>: Case-insensitive file extension
                    <br><span style="color: #666; font-size: 0.9em;">Examples: .dng, .DNG, .cr3, .CR3, .tiff</span>
                </li>
            </ul>
            <p><strong>Valid filename examples:</strong></p>
            <ul style="font-family: monospace; color: #28a745;">
                <li>AB3D0001.dng</li>
                <li>XYZW0035-HDR.tiff</li>
                <li>AB3D0042-2.cr3</li>
                <li>R5M21234-HDR-BW.dng</li>
                <li>AB3D0001-Focus Stack.tiff</li>
            </ul>
        </div>
        """

        sections.append(ReportSection(
            title="Filename Format Requirements",
            type="html",
            html_content=format_html,
            description="Naming convention rules for photo files"
        ))

        # Build warnings if invalid files exist
        warnings = []
        if invalid_files:
            warnings.append(WarningMessage(
                message=f"Found {len(invalid_files)} files with invalid filenames",
                details=[f"{inv['filename']}: {inv['reason']}" for inv in invalid_files[:5]],
                severity="high" if len(invalid_files) > 10 else "medium"
            ))

        # Create report context
        context = ReportContext(
            tool_name="Photo Pairing",
            tool_version=TOOL_VERSION,
            scan_path=str(folder_path),
            scan_timestamp=datetime.now(),
            scan_duration=scan_duration,
            kpis=kpis,
            sections=sections,
            warnings=warnings
        )

        # Render report using centralized template
        renderer = ReportRenderer()
        renderer.render_report(
            context=context,
            template_name="photo_pairing.html.j2",
            output_path=output_path
        )

        return output_path

    except Exception as e:
        print(f"\nERROR: Failed to generate HTML report: {e}")
        print("Analysis results are available in console output above.")
        return None


def main():
    """Main entry point for the photo pairing tool."""
    # Register signal handler for graceful Ctrl+C handling
    signal.signal(signal.SIGINT, signal_handler)

    # Determine current configuration mode for help text
    db_url = os.environ.get('PHOTO_ADMIN_DB_URL')
    if db_url:
        current_mode = "  ** CURRENT: Database mode (PHOTO_ADMIN_DB_URL is set) **"
    else:
        current_mode = "  ** CURRENT: File mode (PHOTO_ADMIN_DB_URL is not set) **"

    parser = argparse.ArgumentParser(
        description="""Photo Pairing - Analyze photo filename patterns and group related files.

Validates filenames against naming conventions, tracks camera usage, identifies
processing methods, and generates interactive HTML reports with comprehensive analytics.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s /path/to/photos
      Analyze folder and generate timestamped HTML report

  %(prog)s ~/Photos/2025-01-Shoot
      Analyze specific photo shoot folder

  %(prog)s /mnt/external/RAW_Files
      Analyze photos on external drive

How It Works:
  1. Scan folder for photo files (based on config)
  2. Validate filenames against naming convention
  3. Group related files by 8-character prefix (camera ID + counter)
  4. Prompt for camera and processing method info (first run)
  5. Cache results for faster subsequent runs
  6. Generate interactive HTML report with analytics

Configuration:
{current_mode}

  Database Mode (when web UI is available):
    Set PHOTO_ADMIN_DB_URL environment variable to use shared database config.
    This enables configuration changes made in the web UI to be used by CLI tools.
    New camera/method prompts will be saved to the database for web UI access.
    Example: export PHOTO_ADMIN_DB_URL=postgresql://user:pass@host/db

  File Mode (standalone usage):
    If PHOTO_ADMIN_DB_URL is not set, the tool searches for config files:
      1. config/config.yaml (current directory)
      2. config.yaml (current directory)
      3. ~/.photo_stats_config.yaml (home directory)
      4. config/config.yaml (script directory)

    To create a configuration file:
      cp config/template-config.yaml config/config.yaml

    The tool will prompt interactively to create missing config on first run.

Report Output:
  Default filename: photo_pairing_report_YYYY-MM-DD_HH-MM-SS.html
  Reports include: filename validation, camera usage, processing methods, charts
"""
    )

    parser.add_argument(
        'folder',
        type=str,
        help='Path to folder containing photos to analyze'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {TOOL_VERSION}'
    )

    args = parser.parse_args()

    # Validate folder path
    folder_path = Path(args.folder).resolve()
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        sys.exit(1)

    if not folder_path.is_dir():
        print(f"Error: Not a directory: {folder_path}")
        sys.exit(1)

    print(f"Analyzing folder: {folder_path}")

    # Start timing the scan (excluding user input time)
    scan_start_time = time.time()
    total_pause_time = 0.0  # Track time spent waiting for user input

    # Load configuration
    config = PhotoAdminConfig()
    print(f"Configuration: {config.config_source_description}")

    # Check for cached data
    print("Checking for cached analysis...")
    cache_data = load_cache(folder_path)

    # Calculate current file list hash
    try:
        current_file_list_hash = calculate_file_list_hash(folder_path, config.photo_extensions)
    except (PermissionError, OSError) as e:
        print(f"\nError: Cannot access folder contents: {e}")
        print("Please check folder permissions and try again.")
        sys.exit(1)

    # Validate cache if it exists
    use_cached_data = False
    if cache_data:
        validation = validate_cache(cache_data, current_file_list_hash)

        if validation['valid']:
            print("✓ Found valid cache - using cached data")
            use_cached_data = True
        else:
            # Cache is stale - prompt user (pause timer during user input)
            pause_start = time.time()
            action = prompt_cache_action(validation['folder_changed'], validation['cache_edited'])
            total_pause_time += time.time() - pause_start

            if action is None:
                print("\n\nAnalysis cancelled by user.")
                sys.exit(1)
            elif action == 'use_cache':
                print("Using cached data (ignoring changes)")
                use_cached_data = True
            # else: action == 're_analyze', proceed with full analysis

    # Use cached data or perform full analysis
    if use_cached_data:
        result = {
            'imagegroups': cache_data.get('imagegroups', []),
            'invalid_files': cache_data.get('invalid_files', [])
        }
        print(f"Loaded from cache:")
        print(f"  Total groups: {len(result['imagegroups'])}")
        print(f"  Invalid files: {len(result['invalid_files'])}")
    else:
        # Scan for photo files
        print("Scanning for photo files...")
        try:
            photo_files = list(scan_folder(folder_path, config.photo_extensions))
        except (PermissionError, OSError) as e:
            print(f"\nError: Cannot scan folder: {e}")
            print("Please check folder permissions and try again.")
            sys.exit(1)

        print(f"Found {len(photo_files)} photo files")

        if len(photo_files) == 0:
            print("\nNo photo files found matching configured extensions.")
            print(f"Configured extensions: {', '.join(sorted(config.photo_extensions))}")
            sys.exit(0)

        # Build ImageGroups
        print("Analyzing filenames and grouping...")
        result = build_imagegroups(photo_files, folder_path)

        print(f"\nAnalysis complete:")
        print(f"  Total groups: {len(result['imagegroups'])}")
        print(f"  Invalid files: {len(result['invalid_files'])}")

    if len(result['imagegroups']) == 0:
        print("\nNo valid image groups found.")
        if len(result['invalid_files']) > 0:
            print("All files were invalid. Check the invalid files list in the report.")
        sys.exit(0)

    # Collect all unique camera IDs and processing methods
    camera_ids = set()
    processing_methods_found = set()

    for group in result['imagegroups']:
        camera_ids.add(group['camera_id'])
        for sep_img_data in group['separate_images'].values():
            processing_methods_found.update(sep_img_data['properties'])

    # Ensure all cameras and methods have mappings (prompt user if needed)
    # Pause timer during all user input
    for camera_id in sorted(camera_ids):
        if camera_id not in config.camera_mappings:
            pause_start = time.time()
            info = config.ensure_camera_mapping(camera_id)
            total_pause_time += time.time() - pause_start

            if info is None:
                print("\n\nAnalysis cancelled by user.")
                sys.exit(1)
            print(f"✓ Camera {camera_id} configured")

    for method in sorted(processing_methods_found):
        if method not in config.processing_methods:
            pause_start = time.time()
            description = config.ensure_processing_method(method)
            total_pause_time += time.time() - pause_start

            if description is None:
                print("\n\nAnalysis cancelled by user.")
                sys.exit(1)
            print(f"✓ Method '{method}' configured")

    # Reload config to ensure we have the latest mappings
    config.reload()

    # Calculate analytics
    print("\nCalculating analytics...")
    analytics = calculate_analytics(
        result['imagegroups'],
        config.camera_mappings,
        config.processing_methods
    )

    # Calculate scan duration (excluding user input time)
    scan_duration = time.time() - scan_start_time - total_pause_time

    # Check for shutdown request before generating report
    if shutdown_requested:
        print("\nReport generation skipped due to interruption")
        sys.exit(130)

    # Generate HTML report
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f'photo_pairing_report_{timestamp}.html'
    report_path = Path.cwd() / report_filename

    print("Generating HTML report...")
    generate_html_report(analytics, result['invalid_files'], report_path, folder_path, scan_duration)

    # Save cache if we performed full analysis (not when using cached data)
    if not use_cached_data:
        print("Saving analysis cache...")
        if save_cache(folder_path, result['imagegroups'], result['invalid_files'], current_file_list_hash):
            print("✓ Cache saved to: .photo_pairing_imagegroups")

    print(f"\n✓ Analysis complete")
    print(f"✓ Report saved to: {report_filename}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
