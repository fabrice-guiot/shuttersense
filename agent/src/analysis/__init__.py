"""
Shared analysis modules for ShutterSense tools.

This package contains the canonical analysis logic for Photo Pairing,
PhotoStats, and Pipeline Validation. These modules work with FileInfo
objects to enable unified processing across local and remote collections.

Architecture:
    Local:  LocalAdapter → FileInfo → Shared Analyzer → Results
    Remote: S3/GCS/SMB → FileInfo → Shared Analyzer → Results

Modules:
    - photo_pairing_analyzer: build_imagegroups(), calculate_analytics()
    - photostats_analyzer: analyze_pairing(), calculate_stats()
    - pipeline_analyzer: run_pipeline_validation(), flatten_imagegroups_to_specific_images()
"""

from src.analysis.photo_pairing_analyzer import build_imagegroups, calculate_analytics
from src.analysis.photostats_analyzer import analyze_pairing, calculate_stats
from src.analysis.pipeline_analyzer import (
    run_pipeline_validation,
    flatten_imagegroups_to_specific_images,
    add_metadata_files,
)

__all__ = [
    # Photo Pairing
    "build_imagegroups",
    "calculate_analytics",
    # PhotoStats
    "analyze_pairing",
    "calculate_stats",
    # Pipeline Validation
    "run_pipeline_validation",
    "flatten_imagegroups_to_specific_images",
    "add_metadata_files",
]
