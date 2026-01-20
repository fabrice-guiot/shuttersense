"""
PhotoStats analysis logic.

Extracted from photo_stats.py to enable reuse across local and remote collections.
Works with FileInfo objects instead of Path objects.

Key Concepts:
    - File Stats: Count and size by extension
    - File Pairing: Images with their XMP sidecars
    - Orphaned Files: Images without sidecars (require_sidecar), sidecars without images
"""

from collections import defaultdict
from typing import List, Dict, Any, Set

from src.remote.base import FileInfo


def calculate_stats(
    files: List[FileInfo],
    photo_extensions: Set[str],
    metadata_extensions: Set[str]
) -> Dict[str, Any]:
    """
    Calculate file counts and sizes by extension.

    Args:
        files: List of FileInfo objects
        photo_extensions: Set of photo extensions (e.g., {'.dng', '.cr3'})
        metadata_extensions: Set of metadata extensions (e.g., {'.xmp'})

    Returns:
        Dict with file_counts, file_sizes, total_files, total_size

    Example:
        >>> files = [FileInfo("test.dng", 1000000), FileInfo("test.xmp", 5000)]
        >>> stats = calculate_stats(files, {'.dng'}, {'.xmp'})
        >>> stats['total_files']
        2
    """
    # Normalize extensions to lowercase
    photo_exts = {ext.lower() for ext in photo_extensions}
    metadata_exts = {ext.lower() for ext in metadata_extensions}
    all_extensions = photo_exts | metadata_exts

    file_counts = defaultdict(int)
    file_sizes = defaultdict(list)
    total_size = 0
    total_files = 0

    for f in files:
        if f.extension in all_extensions:
            file_counts[f.extension] += 1
            file_sizes[f.extension].append(f.size)
            total_size += f.size
            total_files += 1

    return {
        'file_counts': dict(file_counts),
        'file_sizes': dict(file_sizes),
        'total_files': total_files,
        'total_size': total_size
    }


def analyze_pairing(
    files: List[FileInfo],
    photo_extensions: Set[str],
    metadata_extensions: Set[str],
    require_sidecar: Set[str]
) -> Dict[str, Any]:
    """
    Analyze file pairing (images with XMP sidecars).

    Args:
        files: List of FileInfo objects
        photo_extensions: Set of photo extensions
        metadata_extensions: Set of metadata extensions (e.g., {'.xmp'})
        require_sidecar: Set of extensions that require sidecars (e.g., {'.cr3'})

    Returns:
        Dict with paired_files, orphaned_images, orphaned_xmp

    Example:
        >>> files = [FileInfo("test.cr3", 1000), FileInfo("test.xmp", 100)]
        >>> result = analyze_pairing(files, {'.cr3'}, {'.xmp'}, {'.cr3'})
        >>> len(result['paired_files'])
        1
    """
    # Normalize extensions
    photo_exts = {ext.lower() for ext in photo_extensions}
    metadata_exts = {ext.lower() for ext in metadata_extensions}
    require_sidecar_exts = {ext.lower() for ext in require_sidecar}

    # Group files by stem (base name without extension)
    file_groups = defaultdict(list)
    for file_info in files:
        file_groups[file_info.stem].append(file_info)

    paired_files = []
    orphaned_images = []
    orphaned_xmp = []

    for base_name, group_files in file_groups.items():
        extensions = {f.extension for f in group_files}
        has_image = bool(extensions & photo_exts)
        has_xmp = bool(extensions & metadata_exts)
        has_image_requiring_sidecar = bool(
            {f.extension for f in group_files if f.extension in photo_exts} & require_sidecar_exts
        )

        if has_image and has_xmp:
            paired_files.append({
                'base_name': base_name,
                'files': [f.path for f in group_files]
            })
        elif has_image and not has_xmp and has_image_requiring_sidecar:
            orphaned_images.extend([
                f.path for f in group_files if f.extension in require_sidecar_exts
            ])
        elif has_xmp and not has_image:
            orphaned_xmp.extend([
                f.path for f in group_files if f.extension in metadata_exts
            ])

    return {
        'paired_files': paired_files,
        'orphaned_images': orphaned_images,
        'orphaned_xmp': orphaned_xmp
    }
