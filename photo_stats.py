#!/usr/bin/env python3
"""
Photo Administration Statistics Tool
Scans folders containing DNG, TIFF, CR3, and XMP files and generates statistics.

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

import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import xml.etree.ElementTree as ET
import json
import argparse
import signal

from utils.config_manager import PhotoAdminConfig
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
    print("Exiting gracefully...")
    sys.exit(130)  # Standard exit code for SIGINT


class PhotoStats:
    """Collects and analyzes statistics for photo files."""

    def __init__(self, folder_path, config_path=None):
        self.folder_path = Path(folder_path)
        self.config_manager = PhotoAdminConfig(config_path)
        self.config = self.config_manager.raw_config
        self.PHOTO_EXTENSIONS = self.config_manager.photo_extensions
        self.METADATA_EXTENSIONS = self.config_manager.metadata_extensions
        self.REQUIRE_SIDECAR = self.config_manager.require_sidecar

        self.stats = {
            'file_counts': defaultdict(int),
            'file_sizes': defaultdict(list),
            'total_size': 0,
            'total_files': 0,
            'paired_files': [],
            'orphaned_images': [],
            'orphaned_xmp': [],
            'xmp_metadata': [],
            'scan_time': None,
            'folder_path': str(self.folder_path.resolve()),
            'config': {
                'photo_extensions': list(self.PHOTO_EXTENSIONS),
                'metadata_extensions': list(self.METADATA_EXTENSIONS),
                'require_sidecar': list(self.REQUIRE_SIDECAR)
            }
        }

    def scan_folder(self):
        """Scan the folder and collect file statistics."""
        print(f"Scanning folder: {self.folder_path}")

        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {self.folder_path}")

        start_time = datetime.now()

        # Collect all files
        all_files = {}
        for file_path in self.folder_path.rglob('*'):
            # Check for shutdown request
            if shutdown_requested:
                print("\nScan interrupted by user")
                sys.exit(130)

            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.PHOTO_EXTENSIONS or ext in self.METADATA_EXTENSIONS:
                    all_files[file_path] = ext

                    # Count files by type
                    self.stats['file_counts'][ext] += 1
                    self.stats['total_files'] += 1

                    # Track file sizes
                    file_size = file_path.stat().st_size
                    self.stats['file_sizes'][ext].append(file_size)
                    self.stats['total_size'] += file_size

        print(f"Found {self.stats['total_files']} files")

        # Check for shutdown request before further processing
        if shutdown_requested:
            print("\nScan interrupted by user")
            sys.exit(130)

        # Analyze file pairing
        self._analyze_pairing(all_files)

        # Extract XMP metadata
        self._extract_xmp_metadata(all_files)

        self.stats['scan_time'] = (datetime.now() - start_time).total_seconds()
        print(f"Scan completed in {self.stats['scan_time']:.2f} seconds")

        return self.stats

    def _analyze_pairing(self, all_files):
        """Analyze which image files have corresponding XMP files."""
        print("Analyzing file pairing...")

        # Group files by base name (without extension)
        file_groups = defaultdict(list)
        for file_path, ext in all_files.items():
            base_name = file_path.stem
            file_groups[base_name].append((file_path, ext))

        # Check pairing status
        for base_name, files in file_groups.items():
            has_image = any(ext in self.PHOTO_EXTENSIONS for _, ext in files)
            has_xmp = any(ext in self.METADATA_EXTENSIONS for _, ext in files)
            # Check if any image in this group requires a sidecar
            has_image_requiring_sidecar = any(
                ext in self.REQUIRE_SIDECAR for _, ext in files if ext in self.PHOTO_EXTENSIONS
            )

            if has_image and has_xmp:
                self.stats['paired_files'].append({
                    'base_name': base_name,
                    'files': [str(f[0]) for f in files]
                })
            elif has_image and not has_xmp and has_image_requiring_sidecar:
                # Only flag as orphaned if the image type requires a sidecar
                image_files = [str(f[0]) for f in files if f[1] in self.REQUIRE_SIDECAR]
                self.stats['orphaned_images'].extend(image_files)
            elif has_xmp and not has_image:
                xmp_files = [str(f[0]) for f in files if f[1] in self.METADATA_EXTENSIONS]
                self.stats['orphaned_xmp'].extend(xmp_files)

    def _extract_xmp_metadata(self, all_files):
        """Extract metadata from XMP files."""
        print("Extracting XMP metadata...")

        xmp_files = [f for f, ext in all_files.items() if ext in self.METADATA_EXTENSIONS]

        for xmp_file in xmp_files:
            try:
                metadata = self._parse_xmp_file(xmp_file)
                if metadata:
                    metadata['file'] = str(xmp_file)
                    self.stats['xmp_metadata'].append(metadata)
            except Exception as e:
                print(f"Warning: Could not parse {xmp_file.name}: {e}")

    def _parse_xmp_file(self, xmp_path):
        """Parse an XMP file and extract useful metadata."""
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()

            metadata = {}

            # Define common XMP namespaces
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'xmp': 'http://ns.adobe.com/xap/1.0/',
                'tiff': 'http://ns.adobe.com/tiff/1.0/',
                'exif': 'http://ns.adobe.com/exif/1.0/',
                'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
            }

            # Extract various metadata fields
            for prefix, uri in namespaces.items():
                for elem in root.iter(f'{{{uri}}}*'):
                    tag_name = elem.tag.split('}')[-1]
                    if elem.text and elem.text.strip():
                        metadata[f'{prefix}:{tag_name}'] = elem.text.strip()
                    elif elem.attrib:
                        for attr, value in elem.attrib.items():
                            attr_name = attr.split('}')[-1]
                            if attr_name != 'about':
                                metadata[f'{prefix}:{tag_name}@{attr_name}'] = value

            return metadata if metadata else None

        except ET.ParseError:
            return None

    def generate_html_report(self, output_path=None):
        """Generate an HTML report with statistics and charts using Jinja2 templates."""
        # Generate timestamped filename if no output path specified
        if output_path is None:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            output_path = f'photo_stats_report_{timestamp}.html'

        print(f"Generating HTML report: {output_path}")

        # Import template renderer
        from utils.report_renderer import (
            ReportRenderer, ReportContext, KPICard, ReportSection, WarningMessage
        )

        try:
            # Build KPI cards
            kpis = [
                KPICard(
                    title="Total Images",
                    value=str(self._get_total_image_count()),
                    status="success",
                    unit="files"
                ),
                KPICard(
                    title="Total Size",
                    value=self._format_size(self.stats['total_size']),
                    status="info"
                ),
                KPICard(
                    title="Orphaned Images",
                    value=str(len(self.stats['orphaned_images'])),
                    status="warning" if self.stats['orphaned_images'] else "success",
                    unit="files"
                ),
                KPICard(
                    title="Orphaned Sidecars",
                    value=str(len(self.stats['orphaned_xmp'])),
                    status="warning" if self.stats['orphaned_xmp'] else "success",
                    unit="files"
                )
            ]

            # Build chart sections
            image_type_labels, image_type_counts = self._get_image_type_distribution()
            storage_labels, storage_sizes = self._get_storage_distribution()

            sections = [
                ReportSection(
                    title="📊 Image Type Distribution",
                    type="chart_pie",
                    data={
                        "labels": image_type_labels,
                        "values": image_type_counts
                    },
                    description="Number of images by file type"
                ),
                ReportSection(
                    title="💾 Storage Distribution",
                    type="chart_bar",
                    data={
                        "labels": storage_labels,
                        "values": [round(size / 1024 / 1024, 2) for size in storage_sizes]
                    },
                    description="Storage usage by image type (including paired sidecars) in MB"
                )
            ]

            # Add file pairing status table if there are orphaned files
            orphaned_count = len(self.stats['orphaned_images']) + len(self.stats['orphaned_xmp'])
            if orphaned_count > 0:
                # Create table rows for orphaned files
                rows = []
                for file_path in self.stats['orphaned_images'][:100]:
                    rows.append([Path(file_path).name, "Missing XMP sidecar"])
                for file_path in self.stats['orphaned_xmp'][:100]:
                    rows.append([Path(file_path).name, "Missing image file"])

                sections.append(
                    ReportSection(
                        title="🔗 File Pairing Status",
                        type="table",
                        data={
                            "headers": ["File", "Issue"],
                            "rows": rows
                        },
                        description=f"Found {orphaned_count} orphaned files"
                    )
                )
            else:
                # Add success message as HTML section
                sections.append(
                    ReportSection(
                        title="🔗 File Pairing Status",
                        type="html",
                        html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>✓ All image files have corresponding XMP metadata files!</strong></div>'
                    )
                )

            # Build warnings list
            warnings = []
            if orphaned_count > 0:
                orphaned_details = []
                if self.stats['orphaned_images']:
                    orphaned_details.append(f"{len(self.stats['orphaned_images'])} images without XMP files")
                if self.stats['orphaned_xmp']:
                    orphaned_details.append(f"{len(self.stats['orphaned_xmp'])} XMP files without images")

                warnings.append(
                    WarningMessage(
                        message=f"Found {orphaned_count} orphaned files",
                        details=orphaned_details,
                        severity="medium"
                    )
                )

            # Create report context
            context = ReportContext(
                tool_name="PhotoStats",
                tool_version=TOOL_VERSION,
                scan_path=str(self.stats['folder_path']),
                scan_timestamp=datetime.now(),
                scan_duration=self.stats['scan_time'],
                kpis=kpis,
                sections=sections,
                warnings=warnings
            )

            # Render report using template
            renderer = ReportRenderer()
            renderer.render_report(
                context=context,
                template_name="photo_stats.html.j2",
                output_path=output_path
            )

            print(f"Report generated: {Path(output_path).resolve()}")
            return Path(output_path)

        except Exception as e:
            print(f"ERROR: Failed to generate HTML report: {e}")
            print("Analysis results are available in console output above.")
            print("Please ensure Jinja2 is installed: pip install Jinja2>=3.1.0")
            return None

    def _format_size(self, size_bytes):
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _get_total_image_count(self):
        """Get total count of image files (excluding sidecars)."""
        return sum(count for ext, count in self.stats['file_counts'].items()
                   if ext in self.PHOTO_EXTENSIONS)

    def _get_image_type_distribution(self):
        """Get image type distribution for chart (images only + orphaned sidecars)."""
        # Get image extensions in config order
        ordered_exts = [ext for ext in self.config.get('photo_extensions', [])
                       if ext in self.stats['file_counts']]

        labels = [ext.upper() for ext in ordered_exts]
        counts = [self.stats['file_counts'][ext] for ext in ordered_exts]

        # Add orphaned sidecars as last series
        if self.stats['orphaned_xmp']:
            labels.append('ORPHANED SIDECARS')
            counts.append(len(self.stats['orphaned_xmp']))

        return labels, counts

    def _get_storage_distribution(self):
        """Get storage distribution combining image + paired sidecar sizes."""
        # Group files by base name to find pairs
        file_groups = defaultdict(lambda: {'image_ext': None, 'image_size': 0, 'sidecar_size': 0})

        for file_path in Path(self.stats['folder_path']).rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.PHOTO_EXTENSIONS or ext in self.METADATA_EXTENSIONS:
                    base_name = file_path.stem
                    file_size = file_path.stat().st_size

                    if ext in self.PHOTO_EXTENSIONS:
                        file_groups[base_name]['image_ext'] = ext
                        file_groups[base_name]['image_size'] = file_size
                    elif ext in self.METADATA_EXTENSIONS:
                        file_groups[base_name]['sidecar_size'] = file_size

        # Calculate combined sizes per image type
        storage_by_type = defaultdict(int)
        orphaned_sidecar_size = 0

        for base_name, group in file_groups.items():
            if group['image_ext']:
                # Image exists - add image size + paired sidecar size
                combined_size = group['image_size'] + group['sidecar_size']
                storage_by_type[group['image_ext']] += combined_size
            elif group['sidecar_size'] > 0:
                # Orphaned sidecar (no image)
                orphaned_sidecar_size += group['sidecar_size']

        # Get extensions in config order
        ordered_exts = [ext for ext in self.config.get('photo_extensions', [])
                       if ext in storage_by_type]

        labels = [ext.upper() for ext in ordered_exts]
        sizes = [storage_by_type[ext] for ext in ordered_exts]

        # Add orphaned sidecars as last series
        if orphaned_sidecar_size > 0:
            labels.append('ORPHANED SIDECARS')
            sizes.append(orphaned_sidecar_size)

        return labels, sizes

    def _generate_pairing_section(self):
        """Generate HTML section for file pairing status."""
        orphaned_count = len(self.stats['orphaned_images']) + len(self.stats['orphaned_xmp'])

        section = '<h2>🔗 File Pairing Status</h2>'

        if orphaned_count == 0:
            section += '<div class="success">✓ All image files have corresponding XMP metadata files!</div>'
        else:
            section += f'<div class="warning">⚠ Found {orphaned_count} orphaned files</div>'

        if self.stats['orphaned_images']:
            section += f'''
            <h3>Images without XMP files ({len(self.stats['orphaned_images'])})</h3>
            <div class="file-list">
                {''.join(f'<div>{Path(f).name}</div>' for f in self.stats['orphaned_images'][:100])}
                {f'<div><em>... and {len(self.stats["orphaned_images"]) - 100} more</em></div>' if len(self.stats['orphaned_images']) > 100 else ''}
            </div>
            '''

        if self.stats['orphaned_xmp']:
            section += f'''
            <h3>XMP files without images ({len(self.stats['orphaned_xmp'])})</h3>
            <div class="file-list">
                {''.join(f'<div>{Path(f).name}</div>' for f in self.stats['orphaned_xmp'][:100])}
                {f'<div><em>... and {len(self.stats["orphaned_xmp"]) - 100} more</em></div>' if len(self.stats['orphaned_xmp']) > 100 else ''}
            </div>
            '''

        return section


def main():
    """Main entry point for the photo statistics tool."""
    # Register signal handler for graceful Ctrl+C handling
    signal.signal(signal.SIGINT, signal_handler)

    # Determine current configuration mode for help text
    db_url = os.environ.get('PHOTO_ADMIN_DB_URL')
    if db_url:
        current_mode = "  ** CURRENT: Database mode (PHOTO_ADMIN_DB_URL is set) **"
    else:
        current_mode = "  ** CURRENT: File mode (PHOTO_ADMIN_DB_URL is not set) **"

    parser = argparse.ArgumentParser(
        description="""PhotoStats - Analyze photo collections for orphaned files and sidecar issues.

