"""
Unit tests for photo_pairing_analyzer module.

Tests the core Photo Pairing analysis logic extracted for unified
local/remote processing.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.remote.base import FileInfo
from src.analysis.photo_pairing_analyzer import build_imagegroups, calculate_analytics


class TestBuildImagegroups:
    """Tests for build_imagegroups function."""

    def test_empty_file_list(self):
        """Test with empty file list."""
        result = build_imagegroups([])

        assert result['imagegroups'] == []
        assert result['invalid_files'] == []

    def test_single_valid_file(self):
        """Test with single valid file."""
        files = [FileInfo(path="AB3D0001.dng", size=1000)]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 1
        assert result['imagegroups'][0]['group_id'] == "AB3D0001"
        assert result['imagegroups'][0]['camera_id'] == "AB3D"
        assert result['imagegroups'][0]['counter'] == "0001"
        assert len(result['invalid_files']) == 0

    def test_group_with_multiple_files(self):
        """Test grouping multiple files with same base."""
        files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="AB3D0001.cr3", size=2000),
            FileInfo(path="AB3D0001.tiff", size=3000),
        ]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 1
        group = result['imagegroups'][0]
        assert group['group_id'] == "AB3D0001"
        assert len(group['separate_images']['']['files']) == 3

    def test_separate_images_numeric_suffix(self):
        """Test that numeric suffix creates separate image."""
        files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="AB3D0001-2.dng", size=1000),
            FileInfo(path="AB3D0001-3.dng", size=1000),
        ]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 1
        group = result['imagegroups'][0]
        assert '' in group['separate_images']  # Base image
        assert '2' in group['separate_images']
        assert '3' in group['separate_images']

    def test_processing_method_suffix(self):
        """Test that non-numeric suffix is processing method."""
        files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="AB3D0001-HDR.dng", size=1000),
        ]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 1
        group = result['imagegroups'][0]
        # Both files belong to base separate image
        assert len(group['separate_images']) == 1
        assert '' in group['separate_images']
        # HDR is a property
        assert 'HDR' in group['separate_images']['']['properties']

    def test_multiple_groups(self):
        """Test multiple distinct groups."""
        files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="AB3D0002.dng", size=1000),
            FileInfo(path="XY1Z0001.dng", size=1000),
        ]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 3
        group_ids = [g['group_id'] for g in result['imagegroups']]
        assert "AB3D0001" in group_ids
        assert "AB3D0002" in group_ids
        assert "XY1Z0001" in group_ids

    def test_invalid_filename(self):
        """Test invalid filename is captured."""
        files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="invalid_file.dng", size=1000),
        ]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 1
        assert len(result['invalid_files']) == 1
        assert result['invalid_files'][0]['filename'] == "invalid_file.dng"

    def test_subdirectory_files(self):
        """Test files in subdirectories maintain paths."""
        files = [
            FileInfo(path="2025/AB3D0001.dng", size=1000),
            FileInfo(path="2025/AB3D0001.xmp", size=100),
        ]

        result = build_imagegroups(files)

        assert len(result['imagegroups']) == 1
        files_in_group = result['imagegroups'][0]['separate_images']['']['files']
        assert any("2025/AB3D0001" in f for f in files_in_group)


class TestCalculateAnalytics:
    """Tests for calculate_analytics function."""

    def test_empty_imagegroups(self):
        """Test with empty imagegroups."""
        analytics = calculate_analytics([], {})

        assert analytics['image_count'] == 0
        assert analytics['group_count'] == 0
        assert analytics['camera_usage'] == {}
        assert analytics['method_usage'] == {}

    def test_camera_usage_counting(self):
        """Test camera usage is counted correctly."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {'': {'files': ['AB3D0001.dng'], 'properties': []}}
            },
            {
                'group_id': 'AB3D0002',
                'camera_id': 'AB3D',
                'counter': '0002',
                'separate_images': {'': {'files': ['AB3D0002.dng'], 'properties': []}}
            },
        ]

        analytics = calculate_analytics(imagegroups, {})

        # Without camera mappings, camera_id is used as key
        assert analytics['camera_usage']['AB3D'] == 2

    def test_camera_name_resolution(self):
        """Test camera name is resolved from config."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {'': {'files': ['AB3D0001.dng'], 'properties': []}}
            },
        ]
        config = {
            'camera_mappings': {
                'AB3D': [{'name': 'Canon EOS R5', 'serial_number': '12345'}]
            }
        }

        analytics = calculate_analytics(imagegroups, config)

        assert 'Canon EOS R5' in analytics['camera_usage']
        assert analytics['camera_usage']['Canon EOS R5'] == 1

    def test_method_usage_counting(self):
        """Test processing method usage is counted."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.dng', 'AB3D0001-HDR.dng'], 'properties': ['HDR']}
                }
            },
        ]

        analytics = calculate_analytics(imagegroups, {})

        assert 'HDR' in analytics['method_usage']
        assert analytics['method_usage']['HDR'] == 1

    def test_method_description_resolution(self):
        """Test method description is resolved from config."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.dng'], 'properties': ['HDR']}
                }
            },
        ]
        config = {
            'processing_methods': {
                'HDR': 'High Dynamic Range'
            }
        }

        analytics = calculate_analytics(imagegroups, config)

        assert 'High Dynamic Range' in analytics['method_usage']

    def test_file_count(self):
        """Test file count calculation."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.dng', 'AB3D0001.cr3'], 'properties': []},
                    '2': {'files': ['AB3D0001-2.dng'], 'properties': []},
                }
            },
        ]

        analytics = calculate_analytics(imagegroups, {})

        assert analytics['file_count'] == 3
        assert analytics['image_count'] == 2  # Two separate images
        assert analytics['group_count'] == 1
