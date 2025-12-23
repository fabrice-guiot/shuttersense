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
import yaml


class PhotoStats:
    """Collects and analyzes statistics for photo files."""

    def __init__(self, folder_path, config_path=None):
        self.folder_path = Path(folder_path)
        self.config = self._load_config(config_path)
        self.PHOTO_EXTENSIONS = set(self.config.get('photo_extensions', []))
        self.METADATA_EXTENSIONS = set(self.config.get('metadata_extensions', []))
        self.REQUIRE_SIDECAR = set(self.config.get('require_sidecar', []))

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

    def _load_config(self, config_path=None):
        """Load configuration from YAML file."""
        if config_path is None:
            # Try to find config file in standard locations
            possible_paths = [
                Path('config/config.yaml'),
                Path('config.yaml'),
                Path.home() / '.photo_stats_config.yaml',
                Path(__file__).parent / 'config' / 'config.yaml'
            ]

            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break

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

    def _handle_missing_config(self):
        """Handle missing configuration file by offering to create from template."""
        # Look for template file
        template_paths = [
            Path('config/template-config.yaml'),
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

    def scan_folder(self):
        """Scan the folder and collect file statistics."""
        print(f"Scanning folder: {self.folder_path}")

        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {self.folder_path}")

        start_time = datetime.now()

        # Collect all files
        all_files = {}
        for file_path in self.folder_path.rglob('*'):
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

    def generate_html_report(self, output_path='photo_stats_report.html'):
        """Generate an HTML report with statistics and charts."""
        print(f"Generating HTML report: {output_path}")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo Statistics Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}

        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }}

        .meta-info {{
            color: #7f8c8d;
            margin-bottom: 30px;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 5px;
        }}

        .meta-info p {{
            margin: 5px 0;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .stat-card.green {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}

        .stat-card.blue {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}

        .stat-card.orange {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}

        .stat-card h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
        }}

        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }}

        th {{
            background: #3498db;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}

        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}

        .file-list {{
            max-height: 400px;
            overflow-y: auto;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}

        .file-list div {{
            padding: 5px 0;
            border-bottom: 1px solid #dee2e6;
        }}

        .file-list div:last-child {{
            border-bottom: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Photo Statistics Report</h1>

        <div class="meta-info">
            <p><strong>Folder:</strong> {self.stats['folder_path']}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Scan Duration:</strong> {self.stats['scan_time']:.2f} seconds</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Files</h3>
                <div class="value">{self.stats['total_files']}</div>
            </div>
            <div class="stat-card green">
                <h3>Total Size</h3>
                <div class="value">{self._format_size(self.stats['total_size'])}</div>
            </div>
            <div class="stat-card blue">
                <h3>Paired Files</h3>
                <div class="value">{len(self.stats['paired_files'])}</div>
            </div>
            <div class="stat-card orange">
                <h3>Orphaned Files</h3>
                <div class="value">{len(self.stats['orphaned_images']) + len(self.stats['orphaned_xmp'])}</div>
            </div>
        </div>

        <h2>📊 File Type Distribution</h2>
        <div class="chart-container">
            <canvas id="fileCountChart"></canvas>
        </div>

        <h2>💾 Storage Distribution</h2>
        <div class="chart-container">
            <canvas id="fileSizeChart"></canvas>
        </div>

        <h2>📁 File Type Details</h2>
        <table>
            <thead>
                <tr>
                    <th>File Type</th>
                    <th>Count</th>
                    <th>Total Size</th>
                    <th>Average Size</th>
                </tr>
            </thead>
            <tbody>
                {self._generate_file_type_rows()}
            </tbody>
        </table>

        {self._generate_pairing_section()}

        {self._generate_xmp_metadata_section()}
    </div>

    <script>
        // File Count Chart
        const fileCountCtx = document.getElementById('fileCountChart').getContext('2d');
        new Chart(fileCountCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(list(self.stats['file_counts'].keys()))},
                datasets: [{{
                    label: 'File Count',
                    data: {json.dumps(list(self.stats['file_counts'].values()))},
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20,
                            font: {{
                                size: 14
                            }}
                        }}
                    }},
                    title: {{
                        display: true,
                        text: 'Number of Files by Type',
                        font: {{
                            size: 16
                        }}
                    }}
                }}
            }}
        }});

        // File Size Chart
        const fileSizeCtx = document.getElementById('fileSizeChart').getContext('2d');
        const fileSizeData = {json.dumps({ext: sum(sizes) for ext, sizes in self.stats['file_sizes'].items()})};
        new Chart(fileSizeCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(list(self.stats['file_sizes'].keys()))},
                datasets: [{{
                    label: 'Total Size (MB)',
                    data: Object.values(fileSizeData).map(v => (v / 1024 / 1024).toFixed(2)),
                    backgroundColor: 'rgba(52, 152, 219, 0.8)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Storage Usage by File Type',
                        font: {{
                            size: 16
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Size (MB)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        output_file = Path(output_path)
        output_file.write_text(html_content, encoding='utf-8')
        print(f"Report generated: {output_file.resolve()}")
        return output_file

    def _format_size(self, size_bytes):
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _generate_file_type_rows(self):
        """Generate table rows for file type details."""
        rows = []
        for ext, count in sorted(self.stats['file_counts'].items()):
            sizes = self.stats['file_sizes'][ext]
            total_size = sum(sizes)
            avg_size = total_size / len(sizes) if sizes else 0

            rows.append(f"""
                <tr>
                    <td><strong>{ext.upper()}</strong></td>
                    <td>{count}</td>
                    <td>{self._format_size(total_size)}</td>
                    <td>{self._format_size(avg_size)}</td>
                </tr>
            """)

        return '\n'.join(rows)

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

    def _generate_xmp_metadata_section(self):
        """Generate HTML section for XMP metadata analysis."""
        if not self.stats['xmp_metadata']:
            return '<h2>📝 XMP Metadata</h2><p>No XMP metadata found or could not be parsed.</p>'

        # Collect all metadata keys
        all_keys = set()
        for metadata in self.stats['xmp_metadata']:
            all_keys.update(metadata.keys())

        all_keys.discard('file')

        section = f'''
        <h2>📝 XMP Metadata Analysis</h2>
        <p>Analyzed {len(self.stats['xmp_metadata'])} XMP files. Found {len(all_keys)} unique metadata fields.</p>

        <h3>Common Metadata Fields</h3>
        <table>
            <thead>
                <tr>
                    <th>Field Name</th>
                    <th>Occurrences</th>
                    <th>Sample Value</th>
                </tr>
            </thead>
            <tbody>
        '''

        # Count occurrences of each field
        field_counts = defaultdict(list)
        for metadata in self.stats['xmp_metadata']:
            for key, value in metadata.items():
                if key != 'file':
                    field_counts[key].append(value)

        # Sort by occurrence count
        sorted_fields = sorted(field_counts.items(), key=lambda x: len(x[1]), reverse=True)

        for field, values in sorted_fields[:20]:  # Show top 20 fields
            sample_value = values[0] if values else ''
            if len(sample_value) > 50:
                sample_value = sample_value[:47] + '...'

            section += f'''
                <tr>
                    <td><code>{field}</code></td>
                    <td>{len(values)}</td>
                    <td>{sample_value}</td>
                </tr>
            '''

        section += '''
            </tbody>
        </table>
        '''

        return section


def main():
    """Main entry point for the photo statistics tool."""
    if len(sys.argv) < 2:
        print("Usage: python photo_stats.py <folder_path> [output_report.html] [config_file.yaml]")
        print("\nExample: python photo_stats.py /path/to/photos report.html")
        print("         python photo_stats.py /path/to/photos report.html config/config.yaml")
        print("\nIf no config file is specified, the tool will look for:")
        print("  - config/config.yaml (in current directory)")
        print("  - config.yaml (in current directory)")
        print("  - ~/.photo_stats_config.yaml (in home directory)")
        print("  - config/config.yaml (in script directory)")
        print("\nTo create a configuration file, copy config/template-config.yaml to config/config.yaml")
        sys.exit(1)

    folder_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'photo_stats_report.html'
    config_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        stats_tool = PhotoStats(folder_path, config_path)
        stats_tool.scan_folder()
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