Scans folders containing DNG, TIFF, CR3, and XMP files, analyzes file pairing,
and generates comprehensive HTML reports with statistics and visualizations.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s /path/to/photos
      Analyze folder and generate timestamped HTML report

  %(prog)s ~/Photos/2025-01-Shoot custom_report.html
      Analyze folder and save report with custom filename

  %(prog)s /path/to/photos report.html config/my_config.yaml
      Analyze using custom configuration file

Configuration:
{current_mode}

  Database Mode (when web UI is available):
    Set PHOTO_ADMIN_DB_URL environment variable to use shared database config.
    This enables configuration changes made in the web UI to be used by CLI tools.
    Example: export PHOTO_ADMIN_DB_URL=postgresql://user:pass@host/db

  File Mode (standalone usage):
    If PHOTO_ADMIN_DB_URL is not set, the tool searches for config files:
      1. config/config.yaml (current directory)
      2. config.yaml (current directory)
      3. ~/.photo_stats_config.yaml (home directory)
      4. config/config.yaml (script directory)

    To create a configuration file:
      cp config/template-config.yaml config/config.yaml

Report Output:
  Default filename: photo_stats_report_YYYY-MM-DD_HH-MM-SS.html
  Reports include: file statistics, pairing analysis, XMP metadata, charts
