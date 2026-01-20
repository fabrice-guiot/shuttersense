"""
Photo Pairing analysis logic.

Extracted from photo_pairing.py to enable reuse across local and remote collections.
Works with FileInfo objects instead of Path objects.

Key Concepts:
    - ImageGroup: Photos with same camera_id + counter (e.g., "AB3D0001")
    - Separate Image: Different captures within a group (suffixes "2", "3", etc.)
    - Processing Method: Edits applied to an image (suffixes "HDR", "BW", etc.)

Example:
    AB3D0001.dng      -> group "AB3D0001", separate_image "", no methods
    AB3D0001-2.dng    -> group "AB3D0001", separate_image "2", no methods
    AB3D0001-HDR.dng  -> group "AB3D0001", separate_image "", method "HDR"
"""

from collections import defaultdict
from typing import List, Dict, Any, Set

from src.remote.base import FileInfo

# Import from repository root - will work when running from agent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.filename_parser import FilenameParser


def build_imagegroups(files: List[FileInfo]) -> Dict[str, Any]:
    """
    Build ImageGroup structure from FileInfo list.

    This is the core Photo Pairing algorithm, extracted to work with
    both local and remote collections via the unified FileInfo interface.

    Args:
        files: List of FileInfo objects (already filtered to photo extensions)

    Returns:
        Dict with 'imagegroups' list and 'invalid_files' list

    Example:
        >>> files = [FileInfo("AB3D0001.dng", 1000), FileInfo("AB3D0001-HDR.dng", 1000)]
        >>> result = build_imagegroups(files)
        >>> len(result['imagegroups'])
        1
    """
    groups = defaultdict(lambda: {
        'group_id': '',
        'camera_id': '',
        'counter': '',
        'separate_images': defaultdict(lambda: {'files': [], 'properties': set()})
    })

    invalid_files = []

    for file_info in files:
        filename = file_info.name

        # Validate filename
        is_valid, error_reason = FilenameParser.validate_filename(filename)

        if not is_valid:
            invalid_files.append({
                'filename': filename,
                'path': file_info.path,
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
        # Key distinction:
        # - Separate image suffix: ALL NUMERIC (e.g., "2", "3") - different captures
        # - Processing method suffix: NOT numeric (e.g., "HDR", "BW") - edits applied
        separate_image_id = ''
        processing_methods = []

        for prop in parsed['properties']:
            prop_type = FilenameParser.detect_property_type(prop)
            if prop_type == 'separate_image':
                if separate_image_id == '':
                    separate_image_id = prop
                else:
                    processing_methods.append(prop)
            else:
                processing_methods.append(prop)

        # Add file to appropriate separate image
        groups[group_id]['separate_images'][separate_image_id]['files'].append(file_info.path)

        # Add processing methods
        for method in processing_methods:
            groups[group_id]['separate_images'][separate_image_id]['properties'].add(method)

    # Convert to final structure
    imagegroups = []
    for group_id, group_data in sorted(groups.items()):
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


def calculate_analytics(
    imagegroups: List[Dict],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate analytics from imagegroups.

    Args:
        imagegroups: List of ImageGroup dicts
        config: Config with camera_mappings and processing_methods

    Returns:
        Dict with camera_usage, method_usage, image_count, group_count, etc.

    Example:
        >>> imagegroups = [{'group_id': 'AB3D0001', 'camera_id': 'AB3D', ...}]
        >>> config = {'camera_mappings': {'AB3D': [{'name': 'Canon R5'}]}}
        >>> analytics = calculate_analytics(imagegroups, config)
        >>> analytics['group_count']
        1
    """
    camera_mappings = config.get('camera_mappings', {})
    processing_methods_config = config.get('processing_methods', {})

    def get_camera_name(cam_id: str) -> str:
        """Resolve camera ID to human-readable name."""
        raw_info = camera_mappings.get(cam_id)
        if raw_info:
            info = raw_info
            # Unwrap lists until we get a dict (handles [dict], [[dict]], etc.)
            while isinstance(info, list) and info:
                info = info[0]
            if isinstance(info, dict) and info.get('name'):
                return info['name']
        return cam_id

    def get_method_desc(method: str) -> str:
        """Resolve method ID to description."""
        return processing_methods_config.get(method, method)

    # Count images per camera (using resolved names)
    camera_usage = defaultdict(int)
    method_usage = defaultdict(int)
    total_images = 0
    total_files = 0

    for group in imagegroups:
        camera_name = get_camera_name(group['camera_id'])
        num_images = len(group['separate_images'])
        camera_usage[camera_name] += num_images
        total_images += num_images

        # Count files and method usage
        for sep_img in group['separate_images'].values():
            total_files += len(sep_img.get('files', []))
            for method in sep_img.get('properties', []):
                method_desc = get_method_desc(method)
                method_usage[method_desc] += 1

    return {
        'camera_usage': dict(camera_usage),
        'method_usage': dict(method_usage),
        'image_count': total_images,
        'group_count': len(imagegroups),
        'file_count': total_files,
    }
