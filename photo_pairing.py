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
import re
import sys
import yaml
import signal
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from config_manager import PhotoAdminConfig


# Filename validation pattern
# Format: 4 uppercase alphanumeric + 4 digits (0001-9999) + optional properties + extension
# Properties can contain letters, digits, spaces, and underscores
# Extensions are case-insensitive (both .DNG and .dng are valid)
VALID_FILENAME_PATTERN = re.compile(
    r'^[A-Z0-9]{4}(0[0-9]{3}|[1-9][0-9]{3})(-[A-Za-z0-9 _]+)*\.[a-zA-Z0-9]+$'
)


def validate_filename(filename):
    """
    Validate if filename matches the expected pattern.

    Args:
        filename: The filename to validate (without path)

    Returns:
        tuple: (is_valid, error_reason)
            is_valid: Boolean indicating if filename is valid
            error_reason: String with specific error reason if invalid, None if valid
    """
    # Check basic pattern
    if not VALID_FILENAME_PATTERN.match(filename):
        # Determine specific reason
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # Check camera ID (first 4 characters)
        if len(name_without_ext) < 4:
            return False, "Filename too short - camera ID must be 4 characters"

        camera_id = name_without_ext[:4]
        if not re.match(r'^[A-Z0-9]{4}$', camera_id):
            if camera_id.islower() or any(c.islower() for c in camera_id):
                return False, "Camera ID must be uppercase alphanumeric [A-Z0-9]"
            else:
                return False, "Camera ID must be exactly 4 uppercase alphanumeric characters"

        # Check counter (characters 5-8)
        if len(name_without_ext) < 8:
            return False, "Counter must be 4 digits"

        counter = name_without_ext[4:8]
        if not re.match(r'^(0[0-9]{3}|[1-9][0-9]{3})$', counter):
            if counter == '0000':
                return False, "Counter cannot be 0000 - must be 0001-9999"
            elif not counter.isdigit():
                return False, "Counter must be 4 digits"
            else:
                return False, "Counter must be 4 digits between 0001 and 9999"

        # Check for empty properties (double dash or trailing dash)
        if '--' in name_without_ext or name_without_ext.endswith('-'):
            return False, "Empty property name detected"

        # Check for invalid characters in properties
        if len(name_without_ext) > 8:
            properties_part = name_without_ext[8:]
            if not re.match(r'^(-[A-Za-z0-9 _]+)*$', properties_part):
                return False, "Invalid characters in property name"

    return True, None


def parse_filename(filename):
    """
    Parse a valid filename into its components.

    Args:
        filename: The filename to parse (without path)

    Returns:
        dict: {
            'camera_id': str,      # First 4 characters
            'counter': str,        # Characters 5-8
            'properties': list,    # List of dash-prefixed properties (without dashes)
            'extension': str       # File extension (with dot)
        }
        Returns None if filename is invalid
    """
    is_valid, _ = validate_filename(filename)
    if not is_valid:
        return None

    # Split filename and extension
    name_without_ext, extension = filename.rsplit('.', 1)
    extension = '.' + extension

    # Extract camera ID and counter
    camera_id = name_without_ext[:4]
    counter = name_without_ext[4:8]

    # Extract properties (everything after position 8)
    properties = []
    if len(name_without_ext) > 8:
        properties_part = name_without_ext[8:]
        # Split by dash and filter out empty strings
        properties = [p for p in properties_part.split('-') if p]

    return {
        'camera_id': camera_id,
        'counter': counter,
        'properties': properties,
        'extension': extension
    }


def detect_property_type(property_str):
    """
    Detect if a property is a separate image identifier or processing method.

    Args:
        property_str: The property string (without leading dash)

    Returns:
        str: 'separate_image' if all-numeric, 'processing_method' otherwise
    """
    return 'separate_image' if property_str.isdigit() else 'processing_method'


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
    for file_path in folder_path.rglob('*'):
        if file_path.is_file():
            file_ext = file_path.suffix.lower()
            if file_ext in normalized_extensions:
                yield file_path


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
        is_valid, error_reason = validate_filename(filename)

        if not is_valid:
            invalid_files.append({
                'filename': filename,
                'path': str(file_path.relative_to(folder_path)),
                'reason': error_reason
            })
            continue

        # Parse filename
        parsed = parse_filename(filename)
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
            prop_type = detect_property_type(prop)
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


def prompt_camera_info(camera_id):
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