"""
    )

    parser.add_argument(
        'folder',
        type=str,
        help='Path to folder containing photos to analyze'
    )

    parser.add_argument(
        'output',
        nargs='?',
        type=str,
        default=None,
        help='Output HTML report filename (default: auto-generated with timestamp)'
    )

    parser.add_argument(
        'config',
        nargs='?',
        type=str,
        default=None,
        help='Path to configuration file (default: auto-discovered)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {TOOL_VERSION}'
    )

    args = parser.parse_args()

    folder_path = args.folder

    # Generate timestamped filename if not specified
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_path = f'photo_stats_report_{timestamp}.html'

    config_path = args.config

    try:
        stats_tool = PhotoStats(folder_path, config_path)
        print(f"Configuration: {stats_tool.config_manager.config_source_description}")
        stats_tool.scan_folder()

        # Check for shutdown request before generating report
        if shutdown_requested:
            print("\nReport generation skipped due to interruption")
            sys.exit(130)

        report_file = stats_tool.generate_html_report(output_path)

        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Total files: {stats_tool.stats['total_files']}")
        print(f"Total size: {stats_tool._format_size(stats_tool.stats['total_size'])}")
        print(f"Paired files: {len(stats_tool.stats['paired_files'])}")
        print(f"Orphaned images: {len(stats_tool.stats['orphaned_images'])}")
        print(f"Orphaned XMP: {len(stats_tool.stats['orphaned_xmp'])}")
        print("\nFile counts:")
        for ext, count in sorted(stats_tool.stats['file_counts'].items()):
            print(f"  {ext.upper()}: {count}")
        print("\n" + "="*50)
        print(f"\n✓ HTML report saved to: {report_file.resolve()}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
