"""
Pipeline Validation analysis logic.

Extracted from pipeline_validation.py to enable reuse across local and remote collections.
Uses shared build_imagegroups() and existing pipeline_processor.py for validation.

Key Concepts:
    - SpecificImage: Individual image unit for validation (e.g., "AB3D0001-2")
    - Pipeline: Directed graph of workflow nodes (Capture → Process → File → Termination)
    - Validation: Matching actual files against expected files per pipeline path
"""

from typing import List, Dict, Any, Set, Optional, Callable
from dataclasses import dataclass, field

from src.remote.base import FileInfo
from src.analysis.photo_pairing_analyzer import build_imagegroups

# Import from repository root - will work when running from agent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.pipeline_processor import (
    SpecificImage,
    ValidationResult,
    ValidationStatus,
    PipelineConfig,
    validate_specific_image,
    generate_expected_files,
    enumerate_paths_with_pairing,
    enumerate_all_paths,
)


def flatten_imagegroups_to_specific_images(imagegroups: List[Dict[str, Any]]) -> List[SpecificImage]:
    """
    Flatten ImageGroups to individual SpecificImage objects.

    Each ImageGroup contains multiple separate_images (suffix-based).
    This function converts each separate_image into a SpecificImage object
    for independent validation.

    Args:
        imagegroups: List of ImageGroup dictionaries

    Returns:
        List of SpecificImage objects (one per separate_image)

    Example:
        >>> groups = [{'group_id': 'AB3D0001', 'camera_id': 'AB3D', 'counter': '0001',
        ...            'separate_images': {'': {'files': ['AB3D0001.dng'], 'properties': []}}}]
        >>> images = flatten_imagegroups_to_specific_images(groups)
        >>> len(images)
        1
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

            # Extract properties from image_data, not from suffix
            # Properties are processing methods like "HDR", "BW"
            properties = list(image_data.get('properties', []))

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


def add_metadata_files(
    specific_images: List[SpecificImage],
    all_files: List[FileInfo],
    metadata_extensions: Set[str]
) -> None:
    """
    Add metadata files (e.g., .xmp) to SpecificImage files.

    Metadata files are not included in photo_extensions, so they need
    to be added separately after building ImageGroups.

    Args:
        specific_images: List of SpecificImage objects to augment
        all_files: All files including metadata files
        metadata_extensions: Set of metadata extensions (e.g., {'.xmp'})

    Side effects:
        Modifies specific_images in-place by adding metadata files
    """
    # Normalize extensions
    metadata_exts = {ext.lower() for ext in metadata_extensions}

    # Build lookup from base_filename to SpecificImage
    image_lookup = {si.base_filename: si for si in specific_images}

    for file_info in all_files:
        if file_info.extension in metadata_exts:
            # Metadata file - find matching SpecificImage by stem
            base = file_info.stem
            if base in image_lookup:
                image_lookup[base].files.append(file_info.path)
                # Keep files sorted
                image_lookup[base].files.sort()


def _determine_image_path(
    specific_image: SpecificImage,
    validation_result: ValidationResult,
    paths_by_term: Dict[str, List[tuple]],
    path_cache: Dict[tuple, tuple],
) -> Optional[tuple]:
    """
    Determine which pipeline path an image followed based on validation results.

    Uses a cache keyed by (properties, suffix, termination_type) so that images
    with identical characteristics resolve to the same path without re-computing
    expected files (optimization — 99% of groups follow the same few paths).

    Args:
        specific_image: The validated SpecificImage
        validation_result: Full validation result with termination matches
        paths_by_term: Pre-enumerated paths grouped by termination type
        path_cache: Cache mapping (properties, suffix, term_type) → path node IDs

    Returns:
        Tuple of node IDs for the matched path, or None if no match
    """
    if not validation_result.termination_matches:
        return None

    # Find best termination match: best status, then most expected files
    best_match = min(
        validation_result.termination_matches,
        key=lambda m: (m.status, -len(m.expected_files)),
    )

    term_type = best_match.termination_type
    term_paths = paths_by_term.get(term_type, [])

    if not term_paths:
        return None

    # Single path for this termination — no ambiguity
    if len(term_paths) == 1:
        return term_paths[0][0]  # node_ids tuple

    # Multiple paths — check cache first (include expected files signature)
    base = f"{specific_image.camera_id}{specific_image.counter}"
    match_expected_set = {f.lower() for f in best_match.expected_files}
    cache_key = (
        tuple(sorted(specific_image.properties)),
        specific_image.suffix,
        term_type,
        tuple(sorted(match_expected_set)),
    )
    if cache_key in path_cache:
        return path_cache[cache_key]

    for node_ids, path_data in term_paths:
        path_expected = generate_expected_files(path_data, base, specific_image.suffix)
        path_expected_set = {f.lower() for f in path_expected}
        if path_expected_set == match_expected_set:
            path_cache[cache_key] = node_ids
            return node_ids

    # Fallback: use first path for this termination
    result = term_paths[0][0]
    path_cache[cache_key] = result
    return result


def run_pipeline_validation(
    files: List[FileInfo],
    pipeline_config: PipelineConfig,
    photo_extensions: Set[str],
    metadata_extensions: Set[str],
    progress_callback: Optional[Callable[[int, int, int], None]] = None
) -> Dict[str, Any]:
    """
    Run full pipeline validation on a file list.

    This is the unified entry point for both local and remote collections.

    Args:
        files: List of FileInfo objects
        pipeline_config: PipelineConfig instance (already parsed)
        photo_extensions: Set of photo extensions
        metadata_extensions: Set of metadata extensions
        progress_callback: Optional callback(current, total, issues) for progress reporting

    Returns:
        Dict with validation results including status counts

    Example:
        >>> # files = adapter.list_files_with_metadata("/path")
        >>> # pipeline = load_pipeline_config(config)
        >>> # results = run_pipeline_validation(files, pipeline, {'.dng'}, {'.xmp'})
        >>> # results['status_counts']['consistent']
    """
    # Normalize extensions
    photo_exts = {ext.lower() for ext in photo_extensions}
    metadata_exts = {ext.lower() for ext in metadata_extensions}

    # Step 1: Filter to photo files and build ImageGroups
    photo_files = [f for f in files if f.extension in photo_exts]
    result = build_imagegroups(photo_files)
    imagegroups = result['imagegroups']
    invalid_files = result['invalid_files']

    # Step 2: Flatten to SpecificImages
    specific_images = flatten_imagegroups_to_specific_images(imagegroups)

    # Step 3: Add metadata files
    add_metadata_files(specific_images, files, metadata_exts)

    # Step 4: Pre-enumerate pipeline paths for path_stats tracking
    try:
        all_paths = enumerate_paths_with_pairing(pipeline_config)
    except NotImplementedError:
        all_paths = enumerate_all_paths(pipeline_config)

    # Build lookup: termination_type → list of (path_node_ids, path_data)
    paths_by_term: Dict[str, List[tuple]] = {}
    for path in all_paths:
        if not path:
            continue
        last_node = path[-1]
        if last_node.get('type') != 'Termination' or last_node.get('truncated', False):
            continue
        term_type = last_node.get('term_type', 'Unknown')
        node_ids = tuple(n['id'] for n in path if n.get('id'))
        if term_type not in paths_by_term:
            paths_by_term[term_type] = []
        paths_by_term[term_type].append((node_ids, path))

    # Path stats tracking
    path_counts: Dict[tuple, int] = {}
    path_cache: Dict[tuple, tuple] = {}

    # Step 5: Run validation with progress reporting
    validation_results = []
    total_images = len(specific_images)

    # Step 6: Aggregate results by overall status (as we go)
    status_counts = {
        'consistent': 0,
        'consistent_with_warning': 0,
        'partial': 0,
        'inconsistent': 0,
    }

    # Step 7: Collect per-termination statistics (for Trends tab)
    termination_stats: Dict[str, Dict[str, int]] = {}

    # Validate each image with progress reporting
    for idx, specific_image in enumerate(specific_images):
        vr = validate_specific_image(specific_image, pipeline_config, show_progress=False)
        validation_results.append(vr)
        # Count overall status
        if vr.overall_status == ValidationStatus.CONSISTENT:
            status_counts['consistent'] += 1
        elif vr.overall_status == ValidationStatus.CONSISTENT_WITH_WARNING:
            status_counts['consistent_with_warning'] += 1
        elif vr.overall_status == ValidationStatus.PARTIAL:
            status_counts['partial'] += 1
        elif vr.overall_status == ValidationStatus.INCONSISTENT:
            status_counts['inconsistent'] += 1

        # Count per-termination status
        for term_match in vr.termination_matches:
            term_type = term_match.termination_type
            match_status = term_match.status

            if term_type not in termination_stats:
                termination_stats[term_type] = {
                    "CONSISTENT": 0,
                    "CONSISTENT_WITH_WARNING": 0,
                    "PARTIAL": 0,
                    "INCONSISTENT": 0,
                }

            if match_status == ValidationStatus.CONSISTENT:
                termination_stats[term_type]["CONSISTENT"] += 1
            elif match_status == ValidationStatus.CONSISTENT_WITH_WARNING:
                termination_stats[term_type]["CONSISTENT_WITH_WARNING"] += 1
            elif match_status == ValidationStatus.PARTIAL:
                termination_stats[term_type]["PARTIAL"] += 1
            elif match_status == ValidationStatus.INCONSISTENT:
                termination_stats[term_type]["INCONSISTENT"] += 1

        # Track path for path_stats
        matched_path = _determine_image_path(
            specific_image, vr, paths_by_term, path_cache
        )
        if matched_path:
            path_counts[matched_path] = path_counts.get(matched_path, 0) + 1

        # Report progress (every 2% or every 50 images, like backend)
        if progress_callback:
            issues_so_far = status_counts['partial'] + status_counts['inconsistent']
            progress_callback(idx + 1, total_images, issues_so_far)

    # Build per-termination consistency counts for frontend (merges CONSISTENT_WITH_WARNING into CONSISTENT)
    by_termination = {}
    for term_type, counts in termination_stats.items():
        by_termination[term_type] = {
            "CONSISTENT": counts.get("CONSISTENT", 0) + counts.get("CONSISTENT_WITH_WARNING", 0),
            "PARTIAL": counts.get("PARTIAL", 0),
            "INCONSISTENT": counts.get("INCONSISTENT", 0)
        }

    # Build path_stats output
    path_stats = [
        {"path": list(path_ids), "image_count": count}
        for path_ids, count in path_counts.items()
    ]

    return {
        'total_images': len(specific_images),
        'total_groups': len(imagegroups),
        'status_counts': status_counts,
        'by_termination': by_termination,
        'validation_results': validation_results,
        'invalid_files_count': len(invalid_files),
        'invalid_files': invalid_files,
        'path_stats': path_stats,
    }