def prompt_processing_method(method_keyword):
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


def update_config_cameras(config_path, camera_updates):
    """
    Update config file with new camera mappings.

    Args:
        config_path: Path to config file
        camera_updates: dict of {camera_id: {'name': str, 'serial_number': str}}
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'camera_mappings' not in config:
        config['camera_mappings'] = {}

    for camera_id, info in camera_updates.items():
        # Store as list for future compatibility
        config['camera_mappings'][camera_id] = [{
            'name': info['name'],
            'serial_number': info['serial_number']
        }]

    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def update_config_methods(config_path, method_updates):
    """
    Update config file with new processing method descriptions.

    Args:
        config_path: Path to config file
        method_updates: dict of {method_keyword: description}
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'processing_methods' not in config:
        config['processing_methods'] = {}

    for keyword, description in method_updates.items():
        config['processing_methods'][keyword] = description

    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


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
        # Get camera info (v1.0: use first entry in list)
        camera_info = camera_mappings.get(camera_id, [{}])[0] if camera_mappings.get(camera_id) else {}

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
    Generate HTML report with analytics and visualizations.

    Args:
        analytics: Dictionary with camera_usage, method_usage, statistics
        invalid_files: List of invalid file dictionaries
        output_path: Path where to save the HTML report
        folder_path: Path object for the analyzed folder
        scan_duration: Time taken to scan in seconds (float)
    """
    stats = analytics['statistics']
    camera_usage = analytics['camera_usage']
    method_usage = analytics['method_usage']

    # Prepare data for charts
    camera_labels = [f"{info['name']} ({cam_id})" for cam_id, info in sorted(camera_usage.items())]
    camera_counts = [info['image_count'] for _, info in sorted(camera_usage.items())]

    method_labels = [f"{info['description']} ({keyword})" for keyword, info in sorted(method_usage.items())]
    method_counts = [info['image_count'] for _, info in sorted(method_usage.items())]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo Pairing Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #007bff;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <h1>Photo Pairing Analysis Report</h1>
    <p><strong>Folder scanned:</strong> {folder_path}</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Scan duration:</strong> {scan_duration:.2f} seconds</p>

    <h2>Summary Statistics</h2>
    <div class="summary">
        <div class="stat-card">
            <div class="stat-value">{stats['total_groups']}</div>
            <div class="stat-label">Total Groups</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['total_images']}</div>
            <div class="stat-label">Total Images</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['total_files_scanned']}</div>
            <div class="stat-label">Total Files</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['avg_files_per_group']:.1f}</div>
            <div class="stat-label">Avg Files/Group</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['cameras_used']}</div>
            <div class="stat-label">Cameras Used</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['processing_methods_used']}</div>
            <div class="stat-label">Processing Methods</div>
        </div>
    </div>

    <h2>Camera Usage</h2>
    <div class="chart-container">
        <canvas id="cameraChart"></canvas>
    </div>

    <table>
        <thead>
            <tr>
                <th>Camera ID</th>
                <th>Camera Name</th>
                <th>Serial Number</th>
                <th>Groups</th>
                <th>Images</th>
            </tr>
        </thead>
        <tbody>
"""

    for cam_id, info in sorted(camera_usage.items()):
        html += f"""            <tr>
                <td>{cam_id}</td>
                <td>{info['name']}</td>
                <td>{info['serial_number'] or 'N/A'}</td>
                <td>{info['group_count']}</td>
                <td>{info['image_count']}</td>
            </tr>
"""

    html += """        </tbody>
    </table>

    <h2>Processing Methods</h2>
"""

    if method_usage:
        html += """    <div class="chart-container">
        <canvas id="methodChart"></canvas>
    </div>

    <table>
        <thead>
            <tr>
                <th>Method</th>
                <th>Description</th>
                <th>Images</th>
            </tr>
        </thead>
        <tbody>
"""

        for keyword, info in sorted(method_usage.items()):
            html += f"""            <tr>
                <td>{keyword}</td>
                <td>{info['description']}</td>
                <td>{info['image_count']}</td>
            </tr>
"""

        html += """        </tbody>
    </table>
"""
    else:
        html += """    <p>No processing methods detected in filenames.</p>
"""

    # Invalid files section
    html += f"""
    <h2>Invalid Files</h2>
"""

    if invalid_files:
        html += f"""    <p><strong>{len(invalid_files)} files</strong> did not match the expected naming pattern:</p>
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Reason</th>
            </tr>
        </thead>
        <tbody>
"""
        for invalid in invalid_files:
            html += f"""            <tr>
                <td>{invalid['filename']}</td>
                <td>{invalid['reason']}</td>
            </tr>
"""
        html += """        </tbody>
    </table>
"""
    else:
        html += """    <p>All files matched the expected naming pattern.</p>
"""

    html += """
    <div class="footer">
        <p>Generated by Photo Pairing Tool - photo-admin toolbox</p>
    </div>

    <script>
"""

    # Camera chart
    html += f"""
        new Chart(document.getElementById('cameraChart'), {{
            type: 'bar',
            data: {{
                labels: {camera_labels},
                datasets: [{{
                    label: 'Images per Camera',
                    data: {camera_counts},
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    title: {{ display: true, text: 'Images by Camera' }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
"""

    # Method chart (if methods exist)
    if method_usage:
        html += f"""
        new Chart(document.getElementById('methodChart'), {{
            type: 'bar',
            data: {{
                labels: {method_labels},
                datasets: [{{
                    label: 'Images per Method',
                    data: {method_counts},
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    title: {{ display: true, text: 'Images by Processing Method' }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
"""

    html += """    </script>
</body>
</html>"""

    with open(output_path, 'w') as f:
        f.write(html)


