"""
Unit tests for photostats_analyzer module.

Tests the PhotoStats analysis logic extracted for unified
local/remote processing.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.remote.base import FileInfo
from src.analysis.photostats_analyzer import calculate_stats, analyze_pairing


class TestCalculateStats:
    """Tests for calculate_stats function."""

    def test_empty_file_list(self):
        """Test with empty file list."""
        result = calculate_stats([], {'.dng'}, {'.xmp'})

        assert result['total_files'] == 0
        assert result['total_size'] == 0
        assert result['file_counts'] == {}
        assert result['file_sizes'] == {}

    def test_single_photo_file(self):
        """Test stats for single photo file."""
        files = [FileInfo(path="photo.dng", size=1000)]

        result = calculate_stats(files, {'.dng'}, {'.xmp'})

        assert result['total_files'] == 1
        assert result['total_size'] == 1000
        assert result['file_counts']['.dng'] == 1

    def test_multiple_extensions(self):
        """Test stats for multiple file extensions."""
        files = [
            FileInfo(path="photo1.dng", size=1000),
            FileInfo(path="photo2.cr3", size=2000),
            FileInfo(path="photo3.dng", size=1500),
        ]

        result = calculate_stats(files, {'.dng', '.cr3'}, {'.xmp'})

        assert result['total_files'] == 3
        assert result['total_size'] == 4500
        assert result['file_counts']['.dng'] == 2
        assert result['file_counts']['.cr3'] == 1

    def test_case_insensitive_extensions(self):
        """Test extensions are matched case-insensitively."""
        files = [
            FileInfo(path="photo.DNG", size=1000),
            FileInfo(path="photo2.dng", size=1000),
        ]

        result = calculate_stats(files, {'.dng'}, {'.xmp'})

        assert result['total_files'] == 2
        assert result['file_counts']['.dng'] == 2

    def test_excludes_non_matching_extensions(self):
        """Test that non-matching extensions are excluded."""
        files = [
            FileInfo(path="photo.dng", size=1000),
            FileInfo(path="document.pdf", size=500),
            FileInfo(path="readme.txt", size=100),
        ]

        result = calculate_stats(files, {'.dng'}, {'.xmp'})

        assert result['total_files'] == 1
        assert result['total_size'] == 1000

    def test_file_sizes_tracking(self):
        """Test file sizes are tracked per extension."""
        files = [
            FileInfo(path="photo1.dng", size=1000),
            FileInfo(path="photo2.dng", size=2000),
        ]

        result = calculate_stats(files, {'.dng'}, {'.xmp'})

        assert result['file_sizes']['.dng'] == [1000, 2000]


class TestAnalyzePairing:
    """Tests for analyze_pairing function."""

    def test_empty_file_list(self):
        """Test with empty file list."""
        result = analyze_pairing([], {'.dng'}, {'.xmp'}, {'.cr3'})

        assert result['paired_files'] == []
        assert result['orphaned_images'] == []
        assert result['orphaned_xmp'] == []

    def test_paired_files(self):
        """Test that image + xmp is paired."""
        files = [
            FileInfo(path="photo.dng", size=1000),
            FileInfo(path="photo.xmp", size=100),
        ]

        result = analyze_pairing(files, {'.dng'}, {'.xmp'}, set())

        assert len(result['paired_files']) == 1
        assert result['paired_files'][0]['base_name'] == "photo"
        assert len(result['orphaned_images']) == 0
        assert len(result['orphaned_xmp']) == 0

    def test_orphaned_image_requiring_sidecar(self):
        """Test that image requiring sidecar without xmp is orphaned."""
        files = [
            FileInfo(path="photo.cr3", size=1000),
        ]

        result = analyze_pairing(files, {'.cr3'}, {'.xmp'}, {'.cr3'})

        assert len(result['paired_files']) == 0
        assert len(result['orphaned_images']) == 1
        assert "photo.cr3" in result['orphaned_images']

    def test_image_not_requiring_sidecar(self):
        """Test that image not requiring sidecar is not orphaned."""
        files = [
            FileInfo(path="photo.jpg", size=1000),
        ]

        result = analyze_pairing(files, {'.jpg'}, {'.xmp'}, {'.cr3'})

        assert len(result['paired_files']) == 0
        assert len(result['orphaned_images']) == 0

    def test_orphaned_xmp(self):
        """Test that xmp without image is orphaned."""
        files = [
            FileInfo(path="photo.xmp", size=100),
        ]

        result = analyze_pairing(files, {'.dng'}, {'.xmp'}, set())

        assert len(result['paired_files']) == 0
        assert len(result['orphaned_xmp']) == 1
        assert "photo.xmp" in result['orphaned_xmp']

    def test_mixed_paired_and_orphaned(self):
        """Test mixed paired and orphaned files."""
        files = [
            FileInfo(path="paired.dng", size=1000),
            FileInfo(path="paired.xmp", size=100),
            FileInfo(path="orphan_image.cr3", size=2000),
            FileInfo(path="orphan_sidecar.xmp", size=50),
        ]

        result = analyze_pairing(files, {'.dng', '.cr3'}, {'.xmp'}, {'.cr3'})

        assert len(result['paired_files']) == 1
        assert result['paired_files'][0]['base_name'] == "paired"
        assert len(result['orphaned_images']) == 1
        assert "orphan_image.cr3" in result['orphaned_images']
        assert len(result['orphaned_xmp']) == 1
        assert "orphan_sidecar.xmp" in result['orphaned_xmp']

    def test_case_insensitive_extension_matching(self):
        """Test extension matching is case-insensitive."""
        files = [
            FileInfo(path="photo.DNG", size=1000),
            FileInfo(path="photo.XMP", size=100),
        ]

        result = analyze_pairing(files, {'.dng'}, {'.xmp'}, set())

        assert len(result['paired_files']) == 1
