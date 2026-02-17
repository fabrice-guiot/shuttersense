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

import logging
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Set

from src.remote.base import FileInfo

# Import from repository root - will work when running from agent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.filename_parser import FilenameParser

logger = logging.getLogger(__name__)


def build_imagegroups(
    files: List[FileInfo],
    filename_regex: Optional[str] = None,
    camera_id_group: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build ImageGroup structure from FileInfo list.

    This is the core Photo Pairing algorithm, extracted to work with
    both local and remote collections via the unified FileInfo interface.

    When filename_regex is provided (from Pipeline Capture node), uses
    regex-based parsing. Otherwise falls back to FilenameParser (FR-009).

    Args:
        files: List of FileInfo objects (already filtered to photo extensions)
        filename_regex: Optional regex pattern with capture groups for
            camera_id and counter (Issue #217, FR-009)
        camera_id_group: Which capture group is the camera ID (1 or 2).
            The other group is the counter. Defaults to 1.

    Returns:
        Dict with 'imagegroups' list and 'invalid_files' list

    Example:
        >>> files = [FileInfo("AB3D0001.dng", 1000), FileInfo("AB3D0001-HDR.dng", 1000)]
        >>> result = build_imagegroups(files)
        >>> len(result['imagegroups'])
        1
    """
    # Compile regex if provided
    compiled_regex = None
    if filename_regex:
        try:
            compiled_regex = re.compile(filename_regex)
        except re.error as e:
            logger.warning(
                "Invalid filename_regex '%s', falling back to FilenameParser: %s",
                filename_regex, e,
            )

    if camera_id_group is None:
        camera_id_group = 1

    groups = defaultdict(lambda: {
        'group_id': '',
        'camera_id': '',
        'counter': '',
        'separate_images': defaultdict(lambda: {'files': [], 'properties': set()})
    })

    invalid_files = []

    for file_info in files:
        filename = file_info.name
        stem = file_info.stem

        if compiled_regex is not None:
            # Pipeline regex-based parsing
            parsed = _parse_with_regex(
                filename, stem, compiled_regex, camera_id_group
            )
        else:
            # Legacy FilenameParser-based parsing
            parsed = _parse_with_filename_parser(filename)

        if parsed is None:
            invalid_files.append({
                'filename': filename,
                'path': file_info.path,
                'reason': 'Filename does not match expected pattern',
            })
            continue

        group_id = parsed['camera_id'] + parsed['counter']

        # Initialize group if first file
        if not groups[group_id]['group_id']:
            groups[group_id]['group_id'] = group_id
            groups[group_id]['camera_id'] = parsed['camera_id']
            groups[group_id]['counter'] = parsed['counter']

        # Determine which separate image this file belongs to
        # Key distinction (FR-012):
        # - Separate image suffix: ALL NUMERIC (e.g., "2", "3") - different captures
        # - Processing method suffix: NOT numeric (e.g., "HDR", "BW") - edits applied
        separate_image_id = ''
        processing_methods = []

        for prop in parsed['properties']:
            if prop.isdigit():
                # FR-012: All-numeric suffix is always a separate image indicator
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


def _parse_with_regex(
    filename: str,
    stem: str,
    compiled_regex: re.Pattern,
    camera_id_group: int,
) -> Optional[Dict[str, Any]]:
    """
    Parse a filename using a Pipeline Capture node's regex.

    The regex must have at least 2 capture groups (camera_id and counter).
    After the regex match, the remainder of the stem is split on '-' to
    extract properties (processing suffixes and separate image indicators).

    Args:
        filename: Full filename (with extension)
        stem: Filename without extension
        compiled_regex: Compiled regex pattern
        camera_id_group: Which group (1 or 2) is the camera ID

    Returns:
        Parsed dict with camera_id, counter, properties, or None if no match
    """
    match = compiled_regex.match(stem)
    if not match:
        return None

    groups = match.groups()
    if len(groups) < 2:
        return None

    counter_group = 2 if camera_id_group == 1 else 1
    camera_id = groups[camera_id_group - 1]
    counter = groups[counter_group - 1]

    # Extract properties from the remainder after the match
    remainder = stem[match.end():]
    properties = []
    if remainder:
        # Strip leading delimiter (remainder typically starts with '-')
        stripped = remainder.lstrip('-')
        if not stripped:
            # Remainder is only delimiters (trailing dash) — malformed
            return None
        parts = stripped.split('-')
        if any(p == '' for p in parts):
            # Double-dash or trailing dash produced empty property — malformed
            return None
        properties = parts

    return {
        'camera_id': camera_id,
        'counter': counter,
        'properties': properties,
    }


def _parse_with_filename_parser(filename: str) -> Optional[Dict[str, Any]]:
    """
    Parse a filename using the legacy FilenameParser.

    Args:
        filename: Full filename (with extension)

    Returns:
        Parsed dict with camera_id, counter, properties, or None if invalid
    """
    is_valid, error_reason = FilenameParser.validate_filename(filename)
    if not is_valid:
        return None

    parsed = FilenameParser.parse_filename(filename)
    return {
        'camera_id': parsed['camera_id'],
        'counter': parsed['counter'],
        'properties': parsed['properties'],
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
