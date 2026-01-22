"""
Unit tests for pipeline_analyzer module.

Tests the Pipeline Validation analysis logic extracted for unified
local/remote processing.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # For utils

from src.remote.base import FileInfo
from src.analysis.pipeline_analyzer import (
    flatten_imagegroups_to_specific_images,
    add_metadata_files,
)
from utils.pipeline_processor import SpecificImage


class TestFlattenImagegroupsToSpecificImages:
    """Tests for flatten_imagegroups_to_specific_images function."""

    def test_empty_imagegroups(self):
        """Test with empty imagegroups."""
        result = flatten_imagegroups_to_specific_images([])
        assert result == []

    def test_single_group_single_image(self):
        """Test single group with single image."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.dng'], 'properties': []}
                }
            }
        ]

        result = flatten_imagegroups_to_specific_images(imagegroups)

        assert len(result) == 1
        assert isinstance(result[0], SpecificImage)
        assert result[0].base_filename == "AB3D0001"
        assert result[0].camera_id == "AB3D"
        assert result[0].counter == "0001"
        assert result[0].suffix == ""

    def test_group_with_multiple_separate_images(self):
        """Test group with multiple separate images."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.dng'], 'properties': []},
                    '2': {'files': ['AB3D0001-2.dng'], 'properties': []},
                }
            }
        ]

        result = flatten_imagegroups_to_specific_images(imagegroups)

        assert len(result) == 2
        base_filenames = [si.base_filename for si in result]
        assert "AB3D0001" in base_filenames
        assert "AB3D0001-2" in base_filenames

    def test_separate_image_with_properties(self):
        """Test that properties are captured."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.dng', 'AB3D0001-HDR.dng'], 'properties': ['HDR']}
                }
            }
        ]

        result = flatten_imagegroups_to_specific_images(imagegroups)

        assert len(result) == 1
        assert result[0].properties == ['HDR']

    def test_files_are_sorted(self):
        """Test that files list is sorted."""
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['z.dng', 'a.dng', 'm.dng'], 'properties': []}
                }
            }
        ]

        result = flatten_imagegroups_to_specific_images(imagegroups)

        assert result[0].files == ['a.dng', 'm.dng', 'z.dng']


class TestAddMetadataFiles:
    """Tests for add_metadata_files function."""

    def test_no_metadata_files(self):
        """Test when no metadata files exist."""
        specific_images = [
            SpecificImage(
                base_filename="AB3D0001",
                camera_id="AB3D",
                counter="0001",
                suffix="",
                properties=[],
                files=["AB3D0001.dng"]
            )
        ]
        all_files = [
            FileInfo(path="AB3D0001.dng", size=1000),
        ]

        add_metadata_files(specific_images, all_files, {'.xmp'})

        # No metadata added
        assert specific_images[0].files == ["AB3D0001.dng"]

    def test_matching_metadata_file(self):
        """Test metadata file is added to matching image."""
        specific_images = [
            SpecificImage(
                base_filename="AB3D0001",
                camera_id="AB3D",
                counter="0001",
                suffix="",
                properties=[],
                files=["AB3D0001.dng"]
            )
        ]
        all_files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="AB3D0001.xmp", size=100),
        ]

        add_metadata_files(specific_images, all_files, {'.xmp'})

        assert len(specific_images[0].files) == 2
        assert "AB3D0001.xmp" in specific_images[0].files

    def test_unmatched_metadata_file_ignored(self):
        """Test metadata file without matching image is ignored."""
        specific_images = [
            SpecificImage(
                base_filename="AB3D0001",
                camera_id="AB3D",
                counter="0001",
                suffix="",
                properties=[],
                files=["AB3D0001.dng"]
            )
        ]
        all_files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="OTHER0001.xmp", size=100),  # No matching image
        ]

        add_metadata_files(specific_images, all_files, {'.xmp'})

        # Only original file
        assert specific_images[0].files == ["AB3D0001.dng"]

    def test_case_insensitive_extension(self):
        """Test metadata extension matching is case-insensitive."""
        specific_images = [
            SpecificImage(
                base_filename="AB3D0001",
                camera_id="AB3D",
                counter="0001",
                suffix="",
                properties=[],
                files=["AB3D0001.dng"]
            )
        ]
        all_files = [
            FileInfo(path="AB3D0001.dng", size=1000),
            FileInfo(path="AB3D0001.XMP", size=100),
        ]

        add_metadata_files(specific_images, all_files, {'.xmp'})

        assert len(specific_images[0].files) == 2