def main():
    """Main entry point for the photo pairing tool."""
    parser = argparse.ArgumentParser(
        description='Analyze photo filenames and generate analytics reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/photos              Analyze folder and generate report
  %(prog)s ~/Photos/2025-01-Shoot       Analyze specific photo shoot folder

The tool will:
1. Scan the folder for photo files (based on config)
2. Group related files by 8-character prefix
3. Prompt for camera and processing method information (first run)
4. Generate an interactive HTML report with analytics
        """
    )

    parser.add_argument(
        'folder',
        type=str,
        help='Path to folder containing photos to analyze'
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

    # Start timing the scan
    scan_start_time = time.time()

    # Load configuration
    config = PhotoAdminConfig()

    # Scan for photo files
    print("Scanning for photo files...")
    photo_files = list(scan_folder(folder_path, config.photo_extensions))
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

    # Check which cameras and methods need prompts
    existing_cameras = config.camera_mappings
    existing_methods = config.processing_methods

    new_cameras = {}
    new_methods = {}

    # Prompt for new cameras
    for camera_id in sorted(camera_ids):
        if camera_id not in existing_cameras:
            info = prompt_camera_info(camera_id)
            if info is None:
                print("\n\nAnalysis cancelled by user.")
                sys.exit(1)
            new_cameras[camera_id] = info
            print(f"✓ Camera {camera_id} configured")

    # Prompt for new processing methods
    for method in sorted(processing_methods_found):
        if method not in existing_methods:
            description = prompt_processing_method(method)
            if description is None:
                print("\n\nAnalysis cancelled by user.")
                sys.exit(1)
            new_methods[method] = description
            print(f"✓ Method '{method}' configured")

    # Update config file if there are new cameras or methods
    if new_cameras or new_methods:
        # Find config file path (use same logic as PhotoAdminConfig)
        config_paths = [
            Path.cwd() / 'config' / 'config.yaml',
            Path.cwd() / 'config.yaml',
            Path.home() / '.photo_stats_config.yaml',
        ]

        config_path = None
        for path in config_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            print("\nError: Could not find config file to update.")
            sys.exit(1)

        if new_cameras:
            update_config_cameras(config_path, new_cameras)
            print(f"\n✓ Updated {len(new_cameras)} camera mapping(s) in config")

        if new_methods:
            update_config_methods(config_path, new_methods)
            print(f"✓ Updated {len(new_methods)} processing method(s) in config")

        # Reload config
        config = PhotoAdminConfig()

    # Calculate analytics
    print("\nCalculating analytics...")
    analytics = calculate_analytics(
        result['imagegroups'],
        config.camera_mappings,
        config.processing_methods
    )

    # Calculate scan duration
    scan_duration = time.time() - scan_start_time

    # Generate HTML report
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f'photo_pairing_report_{timestamp}.html'
    report_path = Path.cwd() / report_filename

    print("Generating HTML report...")
    generate_html_report(analytics, result['invalid_files'], report_path, folder_path, scan_duration)

    print(f"\n✓ Analysis complete")
    print(f"✓ Report saved to: {report_filename}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
